"""
VANA — Field Operations & Activity Verification Services
Enforces server-side authorization, anti-self-verification gates,
immutable revision history, evidence storage, and 5-ledger accounting.
"""

from datetime import datetime, timezone
from decimal import Decimal
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import uuid

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.storage import get_storage_service
from app.domains.audit.services import record_audit_log
from app.domains.auth.models import User, UserRole
from app.domains.operations.models import (
    ActivityRevision,
    ActivityStatus,
    EvidenceFile,
    FieldActivity,
    RejectionReasonCode,
)
from app.domains.operations.schemas import (
    ActivityCreate,
    ActivityRevisionCreate,
    ActivityRevisionResponse,
    EvidenceFileResponse,
    FieldActivityResponse,
    VerificationDecisionRequest,
    VerificationDecisionResponse,
    VerificationQueueItem,
)
from app.domains.projects.metrics import validate_metric_and_unit
from app.domains.projects.models import Project, ProjectStatus, ProjectTarget
from app.domains.teams.models import ProjectAssignment

# File upload constraints
ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "application/pdf",
}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_FILES_PER_SUBMISSION = 5


class ActivityService:
    @staticmethod
    async def verify_project_assignment(
        db: AsyncSession, project_id: uuid.UUID, user: User
    ) -> None:
        """Verifies that the user has administrative or roster access to the project."""
        if user.role == UserRole.ADMIN.value:
            return

        assignment = await db.scalar(
            select(ProjectAssignment).where(
                ProjectAssignment.project_id == project_id,
                ProjectAssignment.user_id == user.id,
            )
        )
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "PROJECT_ACCESS_DENIED",
                    "message": "You are not assigned to this project.",
                },
            )

    @staticmethod
    async def create_activity(
        db: AsyncSession,
        data: ActivityCreate,
        current_user: User,
        files: Optional[List[UploadFile]] = None,
        ip_address: Optional[str] = None,
    ) -> FieldActivityResponse:
        """
        Submits a new field activity report with optional photo evidence.
        Creates parent FieldActivity and Revision 1 (PENDING).
        """
        # 1. Verify project assignment
        await ActivityService.verify_project_assignment(db, data.project_id, current_user)

        # 2. Verify project exists and is active
        project = await db.scalar(select(Project).where(Project.id == data.project_id))
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_code": "PROJECT_NOT_FOUND",
                    "message": f"Project with ID {data.project_id} not found.",
                },
            )
        if project.status == ProjectStatus.ARCHIVED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_code": "PROJECT_ARCHIVED",
                    "message": "Cannot submit field activities for an archived project.",
                },
            )

        # 3. Verify target exists for (project_id, metric_code)
        target = await db.scalar(
            select(ProjectTarget).where(
                ProjectTarget.project_id == data.project_id,
                ProjectTarget.metric_code == data.metric_code,
            )
        )
        if not target:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_code": "PROJECT_TARGET_NOT_CONFIGURED",
                    "message": f"Project '{project.name}' has no active target defined for metric '{data.metric_code}'.",
                },
            )

        # 4. Validate metric and unit compatibility
        try:
            metric_def = validate_metric_and_unit(data.metric_code, data.unit)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_code": "INVALID_METRIC_UNIT",
                    "message": str(e),
                },
            )
        normalized_unit = data.unit.strip().lower()

        # 5. Create parent container FieldActivity
        activity = FieldActivity(
            project_id=data.project_id,
            created_by_id=current_user.id,
            metric_code=data.metric_code,
            unit=normalized_unit,
            is_archived=False,
        )
        db.add(activity)
        await db.flush()

        # 6. Create initial revision (Revision 1, status PENDING, is_active_ledger_entry = False)
        revision = ActivityRevision(
            activity_id=activity.id,
            revision_number=1,
            quantity=data.quantity,
            activity_date=data.activity_date,
            latitude=data.latitude,
            longitude=data.longitude,
            gps_accuracy_meters=data.gps_accuracy_meters,
            field_notes=data.field_notes.strip() if data.field_notes else None,
            status=ActivityStatus.PENDING.value,
            is_active_ledger_entry=False,
        )
        db.add(revision)
        await db.flush()

        # Set current revision on parent activity
        activity.current_revision_id = revision.id
        await db.flush()

        # 7. Process evidence file uploads
        storage = get_storage_service()
        evidence_records: List[EvidenceFile] = []
        if files:
            if len(files) > MAX_FILES_PER_SUBMISSION:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error_code": "TOO_MANY_FILES",
                        "message": f"Maximum {MAX_FILES_PER_SUBMISSION} evidence files permitted per submission.",
                    },
                )

            for file in files:
                if not file.filename:
                    continue
                content = await file.read()
                file_size = len(content)

                if file_size == 0:
                    continue
                if file_size > MAX_FILE_SIZE_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail={
                            "error_code": "FILE_TOO_LARGE",
                            "message": f"File '{file.filename}' exceeds maximum allowable size of 10 MB.",
                        },
                    )

                mime_type = file.content_type or "application/octet-stream"
                if mime_type.lower() not in ALLOWED_MIME_TYPES:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail={
                            "error_code": "UNSUPPORTED_FILE_TYPE",
                            "message": f"File type '{mime_type}' is not supported. Allowed formats: JPEG, PNG, WEBP, PDF.",
                        },
                    )

                safe_name = os.path.basename(file.filename)
                storage_key = await storage.upload_file(content, safe_name)

                evidence = EvidenceFile(
                    activity_id=activity.id,
                    revision_id=revision.id,
                    file_storage_key=storage_key,
                    original_filename=safe_name,
                    mime_type=mime_type,
                    file_size_bytes=file_size,
                )
                db.add(evidence)
                evidence_records.append(evidence)

            await db.flush()

        # 8. Immutable audit logging
        await record_audit_log(
            db=db,
            action_type="ACTIVITY_CREATED",
            entity_type="field_activity",
            entity_id=activity.id,
            actor_id=current_user.id,
            new_state={
                "activity_id": str(activity.id),
                "project_id": str(activity.project_id),
                "metric_code": activity.metric_code,
                "unit": activity.unit,
                "quantity": float(revision.quantity),
                "revision_number": 1,
                "status": revision.status,
                "files_count": len(evidence_records),
            },
            ip_address=ip_address,
        )

        if evidence_records:
            await record_audit_log(
                db=db,
                action_type="EVIDENCE_UPLOADED",
                entity_type="field_activity",
                entity_id=activity.id,
                actor_id=current_user.id,
                new_state={
                    "activity_id": str(activity.id),
                    "revision_id": str(revision.id),
                    "files": [
                        {
                            "id": str(e.id),
                            "filename": e.original_filename,
                            "size_bytes": e.file_size_bytes,
                        }
                        for e in evidence_records
                    ],
                },
                ip_address=ip_address,
            )

        await db.commit()

        return await ActivityService.get_activity(
            db=db, activity_id=activity.id, current_user=current_user
        )

    @staticmethod
    async def amend_activity(
        db: AsyncSession,
        activity_id: uuid.UUID,
        data: ActivityRevisionCreate,
        current_user: User,
        files: Optional[List[UploadFile]] = None,
        ip_address: Optional[str] = None,
    ) -> FieldActivityResponse:
        """
        Submits a new revision for an activity (either an amendment to a verified activity
        or a correction for a rejected activity).
        """
        # 1. Fetch activity with existing revisions and lock row
        stmt = (
            select(FieldActivity)
            .where(FieldActivity.id == activity_id)
            .options(
                selectinload(FieldActivity.revisions),
                selectinload(FieldActivity.project),
            )
            .with_for_update()
        )
        activity = await db.scalar(stmt)
        if not activity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_code": "ACTIVITY_NOT_FOUND",
                    "message": f"Activity with ID {activity_id} not found.",
                },
            )

        if activity.is_archived:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_code": "ACTIVITY_ARCHIVED",
                    "message": "Cannot amend an archived activity.",
                },
            )

        # 2. Check project assignment
        await ActivityService.verify_project_assignment(db, activity.project_id, current_user)

        # 3. Prevent duplicate simultaneous pending revisions
        for r in activity.revisions:
            if r.status == ActivityStatus.PENDING.value:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error_code": "PENDING_REVISION_EXISTS",
                        "message": "An unreviewed revision is already pending for this activity. Please await review before submitting another amendment.",
                    },
                )

        # 4. Next revision number
        next_rev_num = max(r.revision_number for r in activity.revisions) + 1

        # Format field notes with amendment reason if provided
        notes = data.field_notes.strip() if data.field_notes else None
        if data.amendment_reason and data.amendment_reason.strip():
            reason_header = f"[Amendment Reason: {data.amendment_reason.strip()}]"
            notes = f"{reason_header}\n{notes}" if notes else reason_header

        # 5. Create new revision (PENDING, is_active_ledger_entry = False)
        new_revision = ActivityRevision(
            activity_id=activity.id,
            revision_number=next_rev_num,
            quantity=data.quantity,
            activity_date=data.activity_date,
            latitude=data.latitude,
            longitude=data.longitude,
            gps_accuracy_meters=data.gps_accuracy_meters,
            field_notes=notes,
            status=ActivityStatus.PENDING.value,
            is_active_ledger_entry=False,
        )
        db.add(new_revision)
        await db.flush()

        activity.current_revision_id = new_revision.id
        await db.flush()

        # 6. Process attached evidence files
        storage = get_storage_service()
        evidence_records: List[EvidenceFile] = []
        if files:
            if len(files) > MAX_FILES_PER_SUBMISSION:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error_code": "TOO_MANY_FILES",
                        "message": f"Maximum {MAX_FILES_PER_SUBMISSION} evidence files permitted per submission.",
                    },
                )

            for file in files:
                if not file.filename:
                    continue
                content = await file.read()
                file_size = len(content)
                if file_size == 0:
                    continue
                if file_size > MAX_FILE_SIZE_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail={
                            "error_code": "FILE_TOO_LARGE",
                            "message": f"File '{file.filename}' exceeds maximum allowable size of 10 MB.",
                        },
                    )

                mime_type = file.content_type or "application/octet-stream"
                if mime_type.lower() not in ALLOWED_MIME_TYPES:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail={
                            "error_code": "UNSUPPORTED_FILE_TYPE",
                            "message": f"File type '{mime_type}' is not supported. Allowed formats: JPEG, PNG, WEBP, PDF.",
                        },
                    )

                safe_name = os.path.basename(file.filename)
                storage_key = await storage.upload_file(content, safe_name)

                evidence = EvidenceFile(
                    activity_id=activity.id,
                    revision_id=new_revision.id,
                    file_storage_key=storage_key,
                    original_filename=safe_name,
                    mime_type=mime_type,
                    file_size_bytes=file_size,
                )
                db.add(evidence)
                evidence_records.append(evidence)

            await db.flush()

        # 7. Immutable audit logging
        active_ledger = next((r for r in activity.revisions if r.is_active_ledger_entry), None)
        prev_verified_qty = float(active_ledger.quantity) if active_ledger else None

        await record_audit_log(
            db=db,
            action_type="ACTIVITY_AMENDED",
            entity_type="field_activity",
            entity_id=activity.id,
            actor_id=current_user.id,
            new_state={
                "activity_id": str(activity.id),
                "revision_number": next_rev_num,
                "amended_quantity": float(new_revision.quantity),
                "previously_verified_quantity": prev_verified_qty,
                "net_pending_adjustment": (
                    float(new_revision.quantity) - prev_verified_qty
                    if prev_verified_qty is not None
                    else float(new_revision.quantity)
                ),
                "files_count": len(evidence_records),
            },
            ip_address=ip_address,
        )

        await db.commit()

        return await ActivityService.get_activity(
            db=db, activity_id=activity.id, current_user=current_user
        )

    @staticmethod
    async def archive_activity(
        db: AsyncSession,
        activity_id: uuid.UUID,
        current_user: User,
        ip_address: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Soft-deletes an activity. Authorized for ADMIN or assigned PROJECT_MANAGER.
        Deactivates any active ledger entry so it ceases contributing to verified totals.
        """
        stmt = (
            select(FieldActivity)
            .where(FieldActivity.id == activity_id)
            .options(selectinload(FieldActivity.revisions))
            .with_for_update()
        )
        activity = await db.scalar(stmt)
        if not activity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_code": "ACTIVITY_NOT_FOUND",
                    "message": f"Activity with ID {activity_id} not found.",
                },
            )

        if current_user.role != UserRole.ADMIN.value:
            assignment = await db.scalar(
                select(ProjectAssignment).where(
                    ProjectAssignment.project_id == activity.project_id,
                    ProjectAssignment.user_id == current_user.id,
                    ProjectAssignment.assigned_role == "PROJECT_MANAGER",
                )
            )
            if not assignment:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error_code": "INSUFFICIENT_PROJECT_ROLE",
                        "message": "Only assigned Project Managers or Admins can archive an activity.",
                    },
                )

        if activity.is_archived:
            return {"activity_id": str(activity.id), "status": "ALREADY_ARCHIVED"}

        activity.is_archived = True

        # Deactivate any active ledger entry
        deactivated_revision_id: Optional[str] = None
        for rev in activity.revisions:
            if rev.is_active_ledger_entry:
                rev.is_active_ledger_entry = False
                deactivated_revision_id = str(rev.id)

        await db.flush()

        await record_audit_log(
            db=db,
            action_type="ACTIVITY_ARCHIVED",
            entity_type="field_activity",
            entity_id=activity.id,
            actor_id=current_user.id,
            new_state={
                "activity_id": str(activity.id),
                "is_archived": True,
                "deactivated_revision_id": deactivated_revision_id,
            },
            ip_address=ip_address,
        )
        await db.commit()

        return {
            "activity_id": str(activity.id),
            "status": "ARCHIVED",
            "deactivated_revision_id": deactivated_revision_id,
        }

    @staticmethod
    async def get_activity(
        db: AsyncSession, activity_id: uuid.UUID, current_user: User
    ) -> FieldActivityResponse:
        """Retrieves an activity with full revision history, evidence files, and net adjustments."""
        stmt = (
            select(FieldActivity)
            .where(FieldActivity.id == activity_id)
            .execution_options(populate_existing=True)
            .options(
                selectinload(FieldActivity.project),
                selectinload(FieldActivity.created_by),
                selectinload(FieldActivity.revisions).selectinload(ActivityRevision.verifier),
                selectinload(FieldActivity.revisions).selectinload(ActivityRevision.evidence_files),
            )
        )
        activity = await db.scalar(stmt)
        if not activity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_code": "ACTIVITY_NOT_FOUND",
                    "message": f"Activity with ID {activity_id} not found.",
                },
            )

        # Scoping check
        await ActivityService.verify_project_assignment(db, activity.project_id, current_user)

        return ActivityService._build_activity_response(activity)

    @staticmethod
    async def list_activities(
        db: AsyncSession,
        current_user: User,
        project_id: Optional[uuid.UUID] = None,
        status_filter: Optional[str] = None,
        metric_code: Optional[str] = None,
        is_archived: bool = False,
    ) -> List[FieldActivityResponse]:
        """
        Lists activities matching filters. Scoped to user's assigned projects.
        """
        stmt = (
            select(FieldActivity)
            .where(FieldActivity.is_archived == is_archived)
            .order_by(desc(FieldActivity.created_at))
            .options(
                selectinload(FieldActivity.project),
                selectinload(FieldActivity.created_by),
                selectinload(FieldActivity.revisions).selectinload(ActivityRevision.verifier),
                selectinload(FieldActivity.revisions).selectinload(ActivityRevision.evidence_files),
            )
        )

        if current_user.role != UserRole.ADMIN.value:
            stmt = stmt.join(
                ProjectAssignment,
                (ProjectAssignment.project_id == FieldActivity.project_id)
                & (ProjectAssignment.user_id == current_user.id),
            )

        if project_id:
            stmt = stmt.where(FieldActivity.project_id == project_id)

        if metric_code:
            stmt = stmt.where(FieldActivity.metric_code == metric_code)

        result = await db.scalars(stmt)
        activities = list(result.all())

        responses = [ActivityService._build_activity_response(a) for a in activities]

        if status_filter:
            sf_upper = status_filter.strip().upper()
            responses = [
                r
                for r in responses
                if r.current_revision and r.current_revision.status == sf_upper
            ]

        return responses

    @staticmethod
    def _build_activity_response(activity: FieldActivity) -> FieldActivityResponse:
        """Internal helper to assemble FieldActivityResponse with revisions and net adjustments."""
        sorted_revisions = sorted(activity.revisions, key=lambda r: r.revision_number)

        # Build revision responses
        revision_responses: List[ActivityRevisionResponse] = []
        for r in sorted_revisions:
            evidence_responses = [
                EvidenceFileResponse(
                    id=e.id,
                    activity_id=e.activity_id,
                    revision_id=e.revision_id,
                    original_filename=e.original_filename,
                    mime_type=e.mime_type,
                    file_size_bytes=e.file_size_bytes,
                    download_url=f"/api/v1/operations/evidence/{e.id}",
                    uploaded_at=e.uploaded_at,
                )
                for e in r.evidence_files
            ]

            rev_dto = ActivityRevisionResponse(
                id=r.id,
                activity_id=r.activity_id,
                revision_number=r.revision_number,
                quantity=r.quantity,
                activity_date=r.activity_date,
                latitude=r.latitude,
                longitude=r.longitude,
                gps_accuracy_meters=r.gps_accuracy_meters,
                field_notes=r.field_notes,
                status=r.status,
                is_active_ledger_entry=r.is_active_ledger_entry,
                verifier_id=r.verifier_id,
                verifier_name=r.verifier.full_name if r.verifier else None,
                verified_at=r.verified_at,
                rejection_reason_code=r.rejection_reason_code,
                review_notes=r.review_notes,
                created_at=r.created_at,
                evidence_files=evidence_responses,
            )
            revision_responses.append(rev_dto)

        # Current revision (matching current_revision_id or latest by revision_number)
        current_rev = None
        if activity.current_revision_id:
            current_rev = next(
                (r for r in revision_responses if r.id == activity.current_revision_id),
                None,
            )
        if not current_rev and revision_responses:
            current_rev = revision_responses[-1]
        active_rev = next((r for r in revision_responses if r.is_active_ledger_entry), None)
        active_verified_qty = active_rev.quantity if active_rev else Decimal("0.0")

        # Net pending adjustment:
        # If current revision is PENDING:
        # If active_rev exists: current.quantity - active.quantity
        # Else: current.quantity
        net_pending_adj: Optional[Decimal] = None
        if current_rev and current_rev.status == ActivityStatus.PENDING.value:
            if active_rev:
                net_pending_adj = current_rev.quantity - active_rev.quantity
            else:
                net_pending_adj = current_rev.quantity

        return FieldActivityResponse(
            id=activity.id,
            project_id=activity.project_id,
            project_name=activity.project.name if activity.project else None,
            project_code=activity.project.code if activity.project else None,
            created_by_id=activity.created_by_id,
            created_by_name=activity.created_by.full_name if activity.created_by else None,
            metric_code=activity.metric_code,
            unit=activity.unit,
            is_archived=activity.is_archived,
            current_revision_id=activity.current_revision_id,
            created_at=activity.created_at,
            updated_at=activity.updated_at,
            current_revision=current_rev,
            active_ledger_revision=active_rev,
            active_verified_quantity=active_verified_qty,
            net_pending_adjustment=net_pending_adj,
            revisions_count=len(revision_responses),
            revisions=revision_responses,
        )


class VerificationService:
    @staticmethod
    async def get_verification_queue(
        db: AsyncSession, current_user: User
    ) -> List[VerificationQueueItem]:
        """
        Retrieves all pending activity revisions awaiting verification.
        - ADMIN: Sees all pending revisions across the portfolio.
        - PROJECT_MANAGER: Sees pending revisions strictly for assigned projects.
        - FIELD_OFFICER: 403 Forbidden.
        """
        if current_user.role == UserRole.FIELD_OFFICER.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "INSUFFICIENT_ROLE",
                    "message": "Field Officers are not authorized to access the Verification Centre queue.",
                },
            )

        stmt = (
            select(ActivityRevision)
            .join(FieldActivity, FieldActivity.id == ActivityRevision.activity_id)
            .where(
                ActivityRevision.status == ActivityStatus.PENDING.value,
                FieldActivity.is_archived == False,
            )
            .order_by(desc(ActivityRevision.created_at))
            .options(
                selectinload(ActivityRevision.activity).selectinload(FieldActivity.project),
                selectinload(ActivityRevision.activity).selectinload(FieldActivity.created_by),
                selectinload(ActivityRevision.activity).selectinload(FieldActivity.revisions),
                selectinload(ActivityRevision.evidence_files),
            )
        )

        if current_user.role != UserRole.ADMIN.value:
            stmt = stmt.join(
                ProjectAssignment,
                (ProjectAssignment.project_id == FieldActivity.project_id)
                & (ProjectAssignment.user_id == current_user.id),
            )

        result = await db.scalars(stmt)
        revisions = list(result.all())

        queue_items: List[VerificationQueueItem] = []
        for r in revisions:
            activity = r.activity
            project = activity.project

            # Check if this revision is an amendment to a previously verified revision
            prev_active = next(
                (
                    rev
                    for rev in activity.revisions
                    if rev.is_active_ledger_entry and rev.id != r.id
                ),
                None,
            )

            is_amendment = prev_active is not None
            prev_qty = prev_active.quantity if prev_active else None
            net_adj = (r.quantity - prev_qty) if prev_active else r.quantity

            # Anti-Self-Verification rule indicator
            can_verify = current_user.id != activity.created_by_id

            evidence_dtos = [
                EvidenceFileResponse(
                    id=e.id,
                    activity_id=e.activity_id,
                    revision_id=e.revision_id,
                    original_filename=e.original_filename,
                    mime_type=e.mime_type,
                    file_size_bytes=e.file_size_bytes,
                    download_url=f"/api/v1/operations/evidence/{e.id}",
                    uploaded_at=e.uploaded_at,
                )
                for e in r.evidence_files
            ]

            queue_items.append(
                VerificationQueueItem(
                    revision_id=r.id,
                    activity_id=activity.id,
                    project_id=project.id,
                    project_name=project.name,
                    project_code=project.code,
                    creator_id=activity.created_by_id,
                    creator_name=activity.created_by.full_name if activity.created_by else "Unknown",
                    metric_code=activity.metric_code,
                    unit=activity.unit,
                    quantity=r.quantity,
                    activity_date=r.activity_date,
                    latitude=r.latitude,
                    longitude=r.longitude,
                    gps_accuracy_meters=r.gps_accuracy_meters,
                    field_notes=r.field_notes,
                    revision_number=r.revision_number,
                    is_amendment=is_amendment,
                    previously_verified_quantity=prev_qty,
                    net_adjustment=net_adj,
                    evidence_files=evidence_dtos,
                    created_at=r.created_at,
                    can_verify=can_verify,
                )
            )

        return queue_items

    @staticmethod
    async def record_decision(
        db: AsyncSession,
        revision_id: uuid.UUID,
        data: VerificationDecisionRequest,
        current_user: User,
        ip_address: Optional[str] = None,
    ) -> VerificationDecisionResponse:
        """
        Processes a verification review decision (APPROVE/VERIFIED or REJECT).
        Strictly enforces:
        1. Role check: ADMIN or PROJECT_MANAGER.
        2. Project assignment check for PROJECT_MANAGER.
        3. Mandatory Anti-Self-Verification Gate: current_user.id != activity.created_by_id.
        4. Rejection reason code and notes validation.
        5. Atomic single active ledger enforcement.
        6. Recalculation of project verified totals.
        """
        # 1. Role verification
        if current_user.role == UserRole.FIELD_OFFICER.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "INSUFFICIENT_ROLE",
                    "message": "Field Officers are not authorized to verify activities.",
                },
            )

        # 2. Fetch target revision and parent activity with lock to prevent race conditions
        stmt = (
            select(ActivityRevision)
            .where(ActivityRevision.id == revision_id)
            .options(
                selectinload(ActivityRevision.activity).selectinload(FieldActivity.revisions),
                selectinload(ActivityRevision.activity).selectinload(FieldActivity.project),
            )
            .with_for_update()
        )
        revision = await db.scalar(stmt)
        if not revision:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_code": "REVISION_NOT_FOUND",
                    "message": f"Revision with ID {revision_id} not found.",
                },
            )

        activity = revision.activity

        # 3. Project scoping check for Project Managers
        if current_user.role == UserRole.PROJECT_MANAGER.value:
            assignment = await db.scalar(
                select(ProjectAssignment).where(
                    ProjectAssignment.project_id == activity.project_id,
                    ProjectAssignment.user_id == current_user.id,
                )
            )
            if not assignment:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error_code": "PROJECT_ACCESS_DENIED",
                        "message": "You are not assigned to this project.",
                    },
                )

        # 4. Mandatory Rule 5: Anti-Self-Verification Gate
        if current_user.id == activity.created_by_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "SELF_VERIFICATION_PROHIBITED",
                    "message": "Policy Violation: You cannot verify an activity submission you authored.",
                },
            )

        # 5. Check if revision is currently in PENDING status
        if revision.status != ActivityStatus.PENDING.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_code": "REVISION_ALREADY_REVIEWED",
                    "message": f"Revision {revision.revision_number} is already in '{revision.status}' state.",
                },
            )

        now = datetime.now(timezone.utc)

        # 6. Apply Decision
        if data.decision == ActivityStatus.VERIFIED.value:
            # APPROVE / VERIFY PATH
            # Deactivate any existing active ledger entry for this activity
            for rev in activity.revisions:
                if rev.is_active_ledger_entry and rev.id != revision.id:
                    rev.is_active_ledger_entry = False

            await db.flush()

            # Mark target revision as VERIFIED and active ledger entry
            revision.status = ActivityStatus.VERIFIED.value
            revision.is_active_ledger_entry = True
            revision.verifier_id = current_user.id
            revision.verified_at = now
            revision.review_notes = data.review_notes.strip() if data.review_notes else None
            revision.rejection_reason_code = None

            activity.current_revision_id = revision.id
            await db.flush()

            action_type = "ACTIVITY_VERIFIED"
            audit_new_state = {
                "activity_id": str(activity.id),
                "revision_id": str(revision.id),
                "revision_number": revision.revision_number,
                "status": revision.status,
                "verified_quantity": float(revision.quantity),
                "verifier_id": str(current_user.id),
                "verified_at": now.isoformat(),
            }

        else:
            # REJECT PATH
            revision.status = ActivityStatus.REJECTED.value
            revision.is_active_ledger_entry = False
            revision.verifier_id = current_user.id
            revision.verified_at = now
            revision.rejection_reason_code = data.rejection_reason_code
            revision.review_notes = data.review_notes.strip() if data.review_notes else None
            await db.flush()

            # Note: Any previously verified revision's is_active_ledger_entry remains True!
            action_type = "ACTIVITY_REJECTED"
            audit_new_state = {
                "activity_id": str(activity.id),
                "revision_id": str(revision.id),
                "revision_number": revision.revision_number,
                "status": revision.status,
                "rejection_reason_code": revision.rejection_reason_code,
                "review_notes": revision.review_notes,
                "verifier_id": str(current_user.id),
                "verified_at": now.isoformat(),
            }

        # 7. Recalculate Project Verified Total for this metric
        recalculated_total_stmt = (
            select(func.coalesce(func.sum(ActivityRevision.quantity), Decimal("0.0")))
            .select_from(ActivityRevision)
            .join(FieldActivity, FieldActivity.id == ActivityRevision.activity_id)
            .where(
                FieldActivity.project_id == activity.project_id,
                FieldActivity.metric_code == activity.metric_code,
                FieldActivity.is_archived == False,
                ActivityRevision.is_active_ledger_entry == True,
            )
        )
        recalculated_total = await db.scalar(recalculated_total_stmt) or Decimal("0.0")

        # 8. Record Immutable Audit Log
        await record_audit_log(
            db=db,
            action_type=action_type,
            entity_type="activity_revision",
            entity_id=revision.id,
            actor_id=current_user.id,
            new_state={
                **audit_new_state,
                "project_verified_total_recalculated": float(recalculated_total),
            },
            ip_address=ip_address,
        )

        await db.commit()

        return VerificationDecisionResponse(
            revision_id=revision.id,
            activity_id=activity.id,
            status=revision.status,
            is_active_ledger_entry=revision.is_active_ledger_entry,
            verifier_id=current_user.id,
            verifier_name=current_user.full_name,
            verified_at=now,
            review_notes=revision.review_notes,
            rejection_reason_code=revision.rejection_reason_code,
            project_verified_total_recalculated=recalculated_total,
        )


class EvidenceService:
    @staticmethod
    async def get_evidence_file_path(
        db: AsyncSession, evidence_id: uuid.UUID, current_user: User
    ) -> Tuple[Path, str, str]:
        """
        Resolves evidence file path and metadata.
        Enforces project-level authorization before serving file bytes.
        Returns: (file_path, mime_type, original_filename)
        """
        stmt = (
            select(EvidenceFile)
            .where(EvidenceFile.id == evidence_id)
            .options(
                selectinload(EvidenceFile.activity),
                selectinload(EvidenceFile.inspection),
            )
        )
        evidence = await db.scalar(stmt)
        if not evidence:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_code": "EVIDENCE_NOT_FOUND",
                    "message": f"Evidence file with ID {evidence_id} not found.",
                },
            )

        # Scoping check: verify access to project (via activity or inspection)
        project_id = (
            evidence.activity.project_id
            if evidence.activity
            else (evidence.inspection.project_id if evidence.inspection else None)
        )
        if project_id:
            await ActivityService.verify_project_assignment(
                db, project_id, current_user
            )

        storage = get_storage_service()
        try:
            file_path = storage.get_file_path(evidence.file_storage_key)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_code": "INVALID_STORAGE_KEY",
                    "message": str(e),
                },
            )

        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_code": "FILE_NOT_FOUND_ON_DISK",
                    "message": "The physical evidence file could not be found on storage.",
                },
            )

        return file_path, evidence.mime_type, evidence.original_filename
