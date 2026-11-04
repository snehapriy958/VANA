"""
VANA — Field Monitoring & Follow-up Management API Router
Mounts all REST endpoints under /api/v1/monitoring for:
- Field Inspections (scheduling, lifecycle, addenda, evidence upload)
- Maintenance Tasks (creation, lifecycle, cancellation, reopening)
- Survival Observations (creation, server-derived rates, atomic supersession, trajectory)
- Operational Alerts and Dashboard KPIs
"""

from datetime import date
from typing import Any, Dict, List, Optional
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
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.domains.auth.dependencies import get_current_active_user
from app.domains.auth.models import User
from app.domains.monitoring.schemas import (
    FieldInspectionCreate,
    FieldInspectionResponse,
    InspectionAddendumCreate,
    InspectionCancelRequest,
    InspectionCompleteRequest,
    InspectionStartRequest,
    MaintenanceTaskCreate,
    MaintenanceTaskResponse,
    MonitoringAlertSummaryResponse,
    MonitoringDashboardResponse,
    MonitoringEvidenceResponse,
    SurvivalObservationCorrectionRequest,
    SurvivalObservationCreate,
    SurvivalObservationResponse,
    TaskCancelRequest,
    TaskCompleteRequest,
    TaskReopenRequest,
    TaskStartRequest,
)
from app.domains.monitoring.services import (
    AlertService,
    InspectionService,
    MaintenanceTaskService,
    MonitoringDashboardService,
    SurvivalObservationService,
)

router = APIRouter(prefix="/monitoring", tags=["Field Monitoring"])


# ============================================================================
# Field Inspection Endpoints
# ============================================================================


@router.post(
    "/inspections",
    response_model=FieldInspectionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Schedule Field Inspection",
)
async def schedule_inspection(
    data: FieldInspectionCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> FieldInspectionResponse:
    """Schedules a new field inspection. Restricted to Admins and assigned PMs."""
    inspection = await InspectionService.schedule_inspection(
        db=db, user=current_user, data=data
    )
    await db.commit()
    await db.refresh(inspection)
    return FieldInspectionResponse.model_validate(inspection)


@router.get(
    "/inspections",
    response_model=List[FieldInspectionResponse],
    status_code=status.HTTP_200_OK,
    summary="List Field Inspections",
)
async def list_inspections(
    project_id: Optional[uuid.UUID] = Query(None, description="Filter by project ID"),
    status: Optional[str] = Query(None, description="Filter by status (SCHEDULED, IN_PROGRESS, COMPLETED, CANCELLED)"),
    assigned_to_id: Optional[uuid.UUID] = Query(None, description="Filter by assigned inspector ID"),
    from_date: Optional[date] = Query(None, description="Filter scheduled from date"),
    to_date: Optional[date] = Query(None, description="Filter scheduled to date"),
    skip: int = Query(0, ge=0, description="Pagination skip"),
    limit: int = Query(50, ge=1, le=100, description="Pagination limit"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> List[FieldInspectionResponse]:
    """Lists field inspections with multi-tenant role scoping and pagination."""
    inspections = await InspectionService.list_inspections(
        db=db,
        user=current_user,
        project_id=project_id,
        status_filter=status,
        assigned_to_id=assigned_to_id,
        from_date=from_date,
        to_date=to_date,
    )
    paginated = inspections[skip : skip + limit]
    return [FieldInspectionResponse.model_validate(insp) for insp in paginated]


@router.get(
    "/inspections/{id}",
    response_model=FieldInspectionResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Field Inspection Details",
)
async def get_inspection(
    id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> FieldInspectionResponse:
    """Retrieves full inspection details by ID."""
    inspection = await InspectionService.get_inspection(
        db=db, user=current_user, inspection_id=id
    )
    return FieldInspectionResponse.model_validate(inspection)


@router.post(
    "/inspections/{id}/start",
    response_model=FieldInspectionResponse,
    status_code=status.HTTP_200_OK,
    summary="Start Field Inspection",
)
async def start_inspection(
    id: uuid.UUID,
    data: Optional[InspectionStartRequest] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> FieldInspectionResponse:
    """Transitions inspection from SCHEDULED to IN_PROGRESS."""
    notes = data.notes if data else None
    inspection = await InspectionService.start_inspection(
        db=db, user=current_user, inspection_id=id, notes=notes
    )
    await db.commit()
    await db.refresh(inspection)
    return FieldInspectionResponse.model_validate(inspection)


@router.post(
    "/inspections/{id}/complete",
    response_model=FieldInspectionResponse,
    status_code=status.HTTP_200_OK,
    summary="Complete Field Inspection",
)
async def complete_inspection(
    id: uuid.UUID,
    data: InspectionCompleteRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> FieldInspectionResponse:
    """Transitions inspection from IN_PROGRESS to COMPLETED with mandatory findings."""
    inspection = await InspectionService.complete_inspection(
        db=db, user=current_user, inspection_id=id, data=data
    )
    await db.commit()
    await db.refresh(inspection)
    return FieldInspectionResponse.model_validate(inspection)


@router.post(
    "/inspections/{id}/cancel",
    response_model=FieldInspectionResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel Field Inspection",
)
async def cancel_inspection(
    id: uuid.UUID,
    data: InspectionCancelRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> FieldInspectionResponse:
    """Cancels a scheduled or in-progress inspection. Restricted to Admins and assigned PMs."""
    inspection = await InspectionService.cancel_inspection(
        db=db, user=current_user, inspection_id=id, data=data
    )
    await db.commit()
    await db.refresh(inspection)
    return FieldInspectionResponse.model_validate(inspection)


@router.post(
    "/inspections/{id}/addendum",
    response_model=FieldInspectionResponse,
    status_code=status.HTTP_200_OK,
    summary="Record Post-Completion Addendum",
)
async def add_inspection_addendum(
    id: uuid.UUID,
    data: InspectionAddendumCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> FieldInspectionResponse:
    """Records an immutable correction addendum on a COMPLETED inspection."""
    inspection = await InspectionService.add_addendum(
        db=db, user=current_user, inspection_id=id, data=data
    )
    await db.commit()
    await db.refresh(inspection)
    return FieldInspectionResponse.model_validate(inspection)


@router.post(
    "/inspections/{id}/evidence",
    response_model=MonitoringEvidenceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload Inspection Evidence",
)
async def upload_inspection_evidence(
    id: uuid.UUID,
    file: UploadFile = File(...),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    caption: Optional[str] = Form(None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> MonitoringEvidenceResponse:
    """Uploads photo or document evidence to an inspection with SHA-256 storage."""
    evidence = await InspectionService.upload_evidence(
        db=db,
        user=current_user,
        inspection_id=id,
        file=file,
        latitude=latitude,
        longitude=longitude,
        caption=caption,
    )
    await db.commit()
    await db.refresh(evidence)

    return MonitoringEvidenceResponse(
        id=evidence.id,
        inspection_id=evidence.inspection_id,
        original_filename=evidence.original_filename,
        mime_type=evidence.mime_type,
        file_size_bytes=evidence.file_size_bytes,
        download_url=f"/api/v1/operations/evidence/{evidence.id}",
        latitude=evidence.latitude,
        longitude=evidence.longitude,
        caption=evidence.caption,
        uploaded_at=evidence.uploaded_at,
    )


# ============================================================================
# Maintenance Task Endpoints
# ============================================================================


@router.post(
    "/tasks",
    response_model=MaintenanceTaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Maintenance Task",
)
async def create_task(
    data: MaintenanceTaskCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> MaintenanceTaskResponse:
    """Creates a new maintenance task. Restricted to Admins and assigned PMs."""
    task = await MaintenanceTaskService.create_task(
        db=db, user=current_user, data=data
    )
    await db.commit()
    await db.refresh(task)
    return MaintenanceTaskResponse.model_validate(task)


@router.get(
    "/tasks",
    response_model=List[MaintenanceTaskResponse],
    status_code=status.HTTP_200_OK,
    summary="List Maintenance Tasks",
)
async def list_tasks(
    project_id: Optional[uuid.UUID] = Query(None, description="Filter by project ID"),
    status: Optional[str] = Query(None, description="Filter by task status"),
    assigned_to_id: Optional[uuid.UUID] = Query(None, description="Filter by assignee"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    category: Optional[str] = Query(None, description="Filter by category"),
    skip: int = Query(0, ge=0, description="Pagination skip"),
    limit: int = Query(50, ge=1, le=100, description="Pagination limit"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> List[MaintenanceTaskResponse]:
    """Lists maintenance tasks with multi-tenant role scoping and pagination."""
    tasks = await MaintenanceTaskService.list_tasks(
        db=db,
        user=current_user,
        project_id=project_id,
        status_filter=status,
        assigned_to_id=assigned_to_id,
        priority_filter=priority,
        category_filter=category,
    )
    paginated = tasks[skip : skip + limit]
    return [MaintenanceTaskResponse.model_validate(task) for task in paginated]


@router.get(
    "/tasks/{id}",
    response_model=MaintenanceTaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Maintenance Task Details",
)
async def get_task(
    id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> MaintenanceTaskResponse:
    """Retrieves full maintenance task details by ID."""
    task = await MaintenanceTaskService.get_task(db=db, user=current_user, task_id=id)
    return MaintenanceTaskResponse.model_validate(task)


@router.post(
    "/tasks/{id}/start",
    response_model=MaintenanceTaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Start Maintenance Task",
)
async def start_task(
    id: uuid.UUID,
    data: Optional[TaskStartRequest] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> MaintenanceTaskResponse:
    """Transitions task from TODO to IN_PROGRESS."""
    notes = data.notes if data else None
    task = await MaintenanceTaskService.start_task(
        db=db, user=current_user, task_id=id, notes=notes
    )
    await db.commit()
    await db.refresh(task)
    return MaintenanceTaskResponse.model_validate(task)


@router.post(
    "/tasks/{id}/complete",
    response_model=MaintenanceTaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Complete Maintenance Task",
)
async def complete_task(
    id: uuid.UUID,
    data: TaskCompleteRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> MaintenanceTaskResponse:
    """Transitions task to COMPLETED with mandatory completion notes."""
    task = await MaintenanceTaskService.complete_task(
        db=db, user=current_user, task_id=id, data=data
    )
    await db.commit()
    await db.refresh(task)
    return MaintenanceTaskResponse.model_validate(task)


@router.post(
    "/tasks/{id}/cancel",
    response_model=MaintenanceTaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel Maintenance Task",
)
async def cancel_task(
    id: uuid.UUID,
    data: TaskCancelRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> MaintenanceTaskResponse:
    """Cancels an open task. Restricted to Admins and assigned PMs."""
    task = await MaintenanceTaskService.cancel_task(
        db=db, user=current_user, task_id=id, data=data
    )
    await db.commit()
    await db.refresh(task)
    return MaintenanceTaskResponse.model_validate(task)


@router.post(
    "/tasks/{id}/reopen",
    response_model=MaintenanceTaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Reopen Completed Task",
)
async def reopen_task(
    id: uuid.UUID,
    data: TaskReopenRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> MaintenanceTaskResponse:
    """Reopens a COMPLETED task back to TODO with mandatory justification."""
    task = await MaintenanceTaskService.reopen_task(
        db=db, user=current_user, task_id=id, data=data
    )
    await db.commit()
    await db.refresh(task)
    return MaintenanceTaskResponse.model_validate(task)


# ============================================================================
# Survival Observation Endpoints
# ============================================================================


@router.post(
    "/survival-observations",
    response_model=SurvivalObservationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record Survival Observation",
)
async def create_survival_observation(
    data: SurvivalObservationCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> SurvivalObservationResponse:
    """
    Records a new survival observation.
    Server derives survival_rate; client-supplied survival_rate is rejected.
    """
    obs = await SurvivalObservationService.create_observation(
        db=db, user=current_user, data=data
    )
    await db.commit()
    await db.refresh(obs)

    assessed = obs.alive_count + obs.dead_count
    unassessed = max(0, obs.sample_size - assessed)

    return SurvivalObservationResponse(
        id=obs.id,
        project_id=obs.project_id,
        activity_id=obs.activity_id,
        inspection_id=obs.inspection_id,
        plot_identifier=obs.plot_identifier,
        cohort_identifier=obs.cohort_identifier,
        methodology=obs.methodology,
        coverage_area_sqm=obs.coverage_area_sqm,
        observation_date=obs.observation_date,
        sample_size=obs.sample_size,
        alive_count=obs.alive_count,
        dead_count=obs.dead_count,
        unassessed_count=unassessed,
        survival_rate=obs.survival_rate,
        mortality_causes=obs.mortality_causes,
        is_definitive=obs.is_definitive,
        is_active=obs.is_active,
        superseded_by_id=obs.superseded_by_id,
        correction_notes=obs.correction_notes,
        notes=obs.notes,
        created_at=obs.created_at,
    )


@router.get(
    "/survival-observations",
    response_model=List[SurvivalObservationResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Survival Observation History",
)
async def list_survival_observations(
    project_id: uuid.UUID = Query(..., description="Project ID"),
    plot_identifier: Optional[str] = Query(None, description="Filter by plot identifier"),
    cohort_identifier: Optional[str] = Query(None, description="Filter by cohort identifier"),
    active_only: bool = Query(False, description="Filter to active observations only"),
    skip: int = Query(0, ge=0, description="Pagination skip"),
    limit: int = Query(50, ge=1, le=100, description="Pagination limit"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> List[SurvivalObservationResponse]:
    """Retrieves survival observation history. Preserves historical superseded rows when active_only=False."""
    history = await SurvivalObservationService.get_observation_history(
        db=db,
        user=current_user,
        project_id=project_id,
        plot_identifier=plot_identifier,
        cohort_identifier=cohort_identifier,
        active_only=active_only,
    )
    paginated = history[skip : skip + limit]

    responses = []
    for obs in paginated:
        assessed = obs.alive_count + obs.dead_count
        unassessed = max(0, obs.sample_size - assessed)
        responses.append(
            SurvivalObservationResponse(
                id=obs.id,
                project_id=obs.project_id,
                activity_id=obs.activity_id,
                inspection_id=obs.inspection_id,
                plot_identifier=obs.plot_identifier,
                cohort_identifier=obs.cohort_identifier,
                methodology=obs.methodology,
                coverage_area_sqm=obs.coverage_area_sqm,
                observation_date=obs.observation_date,
                sample_size=obs.sample_size,
                alive_count=obs.alive_count,
                dead_count=obs.dead_count,
                unassessed_count=unassessed,
                survival_rate=obs.survival_rate,
                mortality_causes=obs.mortality_causes,
                is_definitive=obs.is_definitive,
                is_active=obs.is_active,
                superseded_by_id=obs.superseded_by_id,
                correction_notes=obs.correction_notes,
                notes=obs.notes,
                created_at=obs.created_at,
            )
        )
    return responses


@router.get(
    "/survival-observations/{id}",
    response_model=SurvivalObservationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Survival Observation Details",
)
async def get_survival_observation(
    id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> SurvivalObservationResponse:
    """Retrieves full details of a specific survival observation."""
    obs = await SurvivalObservationService.get_observation(
        db=db, user=current_user, observation_id=id
    )
    assessed = obs.alive_count + obs.dead_count
    unassessed = max(0, obs.sample_size - assessed)

    return SurvivalObservationResponse(
        id=obs.id,
        project_id=obs.project_id,
        activity_id=obs.activity_id,
        inspection_id=obs.inspection_id,
        plot_identifier=obs.plot_identifier,
        cohort_identifier=obs.cohort_identifier,
        methodology=obs.methodology,
        coverage_area_sqm=obs.coverage_area_sqm,
        observation_date=obs.observation_date,
        sample_size=obs.sample_size,
        alive_count=obs.alive_count,
        dead_count=obs.dead_count,
        unassessed_count=unassessed,
        survival_rate=obs.survival_rate,
        mortality_causes=obs.mortality_causes,
        is_definitive=obs.is_definitive,
        is_active=obs.is_active,
        superseded_by_id=obs.superseded_by_id,
        correction_notes=obs.correction_notes,
        notes=obs.notes,
        created_at=obs.created_at,
    )


@router.post(
    "/survival-observations/{id}/correct",
    response_model=SurvivalObservationResponse,
    status_code=status.HTTP_200_OK,
    summary="Record Observation Correction (Supersession)",
)
async def correct_survival_observation(
    id: uuid.UUID,
    data: SurvivalObservationCorrectionRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> SurvivalObservationResponse:
    """
    Performs atomic supersession of an active survival observation.
    Restricted to Admins and assigned PMs.
    Deactivates original, sets superseded_by_id, and creates active replacement.
    """
    orig, replacement = await SurvivalObservationService.correct_observation(
        db=db, user=current_user, observation_id=id, replacement_data=data
    )
    await db.commit()
    await db.refresh(replacement)

    assessed = replacement.alive_count + replacement.dead_count
    unassessed = max(0, replacement.sample_size - assessed)

    return SurvivalObservationResponse(
        id=replacement.id,
        project_id=replacement.project_id,
        activity_id=replacement.activity_id,
        inspection_id=replacement.inspection_id,
        plot_identifier=replacement.plot_identifier,
        cohort_identifier=replacement.cohort_identifier,
        methodology=replacement.methodology,
        coverage_area_sqm=replacement.coverage_area_sqm,
        observation_date=replacement.observation_date,
        sample_size=replacement.sample_size,
        alive_count=replacement.alive_count,
        dead_count=replacement.dead_count,
        unassessed_count=unassessed,
        survival_rate=replacement.survival_rate,
        mortality_causes=replacement.mortality_causes,
        is_definitive=replacement.is_definitive,
        is_active=replacement.is_active,
        superseded_by_id=replacement.superseded_by_id,
        correction_notes=replacement.correction_notes,
        notes=replacement.notes,
        created_at=replacement.created_at,
    )


@router.get(
    "/survival-analytics",
    response_model=List[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Get Longitudinal Survival Trajectory",
)
async def get_survival_analytics(
    project_id: uuid.UUID = Query(..., description="Project ID"),
    plot_identifier: str = Query(..., description="Plot identifier"),
    cohort_identifier: str = Query(..., description="Cohort identifier"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Retrieves active longitudinal survival trajectory curves for a plot/cohort unit."""
    return await SurvivalObservationService.get_survival_trajectory(
        db=db,
        user=current_user,
        project_id=project_id,
        plot_identifier=plot_identifier,
        cohort_identifier=cohort_identifier,
    )


# ============================================================================
# Monitoring Operations: Alerts & Dashboard
# ============================================================================


@router.get(
    "/alerts",
    response_model=MonitoringAlertSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Active Monitoring Alerts",
)
async def get_monitoring_alerts(
    project_id: Optional[uuid.UUID] = Query(None, description="Optional project ID scoping"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> MonitoringAlertSummaryResponse:
    """Evaluates dynamic operational monitoring alerts on-demand in PostgreSQL."""
    return await AlertService.get_alert_summary(
        db=db, user=current_user, project_id=project_id
    )


@router.get(
    "/dashboard",
    response_model=MonitoringDashboardResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Monitoring Dashboard Summary",
)
async def get_monitoring_dashboard(
    project_id: Optional[uuid.UUID] = Query(None, description="Optional project ID scoping"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> MonitoringDashboardResponse:
    """Aggregates monitoring KPIs, backlog counts, active alerts, and latest observations."""
    data = await MonitoringDashboardService.get_dashboard_summary(
        db=db, user=current_user, project_id=project_id
    )
    return MonitoringDashboardResponse(**data)
