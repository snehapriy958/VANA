"""
VANA — Milestone 3 Integration & Unit Tests
Tests project portfolio, role authorization, team assignments, geographic boundaries,
environmental targets, metric catalog validation, duplicate prevention, and audit logging.
"""

import uuid
from decimal import Decimal
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.domains.audit.models import AuditLog
from app.domains.auth.models import User, UserRole
from app.domains.projects.models import Project, ProjectStatus, ProjectTarget
from app.domains.teams.models import ProjectAssignment


async def create_user_helper(
    db: AsyncSession,
    role: str = UserRole.FIELD_OFFICER.value,
    full_name: str = "Test User",
    is_active: bool = True,
) -> tuple[User, dict]:
    user = User(
        id=uuid.uuid4(),
        email=f"user_{uuid.uuid4().hex[:6]}@vana.org",
        hashed_password=hash_password("SecurePass123!"),
        full_name=full_name,
        role=role,
        is_active=is_active,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    token = create_access_token(subject=str(user.id), role=user.role, email=user.email)
    return user, {"Authorization": f"Bearer {token}"}


# ============================================================================
# 1. Project Management CRUD & Coordinate Validation Tests
# ============================================================================

@pytest.mark.asyncio
async def test_admin_can_create_project(client: AsyncClient, db_session: AsyncSession):
    _, headers = await create_user_helper(db_session, role=UserRole.ADMIN.value, full_name="Admin Director")
    payload = {
        "name": "Sundarbans Mangrove Conservation",
        "code": f"VANA-SUNDAR-{uuid.uuid4().hex[:4].upper()}",
        "description": "Restoration of coastal mangrove delta buffer zones.",
        "status": "ACTIVE",
        "latitude": 21.9497,
        "longitude": 89.1833,
    }
    res = await client.post("/api/v1/projects", json=payload, headers=headers)
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == payload["name"]
    assert data["code"] == payload["code"]
    assert data["latitude"] == 21.9497
    assert data["longitude"] == 89.1833
    assert data["status"] == "ACTIVE"


@pytest.mark.asyncio
async def test_non_admin_cannot_create_project(client: AsyncClient, db_session: AsyncSession):
    _, pm_headers = await create_user_helper(db_session, role=UserRole.PROJECT_MANAGER.value)
    _, fo_headers = await create_user_helper(db_session, role=UserRole.FIELD_OFFICER.value)

    for headers in [pm_headers, fo_headers]:
        payload = {
            "name": "Unauthorized Project",
            "latitude": 12.9716,
            "longitude": 77.5946,
        }
        res = await client.post("/api/v1/projects", json=payload, headers=headers)
        assert res.status_code == 403
        assert res.json()["detail"]["error_code"] == "INSUFFICIENT_ROLE"


@pytest.mark.asyncio
async def test_project_coordinate_validation(client: AsyncClient, db_session: AsyncSession):
    _, headers = await create_user_helper(db_session, role=UserRole.ADMIN.value)

    # Invalid Latitude > 90
    res = await client.post(
        "/api/v1/projects",
        json={"name": "Bad Lat", "latitude": 91.5, "longitude": 80.0},
        headers=headers,
    )
    assert res.status_code == 422

    # Invalid Longitude < -180
    res = await client.post(
        "/api/v1/projects",
        json={"name": "Bad Lng", "latitude": 20.0, "longitude": -185.0},
        headers=headers,
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_duplicate_project_code_rejected(client: AsyncClient, db_session: AsyncSession):
    _, headers = await create_user_helper(db_session, role=UserRole.ADMIN.value)
    code = f"VANA-DUP-{uuid.uuid4().hex[:4].upper()}"

    res1 = await client.post(
        "/api/v1/projects",
        json={"name": "Project Alpha", "code": code, "latitude": 10.0, "longitude": 70.0},
        headers=headers,
    )
    assert res1.status_code == 201

    res2 = await client.post(
        "/api/v1/projects",
        json={"name": "Project Beta", "code": code, "latitude": 11.0, "longitude": 71.0},
        headers=headers,
    )
    assert res2.status_code == 409
    assert res2.json()["detail"]["error_code"] == "PROJECT_CODE_ALREADY_EXISTS"


# ============================================================================
# 2. GeoJSON Boundary Polygon Validation Tests
# ============================================================================

@pytest.mark.asyncio
async def test_valid_geojson_polygon_boundary(client: AsyncClient, db_session: AsyncSession):
    _, headers = await create_user_helper(db_session, role=UserRole.ADMIN.value)
    valid_polygon = {
        "type": "Polygon",
        "coordinates": [
            [
                [89.180, 21.940],
                [89.190, 21.940],
                [89.190, 21.950],
                [89.180, 21.950],
                [89.180, 21.940],  # Closed ring
            ]
        ],
    }
    res = await client.post(
        "/api/v1/projects",
        json={
            "name": "Mangrove Polygon Project",
            "latitude": 21.945,
            "longitude": 89.185,
            "boundary_geojson": valid_polygon,
        },
        headers=headers,
    )
    assert res.status_code == 201
    data = res.json()
    assert data["boundary_geojson"]["type"] == "Polygon"


@pytest.mark.asyncio
async def test_unclosed_geojson_polygon_rejected(client: AsyncClient, db_session: AsyncSession):
    _, headers = await create_user_helper(db_session, role=UserRole.ADMIN.value)
    unclosed_polygon = {
        "type": "Polygon",
        "coordinates": [
            [
                [89.180, 21.940],
                [89.190, 21.940],
                [89.190, 21.950],
                [89.180, 21.950],  # Missing closing point
            ]
        ],
    }
    res = await client.post(
        "/api/v1/projects",
        json={
            "name": "Bad Polygon",
            "latitude": 21.945,
            "longitude": 89.185,
            "boundary_geojson": unclosed_polygon,
        },
        headers=headers,
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_polygon_with_fewer_than_4_points_rejected(client: AsyncClient, db_session: AsyncSession):
    _, headers = await create_user_helper(db_session, role=UserRole.ADMIN.value)
    triangle_unclosed = {
        "type": "Polygon",
        "coordinates": [
            [
                [89.180, 21.940],
                [89.190, 21.940],
                [89.180, 21.940],
            ]
        ],
    }
    res = await client.post(
        "/api/v1/projects",
        json={
            "name": "Too Few Vertices",
            "latitude": 21.945,
            "longitude": 89.185,
            "boundary_geojson": triangle_unclosed,
        },
        headers=headers,
    )
    assert res.status_code == 422


# ============================================================================
# 3. Status Transitions & Project Updates Tests
# ============================================================================

@pytest.mark.asyncio
async def test_project_status_transitions(client: AsyncClient, db_session: AsyncSession):
    _, headers = await create_user_helper(db_session, role=UserRole.ADMIN.value)

    # Create as ACTIVE
    res = await client.post(
        "/api/v1/projects",
        json={"name": "Transition Test Project", "latitude": 20.0, "longitude": 80.0, "status": "ACTIVE"},
        headers=headers,
    )
    project_id = res.json()["id"]

    # Valid transition: ACTIVE -> COMPLETED
    update_res = await client.put(
        f"/api/v1/projects/{project_id}",
        json={"status": "COMPLETED"},
        headers=headers,
    )
    assert update_res.status_code == 200
    assert update_res.json()["status"] == "COMPLETED"

    # Invalid transition: COMPLETED -> DRAFT
    bad_transition = await client.put(
        f"/api/v1/projects/{project_id}",
        json={"status": "DRAFT"},
        headers=headers,
    )
    assert bad_transition.status_code == 400
    assert bad_transition.json()["detail"]["error_code"] == "INVALID_STATUS_TRANSITION"


# ============================================================================
# 4. Project Listing & Scoping Tests
# ============================================================================

@pytest.mark.asyncio
async def test_project_listing_scoping(client: AsyncClient, db_session: AsyncSession):
    _, admin_hdr = await create_user_helper(db_session, role=UserRole.ADMIN.value)
    pm_user, pm_hdr = await create_user_helper(db_session, role=UserRole.PROJECT_MANAGER.value)
    fo_user, fo_hdr = await create_user_helper(db_session, role=UserRole.FIELD_OFFICER.value)

    # Create 2 projects as Admin
    p1 = (await client.post(
        "/api/v1/projects",
        json={"name": f"Project Scope 1 {uuid.uuid4().hex[:4]}", "latitude": 20.0, "longitude": 80.0},
        headers=admin_hdr,
    )).json()

    p2 = (await client.post(
        "/api/v1/projects",
        json={"name": f"Project Scope 2 {uuid.uuid4().hex[:4]}", "latitude": 21.0, "longitude": 81.0},
        headers=admin_hdr,
    )).json()

    # Assign PM to p1 only
    await client.post(
        f"/api/v1/projects/{p1['id']}/assignments",
        json={"user_id": str(pm_user.id), "assigned_role": "PROJECT_MANAGER"},
        headers=admin_hdr,
    )

    # Admin lists all projects
    admin_list = (await client.get("/api/v1/projects", headers=admin_hdr)).json()
    admin_ids = [p["id"] for p in admin_list]
    assert p1["id"] in admin_ids
    assert p2["id"] in admin_ids

    # PM lists projects: sees only p1, NOT p2
    pm_list = (await client.get("/api/v1/projects", headers=pm_hdr)).json()
    pm_ids = [p["id"] for p in pm_list]
    assert p1["id"] in pm_ids
    assert p2["id"] not in pm_ids

    # Field Officer is not assigned to either yet -> sees 0 projects
    fo_list = (await client.get("/api/v1/projects", headers=fo_hdr)).json()
    fo_ids = [p["id"] for p in fo_list]
    assert p1["id"] not in fo_ids
    assert p2["id"] not in fo_ids


# ============================================================================
# 5. Project Team Assignment Tests
# ============================================================================

@pytest.mark.asyncio
async def test_assignment_workflow_and_rejections(client: AsyncClient, db_session: AsyncSession):
    admin_user, admin_hdr = await create_user_helper(db_session, role=UserRole.ADMIN.value)
    pm_user, pm_hdr = await create_user_helper(db_session, role=UserRole.PROJECT_MANAGER.value)
    fo_user, fo_hdr = await create_user_helper(db_session, role=UserRole.FIELD_OFFICER.value)

    # Create Project
    proj = (await client.post(
        "/api/v1/projects",
        json={"name": "Assignment Workflow Proj", "latitude": 22.0, "longitude": 82.0},
        headers=admin_hdr,
    )).json()

    # Admin assigns PM
    assign_pm = await client.post(
        f"/api/v1/projects/{proj['id']}/assignments",
        json={"user_id": str(pm_user.id), "assigned_role": "PROJECT_MANAGER"},
        headers=admin_hdr,
    )
    assert assign_pm.status_code == 201

    # Assigned PM can now assign Field Officer
    assign_fo = await client.post(
        f"/api/v1/projects/{proj['id']}/assignments",
        json={"user_id": str(fo_user.id), "assigned_role": "FIELD_OFFICER"},
        headers=pm_hdr,
    )
    assert assign_fo.status_code == 201

    # Duplicate assignment rejected
    dup_assign = await client.post(
        f"/api/v1/projects/{proj['id']}/assignments",
        json={"user_id": str(fo_user.id), "assigned_role": "FIELD_OFFICER"},
        headers=pm_hdr,
    )
    assert dup_assign.status_code == 409
    assert dup_assign.json()["detail"]["error_code"] == "DUPLICATE_PROJECT_ASSIGNMENT"

    # Field Officer cannot assign team members
    fo_forbidden = await client.post(
        f"/api/v1/projects/{proj['id']}/assignments",
        json={"user_id": str(admin_user.id), "assigned_role": "FIELD_OFFICER"},
        headers=fo_hdr,
    )
    assert fo_forbidden.status_code == 403

    # Inactive user assignment rejection
    inactive_user, _ = await create_user_helper(db_session, role=UserRole.FIELD_OFFICER.value, is_active=False)
    inactive_assign = await client.post(
        f"/api/v1/projects/{proj['id']}/assignments",
        json={"user_id": str(inactive_user.id), "assigned_role": "FIELD_OFFICER"},
        headers=admin_hdr,
    )
    assert inactive_assign.status_code == 400
    assert inactive_assign.json()["detail"]["error_code"] == "INACTIVE_USER_ASSIGNMENT_PROHIBITED"


# ============================================================================
# 6. Environmental Target Tests & Metric Catalog Validation
# ============================================================================

@pytest.mark.asyncio
async def test_target_creation_and_catalog_validation(client: AsyncClient, db_session: AsyncSession):
    _, admin_hdr = await create_user_helper(db_session, role=UserRole.ADMIN.value)
    pm_user, pm_hdr = await create_user_helper(db_session, role=UserRole.PROJECT_MANAGER.value)
    _, fo_hdr = await create_user_helper(db_session, role=UserRole.FIELD_OFFICER.value)

    proj = (await client.post(
        "/api/v1/projects",
        json={"name": "Target Validation Proj", "latitude": 23.0, "longitude": 83.0},
        headers=admin_hdr,
    )).json()

    # Assign PM
    await client.post(
        f"/api/v1/projects/{proj['id']}/assignments",
        json={"user_id": str(pm_user.id), "assigned_role": "PROJECT_MANAGER"},
        headers=admin_hdr,
    )

    # 1. Valid Target Creation by PM
    target_payload = {
        "metric_code": "TREES_PLANTED",
        "target_quantity": 50000.0,
        "target_unit": "trees",
        "target_date": "2027-12-31",
    }
    res = await client.post(
        f"/api/v1/projects/{proj['id']}/targets",
        json=target_payload,
        headers=pm_hdr,
    )
    assert res.status_code == 201
    data = res.json()
    assert data["metric_code"] == "TREES_PLANTED"
    assert data["display_name"] == "Trees Planted"
    assert data["category"] == "VEGETATION_PLANTING"
    assert data["dimension"] == "COUNT"
    assert float(data["target_quantity"]) == 50000.0

    # 2. Duplicate Target for same metric_code is rejected
    dup_target = await client.post(
        f"/api/v1/projects/{proj['id']}/targets",
        json=target_payload,
        headers=pm_hdr,
    )
    assert dup_target.status_code == 409
    assert dup_target.json()["detail"]["error_code"] == "DUPLICATE_PROJECT_TARGET"

    # 3. Invalid Metric Code rejected
    bad_metric = await client.post(
        f"/api/v1/projects/{proj['id']}/targets",
        json={
            "metric_code": "INVALID_CARBON_CREDITS",
            "target_quantity": 100.0,
            "target_unit": "credits",
            "target_date": "2027-12-31",
        },
        headers=pm_hdr,
    )
    assert bad_metric.status_code == 422

    # 4. Incompatible Unit for valid metric code rejected
    bad_unit = await client.post(
        f"/api/v1/projects/{proj['id']}/targets",
        json={
            "metric_code": "TREES_PLANTED",
            "target_quantity": 100.0,
            "target_unit": "liters",  # Trees cannot be measured in liters!
            "target_date": "2027-12-31",
        },
        headers=pm_hdr,
    )
    assert bad_unit.status_code == 422

    # 5. Non-positive target quantity rejected
    zero_qty = await client.post(
        f"/api/v1/projects/{proj['id']}/targets",
        json={
            "metric_code": "AREA_RESTORED",
            "target_quantity": 0.0,
            "target_unit": "hectares",
            "target_date": "2027-12-31",
        },
        headers=pm_hdr,
    )
    assert zero_qty.status_code == 422

    # 6. Field Officer cannot create targets
    fo_forbidden = await client.post(
        f"/api/v1/projects/{proj['id']}/targets",
        json={
            "metric_code": "AREA_RESTORED",
            "target_quantity": 10.0,
            "target_unit": "hectares",
            "target_date": "2027-12-31",
        },
        headers=fo_hdr,
    )
    assert fo_forbidden.status_code == 403


@pytest.mark.asyncio
async def test_metrics_catalog_endpoint(client: AsyncClient, db_session: AsyncSession):
    _, headers = await create_user_helper(db_session, role=UserRole.ADMIN.value)
    res = await client.get("/api/v1/metrics/catalog", headers=headers)
    assert res.status_code == 200
    catalog = res.json()
    assert len(catalog) >= 7
    codes = [m["metric_code"] for m in catalog]
    assert "TREES_PLANTED" in codes
    assert "AREA_RESTORED" in codes
    assert "RAINWATER_HARVESTED" in codes
    assert "WASTE_REMOVED" in codes


# ============================================================================
# 7. Audit Logging Verification for Project, Target & Assignment Mutations
# ============================================================================

@pytest.mark.asyncio
async def test_audit_logging_for_project_and_target_mutations(client: AsyncClient, db_session: AsyncSession):
    admin_user, admin_hdr = await create_user_helper(db_session, role=UserRole.ADMIN.value)

    # Create project
    proj = (await client.post(
        "/api/v1/projects",
        json={"name": "Audit Tracked Proj", "latitude": 24.0, "longitude": 84.0},
        headers=admin_hdr,
    )).json()
    project_id = proj["id"]

    # Update project status
    await client.put(
        f"/api/v1/projects/{project_id}",
        json={"status": "COMPLETED"},
        headers=admin_hdr,
    )

    # Create target
    target = (await client.post(
        f"/api/v1/projects/{project_id}/targets",
        json={
            "metric_code": "AREA_RESTORED",
            "target_quantity": 25.0,
            "target_unit": "hectares",
            "target_date": "2028-06-30",
        },
        headers=admin_hdr,
    )).json()

    # Delete target
    await client.delete(
        f"/api/v1/projects/{project_id}/targets/{target['id']}",
        headers=admin_hdr,
    )

    # Query audit logs directly
    logs = list((await db_session.scalars(
        select(AuditLog).where(AuditLog.actor_id == admin_user.id)
    )).all())

    actions = [l.action_type for l in logs]
    assert "PROJECT_CREATED" in actions
    assert "PROJECT_UPDATED" in actions
    assert "PROJECT_STATUS_CHANGED" in actions
    assert "TARGET_CREATED" in actions
    assert "TARGET_DELETED" in actions


# ============================================================================
# 8. Milestone 3 Audit Regression Tests
# ============================================================================

@pytest.mark.asyncio
async def test_assignment_does_not_modify_or_elevate_global_user_role(client: AsyncClient, db_session: AsyncSession):
    """
    Verifies that assigning a user to a project roster does NOT alter their
    global user role in the users table, and does not elevate global permissions.
    """
    admin_user, admin_hdr = await create_user_helper(db_session, role=UserRole.ADMIN.value)
    fo_user, fo_hdr = await create_user_helper(db_session, role=UserRole.FIELD_OFFICER.value, full_name="Field Officer Jane")

    # Create Project
    proj = (await client.post(
        "/api/v1/projects",
        json={"name": "Role Separation Proj", "latitude": 25.0, "longitude": 85.0},
        headers=admin_hdr,
    )).json()

    # Assign FO as PROJECT_MANAGER within this project
    assign_res = await client.post(
        f"/api/v1/projects/{proj['id']}/assignments",
        json={"user_id": str(fo_user.id), "assigned_role": "PROJECT_MANAGER"},
        headers=admin_hdr,
    )
    assert assign_res.status_code == 201

    # Verify global user.role in database is STILL FIELD_OFFICER
    await db_session.refresh(fo_user)
    assert fo_user.role == UserRole.FIELD_OFFICER.value

    # Verify user still cannot perform global Admin actions (e.g. creating projects)
    forbidden_create = await client.post(
        "/api/v1/projects",
        json={"name": "Illegal Project", "latitude": 20.0, "longitude": 80.0},
        headers=fo_hdr,
    )
    assert forbidden_create.status_code == 403

    # Remove assignment
    remove_res = await client.delete(
        f"/api/v1/projects/{proj['id']}/assignments/{fo_user.id}",
        headers=admin_hdr,
    )
    assert remove_res.status_code == 204

    # Verify global user.role in database is STILL FIELD_OFFICER
    await db_session.refresh(fo_user)
    assert fo_user.role == UserRole.FIELD_OFFICER.value


@pytest.mark.asyncio
async def test_cross_project_isolation_for_assigned_pm(client: AsyncClient, db_session: AsyncSession):
    """
    Verifies that a Project Manager assigned to Project A cannot view,
    modify, or manage targets/assignments on Project B.
    """
    _, admin_hdr = await create_user_helper(db_session, role=UserRole.ADMIN.value)
    pm_user, pm_hdr = await create_user_helper(db_session, role=UserRole.PROJECT_MANAGER.value)

    # Admin creates Project A and Project B
    proj_a = (await client.post(
        "/api/v1/projects",
        json={"name": "Project A Alpha", "latitude": 20.0, "longitude": 80.0},
        headers=admin_hdr,
    )).json()

    proj_b = (await client.post(
        "/api/v1/projects",
        json={"name": "Project B Beta", "latitude": 21.0, "longitude": 81.0},
        headers=admin_hdr,
    )).json()

    # Assign PM to Project A only
    await client.post(
        f"/api/v1/projects/{proj_a['id']}/assignments",
        json={"user_id": str(pm_user.id), "assigned_role": "PROJECT_MANAGER"},
        headers=admin_hdr,
    )

    # PM CAN access Project A
    res_a = await client.get(f"/api/v1/projects/{proj_a['id']}", headers=pm_hdr)
    assert res_a.status_code == 200

    # PM CANNOT access Project B
    res_b = await client.get(f"/api/v1/projects/{proj_b['id']}", headers=pm_hdr)
    assert res_b.status_code == 403

    # PM CANNOT update Project B
    update_b = await client.put(
        f"/api/v1/projects/{proj_b['id']}",
        json={"name": "Hijacked Project B"},
        headers=pm_hdr,
    )
    assert update_b.status_code == 403

    # PM CANNOT create target on Project B
    target_b = await client.post(
        f"/api/v1/projects/{proj_b['id']}/targets",
        json={"metric_code": "TREES_PLANTED", "target_quantity": 100.0, "target_unit": "trees", "target_date": "2027-12-31"},
        headers=pm_hdr,
    )
    assert target_b.status_code == 403

    # PM CANNOT assign members on Project B
    assign_b = await client.post(
        f"/api/v1/projects/{proj_b['id']}/assignments",
        json={"user_id": str(pm_user.id), "assigned_role": "FIELD_OFFICER"},
        headers=pm_hdr,
    )
    assert assign_b.status_code == 403


@pytest.mark.asyncio
async def test_geojson_polygon_extended_validation(client: AsyncClient, db_session: AsyncSession):
    """
    Tests edge cases in GeoJSON polygon validation: invalid types, 1D coordinates,
    and valid multi-ring polygons with holes.
    """
    _, admin_hdr = await create_user_helper(db_session, role=UserRole.ADMIN.value)

    # 1. Invalid Geometry Type (Point instead of Polygon)
    res_point = await client.post(
        "/api/v1/projects",
        json={"name": "Point GeoJSON", "latitude": 20.0, "longitude": 80.0, "boundary_geojson": {"type": "Point", "coordinates": [80.0, 20.0]}},
        headers=admin_hdr,
    )
    assert res_point.status_code == 422

    # 2. Coordinate dimensionality error (1D array instead of 2D [lng, lat])
    res_1d = await client.post(
        "/api/v1/projects",
        json={"name": "1D Coordinate", "latitude": 20.0, "longitude": 80.0, "boundary_geojson": {"type": "Polygon", "coordinates": [[[80.0], [81.0], [81.0], [80.0]]]}},
        headers=admin_hdr,
    )
    assert res_1d.status_code == 422

    # 3. Valid polygon with interior hole (multiple linear rings)
    donut_polygon = {
        "type": "Polygon",
        "coordinates": [
            # Exterior ring
            [
                [80.0, 20.0],
                [85.0, 20.0],
                [85.0, 25.0],
                [80.0, 25.0],
                [80.0, 20.0],
            ],
            # Interior hole ring
            [
                [81.0, 21.0],
                [84.0, 21.0],
                [84.0, 24.0],
                [81.0, 24.0],
                [81.0, 21.0],
            ],
        ],
    }
    res_donut = await client.post(
        "/api/v1/projects",
        json={"name": "Donut Polygon Project", "latitude": 22.5, "longitude": 82.5, "boundary_geojson": donut_polygon},
        headers=admin_hdr,
    )
    assert res_donut.status_code == 201
    assert len(res_donut.json()["boundary_geojson"]["coordinates"]) == 2


@pytest.mark.asyncio
async def test_target_update_preserves_metric_identity_and_rejects_incompatible_unit(client: AsyncClient, db_session: AsyncSession):
    """
    Verifies that updating a target cannot change its metric_code, and
    rejects incompatible unit changes with 422.
    """
    _, admin_hdr = await create_user_helper(db_session, role=UserRole.ADMIN.value)

    proj = (await client.post(
        "/api/v1/projects",
        json={"name": "Target Unit Test Proj", "latitude": 26.0, "longitude": 86.0},
        headers=admin_hdr,
    )).json()

    target = (await client.post(
        f"/api/v1/projects/{proj['id']}/targets",
        json={"metric_code": "AREA_RESTORED", "target_quantity": 100.0, "target_unit": "hectares", "target_date": "2028-12-31"},
        headers=admin_hdr,
    )).json()

    # 1. Valid unit update (compatible unit within AREA dimension: hectares -> acres)
    valid_unit_res = await client.put(
        f"/api/v1/projects/{proj['id']}/targets/{target['id']}",
        json={"target_unit": "acres"},
        headers=admin_hdr,
    )
    assert valid_unit_res.status_code == 200
    assert valid_unit_res.json()["target_unit"] == "acres"
    assert valid_unit_res.json()["metric_code"] == "AREA_RESTORED"

    # 2. Incompatible unit update (acres -> liters)
    bad_unit_res = await client.put(
        f"/api/v1/projects/{proj['id']}/targets/{target['id']}",
        json={"target_unit": "liters"},
        headers=admin_hdr,
    )
    assert bad_unit_res.status_code == 422
    assert bad_unit_res.json()["detail"]["error_code"] == "INCOMPATIBLE_UNIT"


@pytest.mark.asyncio
async def test_target_deletion_safeguard_with_field_activities(client: AsyncClient, db_session: AsyncSession):
    """
    Verifies that a target cannot be deleted if active non-archived field activities
    reference its metric_code on that project.
    """
    admin_user, admin_hdr = await create_user_helper(db_session, role=UserRole.ADMIN.value)

    proj = (await client.post(
        "/api/v1/projects",
        json={"name": "Activity Safety Proj", "latitude": 27.0, "longitude": 87.0},
        headers=admin_hdr,
    )).json()
    project_id = proj["id"]

    target = (await client.post(
        f"/api/v1/projects/{project_id}/targets",
        json={"metric_code": "TREES_PLANTED", "target_quantity": 5000.0, "target_unit": "trees", "target_date": "2027-12-31"},
        headers=admin_hdr,
    )).json()

    # Insert an active FieldActivity referencing this project & metric_code
    from app.domains.operations.models import FieldActivity
    activity = FieldActivity(
        id=uuid.uuid4(),
        project_id=uuid.UUID(project_id),
        created_by_id=admin_user.id,
        metric_code="TREES_PLANTED",
        unit="trees",
        is_archived=False,
    )
    db_session.add(activity)
    await db_session.commit()

    # Attempt to delete target -> must be blocked
    del_res = await client.delete(
        f"/api/v1/projects/{project_id}/targets/{target['id']}",
        headers=admin_hdr,
    )
    assert del_res.status_code == 400
    assert del_res.json()["detail"]["error_code"] == "TARGET_HAS_ACTIVE_ACTIVITIES"

    # Soft-archive the activity
    activity.is_archived = True
    await db_session.commit()

    # Now deletion must succeed
    del_res_success = await client.delete(
        f"/api/v1/projects/{project_id}/targets/{target['id']}",
        headers=admin_hdr,
    )
    assert del_res_success.status_code == 204

