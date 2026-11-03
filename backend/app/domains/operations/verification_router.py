"""
VANA — Activity Verification Centre API Router
Exposes verification triage queue, digital sign-off, rejection handling,
and enforces Anti-Self-Verification Gate (Rule 5).
"""

from typing import List
import uuid

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.domains.auth.dependencies import get_current_active_user
from app.domains.auth.models import User
from app.domains.operations.schemas import (
    VerificationDecisionRequest,
    VerificationDecisionResponse,
    VerificationQueueItem,
)
from app.domains.operations.services import VerificationService

router = APIRouter(prefix="/verification", tags=["Activity Verification Centre"])


@router.get(
    "/queue",
    response_model=List[VerificationQueueItem],
    status_code=status.HTTP_200_OK,
    summary="Get Verification Triage Queue",
)
async def get_verification_queue(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> List[VerificationQueueItem]:
    """
    Fetches pending activity revisions awaiting verification review.
    - Admins see org-wide pending queue.
    - Project Managers see queue for assigned projects.
    - Field Officers are rejected with HTTP 403 Forbidden.
    """
    return await VerificationService.get_verification_queue(db=db, current_user=current_user)


@router.post(
    "/revisions/{revision_id}/decision",
    response_model=VerificationDecisionResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit Verification Decision (Approve / Reject)",
)
async def submit_verification_decision(
    revision_id: uuid.UUID,
    data: VerificationDecisionRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> VerificationDecisionResponse:
    """
    Submits a review decision (VERIFIED or REJECTED) on a pending revision.
    - Anti-Self-Verification Gate (Rule 5): Verifier cannot be the activity author (HTTP 403).
    - Field Officers cannot verify (HTTP 403).
    - Unassigned Project Managers cannot verify (HTTP 403).
    - Rejections require valid rejection reason code and review notes.
    - Approvals atomically deactivate previous active revision and mark target as active ledger entry.
    """
    ip_address = request.client.host if request.client else None
    return await VerificationService.record_decision(
        db=db,
        revision_id=revision_id,
        data=data,
        current_user=current_user,
        ip_address=ip_address,
    )
