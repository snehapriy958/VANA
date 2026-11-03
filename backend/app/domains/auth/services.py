import uuid
from typing import List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
import jwt

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.domains.audit.services import record_audit_log
from app.domains.auth.models import User, UserRole
from app.domains.auth.schemas import (
    LoginRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserCreate,
    UserRead,
    UserUpdate,
)
from app.domains.teams.models import ProjectAssignment


async def authenticate_user(
    db: AsyncSession,
    login_data: LoginRequest,
    ip_address: Optional[str] = None,
) -> TokenResponse:
    """Authenticates user credentials and generates access/refresh tokens with audit trail."""
    stmt = select(User).where(User.email == login_data.email.lower().strip())
    user = await db.scalar(stmt)

    if not user or not verify_password(login_data.password, user.hashed_password):
        # Audit failed login attempt (do not record password or sensitive data)
        await record_audit_log(
            db=db,
            action_type="USER_LOGIN_FAILED",
            entity_type="AUTH",
            entity_id=user.id if user else uuid.uuid4(),
            actor_id=user.id if user else None,
            new_state={"email": login_data.email.lower().strip(), "reason": "invalid_credentials"},
            ip_address=ip_address,
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "INVALID_CREDENTIALS", "message": "Invalid email or password."},
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        await record_audit_log(
            db=db,
            action_type="USER_LOGIN_FAILED_DEACTIVATED",
            entity_type="AUTH",
            entity_id=user.id,
            actor_id=user.id,
            new_state={"email": user.email, "reason": "account_deactivated"},
            ip_address=ip_address,
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error_code": "ACCOUNT_DEACTIVATED", "message": "This account has been deactivated. Contact an administrator."},
        )

    # Issue tokens
    access_token = create_access_token(
        subject=str(user.id),
        role=user.role,
        email=user.email,
    )
    refresh_token = create_refresh_token(
        subject=str(user.id),
    )
    refresh_payload = decode_token(refresh_token)
    refresh_jti = uuid.UUID(refresh_payload["jti"])

    # Record active refresh token JTI issuance
    await record_audit_log(
        db=db,
        action_type="REFRESH_TOKEN_ISSUED",
        entity_type="REFRESH_TOKEN",
        entity_id=refresh_jti,
        actor_id=user.id,
        new_state={"user_id": str(user.id)},
        ip_address=ip_address,
    )

    # Audit successful login
    await record_audit_log(
        db=db,
        action_type="USER_LOGIN_SUCCESS",
        entity_type="AUTH",
        entity_id=user.id,
        actor_id=user.id,
        new_state={"email": user.email, "role": user.role},
        ip_address=ip_address,
    )
    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserRead.model_validate(user),
    )


async def refresh_tokens(
    db: AsyncSession,
    refresh_data: RefreshTokenRequest,
    ip_address: Optional[str] = None,
) -> TokenResponse:
    """Exchanges a valid refresh token for a newly issued access token."""
    try:
        payload = decode_token(refresh_data.refresh_token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "TOKEN_EXPIRED", "message": "Refresh token has expired."},
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "INVALID_TOKEN", "message": "Invalid refresh token."},
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "INVALID_TOKEN_TYPE", "message": "Supplied token is not a refresh token."},
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "MALFORMED_TOKEN", "message": "Token missing subject identifier."},
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_uuid = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "MALFORMED_TOKEN", "message": "Invalid user UUID in token."},
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Validate and enforce JTI presence
    jti_str = payload.get("jti")
    if not jti_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "MALFORMED_TOKEN", "message": "Refresh token missing JTI identifier."},
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        old_jti = uuid.UUID(jti_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "MALFORMED_TOKEN", "message": "Invalid JTI format in refresh token."},
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 0. Concurrency Lock: Serialize concurrent refresh attempts on the exact same token JTI in PostgreSQL
    from sqlalchemy import text
    await db.execute(
        text("SELECT pg_advisory_xact_lock(hashtext(:jti))"),
        {"jti": str(old_jti)},
    )

    user = await db.get(User, user_uuid)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "USER_NOT_FOUND", "message": "User no longer exists."},
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error_code": "ACCOUNT_DEACTIVATED", "message": "Account has been deactivated."},
        )

    # 1. Anti-Replay: Verify this JTI was not already consumed or revoked
    from app.domains.audit.models import AuditLog
    from datetime import datetime, timezone

    revocation_stmt = select(AuditLog).where(
        AuditLog.entity_type == "REFRESH_TOKEN",
        AuditLog.entity_id == old_jti,
        AuditLog.action_type.in_(["REFRESH_TOKEN_CONSUMED", "REFRESH_TOKEN_REVOKED"])
    )
    is_revoked = await db.scalar(revocation_stmt)
    if is_revoked:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "TOKEN_REVOKED", "message": "Refresh token has been revoked or already consumed."},
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 2. Invalidate refresh token if user logged out after token was issued
    token_iat_ts = payload.get("iat")
    if token_iat_ts:
        token_iat_dt = datetime.fromtimestamp(token_iat_ts, tz=timezone.utc)
        logout_stmt = select(AuditLog).where(
            AuditLog.actor_id == user.id,
            AuditLog.action_type == "USER_LOGOUT",
            AuditLog.created_at >= token_iat_dt
        )
        has_logged_out = await db.scalar(logout_stmt)
        if has_logged_out:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error_code": "TOKEN_REVOKED", "message": "Session has been terminated by logout."},
                headers={"WWW-Authenticate": "Bearer"},
            )

    # 3. Mark old JTI as consumed
    await record_audit_log(
        db=db,
        action_type="REFRESH_TOKEN_CONSUMED",
        entity_type="REFRESH_TOKEN",
        entity_id=old_jti,
        actor_id=user.id,
        new_state={"user_id": str(user.id)},
        ip_address=ip_address,
    )

    new_access_token = create_access_token(
        subject=str(user.id),
        role=user.role,
        email=user.email,
    )
    new_refresh_token = create_refresh_token(
        subject=str(user.id),
    )
    new_refresh_payload = decode_token(new_refresh_token)
    new_jti = uuid.UUID(new_refresh_payload["jti"])

    # 4. Record new JTI as active
    await record_audit_log(
        db=db,
        action_type="REFRESH_TOKEN_ISSUED",
        entity_type="REFRESH_TOKEN",
        entity_id=new_jti,
        actor_id=user.id,
        new_state={"user_id": str(user.id)},
        ip_address=ip_address,
    )

    await record_audit_log(
        db=db,
        action_type="TOKEN_REFRESHED",
        entity_type="AUTH",
        entity_id=user.id,
        actor_id=user.id,
        new_state={"email": user.email},
        ip_address=ip_address,
    )
    await db.commit()

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserRead.model_validate(user),
    )


async def create_user(
    db: AsyncSession,
    user_in: UserCreate,
    actor: User,
    ip_address: Optional[str] = None,
) -> User:
    """Provisions a new user account with duplicate email rejection and audit logging."""
    normalized_email = user_in.email.lower().strip()
    existing = await db.scalar(select(User).where(User.email == normalized_email))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error_code": "EMAIL_ALREADY_EXISTS", "message": f"User with email '{normalized_email}' already exists."},
        )

    new_user = User(
        id=uuid.uuid4(),
        email=normalized_email,
        hashed_password=hash_password(user_in.password),
        full_name=user_in.full_name.strip(),
        role=user_in.role.value if isinstance(user_in.role, UserRole) else user_in.role,
        is_active=True,
    )
    db.add(new_user)
    await db.flush()

    # Record audit log
    await record_audit_log(
        db=db,
        action_type="USER_CREATED",
        entity_type="USER",
        entity_id=new_user.id,
        actor_id=actor.id,
        new_state={
            "email": new_user.email,
            "full_name": new_user.full_name,
            "role": new_user.role,
            "is_active": True,
        },
        ip_address=ip_address,
    )
    await db.commit()
    await db.refresh(new_user)
    return new_user


async def update_user(
    db: AsyncSession,
    user_id: uuid.UUID,
    user_update: UserUpdate,
    actor: User,
    ip_address: Optional[str] = None,
) -> User:
    """
    Updates user attributes enforcing strict RBAC invariants:
    - Non-admins cannot alter roles or activation status.
    - Admins cannot alter their own role (anti-self-lockout / role elevation invariant).
    - Audit logging for all attribute changes.
    """
    target_user = await db.get(User, user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "USER_NOT_FOUND", "message": f"User with ID {user_id} not found."},
        )

    # Rule 1: Non-admins cannot alter roles or activation status
    if actor.role != UserRole.ADMIN.value:
        if user_update.role is not None and user_update.role.value != target_user.role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error_code": "UNAUTHORIZED_ROLE_ESCALATION", "message": "Only administrators can assign or alter user roles."},
            )
        if user_update.is_active is not None and user_update.is_active != target_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error_code": "UNAUTHORIZED_STATUS_CHANGE", "message": "Only administrators can alter user activation status."},
            )
        # Non-admins can only update their own profile
        if actor.id != target_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error_code": "FORBIDDEN", "message": "You do not have permission to modify another user's profile."},
            )

    # Rule 2: Prevent a user from changing their own role (even if admin)
    if user_update.role is not None:
        target_role_val = user_update.role.value if isinstance(user_update.role, UserRole) else user_update.role
        if target_role_val != target_user.role:
            if actor.id == target_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={"error_code": "SELF_ROLE_CHANGE_PROHIBITED", "message": "Users are prohibited from modifying their own role."},
                )

    previous_state = {
        "full_name": target_user.full_name,
        "role": target_user.role,
        "is_active": target_user.is_active,
    }

    action_type = "USER_UPDATED"
    if user_update.role is not None and user_update.role.value != target_user.role:
        action_type = "USER_ROLE_CHANGED"
        target_user.role = user_update.role.value
    if user_update.is_active is not None and user_update.is_active != target_user.is_active:
        action_type = "USER_ACTIVATED" if user_update.is_active else "USER_DEACTIVATED"
        target_user.is_active = user_update.is_active
    if user_update.full_name is not None:
        target_user.full_name = user_update.full_name.strip()
    if user_update.password is not None:
        target_user.hashed_password = hash_password(user_update.password)

    new_state = {
        "full_name": target_user.full_name,
        "role": target_user.role,
        "is_active": target_user.is_active,
    }

    await record_audit_log(
        db=db,
        action_type=action_type,
        entity_type="USER",
        entity_id=target_user.id,
        actor_id=actor.id,
        previous_state=previous_state,
        new_state=new_state,
        ip_address=ip_address,
    )

    await db.commit()
    await db.refresh(target_user)
    return target_user


async def get_user_by_id(
    db: AsyncSession,
    user_id: uuid.UUID,
    actor: User,
) -> User:
    """Retrieves an individual user profile scoped by role and project assignments."""
    target = await db.get(User, user_id)
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "USER_NOT_FOUND", "message": f"User with ID {user_id} not found."},
        )

    # ADMIN and Self always permitted
    if actor.role == UserRole.ADMIN.value or actor.id == target.id:
        return target

    # PROJECT_MANAGER can view users who are assigned to their projects
    if actor.role == UserRole.PROJECT_MANAGER.value:
        # Check if they share any project assignment
        pm_project_ids = select(ProjectAssignment.project_id).where(ProjectAssignment.user_id == actor.id)
        shared_assignment = await db.scalar(
            select(ProjectAssignment).where(
                ProjectAssignment.user_id == target.id,
                ProjectAssignment.project_id.in_(pm_project_ids)
            )
        )
        if shared_assignment:
            return target

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={"error_code": "FORBIDDEN", "message": "You do not have permission to view this user profile."},
    )


async def list_users(
    db: AsyncSession,
    actor: User,
    skip: int = 0,
    limit: int = 50,
    role: Optional[UserRole] = None,
    is_active: Optional[bool] = None,
) -> Tuple[List[User], int]:
    """Lists organization users (ADMIN sees all, PM sees users assigned to their projects)."""
    if actor.role == UserRole.ADMIN.value:
        query = select(User)
        count_query = select(func.count(User.id))

        if role is not None:
            query = query.where(User.role == (role.value if isinstance(role, UserRole) else role))
            count_query = count_query.where(User.role == (role.value if isinstance(role, UserRole) else role))
        if is_active is not None:
            query = query.where(User.is_active == is_active)
            count_query = count_query.where(User.is_active == is_active)

        total = await db.scalar(count_query) or 0
        users = (await db.scalars(query.order_by(User.created_at.desc()).offset(skip).limit(limit))).all()
        return list(users), total

    if actor.role == UserRole.PROJECT_MANAGER.value:
        # PM can only view personnel assigned to their projects
        pm_project_ids = select(ProjectAssignment.project_id).where(ProjectAssignment.user_id == actor.id)
        assigned_user_ids = select(ProjectAssignment.user_id).where(ProjectAssignment.project_id.in_(pm_project_ids))

        query = select(User).where(User.id.in_(assigned_user_ids))
        count_query = select(func.count(User.id)).where(User.id.in_(assigned_user_ids))

        if role is not None:
            query = query.where(User.role == (role.value if isinstance(role, UserRole) else role))
            count_query = count_query.where(User.role == (role.value if isinstance(role, UserRole) else role))
        if is_active is not None:
            query = query.where(User.is_active == is_active)
            count_query = count_query.where(User.is_active == is_active)

        total = await db.scalar(count_query) or 0
        users = (await db.scalars(query.order_by(User.created_at.desc()).offset(skip).limit(limit))).all()
        return list(users), total

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={"error_code": "INSUFFICIENT_ROLE", "message": "Field officers are not authorized to list users."},
    )
