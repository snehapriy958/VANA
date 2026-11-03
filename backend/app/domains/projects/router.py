"""
VANA — Projects, Targets & Assignments API Router
Exposes project lifecycle management, geographic boundaries, environmental targets,
and team allocations per the approved REST API specification.
"""

import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.domains.auth.dependencies import get_current_active_user, require_admin
from app.domains.auth.models import User
from app.domains.projects.schemas import (
    ProjectCreate,
    ProjectDetailResponse,
    ProjectResponse,
    ProjectTargetCreate,
    ProjectTargetResponse,
    ProjectTargetUpdate,
    ProjectUpdate,
)
from app.domains.projects.services import ProjectService, TargetService
from app.domains.teams.schemas import ProjectAssignmentCreate, ProjectAssignmentResponse
from app.domains.teams.services import ProjectAssignmentService

router = APIRouter(prefix="/projects", tags=["Project Management"])


# ============================================================================
# Project Portfolio Management
# ============================================================================

@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    data: ProjectCreate,
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    """Creates a new environmental project. Restricted to ADMIN."""
    ip_address = request.client.host if request.client else None
    project = await ProjectService.create_project(
        db=db,
        data=data,
        current_user=current_user,
        ip_address=ip_address,
    )
    return ProjectResponse(
        id=project.id,
        name=project.name,
        code=project.code,
        description=project.description,
        status=project.status,
        latitude=project.latitude,
        longitude=project.longitude,
        boundary_geojson=project.boundary_geojson,
        created_at=project.created_at,
        updated_at=project.updated_at,
        targets_count=0,
        team_count=0,
    )


@router.get("", response_model=List[ProjectResponse], status_code=status.HTTP_200_OK)
async def list_projects(
    search: Optional[str] = Query(None, description="Search query matching name, code, or description"),
    status: Optional[str] = Query(None, description="Filter by status (DRAFT, ACTIVE, COMPLETED, ARCHIVED)"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> List[ProjectResponse]:
    """Lists projects. Scoped to assigned projects for Project Managers and Field Officers; full portfolio for Admins."""
    projects = await ProjectService.list_projects(
        db=db,
        current_user=current_user,
        search=search,
        status_filter=status,
    )
    return [ProjectResponse(**p) for p in projects]


@router.get("/{project_id}", response_model=ProjectDetailResponse, status_code=status.HTTP_200_OK)
async def get_project_details(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectDetailResponse:
    """Retrieves full project workspace details, including targets and team assignments."""
    project = await ProjectService.get_project(db, project_id, current_user)
    targets = [TargetService.enrich_target_response(t) for t in project.targets]
    assignments = [
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
        for a in project.assignments
    ]

    return ProjectDetailResponse(
        id=project.id,
        name=project.name,
        code=project.code,
        description=project.description,
        status=project.status,
        latitude=project.latitude,
        longitude=project.longitude,
        boundary_geojson=project.boundary_geojson,
        created_at=project.created_at,
        updated_at=project.updated_at,
        targets_count=len(targets),
        team_count=len(assignments),
        targets=targets,
        assignments=assignments,
    )


@router.put("/{project_id}", response_model=ProjectResponse, status_code=status.HTTP_200_OK)
async def update_project(
    project_id: uuid.UUID,
    data: ProjectUpdate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    """Updates project metadata, status, coordinates, or boundary. Authorized for ADMIN or assigned PM."""
    ip_address = request.client.host if request.client else None
    project = await ProjectService.update_project(
        db=db,
        project_id=project_id,
        data=data,
        current_user=current_user,
        ip_address=ip_address,
    )
    targets_count = len(project.targets) if project.targets else 0
    team_count = len(project.assignments) if project.assignments else 0

    return ProjectResponse(
        id=project.id,
        name=project.name,
        code=project.code,
        description=project.description,
        status=project.status,
        latitude=project.latitude,
        longitude=project.longitude,
        boundary_geojson=project.boundary_geojson,
        created_at=project.created_at,
        updated_at=project.updated_at,
        targets_count=targets_count,
        team_count=team_count,
    )


# ============================================================================
# Environmental Targets
# ============================================================================

@router.post("/{project_id}/targets", response_model=ProjectTargetResponse, status_code=status.HTTP_201_CREATED)
async def create_project_target(
    project_id: uuid.UUID,
    data: ProjectTargetCreate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectTargetResponse:
    """Attaches a new dimensional target to a project. Authorized for ADMIN or assigned PM."""
    ip_address = request.client.host if request.client else None
    return await TargetService.create_target(
        db=db,
        project_id=project_id,
        data=data,
        current_user=current_user,
        ip_address=ip_address,
    )


@router.get("/{project_id}/targets", response_model=List[ProjectTargetResponse], status_code=status.HTTP_200_OK)
async def list_project_targets(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> List[ProjectTargetResponse]:
    """Lists targets for a project. Accessible to all users assigned to the project or ADMIN."""
    return await TargetService.list_targets(db=db, project_id=project_id, current_user=current_user)


@router.put("/{project_id}/targets/{target_id}", response_model=ProjectTargetResponse, status_code=status.HTTP_200_OK)
async def update_project_target(
    project_id: uuid.UUID,
    target_id: uuid.UUID,
    data: ProjectTargetUpdate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectTargetResponse:
    """Updates target quantity, unit, or deadline. Authorized for ADMIN or assigned PM."""
    ip_address = request.client.host if request.client else None
    return await TargetService.update_target(
        db=db,
        project_id=project_id,
        target_id=target_id,
        data=data,
        current_user=current_user,
        ip_address=ip_address,
    )


@router.delete("/{project_id}/targets/{target_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project_target(
    project_id: uuid.UUID,
    target_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Deletes a target from a project. Authorized for ADMIN or assigned PM."""
    ip_address = request.client.host if request.client else None
    await TargetService.delete_target(
        db=db,
        project_id=project_id,
        target_id=target_id,
        current_user=current_user,
        ip_address=ip_address,
    )


# ============================================================================
# Project Team Assignments
# ============================================================================

@router.post("/{project_id}/assignments", response_model=ProjectAssignmentResponse, status_code=status.HTTP_201_CREATED)
async def create_project_assignment(
    project_id: uuid.UUID,
    data: ProjectAssignmentCreate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectAssignmentResponse:
    """Allocates a user to a project roster. Authorized for ADMIN or assigned PM."""
    ip_address = request.client.host if request.client else None
    return await ProjectAssignmentService.create_assignment(
        db=db,
        project_id=project_id,
        data=data,
        current_user=current_user,
        ip_address=ip_address,
    )


@router.get("/{project_id}/assignments", response_model=List[ProjectAssignmentResponse], status_code=status.HTTP_200_OK)
async def list_project_assignments(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> List[ProjectAssignmentResponse]:
    """Lists users assigned to this project roster."""
    return await ProjectAssignmentService.list_assignments(
        db=db,
        project_id=project_id,
        current_user=current_user,
    )


@router.delete("/{project_id}/assignments/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project_assignment(
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Removes a user from a project roster. Authorized for ADMIN or assigned PM."""
    ip_address = request.client.host if request.client else None
    await ProjectAssignmentService.delete_assignment(
        db=db,
        project_id=project_id,
        user_id=user_id,
        current_user=current_user,
        ip_address=ip_address,
    )
