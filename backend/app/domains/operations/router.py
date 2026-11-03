"""
VANA — Field Operations API Router
Handles field activity reporting, amendment submissions, file evidence uploads,
and secure access-controlled evidence streaming.
"""

from datetime import date
from decimal import Decimal
import os
from typing import List, Optional
import uuid

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.domains.auth.dependencies import get_current_active_user
from app.domains.auth.models import User
from app.domains.operations.schemas import (
    ActivityCreate,
    ActivityRevisionCreate,
    FieldActivityResponse,
    VerificationDecisionRequest,
    VerificationDecisionResponse,
    VerificationQueueItem,
)
from app.domains.operations.services import (
    ActivityService,
    EvidenceService,
    VerificationService,
)

router = APIRouter(prefix="/operations", tags=["Field Operations"])


@router.post(
    "/activities",
    response_model=FieldActivityResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit Field Activity Report",
)
async def create_activity(
    request: Request,
    project_id: uuid.UUID = Form(...),
    metric_code: str = Form(...),
    quantity: Decimal = Form(..., gt=0),
    unit: str = Form(...),
    activity_date: date = Form(...),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    gps_accuracy_meters: Optional[float] = Form(None),
    field_notes: Optional[str] = Form(None),
    evidence_files: List[UploadFile] = File(default=[]),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> FieldActivityResponse:
    """
    Submits a new field activity report with optional photo evidence.
    Creates parent FieldActivity and Revision 1 (status: PENDING).
    """
    ip_address = request.client.host if request.client else None

    # Construct and validate DTO
    activity_data = ActivityCreate(
        project_id=project_id,
        metric_code=metric_code,
        quantity=quantity,
        unit=unit,
        activity_date=activity_date,
        latitude=latitude,
        longitude=longitude,
        gps_accuracy_meters=gps_accuracy_meters,
        field_notes=field_notes,
    )

    return await ActivityService.create_activity(
        db=db,
        data=activity_data,
        current_user=current_user,
        files=evidence_files,
        ip_address=ip_address,
    )


@router.get(
    "/activities",
    response_model=List[FieldActivityResponse],
    status_code=status.HTTP_200_OK,
    summary="List Field Activities",
)
async def list_activities(
    project_id: Optional[uuid.UUID] = Query(None, description="Filter by project ID"),
    status: Optional[str] = Query(None, description="Filter by status (PENDING, VERIFIED, REJECTED)"),
    metric_code: Optional[str] = Query(None, description="Filter by metric code"),
    is_archived: bool = Query(False, description="Include or filter archived activities"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> List[FieldActivityResponse]:
    """
    Lists field activities. Scoped to user's permitted projects.
    Admins see org-wide activities; Field Officers and PMs see assigned projects.
    """
    return await ActivityService.list_activities(
        db=db,
        current_user=current_user,
        project_id=project_id,
        status_filter=status,
        metric_code=metric_code,
        is_archived=is_archived,
    )


@router.get(
    "/activities/{activity_id}",
    response_model=FieldActivityResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Field Activity Details",
)
async def get_activity(
    activity_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> FieldActivityResponse:
    """Retrieves full activity details, revision history, and evidence file references."""
    return await ActivityService.get_activity(
        db=db, activity_id=activity_id, current_user=current_user
    )


@router.post(
    "/activities/{activity_id}/revisions",
    response_model=FieldActivityResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit Activity Amendment / Revision",
)
async def amend_activity(
    activity_id: uuid.UUID,
    request: Request,
    quantity: Decimal = Form(..., gt=0),
    activity_date: date = Form(...),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    gps_accuracy_meters: Optional[float] = Form(None),
    field_notes: Optional[str] = Form(None),
    amendment_reason: Optional[str] = Form(None),
    evidence_files: List[UploadFile] = File(default=[]),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> FieldActivityResponse:
    """
    Submits a new revision for an existing activity (amendment or correction).
    Creates a new revision (PENDING). The previously verified revision remains active in the ledger
    until this revision is verified.
    """
    ip_address = request.client.host if request.client else None

    amendment_data = ActivityRevisionCreate(
        quantity=quantity,
        activity_date=activity_date,
        latitude=latitude,
        longitude=longitude,
        gps_accuracy_meters=gps_accuracy_meters,
        field_notes=field_notes,
        amendment_reason=amendment_reason,
    )

    return await ActivityService.amend_activity(
        db=db,
        activity_id=activity_id,
        data=amendment_data,
        current_user=current_user,
        files=evidence_files,
        ip_address=ip_address,
    )


@router.delete(
    "/activities/{activity_id}",
    status_code=status.HTTP_200_OK,
    summary="Archive Field Activity",
)
async def archive_activity(
    activity_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Soft-deletes/archives an activity.
    Authorized for ADMIN or assigned PROJECT_MANAGER.
    Deactivates any active ledger entry so it ceases contributing to official achievements.
    """
    ip_address = request.client.host if request.client else None
    return await ActivityService.archive_activity(
        db=db,
        activity_id=activity_id,
        current_user=current_user,
        ip_address=ip_address,
    )


@router.get(
    "/evidence/{evidence_id}",
    summary="Stream Evidence File",
)
async def get_evidence_file(
    evidence_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Streams an evidence file to authorized users.
    Verifies project-level access before streaming content.
    """
    file_path, mime_type, filename = await EvidenceService.get_evidence_file_path(
        db=db, evidence_id=evidence_id, current_user=current_user
    )

    return FileResponse(
        path=str(file_path),
        media_type=mime_type,
        filename=filename,
    )


@router.get(
    "/verification/queue",
    response_model=List[VerificationQueueItem],
    status_code=status.HTTP_200_OK,
    summary="Get Verification Queue (Operations Alias)",
)
async def get_verification_queue_alias(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> List[VerificationQueueItem]:
    """Verification queue alias under /operations/verification/queue."""
    return await VerificationService.get_verification_queue(db=db, current_user=current_user)


@router.post(
    "/revisions/{revision_id}/decision",
    response_model=VerificationDecisionResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit Verification Decision (Operations Alias)",
)
async def submit_verification_decision_alias(
    revision_id: uuid.UUID,
    data: VerificationDecisionRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> VerificationDecisionResponse:
    """Submit verification decision alias under /operations/revisions/{revision_id}/decision."""
    ip_address = request.client.host if request.client else None
    return await VerificationService.record_decision(
        db=db,
        revision_id=revision_id,
        data=data,
        current_user=current_user,
        ip_address=ip_address,
    )
