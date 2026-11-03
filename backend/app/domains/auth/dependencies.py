import uuid
from typing import Callable, List, Optional
import jwt
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_db
from app.core.security import decode_token
from app.domains.auth.models import User, UserRole
from app.domains.teams.models import ProjectAssignment


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> User:
    """Extracts, decodes, and validates the Bearer JWT access token from the request header."""
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "NOT_AUTHENTICATED", "message": "Authentication credentials were not provided."},
            headers={"WWW-Authenticate": "Bearer"},
        )

    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "INVALID_AUTH_HEADER", "message": "Invalid Authorization header format. Expected 'Bearer <token>'."},
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = parts[1]
    try:
        payload = decode_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "TOKEN_EXPIRED", "message": "Authentication token has expired."},
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "INVALID_TOKEN", "message": "Could not validate authentication credentials."},
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_type = payload.get("type")
    if token_type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "INVALID_TOKEN_TYPE", "message": "Invalid token type. Expected access token."},
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "MALFORMED_TOKEN", "message": "Token payload missing user identifier."},
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_uuid = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "MALFORMED_TOKEN", "message": "Invalid user ID format in token."},
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await db.get(User, user_uuid)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "USER_NOT_FOUND", "message": "User associated with this token no longer exists."},
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Verifies that the authenticated user account is active."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error_code": "ACCOUNT_DEACTIVATED", "message": "This user account has been deactivated. Contact an administrator."},
        )
    return current_user


def require_roles(*allowed_roles: UserRole) -> Callable:
    """Dependency factory restricting endpoint access to specific user roles."""
    role_values = [r.value if isinstance(r, UserRole) else r for r in allowed_roles]

    async def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role not in role_values:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "INSUFFICIENT_ROLE",
                    "message": f"Operation not permitted. Required role: {', '.join(role_values)}."
                },
            )
        return current_user

    return role_checker


# Convenient role dependency shortcuts
require_admin = require_roles(UserRole.ADMIN)
require_pm_or_admin = require_roles(UserRole.ADMIN, UserRole.PROJECT_MANAGER)


async def verify_project_access(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    min_role: Optional[UserRole] = None,
) -> Optional[ProjectAssignment]:
    """
    Project-level authorization boundary dependency.
    Validates project existence in PostgreSQL first.
    ADMIN possesses organization-wide access to any existing project.
    PROJECT_MANAGER and FIELD_OFFICER must have an active ProjectAssignment row.
    """
    from app.domains.projects.models import Project

    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "PROJECT_NOT_FOUND", "message": f"Project with ID {project_id} not found."},
        )

    if current_user.role == UserRole.ADMIN.value:
        return None

    stmt = select(ProjectAssignment).where(
        ProjectAssignment.project_id == project_id,
        ProjectAssignment.user_id == current_user.id
    )
    assignment = await db.scalar(stmt)
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error_code": "PROJECT_ACCESS_DENIED", "message": "You are not assigned to this project."},
        )

    if min_role == UserRole.PROJECT_MANAGER and current_user.role != UserRole.PROJECT_MANAGER.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error_code": "INSUFFICIENT_PROJECT_ROLE", "message": "Project Manager role required for this project operation."},
        )

    return assignment
