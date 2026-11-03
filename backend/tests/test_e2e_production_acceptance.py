"""
VANA — Phase 5 End-to-End Acceptance Test
Executes complete production workflow across ADMIN, PROJECT_MANAGER, and FIELD_OFFICER roles:
1. Admin creates project and target (1,000 trees).
2. Admin provisions and assigns PM and Field Officer.
3. Field Officer submits 200 trees with evidence.
4. PM verifies 200 trees.
5. Field Officer submits 250 trees.
6. PM verifies 250 trees.
7. Field Officer submits 150 trees.
8. PM verifies 150 trees.
9. Reconcile ledger: 600/1,000 = 60% achievement, 400 remaining.
10. Submit amendment (+50) and verify pending adjustment does not increase official achievement.
11. Verify RBAC isolation against unassigned projects.
12. Verify evidence file content retrieval and streaming.
"""

from datetime import date
from decimal import Decimal
import io
import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.auth.models import UserRole
from tests.test_operations_and_verification import create_user_helper


@pytest.mark.asyncio
async def test_full_production_e2e_acceptance_workflow(
    client: AsyncClient, db_session: AsyncSession
):
    # ------------------------------------------------------------------------
    # Step 1: Provision System Accounts
    # ------------------------------------------------------------------------
    admin, admin_headers = await create_user_helper(
        db_session, UserRole.ADMIN.value, "Dr. Sunita Sharma (Admin)"
    )
    pm, pm_headers = await create_user_helper(
        db_session, UserRole.PROJECT_MANAGER.value, "Rajesh Kumar (PM)"
    )
    fo, fo_headers = await create_user_helper(
        db_session, UserRole.FIELD_OFFICER.value, "Aarav Patel (FO)"
    )
    unassigned_user, unassigned_headers = await create_user_helper(
        db_session, UserRole.PROJECT_MANAGER.value, "Priya Nair (Unassigned PM)"
    )

    # ------------------------------------------------------------------------
    # Step 2: Admin Creates Project & Environmental Target
    # ------------------------------------------------------------------------
    proj_code = f"DEMO-{uuid.uuid4().hex[:6].upper()}"
    create_proj_res = await client.post(
        "/api/v1/projects",
        json={
            "name": "Nilgiri Biosphere Ecological Restoration",
            "code": proj_code,
            "description": "Native shola forest afforestation and wildlife corridor connectivity.",
            "latitude": 11.4102,
            "longitude": 76.6950,
            "boundary_geojson": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [76.6900, 11.4050],
                        [76.7000, 11.4050],
                        [76.7000, 11.4150],
                        [76.6900, 11.4150],
                        [76.6900, 11.4050],
                    ]
                ],
            },
        },
        headers=admin_headers,
    )
    assert create_proj_res.status_code == 201, create_proj_res.text
    project_id = create_proj_res.json()["id"]

    # Target: 1,000 trees
    create_target_res = await client.post(
        f"/api/v1/projects/{project_id}/targets",
        json={
            "metric_code": "TREES_PLANTED",
            "target_quantity": 1000.0,
            "target_unit": "trees",
            "target_date": "2026-12-31",
        },
        headers=admin_headers,
    )
    assert create_target_res.status_code == 201, create_target_res.text
    target_id = create_target_res.json()["id"]

    # ------------------------------------------------------------------------
    # Step 3: Admin Assigns PM and Field Officer to Project
    # ------------------------------------------------------------------------
    assign_pm_res = await client.post(
        f"/api/v1/projects/{project_id}/assignments",
        json={"user_id": str(pm.id), "assigned_role": "PROJECT_MANAGER"},
        headers=admin_headers,
    )
    assert assign_pm_res.status_code == 201

    assign_fo_res = await client.post(
        f"/api/v1/projects/{project_id}/assignments",
        json={"user_id": str(fo.id), "assigned_role": "FIELD_OFFICER"},
        headers=admin_headers,
    )
    assert assign_fo_res.status_code == 201

    # ------------------------------------------------------------------------
    # Step 4: Field Officer Submits Activity 1 (200 trees + Photo Evidence)
    # ------------------------------------------------------------------------
    fake_photo_bytes = b"\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xFF\xDB\x00C\x00"
    files = [
        ("evidence_files", ("sapling_batch_01.jpg", io.BytesIO(fake_photo_bytes), "image/jpeg"))
    ]
    data_1 = {
        "project_id": project_id,
        "metric_code": "TREES_PLANTED",
        "quantity": "200.00",
        "unit": "trees",
        "activity_date": "2026-11-01",
        "latitude": "11.4110",
        "longitude": "76.6960",
        "gps_accuracy_meters": "4.2",
        "field_notes": "First planting block: 200 native Syzygium saplings tagged.",
    }
    sub_1_res = await client.post(
        "/api/v1/operations/activities", data=data_1, files=files, headers=fo_headers
    )
    assert sub_1_res.status_code == 201, sub_1_res.text
    act_1_id = sub_1_res.json()["id"]
    rev_1_id = sub_1_res.json()["current_revision"]["id"]
    evidence_id = sub_1_res.json()["current_revision"]["evidence_files"][0]["id"]

    # ------------------------------------------------------------------------
    # Step 5: PM Verifies Activity 1
    # ------------------------------------------------------------------------
    verif_1_res = await client.post(
        f"/api/v1/verification/revisions/{rev_1_id}/decision",
        json={"decision": "VERIFIED"},
        headers=pm_headers,
    )
    assert verif_1_res.status_code == 200, verif_1_res.text

    # ------------------------------------------------------------------------
    # Step 6: Field Officer Submits Activity 2 (250 trees) & PM Verifies
    # ------------------------------------------------------------------------
    data_2 = {
        "project_id": project_id,
        "metric_code": "TREES_PLANTED",
        "quantity": "250.00",
        "unit": "trees",
        "activity_date": "2026-11-02",
        "latitude": "11.4115",
        "longitude": "76.6965",
        "gps_accuracy_meters": "3.8",
        "field_notes": "Second block: 250 Elaeocarpus saplings planted along riparian buffer.",
    }
    sub_2_res = await client.post(
        "/api/v1/operations/activities", data=data_2, headers=fo_headers
    )
    assert sub_2_res.status_code == 201
    rev_2_id = sub_2_res.json()["current_revision"]["id"]

    verif_2_res = await client.post(
        f"/api/v1/verification/revisions/{rev_2_id}/decision",
        json={"decision": "VERIFIED"},
        headers=pm_headers,
    )
    assert verif_2_res.status_code == 200

    # ------------------------------------------------------------------------
    # Step 7: Field Officer Submits Activity 3 (150 trees) & PM Verifies
    # ------------------------------------------------------------------------
    data_3 = {
        "project_id": project_id,
        "metric_code": "TREES_PLANTED",
        "quantity": "150.00",
        "unit": "trees",
        "activity_date": "2026-11-03",
        "latitude": "11.4120",
        "longitude": "76.6970",
        "gps_accuracy_meters": "5.0",
        "field_notes": "Third block: 150 Cinnamomum wightii planted.",
    }
    sub_3_res = await client.post(
        "/api/v1/operations/activities", data=data_3, headers=fo_headers
    )
    assert sub_3_res.status_code == 201
    act_3_id = sub_3_res.json()["id"]
    rev_3_id = sub_3_res.json()["current_revision"]["id"]

    verif_3_res = await client.post(
        f"/api/v1/verification/revisions/{rev_3_id}/decision",
        json={"decision": "VERIFIED"},
        headers=pm_headers,
    )
    assert verif_3_res.status_code == 200

    # ------------------------------------------------------------------------
    # Step 8: Reconcile Ledger — Verify 600/1,000 = 60.0% Achievement
    # ------------------------------------------------------------------------
    impact_res = await client.get(
        f"/api/v1/analytics/projects/{project_id}/impact", headers=pm_headers
    )
    assert impact_res.status_code == 200
    impact_data = impact_res.json()

    target_stat = impact_data["targets"][0]
    assert Decimal(str(target_stat["verified_quantity"])) == Decimal("600.00")
    assert Decimal(str(target_stat["target_quantity"])) == Decimal("1000.00")
    assert target_stat["achievement_percentage"] == 60.0
    assert Decimal(str(target_stat["remaining_quantity"])) == Decimal("400.00")
    assert Decimal(str(target_stat["net_pending_adjustment"])) == Decimal("0.00")
    assert impact_data["activities_summary"]["verified_active_revisions_count"] == 3
    assert impact_data["activities_summary"]["pending_revisions_count"] == 0

    # Verify PM and FO dashboard overview sees 60%
    pm_dash_res = await client.get("/api/v1/dashboard/overview", headers=pm_headers)
    assert pm_dash_res.status_code == 200
    trees_metric = next(
        m for m in pm_dash_res.json()["metric_achievements"] if m["metric_code"] == "TREES_PLANTED"
    )
    assert Decimal(str(trees_metric["total_verified_quantity"])) == Decimal("600.00")
    assert Decimal(str(trees_metric["total_target_quantity"])) == Decimal("1000.00")
    assert trees_metric["overall_achievement_percentage"] == 60.0

    # ------------------------------------------------------------------------
    # Step 9: Field Officer Submits Amendment (+50)
    # ------------------------------------------------------------------------
    amend_res = await client.post(
        f"/api/v1/operations/activities/{act_3_id}/revisions",
        data={
            "quantity": "200.00",  # Amended from 150 to 200 (+50)
            "activity_date": "2026-11-03",
            "amendment_reason": "GPS grid recount verified 50 additional trees planted on eastern slope.",
        },
        headers=fo_headers,
    )
    assert amend_res.status_code == 201

    # Verify Official Achievement strictly remains 600, with +50 pending adjustment
    impact_amended = (
        await client.get(f"/api/v1/analytics/projects/{project_id}/impact", headers=pm_headers)
    ).json()
    amended_target = impact_amended["targets"][0]
    assert Decimal(str(amended_target["verified_quantity"])) == Decimal("600.00")  # STRICTLY UNCHANGED
    assert amended_target["achievement_percentage"] == 60.0                       # STRICTLY UNCHANGED
    assert Decimal(str(amended_target["remaining_quantity"])) == Decimal("400.00")# STRICTLY UNCHANGED
    assert Decimal(str(amended_target["net_pending_adjustment"])) == Decimal("50.00")
    assert impact_amended["activities_summary"]["pending_revisions_count"] == 1

    # ------------------------------------------------------------------------
    # Step 10: Multi-Tenant RBAC Project Isolation
    # ------------------------------------------------------------------------
    # Create isolated second project (Aravalli Ridge)
    unassigned_proj_res = await client.post(
        "/api/v1/projects",
        json={
            "name": "Aravalli Ridge Conservation",
            "code": f"ARAV-{uuid.uuid4().hex[:6].upper()}",
            "description": "Arid zone afforestation",
            "latitude": 28.4595,
            "longitude": 77.0266,
        },
        headers=admin_headers,
    )
    unassigned_proj_id = unassigned_proj_res.json()["id"]

    # PM Kumar and FO Patel are NOT assigned to Aravalli Ridge
    # Attempting to access its impact analytics must return 403 Forbidden
    blocked_pm = await client.get(
        f"/api/v1/analytics/projects/{unassigned_proj_id}/impact", headers=pm_headers
    )
    assert blocked_pm.status_code == 403
    assert blocked_pm.json()["detail"]["error_code"] == "PROJECT_ACCESS_DENIED"

    blocked_fo = await client.get(
        f"/api/v1/analytics/projects/{unassigned_proj_id}/impact", headers=fo_headers
    )
    assert blocked_fo.status_code == 403
    assert blocked_fo.json()["detail"]["error_code"] == "PROJECT_ACCESS_DENIED"

    # Attempting to submit activity to unassigned project must return 403
    blocked_fo_sub = await client.post(
        "/api/v1/operations/activities",
        data={
            "project_id": unassigned_proj_id,
            "metric_code": "TREES_PLANTED",
            "quantity": "50.00",
            "unit": "trees",
            "activity_date": "2026-11-03",
        },
        headers=fo_headers,
    )
    assert blocked_fo_sub.status_code == 403

    # Unassigned user has 0 projects visible
    unassigned_overview = (
        await client.get("/api/v1/dashboard/overview", headers=unassigned_headers)
    ).json()
    assert unassigned_overview["total_projects"] == 0

    # ------------------------------------------------------------------------
    # Step 11: Evidence Storage Persistence & Streaming
    # ------------------------------------------------------------------------
    evidence_res = await client.get(
        f"/api/v1/operations/evidence/{evidence_id}", headers=pm_headers
    )
    assert evidence_res.status_code == 200
    assert evidence_res.headers["content-type"] == "image/jpeg"
    assert evidence_res.content == fake_photo_bytes

    # Unassigned user cannot access evidence
    unauth_ev = await client.get(
        f"/api/v1/operations/evidence/{evidence_id}", headers=unassigned_headers
    )
    assert unauth_ev.status_code == 403

    # ------------------------------------------------------------------------
    # Step 12: Health Check Probe
    # ------------------------------------------------------------------------
    health_res = await client.get("/health")
    assert health_res.status_code == 200
    health_json = health_res.json()
    assert health_json["status"] == "healthy"
    assert health_json["database"] == "connected"
    assert health_json["platform"] == "VANA"
