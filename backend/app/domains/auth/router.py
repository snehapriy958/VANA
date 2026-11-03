import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token
from app.domains.audit.services import record_audit_log
from app.domains.auth.dependencies import get_current_active_user
from app.domains.auth.models import User
from app.domains.auth.schemas import (
    LoginRequest,
    LogoutRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserRead,
)
from app.domains.auth.services import authenticate_user, refresh_tokens

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def login(
    login_data: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Authenticates credentials using Argon2id and returns signed JWT access and refresh tokens."""
    client_ip = request.client.host if request.client else None
    return await authenticate_user(db=db, login_data=login_data, ip_address=client_ip)


@router.post("/refresh", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def refresh(
    refresh_data: RefreshTokenRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Exchanges a valid refresh token for a newly generated access token."""
    client_ip = request.client.host if request.client else None
    return await refresh_tokens(db=db, refresh_data=refresh_data, ip_address=client_ip)


@router.get("/me", response_model=UserRead, status_code=status.HTTP_200_OK)
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user),
) -> UserRead:
    """Retrieves the authenticated user's profile and active role."""
    return UserRead.model_validate(current_user)


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    request: Request,
    logout_data: Optional[LogoutRequest] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Terminates user session, revokes refresh token JTI if supplied,
    and logs an immutable USER_LOGOUT audit event.
    """
    client_ip = request.client.host if request.client else None

    if logout_data and logout_data.refresh_token:
        try:
            payload = decode_token(logout_data.refresh_token)
            jti_str = payload.get("jti")
            if jti_str:
                jti_uuid = uuid.UUID(jti_str)
                await record_audit_log(
                    db=db,
                    action_type="REFRESH_TOKEN_REVOKED",
                    entity_type="REFRESH_TOKEN",
                    entity_id=jti_uuid,
                    actor_id=current_user.id,
                    new_state={"reason": "user_logout"},
                    ip_address=client_ip,
                )
        except Exception:
            # Even if token is malformed/expired, ensure user logout event is preserved
            pass

    await record_audit_log(
        db=db,
        action_type="USER_LOGOUT",
        entity_type="AUTH",
        entity_id=current_user.id,
        actor_id=current_user.id,
        new_state={"email": current_user.email},
        ip_address=client_ip,
    )
    await db.commit()
    return {"message": "Successfully logged out."}
