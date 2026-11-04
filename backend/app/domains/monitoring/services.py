"""
VANA — Field Monitoring & Follow-up Management Domain Services
Enforces server-side authorization, deterministic state machines,
cross-project composite integrity, atomic survival supersession,
derived survival rate calculations, dynamic alert evaluations,
and immutable audit logging.
"""

from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import uuid

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import and_, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.storage import get_storage_service
from app.domains.audit.services import record_audit_log
from app.domains.auth.models import User, UserRole
from app.domains.monitoring.models import (
    FieldInspection,
    InspectionStatus,
    InspectionType,
    MaintenanceTask,
    SurvivalMethodology,
    SurvivalObservation,
    TaskCategory,
    TaskPriority,
    TaskStatus,
)
from app.domains.monitoring.schemas import (
    AlertSeverity,
    AlertType,
    FieldInspectionCreate,
    InspectionAddendumCreate,
    InspectionCancelRequest,
    InspectionCompleteRequest,
    MaintenanceTaskCreate,
    MonitoringAlertItem,
    MonitoringAlertSummaryResponse,
    SurvivalObservationCorrectionRequest,
    SurvivalObservationCreate,
    TaskCancelRequest,
    TaskCompleteRequest,
    TaskReopenRequest,
)
from app.domains.operations.models import EvidenceFile, FieldActivity
from app.domains.operations.services import ALLOWED_MIME_TYPES, MAX_FILE_SIZE_BYTES
from app.domains.projects.models import Project
from app.domains.teams.models import ProjectAssignment


# ============================================================================
# Authorization & Project Boundary Helpers
# ============================================================================


class MonitoringAuthorizationService:
    @staticmethod
    async def verify_project_access(
        db: AsyncSession,
        user: User,
        project_id: uuid.UUID,
        allowed_roles: Optional[List[UserRole]] = None,
    ) -> Project:
        """
        Verifies that the target project exists and that the user is authorized to access it.
        ADMIN: Organization-wide access.
        PROJECT_MANAGER & FIELD_OFFICER: Must have an active assignment to the project.
        """
        # Role boundary check
        if allowed_roles is not None:
            allowed_role_values = [r.value for r in allowed_roles]
            if user.role not in allowed_role_values:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="INSUFFICIENT_ROLE_PERMISSIONS: User role is not authorized for this operation",
                )

        # Retrieve project
        project = await db.scalar(select(Project).where(Project.id == project_id))
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="PROJECT_NOT_FOUND: Project does not exist",
            )

        # Admin bypasses assignment checks
        if user.role == UserRole.ADMIN.value:
            return project

        # Verify active ProjectAssignment
        assignment = await db.scalar(
            select(ProjectAssignment).where(
                ProjectAssignment.project_id == project_id,
                ProjectAssignment.user_id == user.id,
            )
        )
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="PROJECT_ACCESS_DENIED: User is not assigned to this project",
            )

        return project

    @staticmethod
    async def get_scoped_project_ids(
        db: AsyncSession, user: User, requested_project_id: Optional[uuid.UUID] = None
    ) -> List[uuid.UUID]:
        """
        Returns authorized project IDs for the user.
        If requested_project_id is provided, validates access and returns [requested_project_id].
        """
        if requested_project_id is not None:
            await MonitoringAuthorizationService.verify_project_access(
                db, user, requested_project_id
            )
            return [requested_project_id]

        if user.role == UserRole.ADMIN.value:
            result = await db.execute(select(Project.id))
            return [row[0] for row in result.fetchall()]

        result = await db.execute(
            select(ProjectAssignment.project_id).where(ProjectAssignment.user_id == user.id)
        )
        return [row[0] for row in result.fetchall()]


# ============================================================================
# Field Inspection Management Service
# ============================================================================


class InspectionService:
    @staticmethod
    async def schedule_inspection(
        db: AsyncSession, user: User, data: FieldInspectionCreate
    ) -> FieldInspection:
        """
        Schedules a new field inspection.
        Restricted to ADMIN and assigned PROJECT_MANAGER.
        Validates project assignment for assigned inspector and cross-project activity link.
        """
        # RBAC: Field Officer cannot schedule inspections
        await MonitoringAuthorizationService.verify_project_access(
            db,
            user,
            data.project_id,
            allowed_roles=[UserRole.ADMIN, UserRole.PROJECT_MANAGER],
        )

        # Validate inspector assignment to project if assigned_to_id is provided
        if data.assigned_to_id is not None:
            inspector = await db.scalar(
                select(User).where(User.id == data.assigned_to_id, User.is_active == True)
            )
            if not inspector:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="INSPECTOR_NOT_FOUND_OR_INACTIVE: Assigned inspector does not exist or is deactivated",
                )

            # Inspector must have an active assignment to the project
            inspector_assignment = await db.scalar(
                select(ProjectAssignment).where(
                    ProjectAssignment.project_id == data.project_id,
                    ProjectAssignment.user_id == data.assigned_to_id,
                )
            )
            if not inspector_assignment and inspector.role != UserRole.ADMIN.value:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="INSPECTOR_NOT_ASSIGNED_TO_PROJECT: Assigned inspector must be assigned to the project",
                )

        # Validate linked activity if provided
        if data.linked_activity_id is not None:
            activity = await db.scalar(
                select(FieldActivity).where(FieldActivity.id == data.linked_activity_id)
            )
            if not activity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="LINKED_ACTIVITY_NOT_FOUND: Referenced activity does not exist",
                )
            if activity.project_id != data.project_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="CROSS_PROJECT_ACTIVITY_LINK_FORBIDDEN: Linked activity belongs to a different project",
                )

        inspection = FieldInspection(
            id=uuid.uuid4(),
            project_id=data.project_id,
            linked_activity_id=data.linked_activity_id,
            scheduled_date=data.scheduled_date,
            status=InspectionStatus.SCHEDULED.value,
            inspection_type=data.inspection_type.value,
            assigned_to_id=data.assigned_to_id,
            findings=None,
            vegetation_health_score=None,
            canopy_condition=None,
            soil_moisture_condition=None,
            threats_detected=[],
            addenda=[],
        )
        db.add(inspection)
        await db.flush()

        await record_audit_log(
            db=db,
            action_type="INSPECTION_SCHEDULED",
            entity_type="FieldInspection",
            entity_id=inspection.id,
            actor_id=user.id,
            previous_state=None,
            new_state={
                "id": str(inspection.id),
                "project_id": str(inspection.project_id),
                "scheduled_date": str(inspection.scheduled_date),
                "inspection_type": inspection.inspection_type,
                "assigned_to_id": str(inspection.assigned_to_id) if inspection.assigned_to_id else None,
                "linked_activity_id": str(inspection.linked_activity_id) if inspection.linked_activity_id else None,
                "status": inspection.status,
            },
        )

        return inspection

    @staticmethod
    async def get_inspection(
        db: AsyncSession, user: User, inspection_id: uuid.UUID
    ) -> FieldInspection:
        """Retrieves inspection by ID with project access validation."""
        inspection = await db.scalar(
            select(FieldInspection)
            .options(
                selectinload(FieldInspection.project),
                selectinload(FieldInspection.assigned_to),
                selectinload(FieldInspection.linked_activity),
            )
            .where(FieldInspection.id == inspection_id)
        )
        if not inspection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="INSPECTION_NOT_FOUND: Inspection does not exist",
            )

        await MonitoringAuthorizationService.verify_project_access(
            db, user, inspection.project_id
        )
        return inspection

    @staticmethod
    async def list_inspections(
        db: AsyncSession,
        user: User,
        project_id: Optional[uuid.UUID] = None,
        status_filter: Optional[str] = None,
        assigned_to_id: Optional[uuid.UUID] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> List[FieldInspection]:
        """Lists field inspections with multi-tenant role scoping and filters."""
        scoped_project_ids = await MonitoringAuthorizationService.get_scoped_project_ids(
            db, user, project_id
        )
        if not scoped_project_ids:
            return []

        query = select(FieldInspection).where(FieldInspection.project_id.in_(scoped_project_ids))

        if status_filter:
            query = query.where(FieldInspection.status == status_filter)
        if assigned_to_id:
            query = query.where(FieldInspection.assigned_to_id == assigned_to_id)
        if from_date:
            query = query.where(FieldInspection.scheduled_date >= from_date)
        if to_date:
            query = query.where(FieldInspection.scheduled_date <= to_date)

        query = query.order_by(FieldInspection.scheduled_date.desc(), FieldInspection.created_at.desc())
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def start_inspection(
        db: AsyncSession, user: User, inspection_id: uuid.UUID, notes: Optional[str] = None
    ) -> FieldInspection:
        """
        Transitions inspection from SCHEDULED to IN_PROGRESS.
        Field Officers can only start inspections assigned to them.
        """
        query = (
            select(FieldInspection)
            .where(FieldInspection.id == inspection_id)
            .with_for_update()
        )
        inspection = await db.scalar(query)
        if not inspection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="INSPECTION_NOT_FOUND: Inspection does not exist",
            )

        await MonitoringAuthorizationService.verify_project_access(
            db, user, inspection.project_id
        )

        # Field Officer ownership check
        if user.role == UserRole.FIELD_OFFICER.value and inspection.assigned_to_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="INSPECTOR_OWNERSHIP_REQUIRED: Field Officers can only start inspections assigned to them",
            )

        # State machine validation: SCHEDULED -> IN_PROGRESS
        if inspection.status != InspectionStatus.SCHEDULED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"INVALID_STATUS_TRANSITION: Cannot start inspection in status '{inspection.status}'. Expected 'SCHEDULED'.",
            )

        prev_status = inspection.status
        inspection.status = InspectionStatus.IN_PROGRESS.value
        await db.flush()

        await record_audit_log(
            db=db,
            action_type="INSPECTION_STARTED",
            entity_type="FieldInspection",
            entity_id=inspection.id,
            actor_id=user.id,
            previous_state={"status": prev_status},
            new_state={"status": inspection.status, "notes": notes},
        )

        return inspection

    @staticmethod
    async def complete_inspection(
        db: AsyncSession,
        user: User,
        inspection_id: uuid.UUID,
        data: InspectionCompleteRequest,
    ) -> FieldInspection:
        """
        Transitions inspection from IN_PROGRESS to COMPLETED.
        Requires mandatory findings. Locks the inspection against direct edits.
        Field Officers can only complete inspections assigned to them.
        """
        query = (
            select(FieldInspection)
            .where(FieldInspection.id == inspection_id)
            .with_for_update()
        )
        inspection = await db.scalar(query)
        if not inspection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="INSPECTION_NOT_FOUND: Inspection does not exist",
            )

        await MonitoringAuthorizationService.verify_project_access(
            db, user, inspection.project_id
        )

        # Field Officer ownership check
        if user.role == UserRole.FIELD_OFFICER.value and inspection.assigned_to_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="INSPECTOR_OWNERSHIP_REQUIRED: Field Officers can only complete inspections assigned to them",
            )

        # Check completed immutability
        if inspection.status == InspectionStatus.COMPLETED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="COMPLETED_INSPECTION_LOCKED: Completed inspections cannot be directly edited. Use correction addenda.",
            )

        # State machine validation: must be IN_PROGRESS
        if inspection.status != InspectionStatus.IN_PROGRESS.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"INVALID_STATUS_TRANSITION: Cannot complete inspection in status '{inspection.status}'. Inspection must be 'IN_PROGRESS'.",
            )

        findings_clean = data.findings.strip()
        if not findings_clean:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="FINDINGS_MANDATORY: Inspection findings cannot be empty",
            )

        prev_status = inspection.status
        inspection.status = InspectionStatus.COMPLETED.value
        inspection.completed_at = datetime.now(timezone.utc)
        inspection.findings = findings_clean
        inspection.vegetation_health_score = data.vegetation_health_score
        inspection.canopy_condition = (
            data.canopy_condition.value if data.canopy_condition else None
        )
        inspection.soil_moisture_condition = (
            data.soil_moisture_condition.value if data.soil_moisture_condition else None
        )
        inspection.threats_detected = data.threats_detected or []

        await db.flush()

        await record_audit_log(
            db=db,
            action_type="INSPECTION_COMPLETED",
            entity_type="FieldInspection",
            entity_id=inspection.id,
            actor_id=user.id,
            previous_state={"status": prev_status},
            new_state={
                "status": inspection.status,
                "completed_at": inspection.completed_at.isoformat(),
                "findings": inspection.findings,
                "vegetation_health_score": inspection.vegetation_health_score,
                "canopy_condition": inspection.canopy_condition,
                "soil_moisture_condition": inspection.soil_moisture_condition,
                "threats_detected": inspection.threats_detected,
            },
        )

        return inspection

    @staticmethod
    async def cancel_inspection(
        db: AsyncSession,
        user: User,
        inspection_id: uuid.UUID,
        data: InspectionCancelRequest,
    ) -> FieldInspection:
        """
        Cancels an inspection from SCHEDULED or IN_PROGRESS.
        Restricted to ADMIN and assigned PROJECT_MANAGER with mandatory cancellation reason.
        Completed inspections cannot be cancelled.
        """
        query = (
            select(FieldInspection)
            .where(FieldInspection.id == inspection_id)
            .with_for_update()
        )
        inspection = await db.scalar(query)
        if not inspection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="INSPECTION_NOT_FOUND: Inspection does not exist",
            )

        # RBAC: Field Officer cannot cancel inspections
        await MonitoringAuthorizationService.verify_project_access(
            db,
            user,
            inspection.project_id,
            allowed_roles=[UserRole.ADMIN, UserRole.PROJECT_MANAGER],
        )

        if inspection.status in (InspectionStatus.COMPLETED.value, InspectionStatus.CANCELLED.value):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"INVALID_STATUS_TRANSITION: Cannot cancel inspection in status '{inspection.status}'",
            )

        prev_status = inspection.status
        inspection.status = InspectionStatus.CANCELLED.value

        # Append cancellation note to addenda
        cancellation_entry = {
            "id": str(uuid.uuid4()),
            "type": "CANCELLATION",
            "author_id": str(user.id),
            "author_name": user.full_name,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "reason": data.cancellation_reason.strip(),
        }
        inspection.addenda = list(inspection.addenda or []) + [cancellation_entry]
        await db.flush()

        await record_audit_log(
            db=db,
            action_type="INSPECTION_CANCELLED",
            entity_type="FieldInspection",
            entity_id=inspection.id,
            actor_id=user.id,
            previous_state={"status": prev_status},
            new_state={
                "status": inspection.status,
                "cancellation_reason": data.cancellation_reason.strip(),
            },
        )

        return inspection

    @staticmethod
    async def add_addendum(
        db: AsyncSession,
        user: User,
        inspection_id: uuid.UUID,
        data: InspectionAddendumCreate,
    ) -> FieldInspection:
        """
        Records an immutable post-completion correction addendum on a COMPLETED inspection.
        Restricted to ADMIN and assigned PROJECT_MANAGER.
        Does not mutate the original findings or health scores.
        """
        query = (
            select(FieldInspection)
            .where(FieldInspection.id == inspection_id)
            .with_for_update()
        )
        inspection = await db.scalar(query)
        if not inspection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="INSPECTION_NOT_FOUND: Inspection does not exist",
            )

        # RBAC: Field Officer cannot record addenda
        await MonitoringAuthorizationService.verify_project_access(
            db,
            user,
            inspection.project_id,
            allowed_roles=[UserRole.ADMIN, UserRole.PROJECT_MANAGER],
        )

        if inspection.status != InspectionStatus.COMPLETED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ADDENDUM_REQUIRES_COMPLETED_INSPECTION: Addenda can only be recorded on COMPLETED inspections",
            )

        content_clean = data.content.strip()
        if not content_clean:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ADDENDUM_CONTENT_MANDATORY: Addendum content cannot be empty",
            )

        addendum_entry = {
            "id": str(uuid.uuid4()),
            "type": "CORRECTION_ADDENDUM",
            "author_id": str(user.id),
            "author_name": user.full_name,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "content": content_clean,
        }
        inspection.addenda = list(inspection.addenda or []) + [addendum_entry]
        await db.flush()

        await record_audit_log(
            db=db,
            action_type="INSPECTION_ADDENDUM_RECORDED",
            entity_type="FieldInspection",
            entity_id=inspection.id,
            actor_id=user.id,
            previous_state=None,
            new_state={"addendum": addendum_entry},
        )

        return inspection

    @staticmethod
    async def upload_evidence(
        db: AsyncSession,
        user: User,
        inspection_id: uuid.UUID,
        file: UploadFile,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        caption: Optional[str] = None,
    ) -> EvidenceFile:
        """
        Uploads and attaches photo or document evidence to an inspection.
        Restricted to ADMIN, assigned PM, or assigned Field Officer.
        Enforces SHA-256 storage, MIME type validation, file size <= 10MB.
        """
        inspection = await db.scalar(
            select(FieldInspection).where(FieldInspection.id == inspection_id)
        )
        if not inspection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="INSPECTION_NOT_FOUND: Inspection does not exist",
            )

        await MonitoringAuthorizationService.verify_project_access(
            db, user, inspection.project_id
        )

        if user.role == UserRole.FIELD_OFFICER.value and inspection.assigned_to_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="INSPECTOR_OWNERSHIP_REQUIRED: Field Officers can only upload evidence to their own assigned inspections",
            )

        if file.content_type not in ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"UNSUPPORTED_MEDIA_TYPE: Allowed formats: {', '.join(sorted(ALLOWED_MIME_TYPES))}",
            )

        content = await file.read()
        if len(content) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="EMPTY_FILE: Evidence file cannot be empty",
            )
        if len(content) > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"FILE_TOO_LARGE: Maximum file size is {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB",
            )

        storage = get_storage_service()
        storage_key = await storage.upload_file(file_content=content, original_filename=file.filename or "evidence.jpg")

        evidence = EvidenceFile(
            id=uuid.uuid4(),
            activity_id=None,
            revision_id=None,
            inspection_id=inspection.id,
            file_storage_key=storage_key,
            original_filename=file.filename or "evidence.jpg",
            mime_type=file.content_type,
            file_size_bytes=len(content),
            latitude=latitude,
            longitude=longitude,
            caption=caption.strip() if caption else None,
        )
        db.add(evidence)
        await db.flush()

        await record_audit_log(
            db=db,
            action_type="INSPECTION_EVIDENCE_UPLOADED",
            entity_type="EvidenceFile",
            entity_id=evidence.id,
            actor_id=user.id,
            previous_state=None,
            new_state={
                "id": str(evidence.id),
                "inspection_id": str(inspection.id),
                "project_id": str(inspection.project_id),
                "filename": evidence.original_filename,
                "file_size_bytes": evidence.file_size_bytes,
            },
        )
        return evidence


# ============================================================================
# Maintenance Task Service
# ============================================================================


class MaintenanceTaskService:
    @staticmethod
    async def create_task(
        db: AsyncSession, user: User, data: MaintenanceTaskCreate
    ) -> MaintenanceTask:
        """
        Creates a new maintenance task.
        Restricted to ADMIN and assigned PROJECT_MANAGER.
        Validates assignee project assignment and cross-project inspection/activity links.
        """
        await MonitoringAuthorizationService.verify_project_access(
            db,
            user,
            data.project_id,
            allowed_roles=[UserRole.ADMIN, UserRole.PROJECT_MANAGER],
        )

        # Validate assignee project membership if provided
        if data.assigned_to_id is not None:
            assignee = await db.scalar(
                select(User).where(User.id == data.assigned_to_id, User.is_active == True)
            )
            if not assignee:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="ASSIGNEE_NOT_FOUND_OR_INACTIVE: Assigned user does not exist or is deactivated",
                )
            assignee_assignment = await db.scalar(
                select(ProjectAssignment).where(
                    ProjectAssignment.project_id == data.project_id,
                    ProjectAssignment.user_id == data.assigned_to_id,
                )
            )
            if not assignee_assignment and assignee.role != UserRole.ADMIN.value:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="ASSIGNEE_NOT_ASSIGNED_TO_PROJECT: Assignee must be assigned to the project",
                )

        # Validate linked inspection
        if data.inspection_id is not None:
            inspection = await db.scalar(
                select(FieldInspection).where(FieldInspection.id == data.inspection_id)
            )
            if not inspection:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="LINKED_INSPECTION_NOT_FOUND: Referenced inspection does not exist",
                )
            if inspection.project_id != data.project_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="CROSS_PROJECT_INSPECTION_LINK_FORBIDDEN: Referenced inspection belongs to a different project",
                )

        # Validate linked activity
        if data.activity_id is not None:
            activity = await db.scalar(
                select(FieldActivity).where(FieldActivity.id == data.activity_id)
            )
            if not activity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="LINKED_ACTIVITY_NOT_FOUND: Referenced activity does not exist",
                )
            if activity.project_id != data.project_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="CROSS_PROJECT_ACTIVITY_LINK_FORBIDDEN: Referenced activity belongs to a different project",
                )

        task = MaintenanceTask(
            id=uuid.uuid4(),
            project_id=data.project_id,
            inspection_id=data.inspection_id,
            activity_id=data.activity_id,
            title=data.title.strip(),
            description=data.description.strip() if data.description else None,
            category=data.category.value,
            priority=data.priority.value,
            status=TaskStatus.TODO.value,
            due_date=data.due_date,
            assigned_to_id=data.assigned_to_id,
            completed_at=None,
            completion_notes=None,
        )
        db.add(task)
        await db.flush()

        await record_audit_log(
            db=db,
            action_type="TASK_CREATED",
            entity_type="MaintenanceTask",
            entity_id=task.id,
            actor_id=user.id,
            previous_state=None,
            new_state={
                "id": str(task.id),
                "project_id": str(task.project_id),
                "title": task.title,
                "category": task.category,
                "priority": task.priority,
                "due_date": str(task.due_date),
                "assigned_to_id": str(task.assigned_to_id) if task.assigned_to_id else None,
                "status": task.status,
            },
        )

        return task

    @staticmethod
    async def get_task(
        db: AsyncSession, user: User, task_id: uuid.UUID
    ) -> MaintenanceTask:
        """Retrieves maintenance task by ID with project access validation."""
        task = await db.scalar(
            select(MaintenanceTask)
            .options(
                selectinload(MaintenanceTask.project),
                selectinload(MaintenanceTask.assigned_to),
                selectinload(MaintenanceTask.inspection),
                selectinload(MaintenanceTask.activity),
            )
            .where(MaintenanceTask.id == task_id)
        )
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="TASK_NOT_FOUND: Maintenance task does not exist",
            )

        await MonitoringAuthorizationService.verify_project_access(
            db, user, task.project_id
        )
        return task

    @staticmethod
    async def list_tasks(
        db: AsyncSession,
        user: User,
        project_id: Optional[uuid.UUID] = None,
        status_filter: Optional[str] = None,
        assigned_to_id: Optional[uuid.UUID] = None,
        priority_filter: Optional[str] = None,
        category_filter: Optional[str] = None,
    ) -> List[MaintenanceTask]:
        """Lists maintenance tasks with multi-tenant role scoping and filters."""
        scoped_project_ids = await MonitoringAuthorizationService.get_scoped_project_ids(
            db, user, project_id
        )
        if not scoped_project_ids:
            return []

        query = select(MaintenanceTask).where(MaintenanceTask.project_id.in_(scoped_project_ids))

        if status_filter:
            query = query.where(MaintenanceTask.status == status_filter)
        if assigned_to_id:
            query = query.where(MaintenanceTask.assigned_to_id == assigned_to_id)
        if priority_filter:
            query = query.where(MaintenanceTask.priority == priority_filter)
        if category_filter:
            query = query.where(MaintenanceTask.category == category_filter)

        query = query.order_by(MaintenanceTask.due_date.asc(), MaintenanceTask.created_at.desc())
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def start_task(
        db: AsyncSession, user: User, task_id: uuid.UUID, notes: Optional[str] = None
    ) -> MaintenanceTask:
        """
        Transitions task from TODO to IN_PROGRESS.
        Field Officers can only start tasks assigned to them.
        """
        query = (
            select(MaintenanceTask)
            .where(MaintenanceTask.id == task_id)
            .with_for_update()
        )
        task = await db.scalar(query)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="TASK_NOT_FOUND: Maintenance task does not exist",
            )

        await MonitoringAuthorizationService.verify_project_access(
            db, user, task.project_id
        )

        # Field Officer ownership check
        if user.role == UserRole.FIELD_OFFICER.value and task.assigned_to_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="TASK_OWNERSHIP_REQUIRED: Field Officers can only start tasks assigned to them",
            )

        # State machine validation: TODO -> IN_PROGRESS
        if task.status != TaskStatus.TODO.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"INVALID_STATUS_TRANSITION: Cannot start task in status '{task.status}'. Expected 'TODO'.",
            )

        prev_status = task.status
        task.status = TaskStatus.IN_PROGRESS.value
        await db.flush()

        await record_audit_log(
            db=db,
            action_type="TASK_STARTED",
            entity_type="MaintenanceTask",
            entity_id=task.id,
            actor_id=user.id,
            previous_state={"status": prev_status},
            new_state={"status": task.status, "notes": notes},
        )

        return task

    @staticmethod
    async def complete_task(
        db: AsyncSession,
        user: User,
        task_id: uuid.UUID,
        data: TaskCompleteRequest,
    ) -> MaintenanceTask:
        """
        Transitions task from IN_PROGRESS (or TODO) to COMPLETED with mandatory completion notes.
        Field Officers can only complete tasks assigned to them.
        """
        query = (
            select(MaintenanceTask)
            .where(MaintenanceTask.id == task_id)
            .with_for_update()
        )
        task = await db.scalar(query)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="TASK_NOT_FOUND: Maintenance task does not exist",
            )

        await MonitoringAuthorizationService.verify_project_access(
            db, user, task.project_id
        )

        # Field Officer ownership check
        if user.role == UserRole.FIELD_OFFICER.value and task.assigned_to_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="TASK_OWNERSHIP_REQUIRED: Field Officers can only complete tasks assigned to them",
            )

        if task.status not in (TaskStatus.TODO.value, TaskStatus.IN_PROGRESS.value):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"INVALID_STATUS_TRANSITION: Cannot complete task in status '{task.status}'",
            )

        notes_clean = data.completion_notes.strip()
        if not notes_clean:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="COMPLETION_NOTES_MANDATORY: Completion notes cannot be empty",
            )

        prev_status = task.status
        task.status = TaskStatus.COMPLETED.value
        task.completed_at = datetime.now(timezone.utc)
        task.completion_notes = notes_clean
        await db.flush()

        await record_audit_log(
            db=db,
            action_type="TASK_COMPLETED",
            entity_type="MaintenanceTask",
            entity_id=task.id,
            actor_id=user.id,
            previous_state={"status": prev_status},
            new_state={
                "status": task.status,
                "completed_at": task.completed_at.isoformat(),
                "completion_notes": task.completion_notes,
            },
        )

        return task

    @staticmethod
    async def cancel_task(
        db: AsyncSession,
        user: User,
        task_id: uuid.UUID,
        data: TaskCancelRequest,
    ) -> MaintenanceTask:
        """
        Cancels an open task.
        Restricted to ADMIN and assigned PROJECT_MANAGER with mandatory cancellation reason.
        Completed tasks cannot be cancelled.
        """
        query = (
            select(MaintenanceTask)
            .where(MaintenanceTask.id == task_id)
            .with_for_update()
        )
        task = await db.scalar(query)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="TASK_NOT_FOUND: Maintenance task does not exist",
            )

        # RBAC: Field Officer cannot cancel tasks
        await MonitoringAuthorizationService.verify_project_access(
            db,
            user,
            task.project_id,
            allowed_roles=[UserRole.ADMIN, UserRole.PROJECT_MANAGER],
        )

        if task.status in (TaskStatus.COMPLETED.value, TaskStatus.CANCELLED.value):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"INVALID_STATUS_TRANSITION: Cannot cancel task in status '{task.status}'",
            )

        prev_status = task.status
        task.status = TaskStatus.CANCELLED.value
        reason = data.cancellation_reason.strip()
        task.completion_notes = f"CANCELLED: {reason}"
        await db.flush()

        await record_audit_log(
            db=db,
            action_type="TASK_CANCELLED",
            entity_type="MaintenanceTask",
            entity_id=task.id,
            actor_id=user.id,
            previous_state={"status": prev_status},
            new_state={"status": task.status, "cancellation_reason": reason},
        )

        return task

    @staticmethod
    async def reopen_task(
        db: AsyncSession,
        user: User,
        task_id: uuid.UUID,
        data: TaskReopenRequest,
    ) -> MaintenanceTask:
        """
        Reopens a COMPLETED task back to TODO.
        Restricted to ADMIN and assigned PROJECT_MANAGER with mandatory justification.
        """
        query = (
            select(MaintenanceTask)
            .where(MaintenanceTask.id == task_id)
            .with_for_update()
        )
        task = await db.scalar(query)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="TASK_NOT_FOUND: Maintenance task does not exist",
            )

        # RBAC: Field Officer cannot reopen tasks
        await MonitoringAuthorizationService.verify_project_access(
            db,
            user,
            task.project_id,
            allowed_roles=[UserRole.ADMIN, UserRole.PROJECT_MANAGER],
        )

        if task.status != TaskStatus.COMPLETED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"TASK_REOPEN_REQUIRES_COMPLETED_TASK: Cannot reopen task in status '{task.status}'. Only COMPLETED tasks can be reopened.",
            )

        justification_clean = data.justification.strip()
        if not justification_clean:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="REOPEN_JUSTIFICATION_MANDATORY: Reopen justification cannot be empty",
            )

        prev_status = task.status
        prev_completed_at = task.completed_at.isoformat() if task.completed_at else None
        prev_notes = task.completion_notes

        task.status = TaskStatus.TODO.value
        task.completed_at = None
        task.completion_notes = f"REOPENED by {user.full_name}: {justification_clean} | Previous Notes: {prev_notes or ''}"
        await db.flush()

        await record_audit_log(
            db=db,
            action_type="TASK_REOPENED",
            entity_type="MaintenanceTask",
            entity_id=task.id,
            actor_id=user.id,
            previous_state={"status": prev_status, "completed_at": prev_completed_at},
            new_state={"status": task.status, "justification": justification_clean},
        )

        return task


# ============================================================================
# Survival Observation Service
# ============================================================================


class SurvivalObservationService:
    @staticmethod
    async def create_observation(
        db: AsyncSession, user: User, data: SurvivalObservationCreate
    ) -> SurvivalObservation:
        """
        Creates a new survival observation.
        Permitted for ADMIN, assigned PM, and assigned FIELD_OFFICER.
        Server calculates survival rate dynamically; client-supplied survival_rate is ignored.
        Enforces single active observation per (project_id, plot, cohort, observation_date).
        """
        await MonitoringAuthorizationService.verify_project_access(
            db, user, data.project_id
        )

        # Validate cross-project activity reference if provided
        if data.activity_id is not None:
            activity = await db.scalar(
                select(FieldActivity).where(FieldActivity.id == data.activity_id)
            )
            if not activity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="LINKED_ACTIVITY_NOT_FOUND: Referenced activity does not exist",
                )
            if activity.project_id != data.project_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="CROSS_PROJECT_ACTIVITY_LINK_FORBIDDEN: Referenced activity belongs to a different project",
                )

        # Validate cross-project inspection reference if provided
        if data.inspection_id is not None:
            inspection = await db.scalar(
                select(FieldInspection).where(FieldInspection.id == data.inspection_id)
            )
            if not inspection:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="LINKED_INSPECTION_NOT_FOUND: Referenced inspection does not exist",
                )
            if inspection.project_id != data.project_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="CROSS_PROJECT_INSPECTION_LINK_FORBIDDEN: Referenced inspection belongs to a different project",
                )

        # Scientific count validations: (alive + dead) <= sample_size
        if (data.alive_count + data.dead_count) > data.sample_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"INVALID_SURVIVAL_SUM: Sum of alive ({data.alive_count}) and dead ({data.dead_count}) cannot exceed sample size ({data.sample_size})",
            )

        # Check for active duplicate observation on same date
        existing_active = await db.scalar(
            select(SurvivalObservation).where(
                SurvivalObservation.project_id == data.project_id,
                SurvivalObservation.plot_identifier == data.plot_identifier,
                SurvivalObservation.cohort_identifier == data.cohort_identifier,
                SurvivalObservation.observation_date == data.observation_date,
                SurvivalObservation.is_active == True,
            )
        )
        if existing_active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="ACTIVE_OBSERVATION_ALREADY_EXISTS: An active observation already exists for this plot, cohort, and observation date. Use the supersession endpoint to record a correction.",
            )

        observation = SurvivalObservation(
            id=uuid.uuid4(),
            project_id=data.project_id,
            activity_id=data.activity_id,
            inspection_id=data.inspection_id,
            plot_identifier=data.plot_identifier.strip(),
            cohort_identifier=data.cohort_identifier.strip(),
            methodology=data.methodology.value,
            coverage_area_sqm=data.coverage_area_sqm,
            observation_date=data.observation_date,
            sample_size=data.sample_size,
            alive_count=data.alive_count,
            dead_count=data.dead_count,
            mortality_causes=data.mortality_causes or [],
            is_definitive=data.is_definitive,
            is_active=True,
            superseded_by_id=None,
            correction_notes=None,
            notes=data.notes.strip() if data.notes else None,
        )
        db.add(observation)
        await db.flush()

        await record_audit_log(
            db=db,
            action_type="SURVIVAL_OBSERVATION_CREATED",
            entity_type="SurvivalObservation",
            entity_id=observation.id,
            actor_id=user.id,
            previous_state=None,
            new_state={
                "id": str(observation.id),
                "project_id": str(observation.project_id),
                "plot_identifier": observation.plot_identifier,
                "cohort_identifier": observation.cohort_identifier,
                "observation_date": str(observation.observation_date),
                "sample_size": observation.sample_size,
                "alive_count": observation.alive_count,
                "dead_count": observation.dead_count,
                "survival_rate": observation.survival_rate,
                "methodology": observation.methodology,
            },
        )

        return observation

    @staticmethod
    async def get_observation(
        db: AsyncSession, user: User, observation_id: uuid.UUID
    ) -> SurvivalObservation:
        """Retrieves observation by ID with project access validation."""
        observation = await db.scalar(
            select(SurvivalObservation).where(SurvivalObservation.id == observation_id)
        )
        if not observation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="OBSERVATION_NOT_FOUND: Survival observation does not exist",
            )

        await MonitoringAuthorizationService.verify_project_access(
            db, user, observation.project_id
        )
        return observation

    @staticmethod
    async def get_observation_history(
        db: AsyncSession,
        user: User,
        project_id: uuid.UUID,
        plot_identifier: Optional[str] = None,
        cohort_identifier: Optional[str] = None,
        active_only: bool = False,
    ) -> List[SurvivalObservation]:
        """
        Retrieves observation history for a project/plot/cohort.
        Preserves historical superseded records when active_only=False.
        """
        await MonitoringAuthorizationService.verify_project_access(
            db, user, project_id
        )

        query = select(SurvivalObservation).where(SurvivalObservation.project_id == project_id)

        if plot_identifier:
            query = query.where(SurvivalObservation.plot_identifier == plot_identifier)
        if cohort_identifier:
            query = query.where(SurvivalObservation.cohort_identifier == cohort_identifier)
        if active_only:
            query = query.where(SurvivalObservation.is_active == True)

        query = query.order_by(
            SurvivalObservation.observation_date.asc(),
            SurvivalObservation.created_at.asc(),
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def correct_observation(
        db: AsyncSession,
        user: User,
        observation_id: uuid.UUID,
        replacement_data: SurvivalObservationCorrectionRequest,
    ) -> Tuple[SurvivalObservation, SurvivalObservation]:
        """
        Performs atomic supersession of an existing active survival observation.
        Restricted to ADMIN and assigned PROJECT_MANAGER.
        Pessimistically locks the original observation.
        Preserves original as is_active=False with superseded_by_id pointing to replacement.
        Creates replacement observation with is_active=True.
        Guarantees exact identity preservation (project, plot, cohort, observation_date).
        """
        # Pessimistic row-level lock on the original observation
        query = (
            select(SurvivalObservation)
            .where(SurvivalObservation.id == observation_id)
            .with_for_update()
        )
        original = await db.scalar(query)
        if not original:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="OBSERVATION_NOT_FOUND: Survival observation does not exist",
            )

        # RBAC: Field Officer cannot correct observations
        await MonitoringAuthorizationService.verify_project_access(
            db,
            user,
            original.project_id,
            allowed_roles=[UserRole.ADMIN, UserRole.PROJECT_MANAGER],
        )

        # Validate that the original observation is active and not already superseded
        if not original.is_active or original.superseded_by_id is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OBSERVATION_ALREADY_SUPERSEDED: This observation is already inactive or superseded and cannot be corrected again.",
            )

        # Validate replacement counts
        if (replacement_data.alive_count + replacement_data.dead_count) > replacement_data.sample_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"INVALID_SURVIVAL_SUM: Sum of alive ({replacement_data.alive_count}) and dead ({replacement_data.dead_count}) cannot exceed sample size ({replacement_data.sample_size})",
            )

        correction_notes_clean = replacement_data.correction_notes.strip()
        if not correction_notes_clean:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CORRECTION_NOTES_MANDATORY: Correction notes explaining the change are required",
            )

        # Step 1: Deactivate the original observation first to prevent partial unique index collision
        original.is_active = False
        original.correction_notes = correction_notes_clean
        await db.flush()

        # Step 2: Create the replacement observation maintaining identical population identity
        replacement = SurvivalObservation(
            id=uuid.uuid4(),
            project_id=original.project_id,
            activity_id=original.activity_id,
            inspection_id=original.inspection_id,
            plot_identifier=original.plot_identifier,
            cohort_identifier=original.cohort_identifier,
            methodology=(
                replacement_data.methodology.value
                if replacement_data.methodology
                else original.methodology
            ),
            coverage_area_sqm=(
                replacement_data.coverage_area_sqm
                if replacement_data.coverage_area_sqm is not None
                else original.coverage_area_sqm
            ),
            observation_date=original.observation_date,
            sample_size=replacement_data.sample_size,
            alive_count=replacement_data.alive_count,
            dead_count=replacement_data.dead_count,
            mortality_causes=(
                replacement_data.mortality_causes
                if replacement_data.mortality_causes is not None
                else original.mortality_causes
            ),
            is_definitive=(
                replacement_data.is_definitive
                if replacement_data.is_definitive is not None
                else original.is_definitive
            ),
            is_active=True,
            superseded_by_id=None,
            correction_notes=None,
            notes=(
                replacement_data.notes.strip()
                if replacement_data.notes
                else original.notes
            ),
        )
        db.add(replacement)
        await db.flush()

        # Step 3: Link original to replacement via superseded_by_id (acyclic)
        assert original.id != replacement.id, "Self-supersession violation"
        original.superseded_by_id = replacement.id
        await db.flush()

        # Step 4: Audit trail for both supersession retirement and new observation creation
        await record_audit_log(
            db=db,
            action_type="SURVIVAL_OBSERVATION_SUPERSEDED",
            entity_type="SurvivalObservation",
            entity_id=original.id,
            actor_id=user.id,
            previous_state={
                "is_active": True,
                "alive_count": original.alive_count,
                "dead_count": original.dead_count,
                "sample_size": original.sample_size,
            },
            new_state={
                "is_active": False,
                "superseded_by_id": str(replacement.id),
                "correction_notes": correction_notes_clean,
            },
        )

        await record_audit_log(
            db=db,
            action_type="SURVIVAL_OBSERVATION_CORRECTION_CREATED",
            entity_type="SurvivalObservation",
            entity_id=replacement.id,
            actor_id=user.id,
            previous_state=None,
            new_state={
                "id": str(replacement.id),
                "supersedes_id": str(original.id),
                "alive_count": replacement.alive_count,
                "dead_count": replacement.dead_count,
                "sample_size": replacement.sample_size,
                "survival_rate": replacement.survival_rate,
            },
        )

        return original, replacement

    @staticmethod
    async def get_survival_trajectory(
        db: AsyncSession,
        user: User,
        project_id: uuid.UUID,
        plot_identifier: str,
        cohort_identifier: str,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves active longitudinal survival trajectory for a specific plot and cohort tuple.
        Returns derived survival rate and assessed/unassessed breakdown.
        """
        await MonitoringAuthorizationService.verify_project_access(
            db, user, project_id
        )

        query = (
            select(SurvivalObservation)
            .where(
                SurvivalObservation.project_id == project_id,
                SurvivalObservation.plot_identifier == plot_identifier,
                SurvivalObservation.cohort_identifier == cohort_identifier,
                SurvivalObservation.is_active == True,
            )
            .order_by(SurvivalObservation.observation_date.asc())
        )
        result = await db.execute(query)
        observations = result.scalars().all()

        trajectory = []
        for obs in observations:
            assessed = obs.alive_count + obs.dead_count
            unassessed = max(0, obs.sample_size - assessed)
            trajectory.append(
                {
                    "id": obs.id,
                    "observation_date": obs.observation_date,
                    "methodology": obs.methodology,
                    "sample_size": obs.sample_size,
                    "alive_count": obs.alive_count,
                    "dead_count": obs.dead_count,
                    "assessed_count": assessed,
                    "unassessed_count": unassessed,
                    "survival_rate": obs.survival_rate,
                    "is_definitive": obs.is_definitive,
                }
            )

        return trajectory


# ============================================================================
# Dynamic Alert Evaluation Service
# ============================================================================


class AlertService:
    @staticmethod
    async def evaluate_alerts(
        db: AsyncSession, user: User, project_id: Optional[uuid.UUID] = None
    ) -> List[MonitoringAlertItem]:
        """
        Evaluates dynamic operational monitoring alerts on-demand in PostgreSQL:
        1. OVERDUE_INSPECTION: status = 'SCHEDULED' AND scheduled_date < CURRENT_DATE
        2. UPCOMING_INSPECTION: status = 'SCHEDULED' AND scheduled_date BETWEEN CURRENT_DATE AND (CURRENT_DATE + 7 days)
        3. OVERDUE_TASK: status IN ('TODO', 'IN_PROGRESS') AND due_date < CURRENT_DATE
        """
        scoped_project_ids = await MonitoringAuthorizationService.get_scoped_project_ids(
            db, user, project_id
        )
        if not scoped_project_ids:
            return []

        today = date.today()
        alerts: List[MonitoringAlertItem] = []

        # 1. OVERDUE_INSPECTIONS (Severity: HIGH)
        overdue_insp_query = (
            select(FieldInspection)
            .where(
                FieldInspection.project_id.in_(scoped_project_ids),
                FieldInspection.status == InspectionStatus.SCHEDULED.value,
                FieldInspection.scheduled_date < today,
            )
            .order_by(FieldInspection.scheduled_date.asc())
        )
        overdue_insps = (await db.execute(overdue_insp_query)).scalars().all()
        for insp in overdue_insps:
            alerts.append(
                MonitoringAlertItem(
                    alert_type=AlertType.OVERDUE_INSPECTION,
                    severity=AlertSeverity.HIGH,
                    entity_id=insp.id,
                    project_id=insp.project_id,
                    title=f"Overdue Inspection ({insp.inspection_type})",
                    due_date=insp.scheduled_date,
                    details=f"Inspection scheduled for {insp.scheduled_date} has not been started",
                )
            )

        # 2. UPCOMING_INSPECTIONS (Severity: MEDIUM)
        upcoming_insp_query = (
            select(FieldInspection)
            .where(
                FieldInspection.project_id.in_(scoped_project_ids),
                FieldInspection.status == InspectionStatus.SCHEDULED.value,
                FieldInspection.scheduled_date >= today,
                FieldInspection.scheduled_date <= text("CURRENT_DATE + INTERVAL '7 days'"),
            )
            .order_by(FieldInspection.scheduled_date.asc())
        )
        upcoming_insps = (await db.execute(upcoming_insp_query)).scalars().all()
        for insp in upcoming_insps:
            alerts.append(
                MonitoringAlertItem(
                    alert_type=AlertType.UPCOMING_INSPECTION,
                    severity=AlertSeverity.MEDIUM,
                    entity_id=insp.id,
                    project_id=insp.project_id,
                    title=f"Upcoming Inspection ({insp.inspection_type})",
                    due_date=insp.scheduled_date,
                    details=f"Inspection scheduled on {insp.scheduled_date} within the next 7 days",
                )
            )

        # 3. OVERDUE_TASKS (Severity: HIGH if HIGH/URGENT priority, else MEDIUM)
        overdue_task_query = (
            select(MaintenanceTask)
            .where(
                MaintenanceTask.project_id.in_(scoped_project_ids),
                MaintenanceTask.status.in_([TaskStatus.TODO.value, TaskStatus.IN_PROGRESS.value]),
                MaintenanceTask.due_date < today,
            )
            .order_by(MaintenanceTask.due_date.asc())
        )
        overdue_tasks = (await db.execute(overdue_task_query)).scalars().all()
        for task in overdue_tasks:
            severity = (
                AlertSeverity.HIGH
                if task.priority in (TaskPriority.HIGH.value, TaskPriority.URGENT.value)
                else AlertSeverity.MEDIUM
            )
            alerts.append(
                MonitoringAlertItem(
                    alert_type=AlertType.OVERDUE_TASK,
                    severity=severity,
                    entity_id=task.id,
                    project_id=task.project_id,
                    title=f"Overdue Task: {task.title}",
                    due_date=task.due_date,
                    details=f"Task was due on {task.due_date} (Priority: {task.priority}, Category: {task.category})",
                )
            )

        return alerts

    @staticmethod
    async def get_alert_summary(
        db: AsyncSession, user: User, project_id: Optional[uuid.UUID] = None
    ) -> MonitoringAlertSummaryResponse:
        """Evaluates alerts and aggregates counts by severity."""
        alerts = await AlertService.evaluate_alerts(db, user, project_id)
        high_count = sum(1 for a in alerts if a.severity == AlertSeverity.HIGH)
        medium_count = sum(1 for a in alerts if a.severity == AlertSeverity.MEDIUM)
        low_count = sum(1 for a in alerts if a.severity == AlertSeverity.LOW)

        return MonitoringAlertSummaryResponse(
            total_alerts=len(alerts),
            high_count=high_count,
            medium_count=medium_count,
            low_count=low_count,
            alerts=alerts,
        )



# ============================================================================
# Monitoring Dashboard Service
# ============================================================================


class MonitoringDashboardService:
    @staticmethod
    async def get_dashboard_summary(
        db: AsyncSession, user: User, project_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        """Aggregates operational monitoring KPIs, backlog counts, and active alert summaries."""
        scoped_ids = await MonitoringAuthorizationService.get_scoped_project_ids(
            db, user, project_id
        )
        if not scoped_ids:
            return {
                "project_id": project_id,
                "total_inspections": 0,
                "scheduled_inspections": 0,
                "in_progress_inspections": 0,
                "completed_inspections": 0,
                "total_tasks": 0,
                "open_tasks": 0,
                "completed_tasks": 0,
                "overdue_tasks": 0,
                "total_alerts": 0,
                "high_severity_alerts": 0,
                "latest_observations": [],
            }

        # Inspections stats
        insp_stmt = select(
            func.count(FieldInspection.id),
            func.count(FieldInspection.id).filter(
                FieldInspection.status == InspectionStatus.SCHEDULED.value
            ),
            func.count(FieldInspection.id).filter(
                FieldInspection.status == InspectionStatus.IN_PROGRESS.value
            ),
            func.count(FieldInspection.id).filter(
                FieldInspection.status == InspectionStatus.COMPLETED.value
            ),
        ).where(FieldInspection.project_id.in_(scoped_ids))
        insp_row = (await db.execute(insp_stmt)).one()
        total_insp, sched_insp, in_prog_insp, comp_insp = insp_row

        # Tasks stats
        today = date.today()
        task_stmt = select(
            func.count(MaintenanceTask.id),
            func.count(MaintenanceTask.id).filter(
                MaintenanceTask.status.in_([TaskStatus.TODO.value, TaskStatus.IN_PROGRESS.value])
            ),
            func.count(MaintenanceTask.id).filter(
                MaintenanceTask.status == TaskStatus.COMPLETED.value
            ),
            func.count(MaintenanceTask.id).filter(
                MaintenanceTask.status.in_([TaskStatus.TODO.value, TaskStatus.IN_PROGRESS.value]),
                MaintenanceTask.due_date < today,
            ),
        ).where(MaintenanceTask.project_id.in_(scoped_ids))
        task_row = (await db.execute(task_stmt)).one()
        total_tasks, open_tasks, comp_tasks, overdue_tasks = task_row

        # Alert summary
        alert_summary = await AlertService.get_alert_summary(db, user, project_id)

        # Latest active observations
        obs_stmt = (
            select(SurvivalObservation)
            .where(
                SurvivalObservation.project_id.in_(scoped_ids),
                SurvivalObservation.is_active == True,
            )
            .order_by(
                SurvivalObservation.observation_date.desc(),
                SurvivalObservation.created_at.desc(),
            )
            .limit(10)
        )
        latest_obs = (await db.execute(obs_stmt)).scalars().all()

        return {
            "project_id": project_id,
            "total_inspections": total_insp,
            "scheduled_inspections": sched_insp,
            "in_progress_inspections": in_prog_insp,
            "completed_inspections": comp_insp,
            "total_tasks": total_tasks,
            "open_tasks": open_tasks,
            "completed_tasks": comp_tasks,
            "overdue_tasks": overdue_tasks,
            "total_alerts": alert_summary.total_alerts,
            "high_severity_alerts": alert_summary.high_count,
            "latest_observations": [
                {
                    "id": obs.id,
                    "project_id": obs.project_id,
                    "activity_id": obs.activity_id,
                    "inspection_id": obs.inspection_id,
                    "plot_identifier": obs.plot_identifier,
                    "cohort_identifier": obs.cohort_identifier,
                    "methodology": obs.methodology,
                    "coverage_area_sqm": obs.coverage_area_sqm,
                    "observation_date": obs.observation_date,
                    "sample_size": obs.sample_size,
                    "alive_count": obs.alive_count,
                    "dead_count": obs.dead_count,
                    "unassessed_count": max(0, obs.sample_size - (obs.alive_count + obs.dead_count)),
                    "survival_rate": obs.survival_rate,
                    "mortality_causes": obs.mortality_causes,
                    "is_definitive": obs.is_definitive,
                    "is_active": obs.is_active,
                    "superseded_by_id": obs.superseded_by_id,
                    "correction_notes": obs.correction_notes,
                    "notes": obs.notes,
                    "created_at": obs.created_at,
                }
                for obs in latest_obs
            ],
        }
