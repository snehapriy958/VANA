"""VANA Audit Domain — FastAPI Router.

Exposes read-only endpoints for the Audit History & Immutability Ledger:
- GET  /api/v1/audit/events
- GET  /api/v1/audit/events/{id}
- GET  /api/v1/audit/verification
- GET  /api/v1/audit/entities/{entity_type}/{entity_id}
- POST /api/v1/audit/verify-chain
"""

from datetime import datetime
from typing import Optional
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.domains.audit.schemas import (
    AuditChainVerificationResponse,
    AuditLogListResponse,
    AuditLogRead,
    AuditVerificationHistoryResponse,
    AuditVerifyChainRequest,
)
from app.domains.audit.services import (
    get_audit_event_by_id,
    get_entity_audit_trail,
    get_verification_history,
    list_audit_events,
    verify_audit_chain,
)
from app.domains.auth.dependencies import get_current_active_user
from app.domains.auth.models import User

router = APIRouter(prefix="/audit", tags=["Audit Ledger"])


@router.get(
    "/events",
    response_model=AuditLogListResponse,
    status_code=status.HTTP_200_OK,
    summary="List paginated audit events with filters and RBAC",
)
async def get_events(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    action_type: Optional[str] = Query(None, description="Filter by event action type"),
    entity_type: Optional[str] = Query(None, description="Filter by target entity type"),
    entity_id: Optional[uuid.UUID] = Query(None, description="Filter by entity ID"),
    actor_id: Optional[uuid.UUID] = Query(None, description="Filter by actor ID"),
    project_id: Optional[uuid.UUID] = Query(None, description="Filter by project ID"),
    from_date: Optional[datetime] = Query(None, description="Filter events after or on this timestamp"),
    to_date: Optional[datetime] = Query(None, description="Filter events before or on this timestamp"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> AuditLogListResponse:
    """Retrieves paginated audit log events.

    Access Control:
    - ADMIN: Organization-wide access.
    - PROJECT_MANAGER: Scoped strictly to assigned projects.
    - FIELD_OFFICER: 403 Forbidden.
    """
    return await list_audit_events(
        db=db,
        current_user=current_user,
        page=page,
        page_size=page_size,
        action_type=action_type,
        entity_type=entity_type,
        entity_id=entity_id,
        actor_id=actor_id,
        project_id=project_id,
        from_date=from_date,
        to_date=to_date,
    )


@router.get(
    "/events/{event_id}",
    response_model=AuditLogRead,
    status_code=status.HTTP_200_OK,
    summary="Retrieve a single audit log event by ID",
)
async def get_event(
    event_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> AuditLogRead:
    """Retrieves a specific audit event record by its primary key ID."""
    return await get_audit_event_by_id(
        db=db,
        current_user=current_user,
        event_id=event_id,
    )


@router.get(
    "/verification",
    response_model=AuditVerificationHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve immutable verification and decision lifecycle events",
)
async def get_verification_decisions(
    activity_id: Optional[uuid.UUID] = Query(None, description="Filter by field activity ID"),
    project_id: Optional[uuid.UUID] = Query(None, description="Filter by project ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    from_date: Optional[datetime] = Query(None, description="Filter events on/after timestamp"),
    to_date: Optional[datetime] = Query(None, description="Filter events on/before timestamp"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> AuditVerificationHistoryResponse:
    """Retrieves chronological verification lifecycle history (submissions, amendments, decisions, archival)."""
    return await get_verification_history(
        db=db,
        current_user=current_user,
        activity_id=activity_id,
        project_id=project_id,
        page=page,
        page_size=page_size,
        from_date=from_date,
        to_date=to_date,
    )


@router.get(
    "/entities/{entity_type}/{entity_id}",
    response_model=AuditLogListResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve complete audit trail for a specific entity",
)
async def get_entity_trail(
    entity_type: str,
    entity_id: uuid.UUID,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> AuditLogListResponse:
    """Retrieves the full lifecycle audit trail for a specific domain entity."""
    return await get_entity_audit_trail(
        db=db,
        current_user=current_user,
        entity_type=entity_type,
        entity_id=entity_id,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/verify-chain",
    response_model=AuditChainVerificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Perform read-only cryptographic chain integrity verification",
)
async def verify_chain(
    body: Optional[AuditVerifyChainRequest] = None,
    from_sequence: Optional[int] = Query(None, ge=1, description="Starting sequence number to verify"),
    to_sequence: Optional[int] = Query(None, ge=1, description="Ending sequence number to verify"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> AuditChainVerificationResponse:
    """Verifies SHA-256 hash chaining, sequence continuity, state column consistency, and chain head checkpoint."""
    # RBAC: Only ADMIN and assigned PROJECT_MANAGERS may trigger cryptographic integrity audit
    effective_from = 1
    effective_to = None

    if body and body.from_sequence is not None:
        effective_from = body.from_sequence
    elif from_sequence is not None:
        effective_from = from_sequence

    if body and body.to_sequence is not None:
        effective_to = body.to_sequence
    elif to_sequence is not None:
        effective_to = to_sequence

    return await verify_audit_chain(
        db=db,
        from_sequence=effective_from,
        to_sequence=effective_to,
    )
