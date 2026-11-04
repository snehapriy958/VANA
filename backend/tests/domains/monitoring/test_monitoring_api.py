"""
VANA — Phase 6.3 Monitoring API & RBAC Integration Tests
Verifies HTTP endpoint behavior, serialization, validation, multi-tenancy,
evidence upload, IDOR protection, and RBAC matrix.
"""

from datetime import date, datetime, timedelta, timezone
import io
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
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
from app.domains.operations.models import FieldActivity
from app.domains.projects.models import Project, ProjectStatus
from app.domains.teams.models import ProjectAssignment


# ============================================================================
# Test Helpers
# ============================================================================


async def create_user_with_token(
    db: AsyncSession, role: UserRole, full_name: str = "Test User"
) -> tuple[User, dict]:
    user = User(
        id=uuid.uuid4(),
        email=f"user_{uuid.uuid4().hex[:8]}@vana.org",
        hashed_password=hash_password("SecurePassword123!"),
        full_name=full_name,
        role=role.value,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    token = create_access_token(subject=str(user.id), role=user.role, email=user.email)
    return user, {"Authorization": f"Bearer {token}"}


async def create_project_helper(db: AsyncSession, name: str = "Project Green") -> Project:
    project = Project(
        id=uuid.uuid4(),
        name=name,
        code=f"PRJ-{uuid.uuid4().hex[:6].upper()}",
        status=ProjectStatus.ACTIVE.value,
        latitude=13.0827,
        longitude=80.2707,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


async def assign_user_helper(
    db: AsyncSession, user_id: uuid.UUID, project_id: uuid.UUID, role: str = "FIELD_OFFICER"
) -> ProjectAssignment:
    assignment = ProjectAssignment(
        id=uuid.uuid4(),
        project_id=project_id,
        user_id=user_id,
        assigned_role=role,
    )
    db.add(assignment)
    await db.commit()
    return assignment


async def create_activity_helper(
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
    await db.commit()
    return act


# ============================================================================
# 1. Field Inspection API Tests
# ============================================================================


@pytest.mark.asyncio
async def test_api_schedule_and_list_inspections(client: AsyncClient, db_session: AsyncSession):
    """Verifies inspection scheduling, RBAC restrictions, validation, and listing with pagination."""
    admin, admin_hdr = await create_user_with_token(db_session, UserRole.ADMIN, "Admin")
    pm, pm_hdr = await create_user_with_token(db_session, UserRole.PROJECT_MANAGER, "PM")
    officer, officer_hdr = await create_user_with_token(db_session, UserRole.FIELD_OFFICER, "Officer")
    unassigned_officer, unassigned_hdr = await create_user_with_token(db_session, UserRole.FIELD_OFFICER, "Unassigned FO")

    proj = await create_project_helper(db_session, "Kaveri Basin")
    await assign_user_helper(db_session, pm.id, proj.id, "PROJECT_MANAGER")
    await assign_user_helper(db_session, officer.id, proj.id, "FIELD_OFFICER")

    # 1. Field Officer cannot schedule -> 403 Forbidden
    payload = {
        "project_id": str(proj.id),
        "scheduled_date": str(date.today() + timedelta(days=2)),
        "inspection_type": "ROUTINE",
        "assigned_to_id": str(officer.id),
    }
    resp = await client.post("/api/v1/monitoring/inspections", json=payload, headers=officer_hdr)
    assert resp.status_code == 403

    # 2. Assigning an unassigned inspector -> 400 Bad Request
    bad_inspector_payload = {
        **payload,
        "assigned_to_id": str(unassigned_officer.id),
    }
    resp = await client.post("/api/v1/monitoring/inspections", json=bad_inspector_payload, headers=pm_hdr)
    assert resp.status_code == 400
    assert "INSPECTOR_NOT_ASSIGNED_TO_PROJECT" in resp.text

    # 3. PM schedules successfully -> 201 Created
    resp = await client.post("/api/v1/monitoring/inspections", json=payload, headers=pm_hdr)
    assert resp.status_code == 201
    insp_data = resp.json()
    assert insp_data["status"] == "SCHEDULED"
    assert insp_data["project_id"] == str(proj.id)
    assert insp_data["assigned_to_id"] == str(officer.id)
    insp_id = insp_data["id"]

    # 4. Get inspection details -> 200 OK
    resp_get = await client.get(f"/api/v1/monitoring/inspections/{insp_id}", headers=officer_hdr)
    assert resp_get.status_code == 200
    assert resp_get.json()["id"] == insp_id

    # 5. List inspections with pagination & filters -> 200 OK
    resp_list = await client.get(
        f"/api/v1/monitoring/inspections?project_id={proj.id}&status=SCHEDULED&limit=10",
        headers=pm_hdr,
    )
    assert resp_list.status_code == 200
    items = resp_list.json()
    assert len(items) == 1
    assert items[0]["id"] == insp_id


@pytest.mark.asyncio
async def test_api_inspection_lifecycle_ownership_and_addenda(
    client: AsyncClient, db_session: AsyncSession
):
    """
    Verifies full lifecycle endpoints:
    POST /inspections/{id}/start
    POST /inspections/{id}/complete
    POST /inspections/{id}/addendum
    POST /inspections/{id}/cancel
    Field Officer ownership protection.
    """
    admin, admin_hdr = await create_user_with_token(db_session, UserRole.ADMIN, "Admin")
    pm, pm_hdr = await create_user_with_token(db_session, UserRole.PROJECT_MANAGER, "PM")
    officer_1, officer_1_hdr = await create_user_with_token(db_session, UserRole.FIELD_OFFICER, "Officer 1")
    officer_2, officer_2_hdr = await create_user_with_token(db_session, UserRole.FIELD_OFFICER, "Officer 2")

    proj = await create_project_helper(db_session)
    await assign_user_helper(db_session, pm.id, proj.id, "PROJECT_MANAGER")
    await assign_user_helper(db_session, officer_1.id, proj.id, "FIELD_OFFICER")
    await assign_user_helper(db_session, officer_2.id, proj.id, "FIELD_OFFICER")

    # Schedule inspection for Officer 1
    sched_resp = await client.post(
        "/api/v1/monitoring/inspections",
        json={
            "project_id": str(proj.id),
            "scheduled_date": str(date.today()),
            "assigned_to_id": str(officer_1.id),
        },
        headers=pm_hdr,
    )
    insp_id = sched_resp.json()["id"]

    # 1. Officer 2 attempts to start Officer 1's inspection -> 403 Forbidden
    resp = await client.post(f"/api/v1/monitoring/inspections/{insp_id}/start", headers=officer_2_hdr)
    assert resp.status_code == 403
    assert "INSPECTOR_OWNERSHIP_REQUIRED" in resp.text

    # 2. Officer 1 starts inspection -> 200 OK
    resp = await client.post(f"/api/v1/monitoring/inspections/{insp_id}/start", json={"notes": "Starting patrol"}, headers=officer_1_hdr)
    assert resp.status_code == 200
    assert resp.json()["status"] == "IN_PROGRESS"

    # 3. Officer 2 attempts to complete Officer 1's inspection -> 403
    complete_body = {
        "findings": "Canopy thriving, healthy sapling root growth.",
        "vegetation_health_score": 5,
        "canopy_condition": "EXCELLENT",
        "soil_moisture_condition": "ADEQUATE",
        "threats_detected": [],
    }
    resp = await client.post(f"/api/v1/monitoring/inspections/{insp_id}/complete", json=complete_body, headers=officer_2_hdr)
    assert resp.status_code == 403

    # 4. Officer 1 completes inspection -> 200 OK
    resp = await client.post(f"/api/v1/monitoring/inspections/{insp_id}/complete", json=complete_body, headers=officer_1_hdr)
    assert resp.status_code == 200
    completed_data = resp.json()
    assert completed_data["status"] == "COMPLETED"
    assert completed_data["completed_at"] is not None

    # 5. Direct edit / re-completion locked -> 400 Bad Request
    resp = await client.post(f"/api/v1/monitoring/inspections/{insp_id}/complete", json=complete_body, headers=officer_1_hdr)
    assert resp.status_code == 400
    assert "COMPLETED_INSPECTION_LOCKED" in resp.text

    # 6. Cannot cancel completed inspection -> 400
    resp = await client.post(
        f"/api/v1/monitoring/inspections/{insp_id}/cancel",
        json={"cancellation_reason": "Too late"},
        headers=pm_hdr,
    )
    assert resp.status_code == 400

    # 7. Field officer cannot add addendum -> 403
    addendum_body = {"content": "Correction: minor termite activity observed on outer perimeter."}
    resp = await client.post(f"/api/v1/monitoring/inspections/{insp_id}/addendum", json=addendum_body, headers=officer_1_hdr)
    assert resp.status_code == 403

    # 8. PM records addendum -> 200 OK
    resp = await client.post(f"/api/v1/monitoring/inspections/{insp_id}/addendum", json=addendum_body, headers=pm_hdr)
    assert resp.status_code == 200
    updated_data = resp.json()
    assert len(updated_data["addenda"]) == 1
    assert "termite activity" in updated_data["addenda"][0]["content"]


@pytest.mark.asyncio
async def test_api_inspection_evidence_upload_and_access(
    client: AsyncClient, db_session: AsyncSession
):
    """Verifies photo evidence upload via POST /inspections/{id}/evidence and authorized streaming."""
    pm, pm_hdr = await create_user_with_token(db_session, UserRole.PROJECT_MANAGER, "PM")
    officer, officer_hdr = await create_user_with_token(db_session, UserRole.FIELD_OFFICER, "Officer")
    proj = await create_project_helper(db_session)
    await assign_user_helper(db_session, pm.id, proj.id, "PROJECT_MANAGER")
    await assign_user_helper(db_session, officer.id, proj.id, "FIELD_OFFICER")

    sched_resp = await client.post(
        "/api/v1/monitoring/inspections",
        json={"project_id": str(proj.id), "scheduled_date": str(date.today()), "assigned_to_id": str(officer.id)},
        headers=pm_hdr,
    )
    insp_id = sched_resp.json()["id"]

    # Upload photo evidence as assigned officer
    fake_img = io.BytesIO(b"\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xFF\xDB\x00C\x00")
    files = {"file": ("inspection_photo.jpg", fake_img, "image/jpeg")}
    data = {"latitude": "12.9716", "longitude": "77.5946", "caption": "East sector saplings"}

    resp = await client.post(
        f"/api/v1/monitoring/inspections/{insp_id}/evidence",
        files=files,
        data=data,
        headers=officer_hdr,
    )
    assert resp.status_code == 201
    evidence_data = resp.json()
    assert evidence_data["inspection_id"] == insp_id
    assert evidence_data["original_filename"] == "inspection_photo.jpg"
    assert evidence_data["mime_type"] == "image/jpeg"
    assert evidence_data["download_url"].startswith("/api/v1/operations/evidence/")
    download_url = evidence_data["download_url"]

    # Stream evidence file back via authorized endpoint
    stream_resp = await client.get(download_url, headers=officer_hdr)
    assert stream_resp.status_code == 200
    assert stream_resp.headers["content-type"] == "image/jpeg"


# ============================================================================
# 2. Maintenance Task API Tests
# ============================================================================


@pytest.mark.asyncio
async def test_api_maintenance_task_lifecycle_and_reopen(
    client: AsyncClient, db_session: AsyncSession
):
    """
    Verifies:
    POST /tasks
    GET /tasks
    POST /tasks/{id}/start
    POST /tasks/{id}/complete
    POST /tasks/{id}/cancel
    POST /tasks/{id}/reopen
    """
    admin, admin_hdr = await create_user_with_token(db_session, UserRole.ADMIN, "Admin")
    pm, pm_hdr = await create_user_with_token(db_session, UserRole.PROJECT_MANAGER, "PM")
    officer_1, officer_1_hdr = await create_user_with_token(db_session, UserRole.FIELD_OFFICER, "Officer 1")
    officer_2, officer_2_hdr = await create_user_with_token(db_session, UserRole.FIELD_OFFICER, "Officer 2")

    proj = await create_project_helper(db_session)
    await assign_user_helper(db_session, pm.id, proj.id, "PROJECT_MANAGER")
    await assign_user_helper(db_session, officer_1.id, proj.id, "FIELD_OFFICER")
    await assign_user_helper(db_session, officer_2.id, proj.id, "FIELD_OFFICER")

    # 1. Field officer cannot create task -> 403
    task_payload = {
        "project_id": str(proj.id),
        "title": "Clear invasive Lantana weeds",
        "description": "Sector B undergrowth clearance",
        "category": "WEEDING",
        "priority": "HIGH",
        "due_date": str(date.today() + timedelta(days=3)),
        "assigned_to_id": str(officer_1.id),
    }
    resp = await client.post("/api/v1/monitoring/tasks", json=task_payload, headers=officer_1_hdr)
    assert resp.status_code == 403

    # 2. PM creates task -> 201 Created
    resp = await client.post("/api/v1/monitoring/tasks", json=task_payload, headers=pm_hdr)
    assert resp.status_code == 201
    task_id = resp.json()["id"]

    # 3. Officer 2 attempts to start Officer 1's task -> 403
    resp = await client.post(f"/api/v1/monitoring/tasks/{task_id}/start", headers=officer_2_hdr)
    assert resp.status_code == 403

    # 4. Officer 1 starts task -> 200 OK
    resp = await client.post(f"/api/v1/monitoring/tasks/{task_id}/start", headers=officer_1_hdr)
    assert resp.status_code == 200
    assert resp.json()["status"] == "IN_PROGRESS"

    # 5. Officer 1 completes task with notes -> 200 OK
    complete_resp = await client.post(
        f"/api/v1/monitoring/tasks/{task_id}/complete",
        json={"completion_notes": "Weeds cleared across 2 hectares."},
        headers=officer_1_hdr,
    )
    assert complete_resp.status_code == 200
    assert complete_resp.json()["status"] == "COMPLETED"

    # 6. Field officer cannot reopen task -> 403
    resp = await client.post(
        f"/api/v1/monitoring/tasks/{task_id}/reopen",
        json={"justification": "Needs further weeding"},
        headers=officer_1_hdr,
    )
    assert resp.status_code == 403

    # 7. PM reopens task with justification -> 200 OK
    reopen_resp = await client.post(
        f"/api/v1/monitoring/tasks/{task_id}/reopen",
        json={"justification": "Roots remained in quadrant 4"},
        headers=pm_hdr,
    )
    assert reopen_resp.status_code == 200
    assert reopen_resp.json()["status"] == "TODO"

    # 8. List tasks with filters
    list_resp = await client.get(
        f"/api/v1/monitoring/tasks?project_id={proj.id}&priority=HIGH",
        headers=pm_hdr,
    )
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1


# ============================================================================
# 3. Survival Observation API Tests
# ============================================================================


@pytest.mark.asyncio
async def test_api_survival_observation_creation_and_supersession(
    client: AsyncClient, db_session: AsyncSession
):
    """
    Verifies:
    POST /survival-observations
    GET /survival-observations
    GET /survival-observations/{id}
    POST /survival-observations/{id}/correct (atomic supersession)
    GET /survival-analytics
    """
    admin, admin_hdr = await create_user_with_token(db_session, UserRole.ADMIN, "Admin")
    pm, pm_hdr = await create_user_with_token(db_session, UserRole.PROJECT_MANAGER, "PM")
    officer, officer_hdr = await create_user_with_token(db_session, UserRole.FIELD_OFFICER, "Officer")

    proj = await create_project_helper(db_session)
    await assign_user_helper(db_session, pm.id, proj.id, "PROJECT_MANAGER")
    await assign_user_helper(db_session, officer.id, proj.id, "FIELD_OFFICER")

    # 1. Record survival observation (alive=75, dead=25 out of 100) -> 201 Created
    # Client passes survival_rate=999.0 to verify server ignores it!
    obs_payload = {
        "project_id": str(proj.id),
        "plot_identifier": "PLOT-API-1",
        "cohort_identifier": "COHORT-2025-A",
        "methodology": "SAMPLE_PLOT",
        "observation_date": str(date.today()),
        "sample_size": 100,
        "alive_count": 75,
        "dead_count": 25,
        "survival_rate": 999.0,  # Should be rejected / ignored
    }
    resp = await client.post("/api/v1/monitoring/survival-observations", json=obs_payload, headers=officer_hdr)
    assert resp.status_code == 201
    obs_data = resp.json()
    assert obs_data["survival_rate"] == 75.0  # Derived server-side! 75 / (75 + 25) * 100
    assert obs_data["unassessed_count"] == 0
    obs_id = obs_data["id"]

    # 2. Duplicate active observation on same date -> 409 Conflict
    resp_dup = await client.post("/api/v1/monitoring/survival-observations", json=obs_payload, headers=officer_hdr)
    assert resp_dup.status_code == 409
    assert "ACTIVE_OBSERVATION_ALREADY_EXISTS" in resp_dup.text

    # 3. Field Officer cannot execute correction supersession -> 403
    correct_payload = {
        "sample_size": 100,
        "alive_count": 85,
        "dead_count": 15,
        "correction_notes": "Miscounted 10 saplings in shaded row 3",
    }
    resp_cor_fo = await client.post(
        f"/api/v1/monitoring/survival-observations/{obs_id}/correct",
        json=correct_payload,
        headers=officer_hdr,
    )
    assert resp_cor_fo.status_code == 403

    # 4. PM executes correction supersession -> 200 OK
    resp_cor = await client.post(
        f"/api/v1/monitoring/survival-observations/{obs_id}/correct",
        json=correct_payload,
        headers=pm_hdr,
    )
    assert resp_cor.status_code == 200
    replacement_data = resp_cor.json()
    assert replacement_data["id"] != obs_id
    assert replacement_data["survival_rate"] == 85.0
    assert replacement_data["is_active"] is True

    # 5. Get original observation -> is_active = False, superseded_by_id linked
    resp_orig = await client.get(f"/api/v1/monitoring/survival-observations/{obs_id}", headers=pm_hdr)
    assert resp_orig.status_code == 200
    orig_data = resp_orig.json()
    assert orig_data["is_active"] is False
    assert orig_data["superseded_by_id"] == replacement_data["id"]

    # 6. Survival analytics trajectory -> returns single active observation with 85% rate
    traj_resp = await client.get(
        f"/api/v1/monitoring/survival-analytics?project_id={proj.id}&plot_identifier=PLOT-API-1&cohort_identifier=COHORT-2025-A",
        headers=officer_hdr,
    )
    assert traj_resp.status_code == 200
    traj = traj_resp.json()
    assert len(traj) == 1
    assert traj[0]["survival_rate"] == 85.0


# ============================================================================
# 4. Alerts & Dashboard API Tests
# ============================================================================


@pytest.mark.asyncio
async def test_api_alerts_and_dashboard_endpoints(client: AsyncClient, db_session: AsyncSession):
    """Verifies GET /alerts and GET /dashboard endpoints."""
    admin, admin_hdr = await create_user_with_token(db_session, UserRole.ADMIN, "Admin")
    pm, pm_hdr = await create_user_with_token(db_session, UserRole.PROJECT_MANAGER, "PM")
    unassigned_user, unassigned_hdr = await create_user_with_token(db_session, UserRole.PROJECT_MANAGER, "Unassigned")
    proj = await create_project_helper(db_session)
    await assign_user_helper(db_session, pm.id, proj.id, "PROJECT_MANAGER")

    # Schedule an overdue inspection and an overdue task
    insp = FieldInspection(
        id=uuid.uuid4(),
        project_id=proj.id,
        scheduled_date=date.today() - timedelta(days=2),
        status=InspectionStatus.SCHEDULED.value,
        inspection_type=InspectionType.ROUTINE.value,
    )
    task = MaintenanceTask(
        id=uuid.uuid4(),
        project_id=proj.id,
        title="Check fence boundary",
        category=TaskCategory.FENCING_REPAIR.value,
        priority=TaskPriority.HIGH.value,
        status=TaskStatus.TODO.value,
        due_date=date.today() - timedelta(days=1),
    )
    db_session.add_all([insp, task])
    await db_session.commit()

    # 1. Unassigned user querying specific project -> 403 Forbidden
    resp_unassigned = await client.get(f"/api/v1/monitoring/alerts?project_id={proj.id}", headers=unassigned_hdr)
    assert resp_unassigned.status_code == 403

    # 2. PM querying alerts -> 200 OK
    resp_alerts = await client.get(f"/api/v1/monitoring/alerts?project_id={proj.id}", headers=pm_hdr)
    assert resp_alerts.status_code == 200
    alert_data = resp_alerts.json()
    assert alert_data["total_alerts"] >= 2
    assert alert_data["high_count"] >= 2

    # 3. PM querying dashboard -> 200 OK
    resp_dash = await client.get(f"/api/v1/monitoring/dashboard?project_id={proj.id}", headers=pm_hdr)
    assert resp_dash.status_code == 200
    dash_data = resp_dash.json()
    assert dash_data["total_inspections"] >= 1
    assert dash_data["scheduled_inspections"] >= 1
    assert dash_data["total_tasks"] >= 1
    assert dash_data["overdue_tasks"] >= 1
    assert dash_data["total_alerts"] >= 2
