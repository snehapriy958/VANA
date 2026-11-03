import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.domains.auth.dependencies import (
    get_current_active_user,
    require_admin,
    require_pm_or_admin,
)
from app.domains.auth.models import User, UserRole
from app.domains.auth.schemas import (
    UserCreate,
    UserListResponse,
    UserRead,
    UserUpdate,
)
from app.domains.auth.services import (
    create_user,
    get_user_by_id,
    list_users,
    update_user,
)

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", response_model=UserListResponse, status_code=status.HTTP_200_OK)
async def get_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    role: Optional[UserRole] = Query(None),
    is_active: Optional[bool] = Query(None),
    current_user: User = Depends(require_pm_or_admin),
    db: AsyncSession = Depends(get_db),
) -> UserListResponse:
    """
    Lists users in the organization.
    ADMIN: Organization-wide access with optional role/active filters.
    PROJECT_MANAGER: Restricted strictly to personnel assigned to projects they manage.
    """
    users, total = await list_users(
        db=db,
        actor=current_user,
        skip=skip,
        limit=limit,
        role=role,
        is_active=is_active,
    )
    return UserListResponse(
        users=[UserRead.model_validate(u) for u in users],
        total=total,
    )


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def provision_user(
    user_in: UserCreate,
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> UserRead:
    """Provisions a new user account with initial role. Restricted exclusively to ADMIN."""
    client_ip = request.client.host if request.client else None
    new_user = await create_user(
        db=db,
        user_in=user_in,
        actor=current_user,
        ip_address=client_ip,
    )
    return UserRead.model_validate(new_user)


@router.get("/{id}", response_model=UserRead, status_code=status.HTTP_200_OK)
async def retrieve_user(
    id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> UserRead:
    """Retrieves an individual user profile. Permitted for ADMIN, Self, or PM over assigned personnel."""
    user = await get_user_by_id(db=db, user_id=id, actor=current_user)
    return UserRead.model_validate(user)


@router.put("/{id}", response_model=UserRead, status_code=status.HTTP_200_OK)
async def modify_user(
    id: uuid.UUID,
    user_update: UserUpdate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> UserRead:
    """
    Updates user details.
    ADMIN: Can update full_name, role (except their own), is_active.
    Self: Can update permitted details (full_name, password) but cannot change role or status.
    """
    client_ip = request.client.host if request.client else None
    updated = await update_user(
        db=db,
        user_id=id,
        user_update=user_update,
        actor=current_user,
        ip_address=client_ip,
    )
    return UserRead.model_validate(updated)
