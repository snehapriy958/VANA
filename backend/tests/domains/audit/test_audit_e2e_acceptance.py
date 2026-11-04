"""VANA Milestone 8 — Complete End-to-End Audit & Immutability Ledger Acceptance Test.

Executes the full 14-step operational and cryptographic audit lifecycle:
1. Create a project.
2. Assign users (PM and Field Officer).
3. Submit an activity (Field Officer).
4. Upload evidence.
5. Verify the activity (Project Manager).
6. Submit an amendment (Field Officer).
7. Complete an amendment decision / rejection (Project Manager).
8. Perform a monitoring operation (Schedule inspection & complete task).
9. Inspect the audit timeline via GET /audit/events.
10. Inspect verification history via GET /audit/verification.
11. Inspect entity history via GET /audit/entities/{type}/{id}.
12. Run cryptographic chain verification via POST /audit/verify-chain.
13. Confirm the ledger remains 100% valid with zero sequence gaps or link breaks.
14. Confirm unauthorized users (Field Officer, cross-project PM) cannot access restricted records.
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import io
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.domains.audit.models import AuditChainHead, AuditLog
from app.domains.auth.models import User, UserRole
from app.domains.projects.models import Project, ProjectStatus
from app.domains.teams.models import ProjectAssignment, ProjectRole
from app.domains.operations.models import ActivityStatus, RejectionReasonCode
from tests.test_operations_and_verification import create_user_helper


@pytest.mark.asyncio
async def test_milestone_8_full_audit_ledger_acceptance_workflow(
    client: AsyncClient, db_session: AsyncSession
):
    # ------------------------------------------------------------------------
    # Step 0: Provision System Personas
    # ------------------------------------------------------------------------
    admin, admin_headers = await create_user_helper(
        db_session, UserRole.ADMIN.value, "M8 Dr. Sunita Sharma (Admin)"
    )
    pm, pm_headers = await create_user_helper(
        db_session, UserRole.PROJECT_MANAGER.value, "M8 Rajesh Kumar (PM)"
    )
    fo, fo_headers = await create_user_helper(
        db_session, UserRole.FIELD_OFFICER.value, "M8 Aarav Patel (FO)"
    )
    other_pm, other_pm_headers = await create_user_helper(
        db_session, UserRole.PROJECT_MANAGER.value, "M8 Priya Nair (Unassigned PM)"
    )

    # ------------------------------------------------------------------------
    # Step 1: Admin Creates Project & Environmental Target
    # ------------------------------------------------------------------------
    proj_code = f"M8-{uuid.uuid4().hex[:6].upper()}"
    res_proj = await client.post(
        "/api/v1/projects",
        json={
            "name": "Sundarbans Mangrove Conservation",
            "code": proj_code,
            "description": "Estuarine delta afforestation and coastal wave attenuation.",
            "latitude": 21.9497,
            "longitude": 89.1833,
            "boundary_geojson": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [89.1700, 21.9400],
                        [89.1900, 21.9400],
                        [89.1900, 21.9600],
                        [89.1700, 21.9600],
                        [89.1700, 21.9400],
                    ]
                ],
            },
        },
        headers=admin_headers,
    )
    assert res_proj.status_code == 201
    project_id = res_proj.json()["id"]

    res_target = await client.post(
        f"/api/v1/projects/{project_id}/targets",
        json={
            "metric_code": "TREES_PLANTED",
            "target_quantity": 5000.0,
            "target_unit": "trees",
            "target_date": "2027-06-30",
        },
        headers=admin_headers,
    )
    assert res_target.status_code == 201

    # ------------------------------------------------------------------------
    # Step 2: Assign PM and Field Officer
    # ------------------------------------------------------------------------
    res_as_pm = await client.post(
        f"/api/v1/projects/{project_id}/assignments",
        json={"user_id": str(pm.id), "assigned_role": "PROJECT_MANAGER"},
        headers=admin_headers,
    )
    assert res_as_pm.status_code == 201

    res_as_fo = await client.post(
        f"/api/v1/projects/{project_id}/assignments",
        json={"user_id": str(fo.id), "assigned_role": "FIELD_OFFICER"},
        headers=admin_headers,
    )
    assert res_as_fo.status_code == 201

    # ------------------------------------------------------------------------
    # Step 3 & 4: Field Officer Submits Activity with Evidence File
    # ------------------------------------------------------------------------
    evidence_content = b"GENUINE_GEO_TAGGED_SEEDLING_PHOTO_DATA_JPG"
    activity_payload = {
        "project_id": project_id,
        "metric_code": "TREES_PLANTED",
        "unit": "trees",
        "quantity": "500.0",
        "activity_date": str(date.today()),
        "latitude": "21.9497",
        "longitude": "89.1833",
        "gps_accuracy_meters": "4.5",
        "field_notes": "First planting cohort: Rhizophora mucronata mangroves.",
    }
    files = [
        ("evidence_files", ("mangrove_seedling_01.jpg", io.BytesIO(evidence_content), "image/jpeg"))
    ]

    res_activity = await client.post(
        "/api/v1/operations/activities",
        data=activity_payload,
        files=files,
        headers=fo_headers,
    )
    assert res_activity.status_code == 201
    act_data = res_activity.json()
    activity_id = act_data["id"]
    revision_1_id = act_data["current_revision"]["id"]

    # ------------------------------------------------------------------------
    # Step 5: PM Verifies (Approves) Activity
    # ------------------------------------------------------------------------
    res_verify = await client.post(
        f"/api/v1/verification/revisions/{revision_1_id}/decision",
        json={
            "decision": "VERIFIED",
            "review_notes": "Reviewed geo-tagged photographic evidence. Canopy plot verified.",
        },
        headers=pm_headers,
    )
    assert res_verify.status_code == 200

    # ------------------------------------------------------------------------
    # Step 6: Field Officer Submits an Amendment
    # ------------------------------------------------------------------------
    amend_payload = {
        "quantity": "460.0",
        "activity_date": str(date.today()),
        "field_notes": "Corrected planting count after survival recount: 40 failed to establish.",
        "amendment_reason": "Survival recount deduction",
    }
    res_amend = await client.post(
        f"/api/v1/operations/activities/{activity_id}/revisions",
        data=amend_payload,
        headers=fo_headers,
    )
    assert res_amend.status_code == 201
    amend_data = res_amend.json()
    revision_2 = [r for r in amend_data["revisions"] if r["revision_number"] == 2][0]
    revision_2_id = revision_2["id"]

    # ------------------------------------------------------------------------
    # Step 7: PM Completes Decision on Amendment (Rejection for Audit Trail)
    # ------------------------------------------------------------------------
    res_reject = await client.post(
        f"/api/v1/verification/revisions/{revision_2_id}/decision",
        json={
            "decision": "REJECTED",
            "rejection_reason_code": "INSUFFICIENT_EVIDENCE",
            "review_notes": "Recount deduction lacks formal field inspection addendum.",
        },
        headers=pm_headers,
    )
    assert res_reject.status_code == 200

    # ------------------------------------------------------------------------
    # Step 8: Perform a Monitoring Operation (Schedule Inspection)
    # ------------------------------------------------------------------------
    res_insp = await client.post(
        "/api/v1/monitoring/inspections",
        json={
            "project_id": project_id,
            "linked_activity_id": activity_id,
            "assigned_to_id": str(pm.id),
            "scheduled_date": str(date.today() + timedelta(days=3)),
            "inspection_type": "SURVIVAL_CHECK",
        },
        headers=pm_headers,
    )
    assert res_insp.status_code == 201
    inspection_id = res_insp.json()["id"]

    # ------------------------------------------------------------------------
    # Step 9: Inspect the Audit Timeline via GET /audit/events
    # ------------------------------------------------------------------------
    res_timeline = await client.get(
        f"/api/v1/audit/events?project_id={project_id}&page_size=50",
        headers=pm_headers,
    )
    assert res_timeline.status_code == 200
    timeline_data = res_timeline.json()
    assert timeline_data["total"] >= 6
    action_types = [item["action_type"] for item in timeline_data["items"]]
    assert "ACTIVITY_CREATED" in action_types
    assert "EVIDENCE_UPLOADED" in action_types
    assert "ACTIVITY_VERIFIED" in action_types
    assert "ACTIVITY_AMENDED" in action_types
    assert "ACTIVITY_REJECTED" in action_types
    assert "INSPECTION_SCHEDULED" in action_types

    # Every event must have valid sequence and hashes
    for ev in timeline_data["items"]:
        assert ev["sequence_number"] > 0
        assert len(ev["current_hash"]) == 64
        assert len(ev["previous_hash"]) == 64
        assert ev["project_id"] == project_id

    # ------------------------------------------------------------------------
    # Step 10: Inspect Verification History via GET /audit/verification
    # ------------------------------------------------------------------------
    res_vh = await client.get(
        f"/api/v1/audit/verification?project_id={project_id}",
        headers=pm_headers,
    )
    assert res_vh.status_code == 200
    vh_data = res_vh.json()
    assert vh_data["total"] >= 4
    vh_actions = [v["action_type"] for v in vh_data["items"]]
    assert "ACTIVITY_VERIFIED" in vh_actions
    assert "ACTIVITY_REJECTED" in vh_actions

    rejected_item = [v for v in vh_data["items"] if v["action_type"] == "ACTIVITY_REJECTED"][0]
    assert rejected_item["rejection_reason_code"] == "INSUFFICIENT_EVIDENCE"
    assert "inspection addendum" in rejected_item["review_notes"]

    # ------------------------------------------------------------------------
    # Step 11: Inspect Entity History via GET /audit/entities/{type}/{id}
    # ------------------------------------------------------------------------
    res_entity = await client.get(
        f"/api/v1/audit/entities/field_activity/{activity_id}",
        headers=pm_headers,
    )
    assert res_entity.status_code == 200
    entity_data = res_entity.json()
    assert entity_data["total"] >= 2  # Created, Evidence, Amended
    assert entity_data["items"][0]["entity_id"] == activity_id

    # ------------------------------------------------------------------------
    # Step 12 & 13: Run Cryptographic Chain Verification & Confirm 100% Valid
    # ------------------------------------------------------------------------
    # Verify from the first event of this project to the latest sequence
    min_seq = min(item["sequence_number"] for item in timeline_data["items"])
    max_seq = max(item["sequence_number"] for item in timeline_data["items"])

    res_verify_chain = await client.post(
        "/api/v1/audit/verify-chain",
        json={"from_sequence": min_seq, "to_sequence": max_seq},
        headers=pm_headers,
    )
    assert res_verify_chain.status_code == 200
    chain_report = res_verify_chain.json()
    if not chain_report["is_valid"]:
        print("CHAIN ERRORS:", chain_report["errors"])
    assert chain_report["is_valid"] is True
    assert chain_report["status"] == "VALID"
    assert chain_report["total_events_checked"] == (max_seq - min_seq + 1)
    assert chain_report["last_verified_sequence"] == max_seq
    assert chain_report["first_failure_sequence"] is None
    assert chain_report["errors"] == []
    assert "disclaimer" in chain_report

    # ------------------------------------------------------------------------
    # Step 14: Confirm Unauthorized Users Cannot Access Restricted Records
    # ------------------------------------------------------------------------
    # 1. Field Officer access is denied (403 Forbidden)
    res_fo_denied = await client.get("/api/v1/audit/events", headers=fo_headers)
    assert res_fo_denied.status_code == 403

    res_fo_vh_denied = await client.get("/api/v1/audit/verification", headers=fo_headers)
    assert res_fo_vh_denied.status_code == 403

    res_fo_entity_denied = await client.get(
        f"/api/v1/audit/entities/field_activity/{activity_id}", headers=fo_headers
    )
    assert res_fo_entity_denied.status_code == 403

    # 2. Unassigned PM cannot access Sundarbans project events (403 Forbidden)
    res_unassigned_pm = await client.get(
        f"/api/v1/audit/events?project_id={project_id}", headers=other_pm_headers
    )
    assert res_unassigned_pm.status_code == 403

    res_unassigned_entity = await client.get(
        f"/api/v1/audit/entities/field_activity/{activity_id}", headers=other_pm_headers
    )
    assert res_unassigned_entity.status_code == 403
