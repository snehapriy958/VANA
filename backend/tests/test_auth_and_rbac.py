import uuid
from datetime import timedelta
import pytest
from httpx import AsyncClient
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.domains.audit.models import AuditLog
from app.domains.auth.models import User, UserRole
from app.domains.projects.models import Project
from app.domains.teams.models import ProjectAssignment


async def create_user_in_db(
    db: AsyncSession,
    email: str,
    password: str = "SecurePass123!",
    full_name: str = "Test User",
    role: str = UserRole.FIELD_OFFICER.value,
    is_active: bool = True,
) -> User:
    """Helper to insert and commit a user into test database."""
    user = User(
        id=uuid.uuid4(),
        email=email.lower().strip(),
        hashed_password=hash_password(password),
        full_name=full_name,
        role=role,
        is_active=is_active,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


# ============================================================================
# 1. AUTHENTICATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_login_valid_credentials(client: AsyncClient, db_session: AsyncSession):
    """Verifies that authenticating with correct credentials returns valid JWT tokens."""
    email = f"valid_{uuid.uuid4().hex[:6]}@akshayavana.com"
    user = await create_user_in_db(db_session, email=email, password="ValidPassword123!")

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "ValidPassword123!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == email
    assert data["user"]["role"] == UserRole.FIELD_OFFICER.value
    assert "hashed_password" not in data["user"]


@pytest.mark.asyncio
async def test_login_invalid_password(client: AsyncClient, db_session: AsyncSession):
    """Verifies that an incorrect password produces HTTP 401 Unauthorized."""
    email = f"inv_pass_{uuid.uuid4().hex[:6]}@akshayavana.com"
    await create_user_in_db(db_session, email=email, password="CorrectPassword123!")

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "WrongPassword999!"},
    )
    assert response.status_code == 401
    detail = response.json()["detail"]
    assert detail["error_code"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_login_unknown_email(client: AsyncClient):
    """Verifies that attempting login with non-existent email returns HTTP 401."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@akshayavana.com", "password": "AnyPassword123!"},
    )
    assert response.status_code == 401
    assert response.json()["detail"]["error_code"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_login_deactivated_user(client: AsyncClient, db_session: AsyncSession):
    """Verifies that deactivated users are rejected with HTTP 403 Forbidden."""
    email = f"deactivated_{uuid.uuid4().hex[:6]}@akshayavana.com"
    await create_user_in_db(db_session, email=email, password="ValidPass123!", is_active=False)

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "ValidPass123!"},
    )
    assert response.status_code == 403
    assert response.json()["detail"]["error_code"] == "ACCOUNT_DEACTIVATED"


@pytest.mark.asyncio
async def test_auth_me_protected_endpoint_without_token(client: AsyncClient):
    """Verifies that calling /auth/me without an Authorization header returns HTTP 401."""
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["detail"]["error_code"] == "NOT_AUTHENTICATED"


@pytest.mark.asyncio
async def test_auth_me_with_valid_token(client: AsyncClient, db_session: AsyncSession):
    """Verifies that calling /auth/me with valid Bearer token returns profile."""
    email = f"me_test_{uuid.uuid4().hex[:6]}@akshayavana.com"
    user = await create_user_in_db(db_session, email=email, full_name="Sita Devi")
    token = create_access_token(subject=str(user.id), role=user.role, email=user.email)

    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(user.id)
    assert data["full_name"] == "Sita Devi"
    assert data["email"] == email


@pytest.mark.asyncio
async def test_auth_me_with_expired_token(client: AsyncClient, db_session: AsyncSession):
    """Verifies that an expired token produces HTTP 401 TOKEN_EXPIRED."""
    email = f"expired_{uuid.uuid4().hex[:6]}@akshayavana.com"
    user = await create_user_in_db(db_session, email=email)
    # Generate token that expired 10 minutes ago
    expired_token = create_access_token(
        subject=str(user.id),
        role=user.role,
        expires_delta=timedelta(minutes=-10)
    )

    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert response.status_code == 401
    assert response.json()["detail"]["error_code"] == "TOKEN_EXPIRED"


@pytest.mark.asyncio
async def test_auth_me_with_malformed_token(client: AsyncClient):
    """Verifies that a malformed JWT string produces HTTP 401 INVALID_TOKEN."""
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer this.is.not.a.valid.jwt"},
    )
    assert response.status_code == 401
    assert response.json()["detail"]["error_code"] == "INVALID_TOKEN"


@pytest.mark.asyncio
async def test_refresh_token_exchange(client: AsyncClient, db_session: AsyncSession):
    """Verifies exchanging a valid refresh token yields a new access token."""
    email = f"refresh_{uuid.uuid4().hex[:6]}@akshayavana.com"
    user = await create_user_in_db(db_session, email=email)
    refresh_token = create_refresh_token(subject=str(user.id))

    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_logout_endpoint(client: AsyncClient, db_session: AsyncSession):
    """Verifies that calling /auth/logout succeeds and records an audit log entry."""
    email = f"logout_{uuid.uuid4().hex[:6]}@akshayavana.com"
    user = await create_user_in_db(db_session, email=email)
    token = create_access_token(subject=str(user.id), role=user.role)

    response = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert "logged out" in response.json()["message"].lower()

    # Check audit log entry
    audit = await db_session.scalar(
        select(AuditLog).where(
            AuditLog.actor_id == user.id,
            AuditLog.action_type == "USER_LOGOUT"
        )
    )
    assert audit is not None


# ============================================================================
# 2. RBAC & USER MANAGEMENT TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_admin_can_provision_new_user(client: AsyncClient, db_session: AsyncSession):
    """Verifies that ADMIN can create a new user account."""
    admin_email = f"admin_{uuid.uuid4().hex[:6]}@akshayavana.com"
    admin = await create_user_in_db(db_session, email=admin_email, role=UserRole.ADMIN.value)
    admin_token = create_access_token(subject=str(admin.id), role=admin.role)

    target_email = f"new_fo_{uuid.uuid4().hex[:6]}@akshayavana.com"
    response = await client.post(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "email": target_email,
            "password": "Password123!",
            "full_name": "Ravi Kumar",
            "role": UserRole.FIELD_OFFICER.value,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == target_email
    assert data["full_name"] == "Ravi Kumar"
    assert data["role"] == UserRole.FIELD_OFFICER.value


@pytest.mark.asyncio
async def test_non_admin_cannot_provision_user(client: AsyncClient, db_session: AsyncSession):
    """Verifies that PROJECT_MANAGER and FIELD_OFFICER cannot create users (HTTP 403)."""
    pm_email = f"pm_{uuid.uuid4().hex[:6]}@akshayavana.com"
    pm = await create_user_in_db(db_session, email=pm_email, role=UserRole.PROJECT_MANAGER.value)
    pm_token = create_access_token(subject=str(pm.id), role=pm.role)

    response = await client.post(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {pm_token}"},
        json={
            "email": "should_fail@akshayavana.com",
            "password": "Password123!",
            "full_name": "Unauthorized User",
            "role": UserRole.FIELD_OFFICER.value,
        },
    )
    assert response.status_code == 403
    assert response.json()["detail"]["error_code"] == "INSUFFICIENT_ROLE"


@pytest.mark.asyncio
async def test_duplicate_email_rejected_with_409(client: AsyncClient, db_session: AsyncSession):
    """Verifies that attempting to provision a user with an existing email returns HTTP 409."""
    admin = await create_user_in_db(db_session, email=f"admin_{uuid.uuid4().hex[:6]}@akshayavana.com", role=UserRole.ADMIN.value)
    admin_token = create_access_token(subject=str(admin.id), role=admin.role)

    existing_email = f"existing_{uuid.uuid4().hex[:6]}@akshayavana.com"
    await create_user_in_db(db_session, email=existing_email)

    response = await client.post(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "email": existing_email,
            "password": "Password123!",
            "full_name": "Duplicate User",
            "role": UserRole.FIELD_OFFICER.value,
        },
    )
    assert response.status_code == 409
    assert response.json()["detail"]["error_code"] == "EMAIL_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_admin_cannot_change_own_role(client: AsyncClient, db_session: AsyncSession):
    """Verifies that an ADMIN is prohibited from altering their own role (anti-self-lockout)."""
    admin = await create_user_in_db(db_session, email=f"admin_{uuid.uuid4().hex[:6]}@akshayavana.com", role=UserRole.ADMIN.value)
    admin_token = create_access_token(subject=str(admin.id), role=admin.role)

    response = await client.put(
        f"/api/v1/users/{admin.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"role": UserRole.FIELD_OFFICER.value},
    )
    assert response.status_code == 403
    assert response.json()["detail"]["error_code"] == "SELF_ROLE_CHANGE_PROHIBITED"


@pytest.mark.asyncio
async def test_non_admin_cannot_escalate_role(client: AsyncClient, db_session: AsyncSession):
    """Verifies that a FIELD_OFFICER cannot escalate their own role to ADMIN."""
    fo = await create_user_in_db(db_session, email=f"fo_{uuid.uuid4().hex[:6]}@akshayavana.com", role=UserRole.FIELD_OFFICER.value)
    fo_token = create_access_token(subject=str(fo.id), role=fo.role)

    response = await client.put(
        f"/api/v1/users/{fo.id}",
        headers={"Authorization": f"Bearer {fo_token}"},
        json={"role": UserRole.ADMIN.value},
    )
    assert response.status_code == 403
    assert response.json()["detail"]["error_code"] == "UNAUTHORIZED_ROLE_ESCALATION"


@pytest.mark.asyncio
async def test_field_officer_cannot_list_users(client: AsyncClient, db_session: AsyncSession):
    """Verifies that FIELD_OFFICER is denied from listing users."""
    fo = await create_user_in_db(db_session, email=f"fo_{uuid.uuid4().hex[:6]}@akshayavana.com", role=UserRole.FIELD_OFFICER.value)
    fo_token = create_access_token(subject=str(fo.id), role=fo.role)

    response = await client.get(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {fo_token}"},
    )
    assert response.status_code == 403
    assert response.json()["detail"]["error_code"] == "INSUFFICIENT_ROLE"


@pytest.mark.asyncio
async def test_admin_can_activate_and_deactivate_user(client: AsyncClient, db_session: AsyncSession):
    """Verifies that ADMIN can deactivate and activate user accounts with audit trail."""
    admin = await create_user_in_db(db_session, email=f"admin_{uuid.uuid4().hex[:6]}@akshayavana.com", role=UserRole.ADMIN.value)
    admin_token = create_access_token(subject=str(admin.id), role=admin.role)

    target = await create_user_in_db(db_session, email=f"target_{uuid.uuid4().hex[:6]}@akshayavana.com")

    # Deactivate
    deact_resp = await client.put(
        f"/api/v1/users/{target.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"is_active": False},
    )
    assert deact_resp.status_code == 200
    assert deact_resp.json()["is_active"] is False

    # Verify audit log recorded DEACTIVATION
    audit = await db_session.scalar(
        select(AuditLog).where(
            AuditLog.entity_id == target.id,
            AuditLog.action_type == "USER_DEACTIVATED"
        )
    )
    assert audit is not None
    assert audit.new_state["is_active"] is False

    # Reactivate
    react_resp = await client.put(
        f"/api/v1/users/{target.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"is_active": True},
    )
    assert react_resp.status_code == 200
    assert react_resp.json()["is_active"] is True


@pytest.mark.asyncio
async def test_audit_logs_never_leak_passwords_or_hashes(client: AsyncClient, db_session: AsyncSession):
    """Verifies security invariant: Audit logs never persist plaintext passwords or Argon2 hashes."""
    admin = await create_user_in_db(db_session, email=f"admin_{uuid.uuid4().hex[:6]}@akshayavana.com", role=UserRole.ADMIN.value)
    admin_token = create_access_token(subject=str(admin.id), role=admin.role)

    # Provision user
    new_email = f"audited_{uuid.uuid4().hex[:6]}@akshayavana.com"
    await client.post(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "email": new_email,
            "password": "SuperSecretPassword123!",
            "full_name": "Audit Safety User",
            "role": UserRole.FIELD_OFFICER.value,
        },
    )

    # Inspect all audit logs for this user
    created_user = await db_session.scalar(select(User).where(User.email == new_email))
    assert created_user is not None

    audit_records = (await db_session.scalars(
        select(AuditLog).where(AuditLog.entity_id == created_user.id)
    )).all()

    assert len(audit_records) > 0
    for record in audit_records:
        if record.new_state:
            for k in record.new_state:
                assert k.lower() not in ("password", "hashed_password", "token", "secret")
        if record.previous_state:
            for k in record.previous_state:
                assert k.lower() not in ("password", "hashed_password", "token", "secret")


# ============================================================================
# 3. PROJECT-LEVEL AUTHORIZATION BOUNDARY TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_verify_project_access_boundaries(db_session: AsyncSession):
    """Verifies server-side project authorization boundaries established for subsequent milestones."""
    from fastapi import HTTPException
    from app.domains.auth.dependencies import verify_project_access

    # Create dummy project
    project = Project(
        id=uuid.uuid4(),
        name="Sundarbans Mangrove Project",
        code=f"SMP-{uuid.uuid4().hex[:4]}",
        status="ACTIVE",
        latitude=21.95,
        longitude=89.18,
    )
    db_session.add(project)

    # Users
    admin = await create_user_in_db(db_session, email=f"admin_proj_{uuid.uuid4().hex[:6]}@akshayavana.com", role=UserRole.ADMIN.value)
    assigned_pm = await create_user_in_db(db_session, email=f"pm_proj_{uuid.uuid4().hex[:6]}@akshayavana.com", role=UserRole.PROJECT_MANAGER.value)
    assigned_fo = await create_user_in_db(db_session, email=f"fo_proj_{uuid.uuid4().hex[:6]}@akshayavana.com", role=UserRole.FIELD_OFFICER.value)
    unassigned_user = await create_user_in_db(db_session, email=f"unassigned_{uuid.uuid4().hex[:6]}@akshayavana.com", role=UserRole.FIELD_OFFICER.value)

    # Assign PM and FO to project
    pm_assignment = ProjectAssignment(
        id=uuid.uuid4(),
        project_id=project.id,
        user_id=assigned_pm.id,
        assigned_role=UserRole.PROJECT_MANAGER.value,
    )
    fo_assignment = ProjectAssignment(
        id=uuid.uuid4(),
        project_id=project.id,
        user_id=assigned_fo.id,
        assigned_role=UserRole.FIELD_OFFICER.value,
    )
    db_session.add_all([pm_assignment, fo_assignment])
    await db_session.commit()

    # 1. Admin gets organization-wide access without explicit assignment
    res_admin = await verify_project_access(project_id=project.id, current_user=admin, db=db_session)
    assert res_admin is None  # Admin bypasses assignment check

    # 2. Assigned PM gets access
    res_pm = await verify_project_access(project_id=project.id, current_user=assigned_pm, db=db_session)
    assert res_pm is not None
    assert res_pm.user_id == assigned_pm.id

    # 3. Assigned FO gets access for general operations
    res_fo = await verify_project_access(project_id=project.id, current_user=assigned_fo, db=db_session)
    assert res_fo is not None

    # 4. Assigned FO is denied from PM-restricted operations
    with pytest.raises(HTTPException) as exc_info_fo:
        await verify_project_access(
            project_id=project.id,
            current_user=assigned_fo,
            db=db_session,
            min_role=UserRole.PROJECT_MANAGER
        )
    assert exc_info_fo.value.status_code == 403
    assert exc_info_fo.value.detail["error_code"] == "INSUFFICIENT_PROJECT_ROLE"

    # 5. Unassigned user is denied access
    with pytest.raises(HTTPException) as exc_info_unassigned:
        await verify_project_access(project_id=project.id, current_user=unassigned_user, db=db_session)
    assert exc_info_unassigned.value.status_code == 403
    assert exc_info_unassigned.value.detail["error_code"] == "PROJECT_ACCESS_DENIED"


@pytest.mark.asyncio
async def test_pm_user_listing_is_scoped_to_assigned_projects(client: AsyncClient, db_session: AsyncSession):
    """Verifies that PROJECT_MANAGER only sees users assigned to projects they manage."""
    # Create Project A
    proj_a = Project(id=uuid.uuid4(), name="Project Alpha", code=f"PA-{uuid.uuid4().hex[:4]}", status="ACTIVE", latitude=12.5, longitude=77.5)
    # Create Project B
    proj_b = Project(id=uuid.uuid4(), name="Project Beta", code=f"PB-{uuid.uuid4().hex[:4]}", status="ACTIVE", latitude=13.0, longitude=78.0)
    db_session.add_all([proj_a, proj_b])

    # PM on Project A
    pm_a = await create_user_in_db(db_session, email=f"pm_a_{uuid.uuid4().hex[:6]}@akshayavana.com", role=UserRole.PROJECT_MANAGER.value)
    # FO on Project A
    fo_a = await create_user_in_db(db_session, email=f"fo_a_{uuid.uuid4().hex[:6]}@akshayavana.com", role=UserRole.FIELD_OFFICER.value)
    # FO on Project B (unrelated)
    fo_b = await create_user_in_db(db_session, email=f"fo_b_{uuid.uuid4().hex[:6]}@akshayavana.com", role=UserRole.FIELD_OFFICER.value)

    # Assignments
    db_session.add(ProjectAssignment(id=uuid.uuid4(), project_id=proj_a.id, user_id=pm_a.id, assigned_role="PROJECT_MANAGER"))
    db_session.add(ProjectAssignment(id=uuid.uuid4(), project_id=proj_a.id, user_id=fo_a.id, assigned_role="FIELD_OFFICER"))
    db_session.add(ProjectAssignment(id=uuid.uuid4(), project_id=proj_b.id, user_id=fo_b.id, assigned_role="FIELD_OFFICER"))
    await db_session.commit()

    pm_a_token = create_access_token(subject=str(pm_a.id), role=pm_a.role)

    # PM A lists users
    response = await client.get(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {pm_a_token}"},
    )
    assert response.status_code == 200
    user_ids = [u["id"] for u in response.json()["users"]]

    # PM A can see FO A (shares Project A)
    assert str(fo_a.id) in user_ids
    # PM A CANNOT see FO B (only in Project B)
    assert str(fo_b.id) not in user_ids


# ============================================================================
# 4. JWT LIFECYCLE & SECURITY AUDIT TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_old_access_jwt_after_role_downgrade_is_denied(client: AsyncClient, db_session: AsyncSession):
    """
    Security Invariant Test:
    Verifies that authorization verifies the live database role rather than trusting JWT claims.
    1. User logs in as PROJECT_MANAGER and receives JWT claiming role="PROJECT_MANAGER".
    2. Administrator downgrades user to FIELD_OFFICER in database.
    3. User presents original valid (non-expired) JWT to a PM-restricted endpoint (/api/v1/users).
    4. Expected Result: HTTP 403 Forbidden (INSUFFICIENT_ROLE).
    """
    email = f"downgrade_{uuid.uuid4().hex[:6]}@akshayavana.com"
    user = await create_user_in_db(db_session, email=email, role=UserRole.PROJECT_MANAGER.value)

    # Issue JWT with role=PROJECT_MANAGER claim
    pm_jwt = create_access_token(subject=str(user.id), role=UserRole.PROJECT_MANAGER.value, email=email)

    # Downgrade user's role directly in the database
    user.role = UserRole.FIELD_OFFICER.value
    await db_session.commit()

    # Attempt PM-only operation using the original token
    response = await client.get(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {pm_jwt}"},
    )
    assert response.status_code == 403
    assert response.json()["detail"]["error_code"] == "INSUFFICIENT_ROLE"


@pytest.mark.asyncio
async def test_refresh_token_reuse_after_rotation_is_denied(client: AsyncClient, db_session: AsyncSession):
    """
    Security Invariant Test:
    Verifies single-use refresh token rotation anti-replay mechanism.
    Old refresh tokens cannot be reused after rotation.
    """
    email = f"reuse_{uuid.uuid4().hex[:6]}@akshayavana.com"
    user = await create_user_in_db(db_session, email=email, password="ValidPassword123!")

    # 1. Login to get initial refresh token
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "ValidPassword123!"},
    )
    assert login_resp.status_code == 200
    initial_refresh_token = login_resp.json()["refresh_token"]

    # 2. First rotation: exchange initial_refresh_token for new token pair
    first_refresh_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": initial_refresh_token},
    )
    assert first_refresh_resp.status_code == 200
    rotated_refresh_token = first_refresh_resp.json()["refresh_token"]
    assert rotated_refresh_token != initial_refresh_token

    # 3. Attempt replay of initial_refresh_token: must be rejected with 401 TOKEN_REVOKED
    replay_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": initial_refresh_token},
    )
    assert replay_resp.status_code == 401
    assert replay_resp.json()["detail"]["error_code"] == "TOKEN_REVOKED"


@pytest.mark.asyncio
async def test_refresh_token_after_logout_is_denied(client: AsyncClient, db_session: AsyncSession):
    """
    Security Invariant Test:
    Verifies that calling logout terminates the session and invalidates the refresh token.
    """
    email = f"logout_revoke_{uuid.uuid4().hex[:6]}@akshayavana.com"
    user = await create_user_in_db(db_session, email=email, password="ValidPassword123!")

    # 1. Login
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "ValidPassword123!"},
    )
    assert login_resp.status_code == 200
    access_token = login_resp.json()["access_token"]
    refresh_token = login_resp.json()["refresh_token"]

    # 2. Logout with refresh token revocation
    logout_resp = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"refresh_token": refresh_token},
    )
    assert logout_resp.status_code == 200

    # 3. Attempt refresh with logged-out refresh token: must be rejected
    refresh_attempt = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_attempt.status_code == 401
    assert refresh_attempt.json()["detail"]["error_code"] == "TOKEN_REVOKED"


@pytest.mark.asyncio
async def test_access_token_used_as_refresh_token_is_rejected(client: AsyncClient, db_session: AsyncSession):
    """Verifies that an access token cannot be substituted as a refresh token."""
    email = f"wrong_type_{uuid.uuid4().hex[:6]}@akshayavana.com"
    user = await create_user_in_db(db_session, email=email)
    access_token = create_access_token(subject=str(user.id), role=user.role)

    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": access_token},
    )
    assert response.status_code == 401
    assert response.json()["detail"]["error_code"] == "INVALID_TOKEN_TYPE"


@pytest.mark.asyncio
async def test_refresh_token_used_as_access_token_is_rejected(client: AsyncClient, db_session: AsyncSession):
    """Verifies that a refresh token cannot be substituted as an access token on protected endpoints."""
    email = f"wrong_type2_{uuid.uuid4().hex[:6]}@akshayavana.com"
    user = await create_user_in_db(db_session, email=email)
    refresh_token = create_refresh_token(subject=str(user.id))

    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {refresh_token}"},
    )
    assert response.status_code == 401
    assert response.json()["detail"]["error_code"] == "INVALID_TOKEN_TYPE"


@pytest.mark.asyncio
async def test_deactivated_user_with_existing_valid_token_is_denied(client: AsyncClient, db_session: AsyncSession):
    """Verifies that a deactivated user holding an unexpired JWT is immediately denied with 403."""
    email = f"deact_hold_{uuid.uuid4().hex[:6]}@akshayavana.com"
    user = await create_user_in_db(db_session, email=email, is_active=True)
    valid_jwt = create_access_token(subject=str(user.id), role=user.role, email=email)

    # Deactivate account in database
    user.is_active = False
    await db_session.commit()

    # Call protected endpoint
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {valid_jwt}"},
    )
    assert response.status_code == 403
    assert response.json()["detail"]["error_code"] == "ACCOUNT_DEACTIVATED"


@pytest.mark.asyncio
async def test_nonexistent_project_access_returns_404(db_session: AsyncSession):
    """Verifies that attempting to access a nonexistent project returns HTTP 404."""
    from fastapi import HTTPException
    from app.domains.auth.dependencies import verify_project_access

    admin = await create_user_in_db(db_session, email=f"admin_404_{uuid.uuid4().hex[:6]}@akshayavana.com", role=UserRole.ADMIN.value)
    non_existent_id = uuid.uuid4()

    with pytest.raises(HTTPException) as exc_info:
        await verify_project_access(project_id=non_existent_id, current_user=admin, db=db_session)
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail["error_code"] == "PROJECT_NOT_FOUND"


def test_production_environment_refuses_insecure_default_secret():
    """Verifies that Settings raises a validation error in production if JWT secret is default or weak."""
    from app.core.config import Settings
    import pytest

    # Default secret in production must raise ValueError
    with pytest.raises(ValueError) as exc:
        Settings(
            ENVIRONMENT="production",
            JWT_SECRET_KEY="dev-secret-key-must-be-changed-in-production-at-least-32-chars",
            DATABASE_URL="postgresql+asyncpg://prod_user:pass@ep-remote.neon.tech/vana_prod?ssl=require",
            CORS_ORIGINS=["https://vana.earth"],
        )
    assert "CRITICAL SECURITY ERROR" in str(exc.value)

    # Short secret (< 32 chars) in production must raise ValueError
    with pytest.raises(ValueError) as exc_short:
        Settings(
            ENVIRONMENT="production",
            JWT_SECRET_KEY="short-secret",
            DATABASE_URL="postgresql+asyncpg://prod_user:pass@ep-remote.neon.tech/vana_prod?ssl=require",
            CORS_ORIGINS=["https://vana.earth"],
        )
    assert "CRITICAL SECURITY ERROR" in str(exc_short.value)

    # Strong 32+ char secret in production must succeed
    strong_settings = Settings(
        ENVIRONMENT="production",
        JWT_SECRET_KEY="a-very-secure-production-jwt-signing-secret-with-high-entropy-12345678",
        DATABASE_URL="postgresql+asyncpg://prod_user:pass@ep-remote.neon.tech/vana_prod?ssl=require",
        CORS_ORIGINS=["https://vana.earth"],
    )
    assert strong_settings.ENVIRONMENT == "production"
