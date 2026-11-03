"""
VANA — Project Team Assignment Service
Enforces assignment authorization, active-user checks, duplicate prevention, and audit trails.
"""

import uuid
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domains.audit.services import record_audit_log
from app.domains.auth.models import User, UserRole
from app.domains.projects.models import Project
from app.domains.teams.models import ProjectAssignment, ProjectRole
from app.domains.teams.schemas import ProjectAssignmentCreate, ProjectAssignmentResponse


class ProjectAssignmentService:
    @staticmethod
    async def create_assignment(
        db: AsyncSession,
        project_id: uuid.UUID,
        data: ProjectAssignmentCreate,
        current_user: User,
        ip_address: Optional[str] = None,
    ) -> ProjectAssignmentResponse:
        """
        Allocates a user to a project roster.
        Authorized for ADMIN or assigned PROJECT_MANAGER.
        Rejects inactive users and prevents duplicate allocations.
        """
        # Authorization check
        if current_user.role != UserRole.ADMIN.value:
            pm_assignment = await db.scalar(
                select(ProjectAssignment).where(
                    ProjectAssignment.project_id == project_id,
                    ProjectAssignment.user_id == current_user.id,
                    ProjectAssignment.assigned_role == "PROJECT_MANAGER",
                )
            )
            if not pm_assignment:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={"error_code": "INSUFFICIENT_PROJECT_ROLE", "message": "Only assigned Project Managers or Admins can assign team members."},
                )

        # Verify project exists
        project = await db.get(Project, project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error_code": "PROJECT_NOT_FOUND", "message": f"Project with ID {project_id} not found."},
            )

        # Verify target user exists
        target_user = await db.get(User, data.user_id)
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error_code": "USER_NOT_FOUND", "message": f"User with ID {data.user_id} not found."},
            )

        # Enforce that inactive users cannot be assigned
        if not target_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_code": "INACTIVE_USER_ASSIGNMENT_PROHIBITED",
                    "message": f"User '{target_user.email}' is deactivated and cannot be assigned to projects.",
                },
            )

        # Prevent duplicate assignment
        existing = await db.scalar(
            select(ProjectAssignment).where(
                ProjectAssignment.project_id == project_id,
                ProjectAssignment.user_id == data.user_id,
            )
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error_code": "DUPLICATE_PROJECT_ASSIGNMENT",
                    "message": f"User '{target_user.email}' is already assigned to this project.",
                },
            )

        assignment = ProjectAssignment(
            project_id=project_id,
            user_id=data.user_id,
            assigned_role=data.assigned_role.value,
        )
        db.add(assignment)
        await db.flush()

        await record_audit_log(
            db=db,
            action_type="ASSIGNMENT_CREATED",
            entity_type="project_assignment",
            entity_id=assignment.id,
            actor_id=current_user.id,
            new_state={
                "project_id": str(project_id),
                "user_id": str(target_user.id),
                "user_email": target_user.email,
                "assigned_role": assignment.assigned_role,
            },
            ip_address=ip_address,
        )
        await db.commit()
        await db.refresh(assignment)

        return ProjectAssignmentResponse(
            id=assignment.id,
            project_id=assignment.project_id,
            user_id=assignment.user_id,
            assigned_role=assignment.assigned_role,
            assigned_at=assignment.assigned_at,
            user_email=target_user.email,
            user_full_name=target_user.full_name,
            user_system_role=target_user.role,
            user_is_active=target_user.is_active,
        )

    @staticmethod
    async def list_assignments(
        db: AsyncSession,
        project_id: uuid.UUID,
        current_user: User,
    ) -> List[ProjectAssignmentResponse]:
        """Lists team roster allocations for a project."""
        # Verify project access
        if current_user.role != UserRole.ADMIN.value:
            user_assignment = await db.scalar(
                select(ProjectAssignment).where(
                    ProjectAssignment.project_id == project_id,
                    ProjectAssignment.user_id == current_user.id,
                )
            )
            if not user_assignment:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={"error_code": "PROJECT_ACCESS_DENIED", "message": "You are not assigned to this project."},
                )

        stmt = (
            select(ProjectAssignment)
            .where(ProjectAssignment.project_id == project_id)
            .options(selectinload(ProjectAssignment.user))
            .order_by(ProjectAssignment.assigned_at.asc())
        )
        assignments = list((await db.scalars(stmt)).all())

        return [
            ProjectAssignmentResponse(
                id=a.id,
                project_id=a.project_id,
                user_id=a.user_id,
                assigned_role=a.assigned_role,
                assigned_at=a.assigned_at,
                user_email=a.user.email if a.user else None,
                user_full_name=a.user.full_name if a.user else None,
                user_system_role=a.user.role if a.user else None,
                user_is_active=a.user.is_active if a.user else None,
            )
            for a in assignments
        ]

    @staticmethod
    async def delete_assignment(
        db: AsyncSession,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        current_user: User,
        ip_address: Optional[str] = None,
    ) -> None:
        """Removes a user from a project's active roster."""
        if current_user.role != UserRole.ADMIN.value:
            pm_assignment = await db.scalar(
                select(ProjectAssignment).where(
                    ProjectAssignment.project_id == project_id,
                    ProjectAssignment.user_id == current_user.id,
                    ProjectAssignment.assigned_role == "PROJECT_MANAGER",
                )
            )
            if not pm_assignment:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={"error_code": "INSUFFICIENT_PROJECT_ROLE", "message": "Only assigned Project Managers or Admins can remove team members."},
                )

        stmt = select(ProjectAssignment).where(
            ProjectAssignment.project_id == project_id,
            ProjectAssignment.user_id == user_id,
        )
        assignment = await db.scalar(stmt)
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error_code": "ASSIGNMENT_NOT_FOUND", "message": "User is not assigned to this project."},
            )

        old_state = {
            "project_id": str(project_id),
            "user_id": str(user_id),
            "assigned_role": assignment.assigned_role,
        }

        await db.delete(assignment)
        await record_audit_log(
            db=db,
            action_type="ASSIGNMENT_DELETED",
            entity_type="project_assignment",
            entity_id=assignment.id,
            actor_id=current_user.id,
            previous_state=old_state,
            ip_address=ip_address,
        )
        await db.commit()
