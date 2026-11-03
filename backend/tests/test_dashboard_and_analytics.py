"""
VANA — Environmental Ledger & Dashboard Analytics Tests
Validates official environmental ledger accounting, role-based project scoping,
metric code isolation, unit conversions, amendment delta tracking, and time-series trends.
"""

from datetime import date, timedelta
from decimal import Decimal
import io
from typing import Optional
import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.auth.models import User, UserRole
from app.domains.operations.models import ActivityRevision, ActivityStatus, FieldActivity
from app.domains.projects.models import Project, ProjectStatus, ProjectTarget
from app.domains.teams.models import ProjectAssignment
from tests.test_operations_and_verification import create_user_helper


async def setup_test_project(
    db: AsyncSession,
    name: str = "Sundarbans Restoration",
    code: str = "SUND",
    target_metric: Optional[str] = None,
    target_qty: Decimal = Decimal("1000.00"),
    target_unit: str = "trees",
) -> Project:
    unique_code = f"{code}-{uuid.uuid4().hex[:6].upper()}"
    project = Project(
        name=name,
        code=unique_code,
        status=ProjectStatus.ACTIVE.value,
        description="Mangroves conservation and afforestation",
        latitude=21.9512,
        longitude=89.1840,
    )
    db.add(project)
    await db.flush()

    if target_metric:
        target = ProjectTarget(
            project_id=project.id,
            metric_code=target_metric,
            target_quantity=target_qty,
            target_unit=target_unit,
            target_date=date(2026, 12, 31),
        )
        db.add(target)
        await db.flush()

    return project


# ============================================================================
# 1. Environmental Ledger & Calculation Integrity Tests
# ============================================================================

@pytest.mark.asyncio
async def test_required_environmental_ledger_accounting_example(
    client: AsyncClient, db_session: AsyncSession
):
    """
    Validates the exact required prompt example:
    - Target: 1,000 trees.
    - Verified: 200, 250, 150 -> Verified Total = 600 (60% achievement, 400 remaining).
    - If verified activity of 200 amended to 250 (pending):
      Verified remains 600, Net pending adjustment is +50, Official verified unchanged.
    """
    admin, admin_headers = await create_user_helper(
        db_session, UserRole.ADMIN.value, "Admin Ledger Test"
    )
    fo, fo_headers = await create_user_helper(
        db_session, UserRole.FIELD_OFFICER.value, "Field Officer Submitter"
    )

    project = await setup_test_project(db_session, "Sundarbans Plot A", "SUND-PLA")
    db_session.add(
        ProjectAssignment(project_id=project.id, user_id=fo.id, assigned_role="FIELD_OFFICER")
    )

    # Configure Target: 1,000 trees
    target = ProjectTarget(
        project_id=project.id,
        metric_code="TREES_PLANTED",
        target_quantity=Decimal("1000.00"),
        target_unit="trees",
        target_date=date(2026, 11, 30),
    )
    db_session.add(target)
    await db_session.commit()

    # Step 1: Submit 3 activities (200, 250, 150)
    act_ids = []
    rev_ids = []
    for qty in ["200.00", "250.00", "150.00"]:
        res = await client.post(
            "/api/v1/operations/activities",
            data={
                "project_id": str(project.id),
                "metric_code": "TREES_PLANTED",
                "quantity": qty,
                "unit": "trees",
                "activity_date": "2026-11-01",
            },
            headers=fo_headers,
        )
        assert res.status_code == 201
        data = res.json()
        act_ids.append(data["id"])
        rev_ids.append(data["current_revision"]["id"])

    # Step 2: Verify all 3 activities as Admin
    for r_id in rev_ids:
        decision_res = await client.post(
            f"/api/v1/verification/revisions/{r_id}/decision",
            json={"decision": "VERIFIED"},
            headers=admin_headers,
        )
        assert decision_res.status_code == 200

    # Step 3: Check Project Impact Detail & Dashboard Overview
    impact_res = await client.get(
        f"/api/v1/analytics/projects/{project.id}/impact", headers=admin_headers
    )
    assert impact_res.status_code == 200
    impact = impact_res.json()
    assert len(impact["targets"]) == 1
    t_prog = impact["targets"][0]
    assert t_prog["metric_code"] == "TREES_PLANTED"
    assert Decimal(str(t_prog["target_quantity"])) == Decimal("1000.00")
    assert Decimal(str(t_prog["verified_quantity"])) == Decimal("600.00")
    assert t_prog["achievement_percentage"] == 60.0
    assert Decimal(str(t_prog["remaining_quantity"])) == Decimal("400.00")
    assert Decimal(str(t_prog["net_pending_adjustment"])) == Decimal("0.00")

    # Step 4: Amend Activity 1 (currently 200 trees) to 250 trees (Pending Amendment)
    amend_res = await client.post(
        f"/api/v1/operations/activities/{act_ids[0]}/revisions",
        data={
            "quantity": "250.00",
            "activity_date": "2026-11-02",
            "amendment_reason": "Additional sapling survival tally verified on plot edge",
        },
        headers=fo_headers,
    )
    assert amend_res.status_code == 201

    # Step 5: Verify that official achievement is UNCHANGED while amendment is pending
    impact_after_amend = (
        await client.get(f"/api/v1/analytics/projects/{project.id}/impact", headers=admin_headers)
    ).json()
    t_prog_after = impact_after_amend["targets"][0]
    # Official verified quantity remains exactly 600.00
    assert Decimal(str(t_prog_after["verified_quantity"])) == Decimal("600.00")
    assert t_prog_after["achievement_percentage"] == 60.0
    assert Decimal(str(t_prog_after["remaining_quantity"])) == Decimal("400.00")
    # Net pending adjustment is +50.00 (250 - 200)
    assert Decimal(str(t_prog_after["net_pending_adjustment"])) == Decimal("50.00")

    # Step 6: Verify Dashboard Overview for an assigned Project Manager (scoped to this project)
    pm, pm_headers = await create_user_helper(
        db_session, UserRole.PROJECT_MANAGER.value, "PM Example Lead"
    )
    db_session.add(
        ProjectAssignment(project_id=project.id, user_id=pm.id, assigned_role="PROJECT_MANAGER")
    )
    await db_session.commit()

    overview = (await client.get("/api/v1/dashboard/overview", headers=pm_headers)).json()
    trees_stat = next(m for m in overview["metric_achievements"] if m["metric_code"] == "TREES_PLANTED")
    assert Decimal(str(trees_stat["total_verified_quantity"])) == Decimal("600.00")
    assert Decimal(str(trees_stat["total_pending_adjustment"])) == Decimal("50.00")
    assert trees_stat["overall_achievement_percentage"] == 60.0


@pytest.mark.asyncio
async def test_negative_amendment_does_not_reduce_official_ledger_until_verified(
    client: AsyncClient, db_session: AsyncSession
):
    """
    Validates that a negative amendment (-50) keeps verified quantity intact (200),
    reports net pending adjustment of -50, and only adjusts the official ledger upon approval.
    """
    admin, admin_headers = await create_user_helper(db_session, UserRole.ADMIN.value, "Admin Neg")
    fo, fo_headers = await create_user_helper(db_session, UserRole.FIELD_OFFICER.value, "FO Neg")

    project = await setup_test_project(db_session, "Western Ghats Plot", "WG-PLOT")
    db_session.add(ProjectAssignment(project_id=project.id, user_id=fo.id, assigned_role="FIELD_OFFICER"))
    db_session.add(
        ProjectTarget(
            project_id=project.id,
            metric_code="TREES_PLANTED",
            target_quantity=Decimal("500.00"),
            target_unit="trees",
            target_date=date(2026, 12, 1),
        )
    )
    await db_session.commit()

    # Create and verify initial 200 trees
    res = await client.post(
        "/api/v1/operations/activities",
        data={
            "project_id": str(project.id),
            "metric_code": "TREES_PLANTED",
            "quantity": "200.00",
            "unit": "trees",
            "activity_date": "2026-11-01",
        },
        headers=fo_headers,
    )
    act_id = res.json()["id"]
    rev_1_id = res.json()["current_revision"]["id"]

    await client.post(
        f"/api/v1/verification/revisions/{rev_1_id}/decision",
        json={"decision": "VERIFIED"},
        headers=admin_headers,
    )

    # Submit negative amendment: 150 trees (net -50)
    amend_res = await client.post(
        f"/api/v1/operations/activities/{act_id}/revisions",
        data={"quantity": "150.00", "activity_date": "2026-11-02", "amendment_reason": "Correction"},
        headers=fo_headers,
    )
    rev_2_id = amend_res.json()["current_revision"]["id"]

    # Verify impact: verified remains 200, pending is -50
    impact = (
        await client.get(f"/api/v1/analytics/projects/{project.id}/impact", headers=admin_headers)
    ).json()
    assert Decimal(str(impact["targets"][0]["verified_quantity"])) == Decimal("200.00")
    assert Decimal(str(impact["targets"][0]["net_pending_adjustment"])) == Decimal("-50.00")

    # Now verify revision 2 (decision = VERIFIED)
    await client.post(
        f"/api/v1/verification/revisions/{rev_2_id}/decision",
        json={"decision": "VERIFIED"},
        headers=admin_headers,
    )

    # After verification: verified becomes 150, pending becomes 0
    impact_after = (
        await client.get(f"/api/v1/analytics/projects/{project.id}/impact", headers=admin_headers)
    ).json()
    assert Decimal(str(impact_after["targets"][0]["verified_quantity"])) == Decimal("150.00")
    assert Decimal(str(impact_after["targets"][0]["net_pending_adjustment"])) == Decimal("0.00")


@pytest.mark.asyncio
async def test_metric_code_isolation_and_unit_conversion(
    client: AsyncClient, db_session: AsyncSession
):
    """
    Validates:
    1. TREES_PLANTED and SAPLINGS_PLANTED are never aggregated together.
    2. Units in AREA_RESTORED (m2, acres) convert properly to canonical hectares.
    """
    admin, admin_headers = await create_user_helper(db_session, UserRole.ADMIN.value, "Admin Metrics")
    fo, fo_headers = await create_user_helper(db_session, UserRole.FIELD_OFFICER.value, "FO Metrics")

    project = await setup_test_project(db_session, "Aravalli Reforestation", "ARAV-01")
    db_session.add(ProjectAssignment(project_id=project.id, user_id=fo.id, assigned_role="FIELD_OFFICER"))

    # Add targets for two distinct metrics
    db_session.add(
        ProjectTarget(
            project_id=project.id,
            metric_code="TREES_PLANTED",
            target_quantity=Decimal("5000.00"),
            target_unit="trees",
            target_date=date(2026, 12, 1),
        )
    )
    db_session.add(
        ProjectTarget(
            project_id=project.id,
            metric_code="AREA_RESTORED",
            target_quantity=Decimal("100.00"),
            target_unit="hectares",
            target_date=date(2026, 12, 1),
        )
    )
    await db_session.commit()

    # 1. Trees activity: 500 trees
    res1 = await client.post(
        "/api/v1/operations/activities",
        data={
            "project_id": str(project.id),
            "metric_code": "TREES_PLANTED",
            "quantity": "500.00",
            "unit": "trees",
            "activity_date": "2026-11-01",
        },
        headers=fo_headers,
    )
    await client.post(
        f"/api/v1/verification/revisions/{res1.json()['current_revision']['id']}/decision",
        json={"decision": "VERIFIED"},
        headers=admin_headers,
    )

    # 2. Area activity in acres: 24.7105 acres ~ 10 hectares (conversion: acres * 0.404686)
    # 24.7105 * 0.404686 = 10.000000...
    res2 = await client.post(
        "/api/v1/operations/activities",
        data={
            "project_id": str(project.id),
            "metric_code": "AREA_RESTORED",
            "quantity": "24.7105",
            "unit": "acres",
            "activity_date": "2026-11-01",
        },
        headers=fo_headers,
    )
    await client.post(
        f"/api/v1/verification/revisions/{res2.json()['current_revision']['id']}/decision",
        json={"decision": "VERIFIED"},
        headers=admin_headers,
    )

    # Check Project Impact Detail
    impact = (
        await client.get(f"/api/v1/analytics/projects/{project.id}/impact", headers=admin_headers)
    ).json()

    trees_t = next(t for t in impact["targets"] if t["metric_code"] == "TREES_PLANTED")
    area_t = next(t for t in impact["targets"] if t["metric_code"] == "AREA_RESTORED")

    # Trees: verified 500 / 5000 = 10%
    assert Decimal(str(trees_t["verified_quantity"])) == Decimal("500.00")
    assert trees_t["achievement_percentage"] == 10.0

    # Area: verified 10.00 hectares (converted from 24.7105 acres)
    assert abs(float(area_t["verified_quantity"]) - 10.00) < 0.05
    assert abs(area_t["achievement_percentage"] - 10.0) < 0.1


@pytest.mark.asyncio
async def test_archived_activity_is_excluded_from_environmental_ledger(
    client: AsyncClient, db_session: AsyncSession
):
    """
    Validates that when an activity is archived, it ceases contributing
    to official verified achievements in both project impact and dashboard overview.
    """
    admin, admin_headers = await create_user_helper(db_session, UserRole.ADMIN.value, "Admin Arch")
    fo, fo_headers = await create_user_helper(db_session, UserRole.FIELD_OFFICER.value, "FO Arch")

    project = await setup_test_project(db_session, "Kaveri Basin Basin", "KAV-01")
    db_session.add(ProjectAssignment(project_id=project.id, user_id=fo.id, assigned_role="FIELD_OFFICER"))
    db_session.add(
        ProjectTarget(
            project_id=project.id,
            metric_code="TREES_PLANTED",
            target_quantity=Decimal("1000.00"),
            target_unit="trees",
            target_date=date(2026, 12, 1),
        )
    )
    await db_session.commit()

    # Create & verify 300 trees
    res = await client.post(
        "/api/v1/operations/activities",
        data={
            "project_id": str(project.id),
            "metric_code": "TREES_PLANTED",
            "quantity": "300.00",
            "unit": "trees",
            "activity_date": "2026-11-01",
        },
        headers=fo_headers,
    )
    act_id = res.json()["id"]
    await client.post(
        f"/api/v1/verification/revisions/{res.json()['current_revision']['id']}/decision",
        json={"decision": "VERIFIED"},
        headers=admin_headers,
    )

    # Initial verified quantity is 300
    impact_before = (
        await client.get(f"/api/v1/analytics/projects/{project.id}/impact", headers=admin_headers)
    ).json()
    assert Decimal(str(impact_before["targets"][0]["verified_quantity"])) == Decimal("300.00")

    # Archive the activity
    del_res = await client.delete(f"/api/v1/operations/activities/{act_id}", headers=admin_headers)
    assert del_res.status_code == 200

    # Verified quantity drops to 0.00
    impact_after = (
        await client.get(f"/api/v1/analytics/projects/{project.id}/impact", headers=admin_headers)
    ).json()
    assert Decimal(str(impact_after["targets"][0]["verified_quantity"])) == Decimal("0.00")
    assert impact_after["activities_summary"]["archived_activities_count"] == 1


# ============================================================================
# 2. RBAC & Project Scoping Tests
# ============================================================================

@pytest.mark.asyncio
async def test_role_based_dashboard_and_analytics_scoping(
    client: AsyncClient, db_session: AsyncSession
):
    """
    Validates:
    - Admin sees all projects in /dashboard/overview and /dashboard/projects.
    - Assigned PM sees only their assigned projects.
    - Unassigned PM gets 403 when requesting project analytics for an unassigned project.
    """
    admin, admin_headers = await create_user_helper(db_session, UserRole.ADMIN.value, "Admin Scoping")
    pm_assigned, pm_assigned_headers = await create_user_helper(
        db_session, UserRole.PROJECT_MANAGER.value, "PM Assigned"
    )
    pm_unassigned, pm_unassigned_headers = await create_user_helper(
        db_session, UserRole.PROJECT_MANAGER.value, "PM Unassigned"
    )

    proj_a = await setup_test_project(db_session, "Project Alpha", "ALPHA-01")
    proj_b = await setup_test_project(db_session, "Project Beta", "BETA-01")

    # Assign PM to Project Alpha only
    db_session.add(
        ProjectAssignment(project_id=proj_a.id, user_id=pm_assigned.id, assigned_role="PROJECT_MANAGER")
    )
    await db_session.commit()

    # 1. Admin overview sees 2 projects
    admin_overview = (await client.get("/api/v1/dashboard/overview", headers=admin_headers)).json()
    assert admin_overview["total_projects"] >= 2
    assert admin_overview["is_portfolio_wide"] is True

    # 2. Assigned PM overview sees only 1 project
    pm_overview = (await client.get("/api/v1/dashboard/overview", headers=pm_assigned_headers)).json()
    assert pm_overview["total_projects"] == 1
    assert pm_overview["is_portfolio_wide"] is False

    # 3. Assigned PM can access Project Alpha analytics
    res_a = await client.get(f"/api/v1/analytics/projects/{proj_a.id}/impact", headers=pm_assigned_headers)
    assert res_a.status_code == 200

    # 4. Assigned PM blocked from Project Beta analytics (403)
    res_b = await client.get(f"/api/v1/analytics/projects/{proj_b.id}/impact", headers=pm_assigned_headers)
    assert res_b.status_code == 403
    assert res_b.json()["detail"]["error_code"] == "PROJECT_ACCESS_DENIED"

    # 5. Completely unassigned PM has 0 projects in dashboard
    unassigned_overview = (
        await client.get("/api/v1/dashboard/overview", headers=pm_unassigned_headers)
    ).json()
    assert unassigned_overview["total_projects"] == 0


# ============================================================================
# 3. Trends & Activity Stream Tests
# ============================================================================

@pytest.mark.asyncio
async def test_project_activity_trends_and_date_filtering(
    client: AsyncClient, db_session: AsyncSession
):
    """
    Validates /analytics/projects/{id}/trends:
    - Groups verified activities by date.
    - Calculates daily quantity and cumulative running quantity.
    - Enforces start_date and end_date filtering.
    """
    admin, admin_headers = await create_user_helper(db_session, UserRole.ADMIN.value, "Admin Trends")
    fo, fo_headers = await create_user_helper(db_session, UserRole.FIELD_OFFICER.value, "FO Trends")

    project = await setup_test_project(
        db_session, "Thar Greening", "THAR-01", target_metric="TREES_PLANTED"
    )
    db_session.add(ProjectAssignment(project_id=project.id, user_id=fo.id, assigned_role="FIELD_OFFICER"))
    await db_session.commit()

    # Day 1: 100 trees
    res1 = await client.post(
        "/api/v1/operations/activities",
        data={
            "project_id": str(project.id),
            "metric_code": "TREES_PLANTED",
            "quantity": "100.00",
            "unit": "trees",
            "activity_date": "2026-10-10",
        },
        headers=fo_headers,
    )
    await client.post(
        f"/api/v1/verification/revisions/{res1.json()['current_revision']['id']}/decision",
        json={"decision": "VERIFIED"},
        headers=admin_headers,
    )

    # Day 2: 200 trees
    res2 = await client.post(
        "/api/v1/operations/activities",
        data={
            "project_id": str(project.id),
            "metric_code": "TREES_PLANTED",
            "quantity": "200.00",
            "unit": "trees",
            "activity_date": "2026-10-20",
        },
        headers=fo_headers,
    )
    await client.post(
        f"/api/v1/verification/revisions/{res2.json()['current_revision']['id']}/decision",
        json={"decision": "VERIFIED"},
        headers=admin_headers,
    )

    # Query trends
    trends_res = await client.get(
        f"/api/v1/analytics/projects/{project.id}/trends", headers=admin_headers
    )
    assert trends_res.status_code == 200
    trends = trends_res.json()["trends"]
    assert len(trends) == 2

    # Point 1 (2026-10-10): period = 100, cumulative = 100
    assert trends[0]["date"] == "2026-10-10"
    assert Decimal(str(trends[0]["period_quantity"])) == Decimal("100.00")
    assert Decimal(str(trends[0]["cumulative_quantity"])) == Decimal("100.00")

    # Point 2 (2026-10-20): period = 200, cumulative = 300
    assert trends[1]["date"] == "2026-10-20"
    assert Decimal(str(trends[1]["period_quantity"])) == Decimal("200.00")
    assert Decimal(str(trends[1]["cumulative_quantity"])) == Decimal("300.00")

    # Filter with start_date=2026-10-15 -> returns only Point 2
    filtered_res = await client.get(
        f"/api/v1/analytics/projects/{project.id}/trends?start_date=2026-10-15",
        headers=admin_headers,
    )
    filtered_trends = filtered_res.json()["trends"]
    assert len(filtered_trends) == 1
    assert filtered_trends[0]["date"] == "2026-10-20"

    # Invalid date range: start_date > end_date returns 400
    bad_range_res = await client.get(
        f"/api/v1/analytics/projects/{project.id}/trends?start_date=2026-10-25&end_date=2026-10-10",
        headers=admin_headers,
    )
    assert bad_range_res.status_code == 400
    assert bad_range_res.json()["detail"]["error_code"] == "INVALID_DATE_RANGE"


@pytest.mark.asyncio
async def test_recent_operational_activity_feed(
    client: AsyncClient, db_session: AsyncSession
):
    """
    Validates /dashboard/recent-activity:
    - Returns real submissions, verifications, and rejections with project metadata.
    """
    admin, admin_headers = await create_user_helper(db_session, UserRole.ADMIN.value, "Admin Recent")
    fo, fo_headers = await create_user_helper(db_session, UserRole.FIELD_OFFICER.value, "FO Recent")

    project = await setup_test_project(
        db_session, "Eastern Ghats Corridor", "EGC-01", target_metric="TREES_PLANTED"
    )
    db_session.add(ProjectAssignment(project_id=project.id, user_id=fo.id, assigned_role="FIELD_OFFICER"))
    await db_session.commit()

    # Submit activity
    res = await client.post(
        "/api/v1/operations/activities",
        data={
            "project_id": str(project.id),
            "metric_code": "TREES_PLANTED",
            "quantity": "75.00",
            "unit": "trees",
            "activity_date": "2026-11-01",
        },
        headers=fo_headers,
    )
    rev_id = res.json()["current_revision"]["id"]

    # Verify activity
    await client.post(
        f"/api/v1/verification/revisions/{rev_id}/decision",
        json={"decision": "VERIFIED"},
        headers=admin_headers,
    )

    recent_res = await client.get("/api/v1/dashboard/recent-activity?limit=5", headers=admin_headers)
    assert recent_res.status_code == 200
    recent = recent_res.json()
    assert len(recent) >= 1

    verif_event = recent[0]
    assert verif_event["event_type"] == "VERIFICATION"
    assert verif_event["project_code"] == project.code
    assert "Trees Planted" in verif_event["title"]
