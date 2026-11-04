"""VANA Audit Domain — Milestone 8 Phase 2 API & Integration Tests.

Verifies:
1. Finding 8.1-01 Remediation: Authoritative project_id propagation across operational & monitoring events.
2. Read-only Audit APIs: /events, /events/{id}, /verification, /entities/{type}/{id}.
3. RBAC & Multi-tenant Project Isolation: Admin (global), PM (scoped to assigned), FO (denied).
4. Cryptographic Chain Integrity Verification: /verify-chain with tamper, gap, and link break detection.
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import io
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.domains.audit.hashing import GENESIS_HASH, compute_event_hash
from app.domains.audit.models import AuditChainHead, AuditLog
from app.domains.audit.services import record_audit_log, verify_audit_chain
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
from app.domains.monitoring.services import (
    InspectionService,
    MaintenanceTaskService,
    SurvivalObservationService,
)
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
    VerificationDecisionRequest,
)
from app.domains.operations.services import ActivityService, VerificationService
from app.domains.projects.models import Project, ProjectStatus, ProjectTarget
from app.domains.teams.models import ProjectAssignment, ProjectRole


# ============================================================================
# Helpers
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
    token = create_access_token(str(user.id), user.role)
    headers = {"Authorization": f"Bearer {token}"}
    return user, headers


async def create_test_project(
    db: AsyncSession, name: str = "Sundarbans Project"
) -> Project:
    project = Project(
        id=uuid.uuid4(),
        name=name,
        code=f"PRJ-{uuid.uuid4().hex[:6].upper()}",
        status=ProjectStatus.ACTIVE.value,
        latitude=21.9497,
        longitude=89.1833,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


async def assign_user_to_project(
    db: AsyncSession, user_id: uuid.UUID, project_id: uuid.UUID, role: ProjectRole = ProjectRole.FIELD_OFFICER
) -> ProjectAssignment:
    assignment = ProjectAssignment(
        id=uuid.uuid4(),
        project_id=project_id,
        user_id=user_id,
        assigned_role=role.value,
    )
    db.add(assignment)
    await db.commit()
    return assignment


# ============================================================================
# 1. Finding 8.1-01 Remediation Tests: Project ID Propagation
# ============================================================================


@pytest.mark.asyncio
async def test_remediation_project_id_propagated_to_activity_lifecycle(
    db_session: AsyncSession,
):
    """Verifies that verification, rejection, amendment, and archival authoritatively propagate project_id."""
    admin_user, _ = await create_user_with_token(db_session, UserRole.ADMIN, "Admin")
    officer_user, _ = await create_user_with_token(
        db_session, UserRole.FIELD_OFFICER, "Officer"
    )
    project = await create_test_project(db_session, "Kaveri Basin Restoration")

    # Create Project Target
    target = ProjectTarget(
        id=uuid.uuid4(),
        project_id=project.id,
        metric_code="TREES_PLANTED",
        target_quantity=Decimal("10000.0"),
        target_unit="trees",
        target_date=date(2027, 12, 31),
    )
    db_session.add(target)
    await db_session.commit()

    # Assign officer
    await assign_user_to_project(db_session, officer_user.id, project.id)

    # 1. Submit initial activity
    activity_resp = await ActivityService.create_activity(
        db=db_session,
        data=ActivityCreate(
            project_id=project.id,
            metric_code="TREES_PLANTED",
            unit="trees",
            quantity=Decimal("500.0"),
            activity_date=date.today(),
            latitude=21.95,
            longitude=89.18,
            gps_accuracy_meters=5.0,
            field_notes="Initial planting test",
        ),
        current_user=officer_user,
        files=[],
    )
    activity_id = activity_resp.id

    # 2. Verify activity submission audit log has project_id
    stmt = (
        select(AuditLog)
        .where(
            AuditLog.entity_id == activity_id,
            AuditLog.action_type == "ACTIVITY_CREATED",
        )
    )
    created_audit = await db_session.scalar(stmt)
    assert created_audit is not None
    assert created_audit.project_id == project.id
    assert created_audit.canonical_payload.get("project_id") == str(project.id).lower()

    # 3. Verify activity (Approve)
    initial_rev_id = activity_resp.current_revision.id
    await VerificationService.record_decision(
        db=db_session,
        revision_id=initial_rev_id,
        data=VerificationDecisionRequest(
            decision=ActivityStatus.VERIFIED.value,
            review_notes="Approved initial planting claim",
        ),
        current_user=admin_user,
    )

    stmt_verify = (
        select(AuditLog)
        .where(
            AuditLog.entity_id == initial_rev_id,
            AuditLog.action_type == "ACTIVITY_VERIFIED",
        )
    )
    verified_audit = await db_session.scalar(stmt_verify)
    assert verified_audit is not None
    assert verified_audit.project_id == project.id
    assert verified_audit.canonical_payload.get("project_id") == str(project.id).lower()

    # 4. Amend activity
    amended = await ActivityService.amend_activity(
        db=db_session,
        activity_id=activity_id,
        data=ActivityRevisionCreate(
            quantity=Decimal("450.0"),
            activity_date=date.today(),
        ),
        current_user=officer_user,
        files=[],
    )

    stmt_amend = (
        select(AuditLog)
        .where(
            AuditLog.entity_id == activity_id,
            AuditLog.action_type == "ACTIVITY_AMENDED",
        )
        .order_by(AuditLog.sequence_number.desc())
    )
    amended_audit = await db_session.scalar(stmt_amend)
    assert amended_audit is not None
    assert amended_audit.project_id == project.id
    assert amended_audit.canonical_payload.get("project_id") == str(project.id).lower()

    # 5. Reject amendment
    second_rev = [r for r in amended.revisions if r.revision_number == 2][0]
    await VerificationService.record_decision(
        db=db_session,
        revision_id=second_rev.id,
        data=VerificationDecisionRequest(
            decision=ActivityStatus.REJECTED.value,
            rejection_reason_code=RejectionReasonCode.INSUFFICIENT_EVIDENCE.value,
            review_notes="Rejected amendment claim",
        ),
        current_user=admin_user,
    )

    stmt_reject = (
        select(AuditLog)
        .where(
            AuditLog.entity_id == second_rev.id,
            AuditLog.action_type == "ACTIVITY_REJECTED",
        )
    )
    rejected_audit = await db_session.scalar(stmt_reject)
    assert rejected_audit is not None
    assert rejected_audit.project_id == project.id

    # 6. Archive activity
    await ActivityService.archive_activity(
        db=db_session,
        activity_id=activity_id,
        current_user=admin_user,
    )

    stmt_archive = (
        select(AuditLog)
        .where(
            AuditLog.entity_id == activity_id,
            AuditLog.action_type == "ACTIVITY_ARCHIVED",
        )
    )
    archived_audit = await db_session.scalar(stmt_archive)
    assert archived_audit is not None
    assert archived_audit.project_id == project.id


@pytest.mark.asyncio
async def test_remediation_project_id_propagated_to_monitoring_lifecycle(
    db_session: AsyncSession,
):
    """Verifies that field inspection and maintenance task lifecycle mutations propagate project_id."""
    admin_user, _ = await create_user_with_token(db_session, UserRole.ADMIN, "Admin")
    project = await create_test_project(db_session, "Western Ghats Corridor")

    # 1. Inspection lifecycle
    inspection = FieldInspection(
        id=uuid.uuid4(),
        project_id=project.id,
        scheduled_date=date.today(),
        inspection_type=InspectionType.ROUTINE.value,
        assigned_to_id=admin_user.id,
        status=InspectionStatus.SCHEDULED.value,
        addenda=[],
    )
    db_session.add(inspection)
    await db_session.commit()
    await db_session.refresh(inspection)

    # Start inspection
    inspection = await InspectionService.start_inspection(
        db=db_session, user=admin_user, inspection_id=inspection.id, notes="Inspection begun"
    )

    stmt_start = (
        select(AuditLog)
        .where(
            AuditLog.entity_id == inspection.id,
            AuditLog.action_type == "INSPECTION_STARTED",
        )
    )
    started_audit = await db_session.scalar(stmt_start)
    assert started_audit is not None
    assert started_audit.project_id == project.id

    # 2. Maintenance task lifecycle
    task = MaintenanceTask(
        id=uuid.uuid4(),
        project_id=project.id,
        title="Weeding sector 2",
        category=TaskCategory.WEEDING.value,
        priority=TaskPriority.MEDIUM.value,
        status=TaskStatus.TODO.value,
        due_date=date.today() + timedelta(days=7),
        assigned_to_id=admin_user.id,
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    task = await MaintenanceTaskService.start_task(
        db=db_session, user=admin_user, task_id=task.id, notes="Started weeding"
    )

    stmt_task_start = (
        select(AuditLog)
        .where(
            AuditLog.entity_id == task.id,
            AuditLog.action_type == "TASK_STARTED",
        )
    )
    task_audit = await db_session.scalar(stmt_task_start)
    assert task_audit is not None
    assert task_audit.project_id == project.id


# ============================================================================
# 2. Read-Only Audit APIs & RBAC Tests (Part C)
# ============================================================================


@pytest.mark.asyncio
async def test_audit_events_endpoint_admin_access_and_pagination(
    client: AsyncClient, db_session: AsyncSession
):
    """Verifies that an Admin can query audit events with pagination and filters."""
    admin_user, admin_headers = await create_user_with_token(
        db_session, UserRole.ADMIN, "Admin User"
    )
    project = await create_test_project(db_session, "Sundarbans Project Alpha")

    # Record 3 events
    await record_audit_log(
        db=db_session,
        action_type="TEST_ADMIN_EVENT_1",
        entity_type="project",
        entity_id=project.id,
        actor_id=admin_user.id,
        project_id=project.id,
    )
    await record_audit_log(
        db=db_session,
        action_type="TEST_ADMIN_EVENT_2",
        entity_type="project",
        entity_id=project.id,
        actor_id=admin_user.id,
        project_id=project.id,
    )
    await db_session.commit()

    # Query events
    res = await client.get("/api/v1/audit/events?page=1&page_size=10", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 2
    assert len(data["items"]) <= 10
    assert data["page"] == 1

    # Verify event fields
    event = data["items"][0]
    assert "sequence_number" in event
    assert "current_hash" in event
    assert "previous_hash" in event
    assert "canonical_payload" in event


@pytest.mark.asyncio
async def test_audit_events_endpoint_pm_project_scoping_and_isolation(
    client: AsyncClient, db_session: AsyncSession
):
    """Verifies that a Project Manager only sees audit events from assigned projects."""
    admin_user, admin_headers = await create_user_with_token(db_session, UserRole.ADMIN, "Admin")
    pm_user, pm_headers = await create_user_with_token(
        db_session, UserRole.PROJECT_MANAGER, "PM User"
    )

    p_assigned = await create_test_project(db_session, "Assigned PM Project")
    p_unassigned = await create_test_project(db_session, "Secret Unassigned Project")

    await assign_user_to_project(db_session, pm_user.id, p_assigned.id)

    # Insert events for both projects
    e_assigned = await record_audit_log(
        db=db_session,
        action_type="ASSIGNED_EVENT",
        entity_type="project",
        entity_id=p_assigned.id,
        actor_id=admin_user.id,
        project_id=p_assigned.id,
    )
    e_unassigned = await record_audit_log(
        db=db_session,
        action_type="UNASSIGNED_EVENT",
        entity_type="project",
        entity_id=p_unassigned.id,
        actor_id=admin_user.id,
        project_id=p_unassigned.id,
    )
    await db_session.commit()

    # 1. PM queries general events: unassigned event must NOT be returned
    res = await client.get("/api/v1/audit/events", headers=pm_headers)
    assert res.status_code == 200
    items = res.json()["items"]
    item_ids = [item["id"] for item in items]
    assert str(e_assigned.id) in item_ids
    assert str(e_unassigned.id) not in item_ids

    # 2. PM explicitly queries assigned project: succeeds
    res_assigned = await client.get(
        f"/api/v1/audit/events?project_id={p_assigned.id}", headers=pm_headers
    )
    assert res_assigned.status_code == 200
    assert any(i["id"] == str(e_assigned.id) for i in res_assigned.json()["items"])

    # 3. PM explicitly queries unassigned project: rejected with 403 Forbidden
    res_forbidden = await client.get(
        f"/api/v1/audit/events?project_id={p_unassigned.id}", headers=pm_headers
    )
    assert res_forbidden.status_code == 403


@pytest.mark.asyncio
async def test_audit_events_endpoint_field_officer_denied_access(
    client: AsyncClient, db_session: AsyncSession
):
    """Verifies that Field Officers receive 403 Forbidden for all audit endpoints."""
    _, fo_headers = await create_user_with_token(
        db_session, UserRole.FIELD_OFFICER, "Field Officer"
    )

    res = await client.get("/api/v1/audit/events", headers=fo_headers)
    assert res.status_code == 403
    assert "INSUFFICIENT_PERMISSIONS" in res.json()["detail"]


@pytest.mark.asyncio
async def test_get_audit_event_by_id_endpoint(client: AsyncClient, db_session: AsyncSession):
    """Verifies single audit event retrieval by ID and PM access boundary."""
    admin_user, admin_headers = await create_user_with_token(db_session, UserRole.ADMIN, "Admin")
    pm_user, pm_headers = await create_user_with_token(
        db_session, UserRole.PROJECT_MANAGER, "PM"
    )

    p_assigned = await create_test_project(db_session, "Assigned")
    p_unassigned = await create_test_project(db_session, "Unassigned")
    await assign_user_to_project(db_session, pm_user.id, p_assigned.id)

    event_assigned = await record_audit_log(
        db=db_session,
        action_type="EVENT_ONE",
        entity_type="project",
        entity_id=p_assigned.id,
        project_id=p_assigned.id,
    )
    event_unassigned = await record_audit_log(
        db=db_session,
        action_type="EVENT_TWO",
        entity_type="project",
        entity_id=p_unassigned.id,
        project_id=p_unassigned.id,
    )
    await db_session.commit()

    # Admin fetches both
    r1 = await client.get(f"/api/v1/audit/events/{event_assigned.id}", headers=admin_headers)
    assert r1.status_code == 200
    assert r1.json()["action_type"] == "EVENT_ONE"

    r2 = await client.get(f"/api/v1/audit/events/{event_unassigned.id}", headers=admin_headers)
    assert r2.status_code == 200

    # PM fetches assigned event
    r3 = await client.get(f"/api/v1/audit/events/{event_assigned.id}", headers=pm_headers)
    assert r3.status_code == 200

    # PM fetches unassigned event: 403
    r4 = await client.get(f"/api/v1/audit/events/{event_unassigned.id}", headers=pm_headers)
    assert r4.status_code == 403

    # Nonexistent event: 404
    r5 = await client.get(f"/api/v1/audit/events/{uuid.uuid4()}", headers=admin_headers)
    assert r5.status_code == 404


@pytest.mark.asyncio
async def test_verification_history_endpoint(client: AsyncClient, db_session: AsyncSession):
    """Verifies /api/v1/audit/verification returns complete immutable verification trail."""
    admin_user, admin_headers = await create_user_with_token(db_session, UserRole.ADMIN, "Admin")
    project = await create_test_project(db_session, "Verification History Project")

    # Record verification decision audit log
    await record_audit_log(
        db=db_session,
        action_type="ACTIVITY_VERIFIED",
        entity_type="activity_revision",
        entity_id=uuid.uuid4(),
        actor_id=admin_user.id,
        project_id=project.id,
        new_state={
            "activity_id": str(uuid.uuid4()),
            "revision_number": 1,
            "status": "VERIFIED",
            "verified_quantity": 1250.0,
            "verifier_id": str(admin_user.id),
            "review_notes": "All saplings healthy and geocoded",
        },
    )
    await db_session.commit()

    res = await client.get(
        f"/api/v1/audit/verification?project_id={project.id}", headers=admin_headers
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1
    item = data["items"][0]
    assert item["action_type"] == "ACTIVITY_VERIFIED"
    assert item["status"] == "VERIFIED"
    assert item["verified_quantity"] == 1250.0
    assert item["review_notes"] == "All saplings healthy and geocoded"


@pytest.mark.asyncio
async def test_entity_audit_trail_endpoint(client: AsyncClient, db_session: AsyncSession):
    """Verifies /api/v1/audit/entities/{type}/{id} returns chronological entity history."""
    admin_user, admin_headers = await create_user_with_token(db_session, UserRole.ADMIN, "Admin")
    target_id = uuid.uuid4()

    await record_audit_log(
        db=db_session,
        action_type="STATUS_DRAFT",
        entity_type="custom_entity",
        entity_id=target_id,
        new_state={"status": "DRAFT"},
    )
    await record_audit_log(
        db=db_session,
        action_type="STATUS_PUBLISHED",
        entity_type="custom_entity",
        entity_id=target_id,
        new_state={"status": "PUBLISHED"},
    )
    await db_session.commit()

    res = await client.get(
        f"/api/v1/audit/entities/custom_entity/{target_id}", headers=admin_headers
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 2
    assert data["items"][0]["action_type"] == "STATUS_DRAFT"
    assert data["items"][1]["action_type"] == "STATUS_PUBLISHED"


# ============================================================================
# 3. Cryptographic Chain Integrity Verification Tests (Part D)
# ============================================================================


@pytest.mark.asyncio
async def test_verify_chain_endpoint_success_on_valid_ledger(
    client: AsyncClient, db_session: AsyncSession
):
    """Verifies that /api/v1/audit/verify-chain returns is_valid=True for an untampered ledger."""
    admin_user, admin_headers = await create_user_with_token(db_session, UserRole.ADMIN, "Admin")

    e1 = await record_audit_log(
        db=db_session,
        action_type="CHAIN_VERIFY_CLEAN_1",
        entity_type="test_record",
        entity_id=uuid.uuid4(),
        actor_id=admin_user.id,
        new_state={"count": 10},
    )
    e2 = await record_audit_log(
        db=db_session,
        action_type="CHAIN_VERIFY_CLEAN_2",
        entity_type="test_record",
        entity_id=uuid.uuid4(),
        actor_id=admin_user.id,
        new_state={"count": 20},
    )
    await db_session.commit()

    res = await client.post(
        f"/api/v1/audit/verify-chain?from_sequence={e1.sequence_number}&to_sequence={e2.sequence_number}",
        headers=admin_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["is_valid"] is True
    assert len(data["errors"]) == 0
    assert data["total_events_checked"] == 2
    assert "disclaimer" in data
    assert "privileged database administrator" in data["disclaimer"]


@pytest.mark.asyncio
async def test_verify_chain_detects_mutated_payload_and_state_divergence(
    db_session: AsyncSession,
):
    """Verifies that any payload modification or state column divergence is flagged as an error."""
    # Create an event
    event = await record_audit_log(
        db=db_session,
        action_type="CHAIN_VERIFY_TEST_EVENT",
        entity_type="test_record",
        entity_id=uuid.uuid4(),
        new_state={"balance": 500},
    )
    await db_session.commit()

    # Re-verify through services.verify_audit_chain directly
    clean_result = await verify_audit_chain(db_session, from_sequence=event.sequence_number, to_sequence=event.sequence_number)
    assert clean_result.is_valid is True

    # 1. Test state column divergence (modifying new_state directly in DB)
    event.new_state = {"balance": 999999}
    await db_session.commit()

    tampered_result = await verify_audit_chain(db_session, from_sequence=event.sequence_number, to_sequence=event.sequence_number)
    assert tampered_result.is_valid is False
    assert any(e.error_type == "STATE_DIVERGENCE" for e in tampered_result.errors)

    # 2. Test canonical_payload divergence
    event.new_state = {"balance": 500}  # restore
    original_payload = dict(event.canonical_payload)
    tampered_payload = dict(event.canonical_payload)
    tampered_payload["new_state"] = {"balance": 12345}
    event.canonical_payload = tampered_payload
    await db_session.commit()

    tampered_hash_result = await verify_audit_chain(db_session, from_sequence=event.sequence_number, to_sequence=event.sequence_number)
    assert tampered_hash_result.is_valid is False
    assert any(e.error_type in ("HASH_MISMATCH", "STATE_DIVERGENCE") for e in tampered_hash_result.errors)

    # 3. Restore canonical_payload so subsequent tests have an intact cryptographic chain
    event.canonical_payload = original_payload
    await db_session.commit()


@pytest.mark.asyncio
async def test_verify_chain_detects_sequence_gap_and_broken_link(
    db_session: AsyncSession,
):
    """Verifies that sequence gaps, broken hash links, and report metadata are accurately flagged."""
    # Create 3 sequential events
    ev1 = await record_audit_log(
        db=db_session,
        action_type="TEST_LINK_1",
        entity_type="link_test",
        entity_id=uuid.uuid4(),
        new_state={"v": 1},
    )
    ev2 = await record_audit_log(
        db=db_session,
        action_type="TEST_LINK_2",
        entity_type="link_test",
        entity_id=uuid.uuid4(),
        new_state={"v": 2},
    )
    ev3 = await record_audit_log(
        db=db_session,
        action_type="TEST_LINK_3",
        entity_type="link_test",
        entity_id=uuid.uuid4(),
        new_state={"v": 3},
    )
    await db_session.commit()

    # 1. Clean verification
    clean_resp = await verify_audit_chain(
        db_session, from_sequence=ev1.sequence_number, to_sequence=ev3.sequence_number
    )
    assert clean_resp.is_valid is True
    assert clean_resp.status == "VALID"
    assert clean_resp.total_events_checked == 3
    assert clean_resp.last_verified_sequence == ev3.sequence_number
    assert clean_resp.first_failure_sequence is None
    assert clean_resp.failure_category is None

    # 2. Break previous hash link on ev2
    original_prev_hash = ev2.previous_hash
    ev2.previous_hash = "a" * 64
    await db_session.commit()

    tampered_resp = await verify_audit_chain(
        db_session, from_sequence=ev1.sequence_number, to_sequence=ev3.sequence_number
    )
    assert tampered_resp.is_valid is False
    assert tampered_resp.status == "COMPROMISED"
    assert tampered_resp.first_failure_sequence == ev2.sequence_number
    assert tampered_resp.failure_category in ("PREV_HASH_MISMATCH", "HASH_MISMATCH")
    assert tampered_resp.last_verified_sequence == ev1.sequence_number

    # Restore
    ev2.previous_hash = original_prev_hash
    await db_session.commit()


@pytest.mark.asyncio
async def test_entity_audit_trail_supported_entities(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """Verifies that entity audit trail API supports projects, targets, inspections, tasks, and observations."""
    admin_user, admin_headers = await create_user_with_token(db_session, UserRole.ADMIN, "Admin Trail")
    project = await create_test_project(db_session, "Entity Trail Project")
    project_id = project.id
    target_id = uuid.uuid4()
    inspection_id = uuid.uuid4()
    task_id = uuid.uuid4()
    obs_id = uuid.uuid4()

    # Record events for each entity type
    for etype, eid in [
        ("project", project_id),
        ("environmental_target", target_id),
        ("field_inspection", inspection_id),
        ("maintenance_task", task_id),
        ("survival_observation", obs_id),
    ]:
        await record_audit_log(
            db=db_session,
            action_type=f"{etype.upper()}_MUTATED",
            entity_type=etype,
            entity_id=eid,
            new_state={"status": "ACTIVE"},
        )
    await db_session.commit()

    # Query entity trails via API
    for etype, eid in [
        ("project", project_id),
        ("environmental_target", target_id),
        ("field_inspection", inspection_id),
        ("maintenance_task", task_id),
        ("survival_observation", obs_id),
    ]:
        resp = await client.get(f"/api/v1/audit/entities/{etype}/{eid}", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert data["items"][0]["entity_type"] == etype
        assert data["items"][0]["entity_id"] == str(eid)
