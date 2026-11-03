"""
VANA — Project & Target Management Services
Enforces authorization, coordinate/polygon validation, lifecycle transitions,
duplicate target prevention, and immutable audit logging.
"""

import re
import uuid
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domains.audit.services import record_audit_log
from app.domains.auth.models import User, UserRole
from app.domains.projects.metrics import APPROVED_METRIC_CATALOG, validate_metric_and_unit
from app.domains.projects.models import Project, ProjectStatus, ProjectTarget
from app.domains.projects.schemas import (
    ProjectCreate,
    ProjectResponse,
    ProjectTargetCreate,
    ProjectTargetResponse,
    ProjectTargetUpdate,
    ProjectUpdate,
    VALID_STATUS_TRANSITIONS,
)
from app.domains.teams.models import ProjectAssignment


def generate_project_code(name: str) -> str:
    """Generates an uppercase canonical identifier from a project name."""
    clean_name = re.sub(r"[^A-Za-z0-9]+", "-", name).strip("-").upper()
    short_slug = clean_name[:20] if clean_name else "PROJECT"
    random_suffix = uuid.uuid4().hex[:6].upper()
    return f"VANA-{short_slug}-{random_suffix}"


class ProjectService:
    @staticmethod
    async def create_project(
        db: AsyncSession,
        data: ProjectCreate,
        current_user: User,
        ip_address: Optional[str] = None,
    ) -> Project:
        """
        Creates a new environmental project. Only ADMIN is authorized.
        Validates code uniqueness and records immutable audit log.
        """
        if current_user.role != UserRole.ADMIN.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error_code": "INSUFFICIENT_ROLE", "message": "Only administrators can create projects."},
            )

        code = data.code
        if not code:
            code = generate_project_code(data.name)

        # Check code uniqueness
        existing = await db.scalar(select(Project).where(Project.code == code))
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error_code": "PROJECT_CODE_ALREADY_EXISTS", "message": f"Project code '{code}' is already registered."},
            )

        project = Project(
            name=data.name.strip(),
            code=code,
            description=data.description.strip() if data.description else None,
            status=data.status.value,
            latitude=data.latitude,
            longitude=data.longitude,
            boundary_geojson=data.boundary_geojson,
        )
        db.add(project)
        await db.flush()

        await record_audit_log(
            db=db,
            action_type="PROJECT_CREATED",
            entity_type="project",
            entity_id=project.id,
            actor_id=current_user.id,
            new_state={
                "id": str(project.id),
                "name": project.name,
                "code": project.code,
                "status": project.status,
                "latitude": project.latitude,
                "longitude": project.longitude,
                "has_boundary": project.boundary_geojson is not None,
            },
            ip_address=ip_address,
        )
        await db.commit()
        await db.refresh(project)
        return project

    @staticmethod
    async def list_projects(
        db: AsyncSession,
        current_user: User,
        search: Optional[str] = None,
        status_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Lists projects scoped to user permissions:
        - ADMIN: sees all projects.
        - PM / FIELD_OFFICER: sees only assigned projects.
        """
        stmt = select(Project).order_by(Project.created_at.desc())

        # Scoping: non-admins must have a ProjectAssignment
        if current_user.role != UserRole.ADMIN.value:
            stmt = stmt.join(
                ProjectAssignment,
                (ProjectAssignment.project_id == Project.id) & (ProjectAssignment.user_id == current_user.id),
            )

        if status_filter:
            status_upper = status_filter.strip().upper()
            stmt = stmt.where(Project.status == status_upper)

        if search:
            search_pattern = f"%{search.strip()}%"
            stmt = stmt.where(
                (Project.name.ilike(search_pattern))
                | (Project.code.ilike(search_pattern))
                | (Project.description.ilike(search_pattern))
            )

        result = await db.scalars(stmt)
        projects = list(result.all())

        if not projects:
            return []

        project_ids = [p.id for p in projects]

        # Aggregate counts for targets and team members
        targets_count_stmt = (
            select(ProjectTarget.project_id, func.count(ProjectTarget.id))
            .where(ProjectTarget.project_id.in_(project_ids))
            .group_by(ProjectTarget.project_id)
        )
        targets_counts = dict((await db.execute(targets_count_stmt)).all())

        team_count_stmt = (
            select(ProjectAssignment.project_id, func.count(ProjectAssignment.id))
            .where(ProjectAssignment.project_id.in_(project_ids))
            .group_by(ProjectAssignment.project_id)
        )
        team_counts = dict((await db.execute(team_count_stmt)).all())

        return [
            {
                "id": p.id,
                "name": p.name,
                "code": p.code,
                "description": p.description,
                "status": p.status,
                "latitude": p.latitude,
                "longitude": p.longitude,
                "boundary_geojson": p.boundary_geojson,
                "created_at": p.created_at,
                "updated_at": p.updated_at,
                "targets_count": targets_counts.get(p.id, 0),
                "team_count": team_counts.get(p.id, 0),
            }
            for p in projects
        ]

    @staticmethod
    async def get_project(
        db: AsyncSession,
        project_id: uuid.UUID,
        current_user: User,
    ) -> Project:
        """
        Retrieves project details. Enforces project access boundaries.
        """
        stmt = (
            select(Project)
            .where(Project.id == project_id)
            .options(
                selectinload(Project.targets),
                selectinload(Project.assignments).selectinload(ProjectAssignment.user),
            )
        )
        project = await db.scalar(stmt)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error_code": "PROJECT_NOT_FOUND", "message": f"Project with ID {project_id} not found."},
            )

        # Scoping check
        if current_user.role != UserRole.ADMIN.value:
            assignment = await db.scalar(
                select(ProjectAssignment).where(
                    ProjectAssignment.project_id == project_id,
                    ProjectAssignment.user_id == current_user.id,
                )
            )
            if not assignment:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={"error_code": "PROJECT_ACCESS_DENIED", "message": "You are not assigned to this project."},
                )

        return project

    @staticmethod
    async def update_project(
        db: AsyncSession,
        project_id: uuid.UUID,
        data: ProjectUpdate,
        current_user: User,
        ip_address: Optional[str] = None,
    ) -> Project:
        """
        Updates project metadata, status, or coordinates.
        Authorized for ADMIN or assigned PROJECT_MANAGER.
        """
        project = await ProjectService.get_project(db, project_id, current_user)

        # Non-admins must be assigned as PROJECT_MANAGER
        if current_user.role != UserRole.ADMIN.value:
            assignment = await db.scalar(
                select(ProjectAssignment).where(
                    ProjectAssignment.project_id == project_id,
                    ProjectAssignment.user_id == current_user.id,
                    ProjectAssignment.assigned_role == "PROJECT_MANAGER",
                )
            )
            if not assignment:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={"error_code": "INSUFFICIENT_PROJECT_ROLE", "message": "Only assigned Project Managers or Admins can edit this project."},
                )

        old_state = {
            "name": project.name,
            "status": project.status,
            "latitude": project.latitude,
            "longitude": project.longitude,
            "has_boundary": project.boundary_geojson is not None,
        }

        # Status transition validation
        if data.status is not None and data.status.value != project.status:
            allowed_transitions = VALID_STATUS_TRANSITIONS.get(project.status, [])
            if data.status.value not in allowed_transitions:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error_code": "INVALID_STATUS_TRANSITION",
                        "message": f"Cannot transition project status from '{project.status}' to '{data.status.value}'. Allowed transitions: {', '.join(allowed_transitions)}",
                    },
                )
            project.status = data.status.value

        if data.name is not None:
            project.name = data.name.strip()
        if data.description is not None:
            project.description = data.description.strip() if data.description else None
        if data.latitude is not None:
            project.latitude = data.latitude
        if data.longitude is not None:
            project.longitude = data.longitude
        if data.boundary_geojson is not None:
            project.boundary_geojson = data.boundary_geojson

        new_state = {
            "name": project.name,
            "status": project.status,
            "latitude": project.latitude,
            "longitude": project.longitude,
            "has_boundary": project.boundary_geojson is not None,
        }

        await record_audit_log(
            db=db,
            action_type="PROJECT_UPDATED",
            entity_type="project",
            entity_id=project.id,
            actor_id=current_user.id,
            previous_state=old_state,
            new_state=new_state,
            ip_address=ip_address,
        )

        if old_state["status"] != new_state["status"]:
            await record_audit_log(
                db=db,
                action_type="PROJECT_STATUS_CHANGED",
                entity_type="project",
                entity_id=project.id,
                actor_id=current_user.id,
                previous_state={"status": old_state["status"]},
                new_state={"status": new_state["status"]},
                ip_address=ip_address,
            )

        await db.commit()
        await db.refresh(project)
        return project


class TargetService:
    @staticmethod
    def enrich_target_response(target: ProjectTarget) -> ProjectTargetResponse:
        """Enriches a target ORM model with metadata from the approved metric catalog."""
        metric_meta = APPROVED_METRIC_CATALOG.get(target.metric_code)
        display_name = metric_meta.display_name if metric_meta else target.metric_code
        category = metric_meta.category if metric_meta else "UNKNOWN"
        dimension = metric_meta.dimension if metric_meta else "UNKNOWN"
        canonical_unit = metric_meta.canonical_unit if metric_meta else target.target_unit

        return ProjectTargetResponse(
            id=target.id,
            project_id=target.project_id,
            metric_code=target.metric_code,
            display_name=display_name,
            category=category,
            dimension=dimension,
            canonical_unit=canonical_unit,
            target_quantity=target.target_quantity,
            target_unit=target.target_unit,
            target_date=target.target_date,
            milestone_id=target.milestone_id,
            created_at=target.created_at,
            updated_at=target.updated_at,
        )

    @staticmethod
    async def create_target(
        db: AsyncSession,
        project_id: uuid.UUID,
        data: ProjectTargetCreate,
        current_user: User,
        ip_address: Optional[str] = None,
    ) -> ProjectTargetResponse:
        """
        Creates an environmental target for a project.
        Enforces metric catalog rules, unit compatibility, and duplicate target prevention.
        """
        # Authorization: ADMIN or assigned PM
        if current_user.role != UserRole.ADMIN.value:
            assignment = await db.scalar(
                select(ProjectAssignment).where(
                    ProjectAssignment.project_id == project_id,
                    ProjectAssignment.user_id == current_user.id,
                    ProjectAssignment.assigned_role == "PROJECT_MANAGER",
                )
            )
            if not assignment:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={"error_code": "INSUFFICIENT_PROJECT_ROLE", "message": "Only assigned Project Managers or Admins can define targets."},
                )

        # Verify project exists
        project = await db.get(Project, project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error_code": "PROJECT_NOT_FOUND", "message": f"Project with ID {project_id} not found."},
            )

        # Duplicate check: check if metric_code already exists for this project (milestone_id IS NULL)
        dup_stmt = select(ProjectTarget).where(
            ProjectTarget.project_id == project_id,
            ProjectTarget.metric_code == data.metric_code,
            ProjectTarget.milestone_id.is_(None) if data.milestone_id is None else ProjectTarget.milestone_id == data.milestone_id,
        )
        existing_target = await db.scalar(dup_stmt)
        if existing_target:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error_code": "DUPLICATE_PROJECT_TARGET",
                    "message": f"A target for metric '{data.metric_code}' already exists for this project.",
                },
            )

        target = ProjectTarget(
            project_id=project_id,
            metric_code=data.metric_code,
            target_quantity=data.target_quantity,
            target_unit=data.target_unit,
            target_date=data.target_date,
            milestone_id=data.milestone_id,
        )
        db.add(target)
        await db.flush()

        await record_audit_log(
            db=db,
            action_type="TARGET_CREATED",
            entity_type="project_target",
            entity_id=target.id,
            actor_id=current_user.id,
            new_state={
                "project_id": str(project_id),
                "metric_code": target.metric_code,
                "target_quantity": str(target.target_quantity),
                "target_unit": target.target_unit,
                "target_date": target.target_date.isoformat(),
            },
            ip_address=ip_address,
        )
        await db.commit()
        await db.refresh(target)
        return TargetService.enrich_target_response(target)

    @staticmethod
    async def list_targets(
        db: AsyncSession,
        project_id: uuid.UUID,
        current_user: User,
    ) -> List[ProjectTargetResponse]:
        """Lists all environmental targets for a project."""
        # Access check
        await ProjectService.get_project(db, project_id, current_user)

        stmt = (
            select(ProjectTarget)
            .where(ProjectTarget.project_id == project_id)
            .order_by(ProjectTarget.created_at.asc())
        )
        targets = list((await db.scalars(stmt)).all())
        return [TargetService.enrich_target_response(t) for t in targets]

    @staticmethod
    async def update_target(
        db: AsyncSession,
        project_id: uuid.UUID,
        target_id: uuid.UUID,
        data: ProjectTargetUpdate,
        current_user: User,
        ip_address: Optional[str] = None,
    ) -> ProjectTargetResponse:
        """Updates target quantity, unit, or target date."""
        if current_user.role != UserRole.ADMIN.value:
            assignment = await db.scalar(
                select(ProjectAssignment).where(
                    ProjectAssignment.project_id == project_id,
                    ProjectAssignment.user_id == current_user.id,
                    ProjectAssignment.assigned_role == "PROJECT_MANAGER",
                )
            )
            if not assignment:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={"error_code": "INSUFFICIENT_PROJECT_ROLE", "message": "Only assigned Project Managers or Admins can edit targets."},
                )

        target = await db.get(ProjectTarget, target_id)
        if not target or target.project_id != project_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error_code": "TARGET_NOT_FOUND", "message": f"Target with ID {target_id} not found in this project."},
            )

        old_state = {
            "target_quantity": str(target.target_quantity),
            "target_unit": target.target_unit,
            "target_date": target.target_date.isoformat(),
        }

        if data.target_unit is not None:
            # Validate new unit is compatible with existing metric_code
            try:
                validate_metric_and_unit(target.metric_code, data.target_unit)
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail={"error_code": "INCOMPATIBLE_UNIT", "message": str(e)},
                )
            target.target_unit = data.target_unit

        if data.target_quantity is not None:
            if data.target_quantity <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"error_code": "INVALID_TARGET_QUANTITY", "message": "Target quantity must be greater than zero."},
                )
            target.target_quantity = data.target_quantity

        if data.target_date is not None:
            target.target_date = data.target_date

        new_state = {
            "target_quantity": str(target.target_quantity),
            "target_unit": target.target_unit,
            "target_date": target.target_date.isoformat(),
        }

        await record_audit_log(
            db=db,
            action_type="TARGET_UPDATED",
            entity_type="project_target",
            entity_id=target.id,
            actor_id=current_user.id,
            previous_state=old_state,
            new_state=new_state,
            ip_address=ip_address,
        )
        await db.commit()
        await db.refresh(target)
        return TargetService.enrich_target_response(target)

    @staticmethod
    async def delete_target(
        db: AsyncSession,
        project_id: uuid.UUID,
        target_id: uuid.UUID,
        current_user: User,
        ip_address: Optional[str] = None,
    ) -> None:
        """Deletes an environmental target."""
        if current_user.role != UserRole.ADMIN.value:
            assignment = await db.scalar(
                select(ProjectAssignment).where(
                    ProjectAssignment.project_id == project_id,
                    ProjectAssignment.user_id == current_user.id,
                    ProjectAssignment.assigned_role == "PROJECT_MANAGER",
                )
            )
            if not assignment:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={"error_code": "INSUFFICIENT_PROJECT_ROLE", "message": "Only assigned Project Managers or Admins can delete targets."},
                )

        target = await db.get(ProjectTarget, target_id)
        if not target or target.project_id != project_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error_code": "TARGET_NOT_FOUND", "message": f"Target with ID {target_id} not found in this project."},
            )

        old_state = {
            "project_id": str(project_id),
            "metric_code": target.metric_code,
            "target_quantity": str(target.target_quantity),
            "target_unit": target.target_unit,
        }

        # Safeguard: prevent deletion if non-archived field activities exist for this project and metric
        from app.domains.operations.models import FieldActivity
        active_activities = await db.scalar(
            select(func.count(FieldActivity.id)).where(
                FieldActivity.project_id == project_id,
                FieldActivity.metric_code == target.metric_code,
                FieldActivity.is_archived.is_(False),
            )
        )
        if active_activities and active_activities > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_code": "TARGET_HAS_ACTIVE_ACTIVITIES",
                    "message": f"Cannot delete target '{target.metric_code}': {active_activities} active field activities reference this metric.",
                },
            )

        await db.delete(target)
        await record_audit_log(
            db=db,
            action_type="TARGET_DELETED",
            entity_type="project_target",
            entity_id=target_id,
            actor_id=current_user.id,
            previous_state=old_state,
            ip_address=ip_address,
        )
        await db.commit()
