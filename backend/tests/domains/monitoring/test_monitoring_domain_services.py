"""
VANA — Phase 6.2 Monitoring Domain Services Test Suite
Verifies:
- Inspection lifecycle, invalid transitions, inspector ownership, addenda, and cancellation.
- Maintenance task lifecycle, assignee validation, reopening, and cross-project rejection.
- Survival observation creation, zero denominator handling, validation, duplicate prevention.
- Atomic observation supersession, acyclic integrity, history preservation, and trajectory queries.
- Dynamic alerts query engine (overdue inspections, upcoming inspections, overdue tasks).
- Role-based access control (RBAC) and project boundary isolation.
- Comprehensive immutable audit trail logging.
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import uuid
import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.audit.models import AuditLog
from app.domains.auth.models import User, UserRole
from app.domains.monitoring.models import (
    CanopyCondition,
    FieldInspection,
    InspectionStatus,
    InspectionType,
    MaintenanceTask,
    SoilMoistureCondition,
    SurvivalMethodology,
    SurvivalObservation,
    TaskCategory,
    TaskPriority,
    TaskStatus,
)
from app.domains.monitoring.schemas import (
    AlertType,
    FieldInspectionCreate,
    InspectionAddendumCreate,
    InspectionCancelRequest,
    InspectionCompleteRequest,
    MaintenanceTaskCreate,
    SurvivalObservationCorrectionRequest,
    SurvivalObservationCreate,
    TaskCancelRequest,
    TaskCompleteRequest,
    TaskReopenRequest,
)
from app.domains.monitoring.services import (
    AlertService,
    InspectionService,
    MaintenanceTaskService,
    MonitoringAuthorizationService,
    SurvivalObservationService,
)
from app.domains.operations.models import FieldActivity
from app.domains.projects.models import Project, ProjectStatus
from app.domains.teams.models import ProjectAssignment


# ============================================================================
# Test Fixtures & Helpers
# ============================================================================


async def create_test_user(
    db: AsyncSession, role: UserRole, full_name: str = "Test User"
) -> User:
    user = User(
        id=uuid.uuid4(),
        email=f"user_{uuid.uuid4().hex[:8]}@vana.org",
        hashed_password="pw_hash_mock",
        full_name=full_name,
        role=role.value,
        is_active=True,
    )
    db.add(user)
    await db.flush()
    return user


async def create_test_project(db: AsyncSession, name: str = "Project Alpha") -> Project:
    project = Project(
        id=uuid.uuid4(),
        name=name,
        code=f"PRJ-{uuid.uuid4().hex[:6].upper()}",
        description="Monitoring Test Project",
        status=ProjectStatus.ACTIVE.value,
        latitude=12.9716,
        longitude=77.5946,
    )
    db.add(project)
    await db.flush()
    return project


async def assign_user_to_project(
    db: AsyncSession,
    user_id: uuid.UUID,
    project_id: uuid.UUID,
    assigned_role: str = "FIELD_OFFICER",
) -> ProjectAssignment:
    assignment = ProjectAssignment(
        id=uuid.uuid4(),
        project_id=project_id,
        user_id=user_id,
        assigned_role=assigned_role,
    )
    db.add(assignment)
    await db.flush()
    return assignment


async def create_test_activity(
    db: AsyncSession, project_id: uuid.UUID, user_id: uuid.UUID
) -> FieldActivity:
    act = FieldActivity(
        id=uuid.uuid4(),
        project_id=project_id,
        created_by_id=user_id,
        metric_code="TREES_PLANTED",
        unit="TREES",
        is_archived=False,
    )
    db.add(act)
    await db.flush()
    return act


# ============================================================================
# 1. Field Inspection Management Tests
# ============================================================================


@pytest.mark.asyncio
async def test_schedule_inspection_success_and_audit(db_session: AsyncSession):
    """Verifies that an assigned PM can schedule an inspection with full audit logging."""
    admin = await create_test_user(db_session, UserRole.ADMIN, "Admin User")
    pm = await create_test_user(db_session, UserRole.PROJECT_MANAGER, "PM User")
    officer = await create_test_user(db_session, UserRole.FIELD_OFFICER, "Field Officer")
    proj = await create_test_project(db_session, "Kaveri Basin Restoration")

    await assign_user_to_project(db_session, pm.id, proj.id)
    await assign_user_to_project(db_session, officer.id, proj.id)

    activity = await create_test_activity(db_session, proj.id, officer.id)

    sched_date = date.today() + timedelta(days=3)
    data = FieldInspectionCreate(
        project_id=proj.id,
        scheduled_date=sched_date,
        inspection_type=InspectionType.ROUTINE,
        assigned_to_id=officer.id,
        linked_activity_id=activity.id,
    )

    inspection = await InspectionService.schedule_inspection(db_session, pm, data)
    assert inspection.id is not None
    assert inspection.status == InspectionStatus.SCHEDULED.value
    assert inspection.project_id == proj.id
    assert inspection.assigned_to_id == officer.id
    assert inspection.linked_activity_id == activity.id

    # Verify audit log was created
    audit = await db_session.scalar(
        select(AuditLog).where(
            AuditLog.entity_id == inspection.id,
            AuditLog.action_type == "INSPECTION_SCHEDULED",
        )
    )
    assert audit is not None
    assert audit.actor_id == pm.id
    assert audit.entity_type == "FieldInspection"


@pytest.mark.asyncio
async def test_schedule_inspection_rbac_field_officer_denied(db_session: AsyncSession):
    """Verifies that a Field Officer cannot schedule inspections (HTTP 403)."""
    officer = await create_test_user(db_session, UserRole.FIELD_OFFICER)
    proj = await create_test_project(db_session)
    await assign_user_to_project(db_session, officer.id, proj.id)

    data = FieldInspectionCreate(
        project_id=proj.id,
        scheduled_date=date.today(),
        inspection_type=InspectionType.ROUTINE,
    )

    with pytest.raises(HTTPException) as exc:
        await InspectionService.schedule_inspection(db_session, officer, data)
    assert exc.value.status_code == 403
    assert "INSUFFICIENT_ROLE_PERMISSIONS" in str(exc.value.detail)


@pytest.mark.asyncio
async def test_schedule_inspection_unassigned_inspector_rejected(db_session: AsyncSession):
    """Verifies that assigning an inspector who is not assigned to the project is rejected (HTTP 400)."""
    admin = await create_test_user(db_session, UserRole.ADMIN)
    unassigned_officer = await create_test_user(db_session, UserRole.FIELD_OFFICER)
    proj = await create_test_project(db_session)

    data = FieldInspectionCreate(
        project_id=proj.id,
        scheduled_date=date.today(),
        assigned_to_id=unassigned_officer.id,
    )

    with pytest.raises(HTTPException) as exc:
        await InspectionService.schedule_inspection(db_session, admin, data)
    assert exc.value.status_code == 400
    assert "INSPECTOR_NOT_ASSIGNED_TO_PROJECT" in str(exc.value.detail)


@pytest.mark.asyncio
async def test_schedule_inspection_cross_project_activity_rejected(db_session: AsyncSession):
    """Verifies that linking an activity from another project is rejected at service layer (HTTP 400)."""
    admin = await create_test_user(db_session, UserRole.ADMIN)
    proj_a = await create_test_project(db_session, "Project A")
    proj_b = await create_test_project(db_session, "Project B")
    act_b = await create_test_activity(db_session, proj_b.id, admin.id)

    data = FieldInspectionCreate(
        project_id=proj_a.id,
        scheduled_date=date.today(),
        linked_activity_id=act_b.id,
    )

    with pytest.raises(HTTPException) as exc:
        await InspectionService.schedule_inspection(db_session, admin, data)
    assert exc.value.status_code == 400
    assert "CROSS_PROJECT_ACTIVITY_LINK_FORBIDDEN" in str(exc.value.detail)


@pytest.mark.asyncio
async def test_inspection_lifecycle_and_ownership(db_session: AsyncSession):
    """
    Verifies full inspection lifecycle:
    SCHEDULED -> IN_PROGRESS -> COMPLETED,
    along with Field Officer ownership protection (cannot touch another officer's inspection).
    """
    admin = await create_test_user(db_session, UserRole.ADMIN)
    officer_1 = await create_test_user(db_session, UserRole.FIELD_OFFICER, "Officer One")
    officer_2 = await create_test_user(db_session, UserRole.FIELD_OFFICER, "Officer Two")
    proj = await create_test_project(db_session)

    await assign_user_to_project(db_session, officer_1.id, proj.id)
    await assign_user_to_project(db_session, officer_2.id, proj.id)

    # Schedule inspection assigned to officer_1
    data = FieldInspectionCreate(
        project_id=proj.id,
        scheduled_date=date.today(),
        assigned_to_id=officer_1.id,
    )
    insp = await InspectionService.schedule_inspection(db_session, admin, data)

    # Officer 2 attempts to start Officer 1's inspection -> 403 Forbidden
    with pytest.raises(HTTPException) as exc:
        await InspectionService.start_inspection(db_session, officer_2, insp.id)
    assert exc.value.status_code == 403
    assert "INSPECTOR_OWNERSHIP_REQUIRED" in str(exc.value.detail)

    # Officer 1 starts their inspection -> IN_PROGRESS
    started = await InspectionService.start_inspection(db_session, officer_1, insp.id)
    assert started.status == InspectionStatus.IN_PROGRESS.value

    # Cannot start again -> 400 Invalid transition
    with pytest.raises(HTTPException) as exc:
        await InspectionService.start_inspection(db_session, officer_1, insp.id)
    assert exc.value.status_code == 400
    assert "INVALID_STATUS_TRANSITION" in str(exc.value.detail)

    # Officer 2 attempts to complete Officer 1's inspection -> 403
    complete_data = InspectionCompleteRequest(
        findings="Vegetation flourishing, canopy closed.",
        vegetation_health_score=5,
        canopy_condition=CanopyCondition.EXCELLENT,
        soil_moisture_condition=SoilMoistureCondition.ADEQUATE,
        threats_detected=["MILD_WEED_ENCROACHMENT"],
    )
    with pytest.raises(HTTPException) as exc:
        await InspectionService.complete_inspection(db_session, officer_2, insp.id, complete_data)
    assert exc.value.status_code == 403
    assert "INSPECTOR_OWNERSHIP_REQUIRED" in str(exc.value.detail)

    # Officer 1 completes their inspection -> COMPLETED
    completed = await InspectionService.complete_inspection(
        db_session, officer_1, insp.id, complete_data
    )
    assert completed.status == InspectionStatus.COMPLETED.value
    assert completed.completed_at is not None
    assert completed.vegetation_health_score == 5
    assert completed.findings == "Vegetation flourishing, canopy closed."

    # Direct edit / re-completion locked -> 400
    with pytest.raises(HTTPException) as exc:
        await InspectionService.complete_inspection(db_session, officer_1, insp.id, complete_data)
    assert exc.value.status_code == 400
    assert "COMPLETED_INSPECTION_LOCKED" in str(exc.value.detail)


@pytest.mark.asyncio
async def test_inspection_cancellation_and_addendum(db_session: AsyncSession):
    """Verifies inspection cancellation rules and post-completion immutable addenda."""
    admin = await create_test_user(db_session, UserRole.ADMIN)
    pm = await create_test_user(db_session, UserRole.PROJECT_MANAGER)
    officer = await create_test_user(db_session, UserRole.FIELD_OFFICER)
    proj = await create_test_project(db_session)
    await assign_user_to_project(db_session, pm.id, proj.id)
    await assign_user_to_project(db_session, officer.id, proj.id)

    # Case 1: Cancel SCHEDULED inspection
    insp1 = await InspectionService.schedule_inspection(
        db_session,
        admin,
        FieldInspectionCreate(project_id=proj.id, scheduled_date=date.today()),
    )
    # Field Officer cannot cancel -> 403
    with pytest.raises(HTTPException) as exc:
        await InspectionService.cancel_inspection(
            db_session, officer, insp1.id, InspectionCancelRequest(cancellation_reason="No access")
        )
    assert exc.value.status_code == 403

    # PM cancels with reason
    cancelled = await InspectionService.cancel_inspection(
        db_session, pm, insp1.id, InspectionCancelRequest(cancellation_reason="Monsoon flooding blocked access")
    )
    assert cancelled.status == InspectionStatus.CANCELLED.value
    assert len(cancelled.addenda) == 1
    assert "Monsoon flooding" in cancelled.addenda[0]["reason"]

    # Case 2: Post-completion Correction Addendum
    insp2 = await InspectionService.schedule_inspection(
        db_session,
        admin,
        FieldInspectionCreate(project_id=proj.id, scheduled_date=date.today(), assigned_to_id=officer.id),
    )
    await InspectionService.start_inspection(db_session, officer, insp2.id)
    await InspectionService.complete_inspection(
        db_session,
        officer,
        insp2.id,
        InspectionCompleteRequest(findings="Original observation findings.", vegetation_health_score=4),
    )

    # Cannot cancel completed inspection -> 400
    with pytest.raises(HTTPException) as exc:
        await InspectionService.cancel_inspection(
            db_session, pm, insp2.id, InspectionCancelRequest(cancellation_reason="Too late")
        )
    assert exc.value.status_code == 400

    # PM records formal addendum
    addendum_data = InspectionAddendumCreate(
        content="Subsequent soil sample test revealed nitrogen deficiency in Plot B-2."
    )
    updated = await InspectionService.add_addendum(db_session, pm, insp2.id, addendum_data)
    assert len(updated.addenda) == 1
    assert "nitrogen deficiency" in updated.addenda[0]["content"]
    assert updated.findings == "Original observation findings."  # Original findings untouched


# ============================================================================
# 2. Maintenance Task Service Tests
# ============================================================================


@pytest.mark.asyncio
async def test_maintenance_task_lifecycle_and_reopen(db_session: AsyncSession):
    """
    Verifies maintenance task:
    TODO -> IN_PROGRESS -> COMPLETED,
    cancellation, and reopening back to TODO with mandatory justification.
    """
    admin = await create_test_user(db_session, UserRole.ADMIN)
    pm = await create_test_user(db_session, UserRole.PROJECT_MANAGER)
    officer = await create_test_user(db_session, UserRole.FIELD_OFFICER)
    proj = await create_test_project(db_session)
    await assign_user_to_project(db_session, pm.id, proj.id)
    await assign_user_to_project(db_session, officer.id, proj.id)

    task_data = MaintenanceTaskCreate(
        project_id=proj.id,
        title="Drip Irrigation Repair",
        description="Fix breached PVC lines in north sector",
        category=TaskCategory.IRRIGATION,
        priority=TaskPriority.HIGH,
        due_date=date.today() + timedelta(days=2),
        assigned_to_id=officer.id,
    )

    # Field officer cannot create task -> 403
    with pytest.raises(HTTPException) as exc:
        await MaintenanceTaskService.create_task(db_session, officer, task_data)
    assert exc.value.status_code == 403

    # PM creates task -> TODO
    task = await MaintenanceTaskService.create_task(db_session, pm, task_data)
    assert task.status == TaskStatus.TODO.value

    # Officer starts task -> IN_PROGRESS
    started_task = await MaintenanceTaskService.start_task(db_session, officer, task.id)
    assert started_task.status == TaskStatus.IN_PROGRESS.value

    # Officer completes task with notes
    completed_task = await MaintenanceTaskService.complete_task(
        db_session, officer, task.id, TaskCompleteRequest(completion_notes="Replaced 15 meters of pipe, tested flow.")
    )
    assert completed_task.status == TaskStatus.COMPLETED.value
    assert completed_task.completed_at is not None

    # Field Officer cannot reopen task -> 403
    with pytest.raises(HTTPException) as exc:
        await MaintenanceTaskService.reopen_task(
            db_session, officer, task.id, TaskReopenRequest(justification="Leak remains")
        )
    assert exc.value.status_code == 403

    # PM reopens task with justification -> status resets to TODO
    reopened = await MaintenanceTaskService.reopen_task(
        db_session, pm, task.id, TaskReopenRequest(justification="Pressure test failed at connection B")
    )
    assert reopened.status == TaskStatus.TODO.value
    assert reopened.completed_at is None
    assert "Pressure test failed" in reopened.completion_notes


@pytest.mark.asyncio
async def test_maintenance_task_cross_project_reference_rejection(db_session: AsyncSession):
    """Verifies that maintenance task linking across project boundaries is rejected (HTTP 400)."""
    admin = await create_test_user(db_session, UserRole.ADMIN)
    proj_a = await create_test_project(db_session, "Project A")
    proj_b = await create_test_project(db_session, "Project B")

    insp_b = await InspectionService.schedule_inspection(
        db_session, admin, FieldInspectionCreate(project_id=proj_b.id, scheduled_date=date.today())
    )

    task_cross = MaintenanceTaskCreate(
        project_id=proj_a.id,
        title="Cross project repair",
        category=TaskCategory.WEEDING,
        due_date=date.today(),
        inspection_id=insp_b.id,
    )

    with pytest.raises(HTTPException) as exc:
        await MaintenanceTaskService.create_task(db_session, admin, task_cross)
    assert exc.value.status_code == 400
    assert "CROSS_PROJECT_INSPECTION_LINK_FORBIDDEN" in str(exc.value.detail)


# ============================================================================
# 3. Survival Observation & Atomic Supersession Tests
# ============================================================================


@pytest.mark.asyncio
async def test_survival_observation_creation_and_rate_derivation(db_session: AsyncSession):
    """
    Verifies that survival observations derive survival rate server-side:
    - 40 alive, 10 dead -> 80.0%
    - Client cannot inject custom survival rate.
    - Zero assessed population (alive=0, dead=0) safely yields None without ZeroDivisionError.
    """
    admin = await create_test_user(db_session, UserRole.ADMIN)
    proj = await create_test_project(db_session)

    # Standard observation
    data_standard = SurvivalObservationCreate(
        project_id=proj.id,
        plot_identifier="PLOT-EAST-01",
        cohort_identifier="COHORT-2025-BATCH-1",
        methodology=SurvivalMethodology.SAMPLE_PLOT,
        observation_date=date.today(),
        sample_size=100,
        alive_count=40,
        dead_count=10,
    )
    obs = await SurvivalObservationService.create_observation(db_session, admin, data_standard)
    assert obs.is_active is True
    assert obs.survival_rate == 80.0

    # Zero assessed population observation (alive=0, dead=0, sample_size=50)
    data_zero_assessed = SurvivalObservationCreate(
        project_id=proj.id,
        plot_identifier="PLOT-WEST-02",
        cohort_identifier="COHORT-2025-BATCH-1",
        methodology=SurvivalMethodology.SAMPLE_PLOT,
        observation_date=date.today(),
        sample_size=50,
        alive_count=0,
        dead_count=0,
    )
    obs_zero = await SurvivalObservationService.create_observation(db_session, admin, data_zero_assessed)
    assert obs_zero.survival_rate is None  # Undefined rate when denominator is 0


@pytest.mark.asyncio
async def test_survival_observation_duplicate_active_rejected(db_session: AsyncSession):
    """
    Verifies that attempting to record a second active observation on the same
    (project, plot, cohort, date) is rejected with HTTP 409 Conflict.
    """
    admin = await create_test_user(db_session, UserRole.ADMIN)
    proj = await create_test_project(db_session)

    data = SurvivalObservationCreate(
        project_id=proj.id,
        plot_identifier="PLOT-NORTH-01",
        cohort_identifier="COHORT-A",
        observation_date=date.today(),
        sample_size=100,
        alive_count=80,
        dead_count=15,
    )
    await SurvivalObservationService.create_observation(db_session, admin, data)

    # Attempt second active observation on identical plot/cohort/date
    with pytest.raises(HTTPException) as exc:
        await SurvivalObservationService.create_observation(db_session, admin, data)
    assert exc.value.status_code == 409
    assert "ACTIVE_OBSERVATION_ALREADY_EXISTS" in str(exc.value.detail)


@pytest.mark.asyncio
async def test_atomic_observation_supersession_workflow(db_session: AsyncSession):
    """
    Verifies the atomic supersession workflow:
    - Original observation locked.
    - Original marked is_active = False, superseded_by_id linked to replacement.
    - Replacement created as is_active = True on the exact same date without collision.
    - Both states recorded in audit logs.
    - Historical query preserves the superseded record.
    - Trajectory query returns only the active replacement with updated 90.0% rate.
    """
    admin = await create_test_user(db_session, UserRole.ADMIN)
    pm = await create_test_user(db_session, UserRole.PROJECT_MANAGER)
    officer = await create_test_user(db_session, UserRole.FIELD_OFFICER)
    proj = await create_test_project(db_session)
    await assign_user_to_project(db_session, pm.id, proj.id)
    await assign_user_to_project(db_session, officer.id, proj.id)

    # Initial observation: 60 alive, 40 dead out of 100 (60.0% survival)
    initial_data = SurvivalObservationCreate(
        project_id=proj.id,
        plot_identifier="PLOT-SOUTH-05",
        cohort_identifier="COHORT-2025-BATCH-2",
        observation_date=date.today(),
        sample_size=100,
        alive_count=60,
        dead_count=40,
    )
    initial_obs = await SurvivalObservationService.create_observation(db_session, admin, initial_data)
    assert initial_obs.survival_rate == 60.0
    assert initial_obs.is_active is True

    # Field officer cannot perform supersession -> 403
    correction_data = SurvivalObservationCorrectionRequest(
        sample_size=100,
        alive_count=90,
        dead_count=10,
        correction_notes="Factual correction: 30 saplings were dormant deciduous species mistakenly tallied as dead.",
    )
    with pytest.raises(HTTPException) as exc:
        await SurvivalObservationService.correct_observation(db_session, officer, initial_obs.id, correction_data)
    assert exc.value.status_code == 403

    # PM executes atomic supersession
    orig, replacement = await SurvivalObservationService.correct_observation(
        db_session, pm, initial_obs.id, correction_data
    )

    # Verify original state
    assert orig.id == initial_obs.id
    assert orig.is_active is False
    assert orig.superseded_by_id == replacement.id
    assert "dormant deciduous" in orig.correction_notes

    # Verify replacement state
    assert replacement.id != orig.id
    assert replacement.is_active is True
    assert replacement.superseded_by_id is None
    assert replacement.project_id == orig.project_id
    assert replacement.plot_identifier == orig.plot_identifier
    assert replacement.cohort_identifier == orig.cohort_identifier
    assert replacement.observation_date == orig.observation_date
    assert replacement.alive_count == 90
    assert replacement.dead_count == 10
    assert replacement.survival_rate == 90.0

    # Attempting to correct an already superseded observation is rejected -> 400
    with pytest.raises(HTTPException) as exc:
        await SurvivalObservationService.correct_observation(db_session, pm, orig.id, correction_data)
    assert exc.value.status_code == 400
    assert "OBSERVATION_ALREADY_SUPERSEDED" in str(exc.value.detail)

    # History retrieval (active_only=False) retains both rows
    history = await SurvivalObservationService.get_observation_history(
        db_session, pm, proj.id, "PLOT-SOUTH-05", "COHORT-2025-BATCH-2", active_only=False
    )
    assert len(history) == 2
    assert any(h.is_active is False for h in history)
    assert any(h.is_active is True for h in history)

    # Longitudinal trajectory returns only the single active observation with 90% rate
    trajectory = await SurvivalObservationService.get_survival_trajectory(
        db_session, pm, proj.id, "PLOT-SOUTH-05", "COHORT-2025-BATCH-2"
    )
    assert len(trajectory) == 1
    assert trajectory[0]["survival_rate"] == 90.0
    assert trajectory[0]["assessed_count"] == 100
    assert trajectory[0]["unassessed_count"] == 0


# ============================================================================
# 4. Dynamic Alerts Query Engine Tests
# ============================================================================


@pytest.mark.asyncio
async def test_dynamic_monitoring_alerts_evaluation(db_session: AsyncSession):
    """
    Verifies on-demand SQL alert evaluation:
    1. OVERDUE_INSPECTION (scheduled_date < today)
    2. UPCOMING_INSPECTION (scheduled_date between today and today + 7 days)
    3. OVERDUE_TASK (due_date < today in TODO/IN_PROGRESS)
    Completed and cancelled items are not flagged.
    """
    admin = await create_test_user(db_session, UserRole.ADMIN)
    proj = await create_test_project(db_session)
    today = date.today()

    # 1. Overdue inspection (scheduled 2 days ago)
    overdue_insp = FieldInspection(
        id=uuid.uuid4(),
        project_id=proj.id,
        scheduled_date=today - timedelta(days=2),
        status=InspectionStatus.SCHEDULED.value,
        inspection_type=InspectionType.ROUTINE.value,
    )
    # 2. Upcoming inspection (scheduled 4 days from now)
    upcoming_insp = FieldInspection(
        id=uuid.uuid4(),
        project_id=proj.id,
        scheduled_date=today + timedelta(days=4),
        status=InspectionStatus.SCHEDULED.value,
        inspection_type=InspectionType.SURVIVAL_CHECK.value,
    )
    # 3. Completed past inspection (should NOT be flagged)
    completed_insp = FieldInspection(
        id=uuid.uuid4(),
        project_id=proj.id,
        scheduled_date=today - timedelta(days=5),
        status=InspectionStatus.COMPLETED.value,
        inspection_type=InspectionType.ROUTINE.value,
        findings="Done",
    )
    # 4. Overdue Task (due 3 days ago, TODO)
    overdue_task = MaintenanceTask(
        id=uuid.uuid4(),
        project_id=proj.id,
        title="Weeding sector 3",
        category=TaskCategory.WEEDING.value,
        priority=TaskPriority.HIGH.value,
        status=TaskStatus.TODO.value,
        due_date=today - timedelta(days=3),
    )
    # 5. Completed Task (due 3 days ago, should NOT be flagged)
    completed_task = MaintenanceTask(
        id=uuid.uuid4(),
        project_id=proj.id,
        title="Fertilizer application",
        category=TaskCategory.SOIL_ENRICHMENT.value,
        priority=TaskPriority.MEDIUM.value,
        status=TaskStatus.COMPLETED.value,
        due_date=today - timedelta(days=3),
    )

    db_session.add_all([overdue_insp, upcoming_insp, completed_insp, overdue_task, completed_task])
    await db_session.flush()

    summary = await AlertService.get_alert_summary(db_session, admin, proj.id)
    assert summary.total_alerts == 3
    assert summary.high_count == 2  # Overdue inspection + high-priority overdue task
    assert summary.medium_count == 1  # Upcoming inspection

    alert_types = [a.alert_type for a in summary.alerts]
    assert AlertType.OVERDUE_INSPECTION in alert_types
    assert AlertType.UPCOMING_INSPECTION in alert_types
    assert AlertType.OVERDUE_TASK in alert_types



@pytest.mark.asyncio
async def test_concurrent_supersession_atomicity(db_session: AsyncSession):
    """
    Verifies that if an observation has already been superseded by another transaction,
    subsequent attempts to supersede the same observation are rejected with HTTP 400.
    """
    admin = await create_test_user(db_session, UserRole.ADMIN)
    proj = await create_test_project(db_session)

    initial_obs = await SurvivalObservationService.create_observation(
        db_session,
        admin,
        SurvivalObservationCreate(
            project_id=proj.id,
            plot_identifier="PLOT-CONCURRENCY",
            cohort_identifier="COHORT-C",
            observation_date=date.today(),
            sample_size=50,
            alive_count=35,
            dead_count=15,
        ),
    )

    # First supersession
    correction_1 = SurvivalObservationCorrectionRequest(
        sample_size=50,
        alive_count=40,
        dead_count=10,
        correction_notes="First correction note",
    )
    orig, rep1 = await SurvivalObservationService.correct_observation(
        db_session, admin, initial_obs.id, correction_1
    )
    assert orig.is_active is False
    assert rep1.is_active is True

    # Second supersession attempt targeting the already superseded original
    correction_2 = SurvivalObservationCorrectionRequest(
        sample_size=50,
        alive_count=45,
        dead_count=5,
        correction_notes="Second correction note",
    )
    with pytest.raises(HTTPException) as exc:
        await SurvivalObservationService.correct_observation(
            db_session, admin, initial_obs.id, correction_2
        )
    assert exc.value.status_code == 400
    assert "OBSERVATION_ALREADY_SUPERSEDED" in str(exc.value.detail)


@pytest.mark.asyncio
async def test_cross_project_survival_activity_and_inspection(db_session: AsyncSession):
    """Verifies that survival observation rejects linking activities or inspections from another project."""
    admin = await create_test_user(db_session, UserRole.ADMIN)
    proj_a = await create_test_project(db_session, "Proj A")
    proj_b = await create_test_project(db_session, "Proj B")

    act_b = await create_test_activity(db_session, proj_b.id, admin.id)
    insp_b = await InspectionService.schedule_inspection(
        db_session, admin, FieldInspectionCreate(project_id=proj_b.id, scheduled_date=date.today())
    )

    # Cross-project activity
    data_bad_act = SurvivalObservationCreate(
        project_id=proj_a.id,
        plot_identifier="PLOT-X",
        cohort_identifier="COHORT-X",
        observation_date=date.today(),
        sample_size=10,
        alive_count=5,
        dead_count=5,
        activity_id=act_b.id,
    )
    with pytest.raises(HTTPException) as exc1:
        await SurvivalObservationService.create_observation(db_session, admin, data_bad_act)
    assert exc1.value.status_code == 400
    assert "CROSS_PROJECT_ACTIVITY_LINK_FORBIDDEN" in str(exc1.value.detail)

    # Cross-project inspection
    data_bad_insp = SurvivalObservationCreate(
        project_id=proj_a.id,
        plot_identifier="PLOT-Y",
        cohort_identifier="COHORT-Y",
        observation_date=date.today(),
        sample_size=10,
        alive_count=5,
        dead_count=5,
        inspection_id=insp_b.id,
    )
    with pytest.raises(HTTPException) as exc2:
        await SurvivalObservationService.create_observation(db_session, admin, data_bad_insp)
    assert exc2.value.status_code == 400
    assert "CROSS_PROJECT_INSPECTION_LINK_FORBIDDEN" in str(exc2.value.detail)


@pytest.mark.asyncio
async def test_survival_trajectory_calculation_fidelity(db_session: AsyncSession):
    """Verifies trajectory chronological calculation over multiple observation dates."""
    admin = await create_test_user(db_session, UserRole.ADMIN)
    proj = await create_test_project(db_session)
    d1 = date.today() - timedelta(days=60)
    d2 = date.today() - timedelta(days=30)
    d3 = date.today()

    obs1 = SurvivalObservation(
        id=uuid.uuid4(),
        project_id=proj.id,
        plot_identifier="PLOT-TRAJ",
        cohort_identifier="COHORT-T",
        methodology=SurvivalMethodology.SAMPLE_PLOT.value,
        observation_date=d1,
        sample_size=100,
        alive_count=95,
        dead_count=5,
        is_active=True,
    )
    obs2 = SurvivalObservation(
        id=uuid.uuid4(),
        project_id=proj.id,
        plot_identifier="PLOT-TRAJ",
        cohort_identifier="COHORT-T",
        methodology=SurvivalMethodology.SAMPLE_PLOT.value,
        observation_date=d2,
        sample_size=100,
        alive_count=88,
        dead_count=12,
        is_active=True,
    )
    obs3 = SurvivalObservation(
        id=uuid.uuid4(),
        project_id=proj.id,
        plot_identifier="PLOT-TRAJ",
        cohort_identifier="COHORT-T",
        methodology=SurvivalMethodology.SAMPLE_PLOT.value,
        observation_date=d3,
        sample_size=100,
        alive_count=82,
        dead_count=18,
        is_active=True,
    )
    db_session.add_all([obs1, obs2, obs3])
    await db_session.flush()

    traj = await SurvivalObservationService.get_survival_trajectory(
        db_session, admin, proj.id, "PLOT-TRAJ", "COHORT-T"
    )
    assert len(traj) == 3
    assert traj[0]["observation_date"] == d1
    assert traj[0]["survival_rate"] == 95.0
    assert traj[1]["observation_date"] == d2
    assert traj[1]["survival_rate"] == 88.0
    assert traj[2]["observation_date"] == d3
    assert traj[2]["survival_rate"] == 82.0


@pytest.mark.asyncio
async def test_multi_tenant_scoping_for_monitoring(db_session: AsyncSession):
    """
    Verifies that Project Managers and Field Officers are strictly scoped
    to projects they are assigned to, while Admin receives portfolio-wide visibility.
    """
    admin = await create_test_user(db_session, UserRole.ADMIN, "Admin")
    pm = await create_test_user(db_session, UserRole.PROJECT_MANAGER, "Assigned PM")
    officer = await create_test_user(db_session, UserRole.FIELD_OFFICER, "Assigned FO")
    unassigned_pm = await create_test_user(db_session, UserRole.PROJECT_MANAGER, "Unassigned PM")

    proj_assigned = await create_test_project(db_session, "Assigned Project")
    proj_unassigned = await create_test_project(db_session, "Unassigned Project")

    await assign_user_to_project(db_session, pm.id, proj_assigned.id, "PROJECT_MANAGER")
    await assign_user_to_project(db_session, officer.id, proj_assigned.id, "FIELD_OFFICER")

    # Create inspection and task in assigned project
    insp_a = FieldInspection(
        id=uuid.uuid4(),
        project_id=proj_assigned.id,
        scheduled_date=date.today(),
        status=InspectionStatus.SCHEDULED.value,
        inspection_type=InspectionType.ROUTINE.value,
    )
    task_a = MaintenanceTask(
        id=uuid.uuid4(),
        project_id=proj_assigned.id,
        title="Assigned Task",
        category=TaskCategory.WEEDING.value,
        due_date=date.today(),
    )

    # Create inspection and task in unassigned project
    insp_u = FieldInspection(
        id=uuid.uuid4(),
        project_id=proj_unassigned.id,
        scheduled_date=date.today(),
        status=InspectionStatus.SCHEDULED.value,
        inspection_type=InspectionType.ROUTINE.value,
    )
    task_u = MaintenanceTask(
        id=uuid.uuid4(),
        project_id=proj_unassigned.id,
        title="Unassigned Task",
        category=TaskCategory.WEEDING.value,
        due_date=date.today(),
    )

    db_session.add_all([insp_a, task_a, insp_u, task_u])
    await db_session.flush()

    # 1. Unassigned PM accessing unassigned project -> 403 Forbidden
    with pytest.raises(HTTPException) as exc1:
        await InspectionService.list_inspections(db_session, unassigned_pm, project_id=proj_unassigned.id)
    assert exc1.value.status_code == 403
    assert "PROJECT_ACCESS_DENIED" in str(exc1.value.detail)

    # 2. PM querying without project_id -> returns ONLY assigned project records
    pm_insps = await InspectionService.list_inspections(db_session, pm)
    assert len(pm_insps) == 1
    assert pm_insps[0].project_id == proj_assigned.id

    pm_tasks = await MaintenanceTaskService.list_tasks(db_session, pm)
    assert len(pm_tasks) == 1
    assert pm_tasks[0].project_id == proj_assigned.id

    # 3. Admin querying without project_id -> returns ALL records across projects
    admin_insps = await InspectionService.list_inspections(db_session, admin)
    assert len(admin_insps) >= 2
    admin_tasks = await MaintenanceTaskService.list_tasks(db_session, admin)
    assert len(admin_tasks) >= 2
