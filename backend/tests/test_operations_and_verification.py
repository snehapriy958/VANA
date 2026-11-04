"""
VANA — Milestone 4 Integration & Security Tests
Tests field operations, activity reporting, photo evidence management,
immutable revision history, anti-self-verification enforcement, and 5-ledger accounting.
"""

import asyncio
from datetime import date
from decimal import Decimal
import io
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.domains.audit.models import AuditLog
from app.domains.auth.models import User, UserRole
from app.domains.operations.models import (
    ActivityRevision,
    ActivityStatus,
    EvidenceFile,
    FieldActivity,
    RejectionReasonCode,
)
from app.domains.projects.models import Project, ProjectStatus, ProjectTarget
from app.domains.teams.models import ProjectAssignment


async def create_user_helper(
    db: AsyncSession,
    role: str = UserRole.FIELD_OFFICER.value,
    full_name: str = "Test User",
) -> tuple[User, dict]:
    """Helper to provision a user and return authorization header."""
    user = User(
        id=uuid.uuid4(),
        email=f"user_{uuid.uuid4().hex[:6]}@vana.org",
        hashed_password=hash_password("SecurePass123!"),
        full_name=full_name,
        role=role,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    token = create_access_token(subject=str(user.id), role=user.role, email=user.email)
    return user, {"Authorization": f"Bearer {token}"}


async def setup_test_project_with_target(
    db: AsyncSession,
    metric_code: str = "TREES_PLANTED",
    unit: str = "trees",
    target_qty: Decimal = Decimal("5000.0"),
) -> Project:
    """Helper to create an active project with a configured metric target."""
    project = Project(
        id=uuid.uuid4(),
        name="Sundarbans Delta Mangrove Restoration",
        code=f"VANA-TEST-{uuid.uuid4().hex[:6].upper()}",
        status=ProjectStatus.ACTIVE.value,
        latitude=21.9497,
        longitude=89.1833,
    )
    db.add(project)
    await db.flush()

    target = ProjectTarget(
        id=uuid.uuid4(),
        project_id=project.id,
        metric_code=metric_code,
        target_quantity=target_qty,
        target_unit=unit,
        target_date=date(2027, 12, 31),
    )
    db.add(target)
    await db.commit()
    await db.refresh(project)
    return project


# ============================================================================
# 1. Field Activity Submission & Scoping Tests
# ============================================================================

@pytest.mark.asyncio
async def test_field_officer_can_submit_activity(client: AsyncClient, db_session: AsyncSession):
    project = await setup_test_project_with_target(db_session, "TREES_PLANTED", "trees")
    fo, fo_headers = await create_user_helper(
        db_session, UserRole.FIELD_OFFICER.value, "Field Officer Aris"
    )

    # Assign Field Officer to project
    assignment = ProjectAssignment(
        project_id=project.id, user_id=fo.id, assigned_role="FIELD_OFFICER"
    )
    db_session.add(assignment)
    await db_session.commit()

    form_data = {
        "project_id": str(project.id),
        "metric_code": "TREES_PLANTED",
        "quantity": "250.00",
        "unit": "trees",
        "activity_date": "2026-11-02",
        "latitude": "21.9512",
        "longitude": "89.1840",
        "gps_accuracy_meters": "4.2",
        "field_notes": "Planted Rhizophora mucronata seedlings along river bank.",
    }

    res = await client.post("/api/v1/operations/activities", data=form_data, headers=fo_headers)
    assert res.status_code == 201
    data = res.json()
    assert data["project_id"] == str(project.id)
    assert data["metric_code"] == "TREES_PLANTED"
    assert data["unit"] == "trees"
    assert data["created_by_id"] == str(fo.id)
    assert data["created_by_name"] == "Field Officer Aris"
    assert data["is_archived"] is False
    assert data["active_verified_quantity"] == "0.0"
    assert data["current_revision"]["revision_number"] == 1
    assert data["current_revision"]["status"] == "PENDING"
    assert data["current_revision"]["is_active_ledger_entry"] is False
    assert data["net_pending_adjustment"] == "250.00"


@pytest.mark.asyncio
async def test_unassigned_field_officer_cannot_submit_activity(
    client: AsyncClient, db_session: AsyncSession
):
    project = await setup_test_project_with_target(db_session)
    fo, fo_headers = await create_user_helper(db_session, UserRole.FIELD_OFFICER.value, "Unassigned FO")

    form_data = {
        "project_id": str(project.id),
        "metric_code": "TREES_PLANTED",
        "quantity": "100.00",
        "unit": "trees",
        "activity_date": "2026-11-02",
    }

    res = await client.post("/api/v1/operations/activities", data=form_data, headers=fo_headers)
    assert res.status_code == 403
    assert res.json()["detail"]["error_code"] == "PROJECT_ACCESS_DENIED"


@pytest.mark.asyncio
async def test_submission_for_unconfigured_metric_target_rejected(
    client: AsyncClient, db_session: AsyncSession
):
    project = await setup_test_project_with_target(db_session, "TREES_PLANTED", "trees")
    fo, fo_headers = await create_user_helper(db_session, UserRole.FIELD_OFFICER.value, "FO Assigned")

    assignment = ProjectAssignment(project_id=project.id, user_id=fo.id, assigned_role="FIELD_OFFICER")
    db_session.add(assignment)
    await db_session.commit()

    # Attempt to report AREA_RESTORED when project only has TREES_PLANTED target
    form_data = {
        "project_id": str(project.id),
        "metric_code": "AREA_RESTORED",
        "quantity": "10.00",
        "unit": "hectares",
        "activity_date": "2026-11-02",
    }

    res = await client.post("/api/v1/operations/activities", data=form_data, headers=fo_headers)
    assert res.status_code == 400
    assert res.json()["detail"]["error_code"] == "PROJECT_TARGET_NOT_CONFIGURED"


@pytest.mark.asyncio
async def test_submission_incompatible_unit_rejected(client: AsyncClient, db_session: AsyncSession):
    project = await setup_test_project_with_target(db_session, "TREES_PLANTED", "trees")
    admin, admin_headers = await create_user_helper(db_session, UserRole.ADMIN.value, "Admin")

    # Incompatible unit (liters for TREES_PLANTED)
    form_data = {
        "project_id": str(project.id),
        "metric_code": "TREES_PLANTED",
        "quantity": "50.00",
        "unit": "liters",
        "activity_date": "2026-11-02",
    }

    res = await client.post("/api/v1/operations/activities", data=form_data, headers=admin_headers)
    assert res.status_code == 400
    assert res.json()["detail"]["error_code"] == "INVALID_METRIC_UNIT"


@pytest.mark.asyncio
async def test_submission_negative_quantity_rejected(client: AsyncClient, db_session: AsyncSession):
    project = await setup_test_project_with_target(db_session)
    admin, admin_headers = await create_user_helper(db_session, UserRole.ADMIN.value, "Admin")

    form_data = {
        "project_id": str(project.id),
        "metric_code": "TREES_PLANTED",
        "quantity": "-10.00",
        "unit": "trees",
        "activity_date": "2026-11-02",
    }

    res = await client.post("/api/v1/operations/activities", data=form_data, headers=admin_headers)
    assert res.status_code == 422


# ============================================================================
# 2. Evidence File Upload & Access-Controlled Retrieval Tests
# ============================================================================

@pytest.mark.asyncio
async def test_evidence_file_upload_and_secure_streaming(
    client: AsyncClient, db_session: AsyncSession
):
    project = await setup_test_project_with_target(db_session)
    fo, fo_headers = await create_user_helper(db_session, UserRole.FIELD_OFFICER.value, "FO Assigned")
    unassigned_fo, unassigned_headers = await create_user_helper(
        db_session, UserRole.FIELD_OFFICER.value, "FO Unassigned"
    )

    assignment = ProjectAssignment(project_id=project.id, user_id=fo.id, assigned_role="FIELD_OFFICER")
    db_session.add(assignment)
    await db_session.commit()

    form_data = {
        "project_id": str(project.id),
        "metric_code": "TREES_PLANTED",
        "quantity": "100.00",
        "unit": "trees",
        "activity_date": "2026-11-02",
    }

    fake_image_bytes = b"\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    files = [
        ("evidence_files", ("site_photo.jpg", io.BytesIO(fake_image_bytes), "image/jpeg")),
    ]

    res = await client.post(
        "/api/v1/operations/activities", data=form_data, files=files, headers=fo_headers
    )
    assert res.status_code == 201
    data = res.json()
    evidence_list = data["current_revision"]["evidence_files"]
    assert len(evidence_list) == 1
    evidence_id = evidence_list[0]["id"]
    assert evidence_list[0]["original_filename"] == "site_photo.jpg"
    assert evidence_list[0]["mime_type"] == "image/jpeg"

    # Authorized user can stream evidence
    stream_res = await client.get(f"/api/v1/operations/evidence/{evidence_id}", headers=fo_headers)
    assert stream_res.status_code == 200
    assert stream_res.content == fake_image_bytes

    # Unassigned user is blocked with 403 Forbidden
    denied_res = await client.get(
        f"/api/v1/operations/evidence/{evidence_id}", headers=unassigned_headers
    )
    assert denied_res.status_code == 403
    assert denied_res.json()["detail"]["error_code"] == "PROJECT_ACCESS_DENIED"


@pytest.mark.asyncio
async def test_evidence_file_unsupported_type_rejected(client: AsyncClient, db_session: AsyncSession):
    project = await setup_test_project_with_target(db_session)
    admin, admin_headers = await create_user_helper(db_session, UserRole.ADMIN.value, "Admin")

    form_data = {
        "project_id": str(project.id),
        "metric_code": "TREES_PLANTED",
        "quantity": "50.00",
        "unit": "trees",
        "activity_date": "2026-11-02",
    }

    files = [
        ("evidence_files", ("malicious.exe", io.BytesIO(b"MZBINARY"), "application/x-msdownload")),
    ]

    res = await client.post(
        "/api/v1/operations/activities", data=form_data, files=files, headers=admin_headers
    )
    assert res.status_code == 400
    assert res.json()["detail"]["error_code"] == "UNSUPPORTED_FILE_TYPE"


# ============================================================================
# 3. Activity Amendments & Net Adjustments
# ============================================================================

@pytest.mark.asyncio
async def test_amendment_net_adjustment_accounting(client: AsyncClient, db_session: AsyncSession):
    project = await setup_test_project_with_target(db_session)
    fo, fo_headers = await create_user_helper(db_session, UserRole.FIELD_OFFICER.value, "Author FO")
    pm, pm_headers = await create_user_helper(db_session, UserRole.PROJECT_MANAGER.value, "Lead PM")

    # Assign both to project
    db_session.add(
        ProjectAssignment(project_id=project.id, user_id=fo.id, assigned_role="FIELD_OFFICER")
    )
    db_session.add(
        ProjectAssignment(project_id=project.id, user_id=pm.id, assigned_role="PROJECT_MANAGER")
    )
    await db_session.commit()

    # 1. FO creates activity for 100 trees
    create_res = await client.post(
        "/api/v1/operations/activities",
        data={
            "project_id": str(project.id),
            "metric_code": "TREES_PLANTED",
            "quantity": "100.00",
            "unit": "trees",
            "activity_date": "2026-11-02",
        },
        headers=fo_headers,
    )
    assert create_res.status_code == 201
    act_data = create_res.json()
    activity_id = act_data["id"]
    rev1_id = act_data["current_revision"]["id"]

    # 2. PM approves revision 1
    verify_res = await client.post(
        f"/api/v1/verification/revisions/{rev1_id}/decision",
        json={"decision": "VERIFIED", "review_notes": "Tag counts verified in sector 3."},
        headers=pm_headers,
    )
    assert verify_res.status_code == 200
    v_data = verify_res.json()
    assert v_data["status"] == "VERIFIED"
    assert v_data["is_active_ledger_entry"] is True
    assert Decimal(str(v_data["project_verified_total_recalculated"])) == Decimal("100.00")

    # 3. FO amends activity to 160 trees (+60 net adjustment)
    amend_res = await client.post(
        f"/api/v1/operations/activities/{activity_id}/revisions",
        data={
            "quantity": "160.00",
            "activity_date": "2026-11-03",
            "amendment_reason": "Additional 60 saplings planted in adjacent furrow.",
        },
        headers=fo_headers,
    )
    assert amend_res.status_code == 201
    amend_data = amend_res.json()
    assert amend_data["active_verified_quantity"] == "100.00"
    assert amend_data["net_pending_adjustment"] == "60.00"
    assert amend_data["current_revision"]["revision_number"] == 2
    assert amend_data["current_revision"]["status"] == "PENDING"
    assert amend_data["current_revision"]["is_active_ledger_entry"] is False

    # 4. Attempting to submit another revision while Rev 2 is PENDING is blocked
    blocked_amend = await client.post(
        f"/api/v1/operations/activities/{activity_id}/revisions",
        data={"quantity": "180.00", "activity_date": "2026-11-04"},
        headers=fo_headers,
    )
    assert blocked_amend.status_code == 400
    assert blocked_amend.json()["detail"]["error_code"] == "PENDING_REVISION_EXISTS"

    # 5. Check verification queue calculation
    queue_res = await client.get("/api/v1/verification/queue", headers=pm_headers)
    assert queue_res.status_code == 200
    items = queue_res.json()
    rev2_item = next(i for i in items if i["activity_id"] == activity_id)
    assert rev2_item["is_amendment"] is True
    assert rev2_item["previously_verified_quantity"] == "100.00"
    assert rev2_item["net_adjustment"] == "60.00"
    assert rev2_item["can_verify"] is True


@pytest.mark.asyncio
async def test_negative_amendment_net_adjustment(client: AsyncClient, db_session: AsyncSession):
    project = await setup_test_project_with_target(db_session)
    admin, admin_headers = await create_user_helper(db_session, UserRole.ADMIN.value, "Admin Director")
    pm, pm_headers = await create_user_helper(db_session, UserRole.PROJECT_MANAGER.value, "Lead PM")

    db_session.add(
        ProjectAssignment(project_id=project.id, user_id=pm.id, assigned_role="PROJECT_MANAGER")
    )
    await db_session.commit()

    # PM submits 200 trees
    create_res = await client.post(
        "/api/v1/operations/activities",
        data={
            "project_id": str(project.id),
            "metric_code": "TREES_PLANTED",
            "quantity": "200.00",
            "unit": "trees",
            "activity_date": "2026-11-02",
        },
        headers=pm_headers,
    )
    act_data = create_res.json()
    rev1_id = act_data["current_revision"]["id"]

    # Admin verifies revision 1
    await client.post(
        f"/api/v1/verification/revisions/{rev1_id}/decision",
        json={"decision": "VERIFIED"},
        headers=admin_headers,
    )

    # PM discovers an overcount and amends down to 150 (-50 net adjustment)
    amend_res = await client.post(
        f"/api/v1/operations/activities/{act_data['id']}/revisions",
        data={
            "quantity": "150.00",
            "activity_date": "2026-11-02",
            "amendment_reason": "Mortality in transit; 50 dead saplings removed.",
        },
        headers=pm_headers,
    )
    assert amend_res.status_code == 201
    amend_data = amend_res.json()
    assert amend_data["active_verified_quantity"] == "200.00"
    assert amend_data["net_pending_adjustment"] == "-50.00"


# ============================================================================
# 4. Anti-Self-Verification Gate & Authorization Boundaries
# ============================================================================

@pytest.mark.asyncio
async def test_anti_self_verification_gate_strictly_enforced(
    client: AsyncClient, db_session: AsyncSession
):
    project = await setup_test_project_with_target(db_session)
    pm, pm_headers = await create_user_helper(
        db_session, UserRole.PROJECT_MANAGER.value, "PM Author Verifier"
    )

    db_session.add(
        ProjectAssignment(project_id=project.id, user_id=pm.id, assigned_role="PROJECT_MANAGER")
    )
    await db_session.commit()

    # PM creates activity
    create_res = await client.post(
        "/api/v1/operations/activities",
        data={
            "project_id": str(project.id),
            "metric_code": "TREES_PLANTED",
            "quantity": "300.00",
            "unit": "trees",
            "activity_date": "2026-11-02",
        },
        headers=pm_headers,
    )
    rev_id = create_res.json()["current_revision"]["id"]

    # Same PM attempts to verify their own submission -> HTTP 403 Forbidden
    self_verify_res = await client.post(
        f"/api/v1/verification/revisions/{rev_id}/decision",
        json={"decision": "VERIFIED", "review_notes": "Approving my own work."},
        headers=pm_headers,
    )
    assert self_verify_res.status_code == 403
    assert self_verify_res.json()["detail"]["error_code"] == "SELF_VERIFICATION_PROHIBITED"

    # Queue reflects that PM cannot self-verify
    queue_res = await client.get("/api/v1/verification/queue", headers=pm_headers)
    assert queue_res.status_code == 200
    item = queue_res.json()[0]
    assert item["can_verify"] is False


@pytest.mark.asyncio
async def test_field_officer_cannot_verify_activities(client: AsyncClient, db_session: AsyncSession):
    project = await setup_test_project_with_target(db_session)
    admin, admin_headers = await create_user_helper(db_session, UserRole.ADMIN.value, "Admin Author")
    fo, fo_headers = await create_user_helper(db_session, UserRole.FIELD_OFFICER.value, "Field Officer")

    db_session.add(
        ProjectAssignment(project_id=project.id, user_id=fo.id, assigned_role="FIELD_OFFICER")
    )
    await db_session.commit()

    # Admin creates activity
    create_res = await client.post(
        "/api/v1/operations/activities",
        data={
            "project_id": str(project.id),
            "metric_code": "TREES_PLANTED",
            "quantity": "100.00",
            "unit": "trees",
            "activity_date": "2026-11-02",
        },
        headers=admin_headers,
    )
    rev_id = create_res.json()["current_revision"]["id"]

    # Field officer attempts to access verification queue -> 403
    fo_queue_res = await client.get("/api/v1/verification/queue", headers=fo_headers)
    assert fo_queue_res.status_code == 403
    assert fo_queue_res.json()["detail"]["error_code"] == "INSUFFICIENT_ROLE"

    # Field officer attempts to verify -> 403
    fo_verify_res = await client.post(
        f"/api/v1/verification/revisions/{rev_id}/decision",
        json={"decision": "VERIFIED"},
        headers=fo_headers,
    )
    assert fo_verify_res.status_code == 403
    assert fo_verify_res.json()["detail"]["error_code"] == "INSUFFICIENT_ROLE"


@pytest.mark.asyncio
async def test_cross_project_pm_cannot_verify_unassigned_project(
    client: AsyncClient, db_session: AsyncSession
):
    project_a = await setup_test_project_with_target(db_session)
    project_b = await setup_test_project_with_target(db_session)

    admin, admin_headers = await create_user_helper(db_session, UserRole.ADMIN.value, "Admin Author")
    pm_b, pm_b_headers = await create_user_helper(
        db_session, UserRole.PROJECT_MANAGER.value, "PM Project B"
    )

    # Assign PM only to Project B
    db_session.add(
        ProjectAssignment(project_id=project_b.id, user_id=pm_b.id, assigned_role="PROJECT_MANAGER")
    )
    await db_session.commit()

    # Admin creates activity on Project A
    create_res = await client.post(
        "/api/v1/operations/activities",
        data={
            "project_id": str(project_a.id),
            "metric_code": "TREES_PLANTED",
            "quantity": "100.00",
            "unit": "trees",
            "activity_date": "2026-11-02",
        },
        headers=admin_headers,
    )
    rev_id = create_res.json()["current_revision"]["id"]

    # PM of Project B attempts to verify activity on Project A -> 403
    verify_res = await client.post(
        f"/api/v1/verification/revisions/{rev_id}/decision",
        json={"decision": "VERIFIED"},
        headers=pm_b_headers,
    )
    assert verify_res.status_code == 403
    assert verify_res.json()["detail"]["error_code"] == "PROJECT_ACCESS_DENIED"


# ============================================================================
# 5. Verification Rejection & Active Ledger Invariant Preservation
# ============================================================================

@pytest.mark.asyncio
async def test_verification_rejection_requires_reason_and_notes(
    client: AsyncClient, db_session: AsyncSession
):
    project = await setup_test_project_with_target(db_session)
    fo, fo_headers = await create_user_helper(db_session, UserRole.FIELD_OFFICER.value, "FO Submitter")
    admin, admin_headers = await create_user_helper(db_session, UserRole.ADMIN.value, "Admin Verifier")

    db_session.add(
        ProjectAssignment(project_id=project.id, user_id=fo.id, assigned_role="FIELD_OFFICER")
    )
    await db_session.commit()

    create_res = await client.post(
        "/api/v1/operations/activities",
        data={
            "project_id": str(project.id),
            "metric_code": "TREES_PLANTED",
            "quantity": "500.00",
            "unit": "trees",
            "activity_date": "2026-11-02",
        },
        headers=fo_headers,
    )
    rev_id = create_res.json()["current_revision"]["id"]

    # Missing rejection reason code -> 422
    rej_no_reason = await client.post(
        f"/api/v1/verification/revisions/{rev_id}/decision",
        json={"decision": "REJECTED", "review_notes": "Not clear"},
        headers=admin_headers,
    )
    assert rej_no_reason.status_code == 422

    # Missing review notes -> 422
    rej_no_notes = await client.post(
        f"/api/v1/verification/revisions/{rev_id}/decision",
        json={"decision": "REJECTED", "rejection_reason_code": "INSUFFICIENT_EVIDENCE"},
        headers=admin_headers,
    )
    assert rej_no_notes.status_code == 422

    # Valid rejection
    valid_rej = await client.post(
        f"/api/v1/verification/revisions/{rev_id}/decision",
        json={
            "decision": "REJECTED",
            "rejection_reason_code": "INSUFFICIENT_EVIDENCE",
            "review_notes": "Sapling photo out of focus; cannot verify physical count.",
        },
        headers=admin_headers,
    )
    assert valid_rej.status_code == 200
    v_data = valid_rej.json()
    assert v_data["status"] == "REJECTED"
    assert v_data["is_active_ledger_entry"] is False
    assert v_data["rejection_reason_code"] == "INSUFFICIENT_EVIDENCE"
    assert v_data["project_verified_total_recalculated"] == "0.0"


@pytest.mark.asyncio
async def test_rejection_preserves_previously_verified_revision(
    client: AsyncClient, db_session: AsyncSession
):
    project = await setup_test_project_with_target(db_session)
    fo, fo_headers = await create_user_helper(db_session, UserRole.FIELD_OFFICER.value, "FO Submitter")
    admin, admin_headers = await create_user_helper(db_session, UserRole.ADMIN.value, "Admin Verifier")

    db_session.add(
        ProjectAssignment(project_id=project.id, user_id=fo.id, assigned_role="FIELD_OFFICER")
    )
    await db_session.commit()

    # 1. FO submits 100 trees
    create_res = await client.post(
        "/api/v1/operations/activities",
        data={
            "project_id": str(project.id),
            "metric_code": "TREES_PLANTED",
            "quantity": "100.00",
            "unit": "trees",
            "activity_date": "2026-11-02",
        },
        headers=fo_headers,
    )
    act_id = create_res.json()["id"]
    rev1_id = create_res.json()["current_revision"]["id"]

    # 2. Admin verifies Revision 1
    await client.post(
        f"/api/v1/verification/revisions/{rev1_id}/decision",
        json={"decision": "VERIFIED"},
        headers=admin_headers,
    )

    # 3. FO amends to 200 trees
    amend_res = await client.post(
        f"/api/v1/operations/activities/{act_id}/revisions",
        data={"quantity": "200.00", "activity_date": "2026-11-03"},
        headers=fo_headers,
    )
    rev2_id = amend_res.json()["current_revision"]["id"]

    # 4. Admin rejects Revision 2
    rej_res = await client.post(
        f"/api/v1/verification/revisions/{rev2_id}/decision",
        json={
            "decision": "REJECTED",
            "rejection_reason_code": "DUPLICATE_SUBMISSION",
            "review_notes": "Sector already surveyed under revision 1.",
        },
        headers=admin_headers,
    )
    assert rej_res.status_code == 200
    assert Decimal(str(rej_res.json()["project_verified_total_recalculated"])) == Decimal("100.00")

    # 5. Verify that Revision 1 remains the active ledger entry
    act_fetch = await client.get(f"/api/v1/operations/activities/{act_id}", headers=admin_headers)
    act_json = act_fetch.json()
    assert act_json["active_verified_quantity"] == "100.00"
    assert act_json["active_ledger_revision"]["id"] == rev1_id
    assert act_json["active_ledger_revision"]["is_active_ledger_entry"] is True


# ============================================================================
# 6. Activity Archiving & Soft-Delete Ledger Recalculation
# ============================================================================

@pytest.mark.asyncio
async def test_archiving_activity_deactivates_active_ledger_entry(
    client: AsyncClient, db_session: AsyncSession
):
    project = await setup_test_project_with_target(db_session)
    fo, fo_headers = await create_user_helper(db_session, UserRole.FIELD_OFFICER.value, "FO Submitter")
    admin, admin_headers = await create_user_helper(db_session, UserRole.ADMIN.value, "Admin Verifier")

    db_session.add(
        ProjectAssignment(project_id=project.id, user_id=fo.id, assigned_role="FIELD_OFFICER")
    )
    await db_session.commit()

    # Create and verify activity
    create_res = await client.post(
        "/api/v1/operations/activities",
        data={
            "project_id": str(project.id),
            "metric_code": "TREES_PLANTED",
            "quantity": "300.00",
            "unit": "trees",
            "activity_date": "2026-11-02",
        },
        headers=fo_headers,
    )
    act_id = create_res.json()["id"]
    rev_id = create_res.json()["current_revision"]["id"]

    await client.post(
        f"/api/v1/verification/revisions/{rev_id}/decision",
        json={"decision": "VERIFIED"},
        headers=admin_headers,
    )

    # Field officer cannot archive activity -> 403
    fo_archive_res = await client.delete(
        f"/api/v1/operations/activities/{act_id}", headers=fo_headers
    )
    assert fo_archive_res.status_code == 403

    # Admin archives activity
    archive_res = await client.delete(
        f"/api/v1/operations/activities/{act_id}", headers=admin_headers
    )
    assert archive_res.status_code == 200
    assert archive_res.json()["status"] == "ARCHIVED"
    assert archive_res.json()["deactivated_revision_id"] == rev_id

    # Check that database model reflects is_archived = True and is_active_ledger_entry = False
    rev_db = await db_session.scalar(select(ActivityRevision).where(ActivityRevision.id == rev_id))
    assert rev_db.is_active_ledger_entry is False


@pytest.mark.asyncio
async def test_archiving_ledger_invariants_verified_reduction_and_rejected_unchanged(
    client: AsyncClient, db_session: AsyncSession
):
    """
    Verifies that:
    1. Archiving an activity with an active verified revision (1,800 trees)
       reduces the official verified quantity by exactly 1,800 trees.
    2. Archiving an activity with only rejected revisions (800 trees)
       leaves the official verified quantity completely unchanged.
    """
    project = await setup_test_project_with_target(db_session, target_qty=Decimal("10000.0"))
    fo, fo_headers = await create_user_helper(db_session, UserRole.FIELD_OFFICER.value, "FO Submitter")
    admin, admin_headers = await create_user_helper(db_session, UserRole.ADMIN.value, "Admin Reviewer")

    db_session.add(
        ProjectAssignment(project_id=project.id, user_id=fo.id, assigned_role="FIELD_OFFICER")
    )
    await db_session.commit()

    # 1. Create and verify Activity A (1,800 trees)
    create_a = await client.post(
        "/api/v1/operations/activities",
        data={
            "project_id": str(project.id),
            "metric_code": "TREES_PLANTED",
            "quantity": "1800.00",
            "unit": "trees",
            "activity_date": "2026-11-02",
        },
        headers=fo_headers,
    )
    act_a_id = create_a.json()["id"]
    rev_a_id = create_a.json()["current_revision"]["id"]

    await client.post(
        f"/api/v1/verification/revisions/{rev_a_id}/decision",
        json={"decision": "VERIFIED"},
        headers=admin_headers,
    )

    # 2. Create and reject Activity B (800 trees)
    create_b = await client.post(
        "/api/v1/operations/activities",
        data={
            "project_id": str(project.id),
            "metric_code": "TREES_PLANTED",
            "quantity": "800.00",
            "unit": "trees",
            "activity_date": "2026-11-03",
        },
        headers=fo_headers,
    )
    act_b_id = create_b.json()["id"]
    rev_b_id = create_b.json()["current_revision"]["id"]

    await client.post(
        f"/api/v1/verification/revisions/{rev_b_id}/decision",
        json={
            "decision": "REJECTED",
            "rejection_reason_code": "INSUFFICIENT_EVIDENCE",
            "review_notes": "No proof",
        },
        headers=admin_headers,
    )

    # 3. Check baseline verified quantity: exactly 1,800 trees
    impact_baseline = await client.get(
        f"/api/v1/analytics/projects/{project.id}/impact", headers=admin_headers
    )
    t_base = next(t for t in impact_baseline.json()["targets"] if t["metric_code"] == "TREES_PLANTED")
    assert Decimal(str(t_base["verified_quantity"])) == Decimal("1800.00")

    # 4. Invariant 1: Archive rejected Activity B -> verified quantity remains unchanged at 1,800 trees
    archive_b = await client.delete(
        f"/api/v1/operations/activities/{act_b_id}", headers=admin_headers
    )
    assert archive_b.status_code == 200
    assert archive_b.json()["status"] == "ARCHIVED"
    assert archive_b.json()["deactivated_revision_id"] is None

    impact_after_b = await client.get(
        f"/api/v1/analytics/projects/{project.id}/impact", headers=admin_headers
    )
    t_after_b = next(t for t in impact_after_b.json()["targets"] if t["metric_code"] == "TREES_PLANTED")
    assert Decimal(str(t_after_b["verified_quantity"])) == Decimal("1800.00")

    # 5. Invariant 2: Archive verified Activity A (1,800 trees) -> verified quantity drops by exactly 1,800 to 0
    archive_a = await client.delete(
        f"/api/v1/operations/activities/{act_a_id}", headers=admin_headers
    )
    assert archive_a.status_code == 200
    assert archive_a.json()["status"] == "ARCHIVED"
    assert archive_a.json()["deactivated_revision_id"] == rev_a_id

    impact_after_a = await client.get(
        f"/api/v1/analytics/projects/{project.id}/impact", headers=admin_headers
    )
    t_after_a = next(t for t in impact_after_a.json()["targets"] if t["metric_code"] == "TREES_PLANTED")
    assert Decimal(str(t_after_a["verified_quantity"])) == Decimal("0.00")


# ============================================================================
# 7. Concurrency & Race Condition Safeguard
# ============================================================================

@pytest.mark.asyncio
async def test_concurrent_verification_decisions_safeguard(
    client: AsyncClient, db_session: AsyncSession
):
    project = await setup_test_project_with_target(db_session)
    fo, fo_headers = await create_user_helper(db_session, UserRole.FIELD_OFFICER.value, "FO Submitter")
    admin1, admin1_headers = await create_user_helper(db_session, UserRole.ADMIN.value, "Admin Reviewer 1")
    admin2, admin2_headers = await create_user_helper(db_session, UserRole.ADMIN.value, "Admin Reviewer 2")

    db_session.add(
        ProjectAssignment(project_id=project.id, user_id=fo.id, assigned_role="FIELD_OFFICER")
    )
    await db_session.commit()

    create_res = await client.post(
        "/api/v1/operations/activities",
        data={
            "project_id": str(project.id),
            "metric_code": "TREES_PLANTED",
            "quantity": "150.00",
            "unit": "trees",
            "activity_date": "2026-11-02",
        },
        headers=fo_headers,
    )
    rev_id = create_res.json()["current_revision"]["id"]

    # Two reviewers attempt to verify simultaneously
    res1, res2 = await asyncio.gather(
        client.post(
            f"/api/v1/verification/revisions/{rev_id}/decision",
            json={"decision": "VERIFIED", "review_notes": "First reviewer"},
            headers=admin1_headers,
        ),
        client.post(
            f"/api/v1/verification/revisions/{rev_id}/decision",
            json={"decision": "VERIFIED", "review_notes": "Second reviewer"},
            headers=admin2_headers,
        ),
    )

    statuses = {res1.status_code, res2.status_code}
    # Exactly one must succeed (200) and the other must fail because revision is already reviewed (400)
    assert 200 in statuses
    assert 400 in statuses
    failed_res = res1 if res1.status_code == 400 else res2
    assert failed_res.json()["detail"]["error_code"] == "REVISION_ALREADY_REVIEWED"


# ============================================================================
# 8. Audit Log Verification
# ============================================================================

@pytest.mark.asyncio
async def test_audit_logs_record_all_operation_mutations(
    client: AsyncClient, db_session: AsyncSession
):
    project = await setup_test_project_with_target(db_session)
    fo, fo_headers = await create_user_helper(db_session, UserRole.FIELD_OFFICER.value, "FO Submitter")
    admin, admin_headers = await create_user_helper(db_session, UserRole.ADMIN.value, "Admin Verifier")

    db_session.add(
        ProjectAssignment(project_id=project.id, user_id=fo.id, assigned_role="FIELD_OFFICER")
    )
    await db_session.commit()

    # 1. Create activity
    create_res = await client.post(
        "/api/v1/operations/activities",
        data={
            "project_id": str(project.id),
            "metric_code": "TREES_PLANTED",
            "quantity": "100.00",
            "unit": "trees",
            "activity_date": "2026-11-02",
        },
        headers=fo_headers,
    )
    act_id = create_res.json()["id"]
    rev_id = create_res.json()["current_revision"]["id"]

    # 2. Verify activity
    await client.post(
        f"/api/v1/verification/revisions/{rev_id}/decision",
        json={"decision": "VERIFIED"},
        headers=admin_headers,
    )

    # 3. Archive activity
    await client.delete(f"/api/v1/operations/activities/{act_id}", headers=admin_headers)

    # Verify audit logs in database
    audit_events = await db_session.scalars(
        select(AuditLog)
        .where(AuditLog.entity_id.in_([uuid.UUID(act_id), uuid.UUID(rev_id)]))
        .order_by(AuditLog.created_at)
    )
    actions = [e.action_type for e in audit_events]
    assert "ACTIVITY_CREATED" in actions
    assert "ACTIVITY_VERIFIED" in actions
    assert "ACTIVITY_ARCHIVED" in actions


@pytest.mark.asyncio
async def test_evidence_file_path_traversal_prevention(
    client: AsyncClient, db_session: AsyncSession
):
    project = await setup_test_project_with_target(db_session)
    admin, admin_headers = await create_user_helper(
        db_session, UserRole.ADMIN.value, "Admin Traversal Test"
    )

    activity = FieldActivity(
        project_id=project.id,
        created_by_id=admin.id,
        metric_code="TREES_PLANTED",
        unit="trees",
    )
    db_session.add(activity)
    await db_session.flush()

    revision = ActivityRevision(
        activity_id=activity.id,
        revision_number=1,
        quantity=Decimal("10.0"),
        activity_date=date(2026, 11, 2),
        status="PENDING",
    )
    db_session.add(revision)
    await db_session.flush()

    traversal_evidence = EvidenceFile(
        activity_id=activity.id,
        revision_id=revision.id,
        file_storage_key="../../../windows/win.ini",
        original_filename="win.ini",
        mime_type="text/plain",
        file_size_bytes=100,
    )
    db_session.add(traversal_evidence)
    await db_session.commit()

    res = await client.get(
        f"/api/v1/operations/evidence/{traversal_evidence.id}", headers=admin_headers
    )
    assert res.status_code == 400
    assert res.json()["detail"]["error_code"] == "INVALID_STORAGE_KEY"

