from datetime import date, datetime, timezone
from decimal import Decimal
import uuid
import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.auth.models import User, UserRole
from app.domains.projects.models import Project, ProjectStatus
from app.domains.operations.models import (
    FieldActivity,
    ActivityRevision,
    ActivityStatus,
    EvidenceFile,
)
from app.domains.monitoring.models import (
    FieldInspection,
    InspectionStatus,
    InspectionType,
    CanopyCondition,
    SoilMoistureCondition,
    MaintenanceTask,
    TaskCategory,
    TaskPriority,
    TaskStatus,
    SurvivalObservation,
    SurvivalMethodology,
)


@pytest.mark.asyncio
async def test_schema_constraints_and_indexes(db_session: AsyncSession):
    """Verify that all Phase 6 constraints and indexes exist in PostgreSQL."""
    # Check constraints on field_inspections
    insp_checks = await db_session.execute(
        text(
            "SELECT conname FROM pg_constraint WHERE conrelid = 'field_inspections'::regclass AND contype = 'c';"
        )
    )
    insp_connames = {row[0] for row in insp_checks.fetchall()}
    assert "chk_inspection_status" in insp_connames
    assert "chk_inspection_type" in insp_connames
    assert "chk_vegetation_health_score" in insp_connames
    assert "chk_canopy_condition" in insp_connames
    assert "chk_soil_moisture" in insp_connames

    # Check constraints on maintenance_tasks
    task_checks = await db_session.execute(
        text(
            "SELECT conname FROM pg_constraint WHERE conrelid = 'maintenance_tasks'::regclass AND contype = 'c';"
        )
    )
    task_connames = {row[0] for row in task_checks.fetchall()}
    assert "chk_task_category" in task_connames
    assert "chk_task_priority" in task_connames
    assert "chk_task_status" in task_connames

    # Check constraints on survival_observations
    surv_checks = await db_session.execute(
        text(
            "SELECT conname FROM pg_constraint WHERE conrelid = 'survival_observations'::regclass AND contype = 'c';"
        )
    )
    surv_connames = {row[0] for row in surv_checks.fetchall()}
    assert "chk_survival_methodology" in surv_connames
    assert "chk_survival_counts_positive" in surv_connames
    assert "chk_survival_sum_valid" in surv_connames
    assert "chk_survival_no_self_supersede" in surv_connames

    # Check constraints on evidence_files
    evid_checks = await db_session.execute(
        text(
            "SELECT conname FROM pg_constraint WHERE conrelid = 'evidence_files'::regclass AND contype = 'c';"
        )
    )
    evid_connames = {row[0] for row in evid_checks.fetchall()}
    assert "chk_evidence_target" in evid_connames
    assert "chk_evidence_file_size_positive" in evid_connames

    # Check partial unique index on survival_observations
    indexes = await db_session.execute(
        text(
            "SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'survival_observations';"
        )
    )
    idx_map = {row[0]: row[1] for row in indexes.fetchall()}
    assert "uq_active_survival_observation" in idx_map
    assert "WHERE (is_active = true)" in idx_map["uq_active_survival_observation"]


@pytest.mark.asyncio
async def test_composite_fk_inspection_activity_cross_project(db_session: AsyncSession):
    """Verify that field_inspections rejects linking an activity from another project."""
    admin = User(
        email=f"admin_{uuid.uuid4().hex[:6]}@vana.org",
        hashed_password="pw",
        full_name="Admin User",
        role=UserRole.ADMIN.value,
        is_active=True,
    )
    proj_a = Project(name="Project A", code=f"PRJ-A-{uuid.uuid4().hex[:4]}", latitude=12.5, longitude=77.5)
    proj_b = Project(name="Project B", code=f"PRJ-B-{uuid.uuid4().hex[:4]}", latitude=13.0, longitude=78.0)
    db_session.add_all([admin, proj_a, proj_b])
    await db_session.flush()

    act_b = FieldActivity(project_id=proj_b.id, created_by_id=admin.id, metric_code="TREES_PLANTED", unit="TREES")
    db_session.add(act_b)
    await db_session.flush()

    # Attempt to create inspection in Project A referencing activity in Project B
    insp_cross = FieldInspection(
        project_id=proj_a.id,
        linked_activity_id=act_b.id,
        scheduled_date=date.today(),
        status=InspectionStatus.SCHEDULED.value,
    )
    db_session.add(insp_cross)
    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_composite_fk_task_inspection_cross_project(db_session: AsyncSession):
    """Verify that maintenance_tasks rejects linking an inspection from another project."""
    proj_a = Project(name="Project A", code=f"PRJ-A-{uuid.uuid4().hex[:4]}", latitude=12.5, longitude=77.5)
    proj_b = Project(name="Project B", code=f"PRJ-B-{uuid.uuid4().hex[:4]}", latitude=13.0, longitude=78.0)
    db_session.add_all([proj_a, proj_b])
    await db_session.flush()

    insp_b = FieldInspection(
        project_id=proj_b.id,
        scheduled_date=date.today(),
        status=InspectionStatus.SCHEDULED.value,
    )
    db_session.add(insp_b)
    await db_session.flush()

    # Attempt to create task in Project A referencing inspection in Project B
    task_cross = MaintenanceTask(
        project_id=proj_a.id,
        inspection_id=insp_b.id,
        title="Cross Task",
        category=TaskCategory.WEEDING.value,
        due_date=date.today(),
    )
    db_session.add(task_cross)
    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_composite_fk_survival_activity_cross_project(db_session: AsyncSession):
    """Verify that survival_observations rejects linking an activity from another project."""
    admin = User(
        email=f"admin_{uuid.uuid4().hex[:6]}@vana.org",
        hashed_password="pw",
        full_name="Admin User",
        role=UserRole.ADMIN.value,
        is_active=True,
    )
    proj_a = Project(name="Project A", code=f"PRJ-A-{uuid.uuid4().hex[:4]}", latitude=12.5, longitude=77.5)
    proj_b = Project(name="Project B", code=f"PRJ-B-{uuid.uuid4().hex[:4]}", latitude=13.0, longitude=78.0)
    db_session.add_all([admin, proj_a, proj_b])
    await db_session.flush()

    act_b = FieldActivity(project_id=proj_b.id, created_by_id=admin.id, metric_code="TREES_PLANTED", unit="TREES")
    db_session.add(act_b)
    await db_session.flush()

    surv_cross = SurvivalObservation(
        project_id=proj_a.id,
        activity_id=act_b.id,
        plot_identifier="PLOT-01",
        cohort_identifier="COHORT-2026",
        observation_date=date.today(),
        sample_size=100,
        alive_count=90,
        dead_count=10,
    )
    db_session.add(surv_cross)
    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_column_specific_set_null_behavior(db_session: AsyncSession):
    """Verify that column-specific ON DELETE SET NULL clears referencing column without nullifying project_id."""
    admin = User(
        email=f"admin_{uuid.uuid4().hex[:6]}@vana.org",
        hashed_password="pw",
        full_name="Admin User",
        role=UserRole.ADMIN.value,
        is_active=True,
    )
    proj = Project(
        name="Project Delta",
        code=f"PRJ-D-{uuid.uuid4().hex[:4]}",
        status=ProjectStatus.ACTIVE.value,
        latitude=12.5,
        longitude=77.5,
    )
    db_session.add_all([admin, proj])
    await db_session.flush()

    # Create Activity A
    act_a = FieldActivity(
        project_id=proj.id,
        created_by_id=admin.id,
        metric_code="TREES_PLANTED",
        unit="TREES",
    )
    db_session.add(act_a)
    await db_session.flush()

    # Create Inspection linked to Activity A
    insp = FieldInspection(
        project_id=proj.id,
        linked_activity_id=act_a.id,
        scheduled_date=date.today(),
        status=InspectionStatus.SCHEDULED.value,
    )
    db_session.add(insp)
    await db_session.flush()

    # Create Task linked to Inspection
    task = MaintenanceTask(
        project_id=proj.id,
        inspection_id=insp.id,
        title="Check Irrigation",
        category=TaskCategory.IRRIGATION.value,
        due_date=date.today(),
    )
    db_session.add(task)
    await db_session.flush()

    # Create Survival Observation linked to Inspection
    obs = SurvivalObservation(
        project_id=proj.id,
        inspection_id=insp.id,
        plot_identifier="PLOT-01",
        cohort_identifier="COHORT-A",
        observation_date=date.today(),
        sample_size=100,
        alive_count=90,
        dead_count=10,
    )
    db_session.add(obs)
    await db_session.flush()

    # Delete Inspection via database statement to test PostgreSQL constraint execution
    await db_session.execute(
        text("DELETE FROM field_inspections WHERE id = :id"),
        {"id": insp.id},
    )
    await db_session.flush()

    # Verify task.inspection_id is NULL while task.project_id is preserved
    await db_session.refresh(task)
    assert task.inspection_id is None
    assert task.project_id == proj.id

    # Verify obs.inspection_id is NULL while obs.project_id is preserved
    await db_session.refresh(obs)
    assert obs.inspection_id is None
    assert obs.project_id == proj.id


@pytest.mark.asyncio
async def test_restrict_baseline_activity(db_session: AsyncSession):
    """Verify that ON DELETE RESTRICT blocks deleting baseline activities referenced by survival observations."""
    admin = User(
        email=f"admin_{uuid.uuid4().hex[:6]}@vana.org",
        hashed_password="pw",
        full_name="Admin User",
        role=UserRole.ADMIN.value,
        is_active=True,
    )
    proj = Project(
        name="Project Restrict Act",
        code=f"PRJ-R1-{uuid.uuid4().hex[:4]}",
        status=ProjectStatus.ACTIVE.value,
        latitude=12.5,
        longitude=77.5,
    )
    db_session.add_all([admin, proj])
    await db_session.flush()

    act = FieldActivity(
        project_id=proj.id,
        created_by_id=admin.id,
        metric_code="TREES_PLANTED",
        unit="TREES",
    )
    db_session.add(act)
    await db_session.flush()

    obs = SurvivalObservation(
        project_id=proj.id,
        activity_id=act.id,
        plot_identifier="PLOT-01",
        cohort_identifier="COHORT-A",
        observation_date=date.today(),
        sample_size=100,
        alive_count=90,
        dead_count=10,
    )
    db_session.add(obs)
    await db_session.flush()

    # Attempt to delete act -> FAIL due to RESTRICT on fk_survival_activity
    with pytest.raises(IntegrityError):
        await db_session.execute(
            text("DELETE FROM field_activities WHERE id = :id"),
            {"id": act.id},
        )


@pytest.mark.asyncio
async def test_restrict_inspection_with_evidence(db_session: AsyncSession):
    """Verify that ON DELETE RESTRICT blocks deleting field inspections that contain evidence files."""
    proj = Project(
        name="Project Restrict Insp",
        code=f"PRJ-R2-{uuid.uuid4().hex[:4]}",
        status=ProjectStatus.ACTIVE.value,
        latitude=12.5,
        longitude=77.5,
    )
    db_session.add(proj)
    await db_session.flush()

    insp = FieldInspection(
        project_id=proj.id,
        scheduled_date=date.today(),
        status=InspectionStatus.SCHEDULED.value,
    )
    db_session.add(insp)
    await db_session.flush()

    evidence = EvidenceFile(
        inspection_id=insp.id,
        file_storage_key="test-key-123.jpg",
        original_filename="photo.jpg",
        mime_type="image/jpeg",
        file_size_bytes=2048,
    )
    db_session.add(evidence)
    await db_session.flush()

    # Attempt to delete insp -> FAIL due to RESTRICT on fk_evidence_inspection
    with pytest.raises(IntegrityError):
        await db_session.execute(
            text("DELETE FROM field_inspections WHERE id = :id"),
            {"id": insp.id},
        )


@pytest.mark.asyncio
async def test_partial_unique_index_rejects_active_duplicate(db_session: AsyncSession):
    """Verify that partial unique index rejects two active observations for the same cohort/plot/date."""
    proj = Project(
        name="Project Cohort 1",
        code=f"PRJ-C1-{uuid.uuid4().hex[:4]}",
        status=ProjectStatus.ACTIVE.value,
        latitude=12.5,
        longitude=77.5,
    )
    db_session.add(proj)
    await db_session.flush()

    obs_date = date(2026, 11, 4)

    obs1 = SurvivalObservation(
        project_id=proj.id,
        plot_identifier="PLOT-01",
        cohort_identifier="COHORT-A",
        observation_date=obs_date,
        sample_size=200,
        alive_count=180,
        dead_count=20,
        is_active=True,
    )
    db_session.add(obs1)
    await db_session.flush()

    # Attempt second active observation for exact same 4-tuple -> FAIL
    obs2 = SurvivalObservation(
        project_id=proj.id,
        plot_identifier="PLOT-01",
        cohort_identifier="COHORT-A",
        observation_date=obs_date,
        sample_size=200,
        alive_count=175,
        dead_count=25,
        is_active=True,
    )
    db_session.add(obs2)
    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_observation_supersession_workflow(db_session: AsyncSession):
    """Verify that append-only observation correction preserves both inactive and active records."""
    proj = Project(
        name="Project Cohort 2",
        code=f"PRJ-C2-{uuid.uuid4().hex[:4]}",
        status=ProjectStatus.ACTIVE.value,
        latitude=12.5,
        longitude=77.5,
    )
    db_session.add(proj)
    await db_session.flush()

    obs_date = date(2026, 11, 4)

    obs1 = SurvivalObservation(
        project_id=proj.id,
        plot_identifier="PLOT-01",
        cohort_identifier="COHORT-A",
        observation_date=obs_date,
        sample_size=200,
        alive_count=180,
        dead_count=20,
        is_active=True,
    )
    db_session.add(obs1)
    await db_session.flush()

    # Perform supersession workflow:
    obs2_id = uuid.uuid4()
    obs1.is_active = False
    obs1.superseded_by_id = obs2_id
    obs1.correction_notes = "Recounted sample plot after resolving identification confusion"

    obs2 = SurvivalObservation(
        id=obs2_id,
        project_id=proj.id,
        plot_identifier="PLOT-01",
        cohort_identifier="COHORT-A",
        observation_date=obs_date,
        sample_size=200,
        alive_count=175,
        dead_count=25,
        is_active=True,
    )
    db_session.add(obs2)
    await db_session.flush()

    # Query both records
    res = await db_session.execute(
        select(SurvivalObservation).where(
            SurvivalObservation.project_id == proj.id,
            SurvivalObservation.plot_identifier == "PLOT-01",
            SurvivalObservation.cohort_identifier == "COHORT-A",
            SurvivalObservation.observation_date == obs_date,
        ).order_by(SurvivalObservation.is_active)
    )
    records = res.scalars().all()
    assert len(records) == 2
    inactive_rec = [r for r in records if not r.is_active][0]
    active_rec = [r for r in records if r.is_active][0]
    assert inactive_rec.superseded_by_id == active_rec.id
    assert active_rec.alive_count == 175


@pytest.mark.asyncio
async def test_survival_rate_derived_property():
    """Verify that SurvivalObservation derives survival_rate accurately without client input."""
    # Standard sample
    obs_standard = SurvivalObservation(
        plot_identifier="P1",
        cohort_identifier="C1",
        observation_date=date.today(),
        sample_size=250,
        alive_count=210,
        dead_count=30,
    )
    assert obs_standard.survival_rate == 87.50

    # Zero assessed population
    obs_zero = SurvivalObservation(
        plot_identifier="P1",
        cohort_identifier="C1",
        observation_date=date.today(),
        sample_size=50,
        alive_count=0,
        dead_count=0,
    )
    assert obs_zero.survival_rate is None

    # 100% survival
    obs_full = SurvivalObservation(
        plot_identifier="P1",
        cohort_identifier="C1",
        observation_date=date.today(),
        sample_size=100,
        alive_count=100,
        dead_count=0,
    )
    assert obs_full.survival_rate == 100.00


@pytest.mark.asyncio
async def test_evidence_target_mutual_exclusion(db_session: AsyncSession):
    """Verify that evidence_files chk_evidence_target enforces mutual exclusivity between activity/revision and inspection."""
    proj = Project(
        name="Project Evid",
        code=f"PRJ-E-{uuid.uuid4().hex[:4]}",
        status=ProjectStatus.ACTIVE.value,
        latitude=12.5,
        longitude=77.5,
    )
    admin = User(
        email=f"admin_{uuid.uuid4().hex[:6]}@vana.org",
        hashed_password="pw",
        full_name="Admin User",
        role=UserRole.ADMIN.value,
        is_active=True,
    )
    db_session.add_all([proj, admin])
    await db_session.flush()

    act = FieldActivity(
        project_id=proj.id,
        created_by_id=admin.id,
        metric_code="TREES_PLANTED",
        unit="TREES",
    )
    db_session.add(act)
    await db_session.flush()

    rev = ActivityRevision(
        activity_id=act.id,
        revision_number=1,
        quantity=Decimal("500.00"),
        activity_date=date.today(),
        status=ActivityStatus.PENDING.value,
        is_active_ledger_entry=False,
    )
    db_session.add(rev)
    await db_session.flush()

    insp = FieldInspection(
        project_id=proj.id,
        scheduled_date=date.today(),
        status=InspectionStatus.SCHEDULED.value,
    )
    db_session.add(insp)
    await db_session.flush()

    # 1. Valid activity evidence (inspection_id is NULL)
    ev_act = EvidenceFile(
        activity_id=act.id,
        revision_id=rev.id,
        inspection_id=None,
        file_storage_key="act-photo.jpg",
        original_filename="photo1.jpg",
        mime_type="image/jpeg",
        file_size_bytes=1024,
    )
    db_session.add(ev_act)
    await db_session.flush()
    assert ev_act.id is not None

    # 2. Valid inspection evidence (activity_id and revision_id are NULL)
    ev_insp = EvidenceFile(
        activity_id=None,
        revision_id=None,
        inspection_id=insp.id,
        file_storage_key="insp-photo.jpg",
        original_filename="photo2.jpg",
        mime_type="image/jpeg",
        file_size_bytes=2048,
        latitude=12.55,
        longitude=77.55,
        caption="Canopy health check",
    )
    db_session.add(ev_insp)
    await db_session.flush()
    assert ev_insp.id is not None

    # 3. Invalid evidence (both activity_id and inspection_id populated) -> FAIL
    ev_invalid = EvidenceFile(
        activity_id=act.id,
        revision_id=rev.id,
        inspection_id=insp.id,
        file_storage_key="invalid.jpg",
        original_filename="invalid.jpg",
        mime_type="image/jpeg",
        file_size_bytes=512,
    )
    db_session.add(ev_invalid)
    with pytest.raises(IntegrityError):
        await db_session.flush()
