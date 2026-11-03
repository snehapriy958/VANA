import asyncio
from datetime import timedelta
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, create_refresh_token
from app.domains.audit.models import AuditLog
from app.domains.auth.models import User, UserRole
from tests.test_auth_and_rbac import create_user_in_db


@pytest.mark.asyncio
async def test_concurrent_refresh_atomicity(client: AsyncClient, db_session: AsyncSession):
    """
    Concurrency & Atomicity Test:
    Fires two simultaneous /auth/refresh requests using the exact same refresh token.
    Enforces:
    - Exactly one request succeeds with 200 OK.
    - Exactly one request fails with 401 TOKEN_REVOKED.
    - The old token cannot be reused in any subsequent request.
    - The newly issued replacement refresh token is valid and active.
    """
    email = f"concurr_{uuid.uuid4().hex[:6]}@akshayavana.com"
    user = await create_user_in_db(db_session, email=email, password="Password123!")

    # 1. Login to obtain initial refresh token
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Password123!"},
    )
    assert login_resp.status_code == 200
    initial_refresh_token = login_resp.json()["refresh_token"]

    # 2. Fire simultaneous requests
    resp1, resp2 = await asyncio.gather(
        client.post("/api/v1/auth/refresh", json={"refresh_token": initial_refresh_token}),
        client.post("/api/v1/auth/refresh", json={"refresh_token": initial_refresh_token}),
    )

    statuses = [resp1.status_code, resp2.status_code]
    assert 200 in statuses, f"Expected one 200 OK, got {statuses}"
    assert 401 in statuses, f"Expected one 401 Unauthorized, got {statuses}"

    successful_resp = resp1 if resp1.status_code == 200 else resp2
    failed_resp = resp2 if resp1.status_code == 200 else resp1

    # Verify failure detail
    assert failed_resp.json()["detail"]["error_code"] == "TOKEN_REVOKED"

    # Verify successful response has new tokens
    new_refresh_token = successful_resp.json()["refresh_token"]
    assert new_refresh_token != initial_refresh_token

    # 3. Verify old token is permanently unusable
    post_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": initial_refresh_token},
    )
    assert post_resp.status_code == 401
    assert post_resp.json()["detail"]["error_code"] == "TOKEN_REVOKED"

    # 4. Verify new token can be used for a subsequent refresh
    subsequent_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": new_refresh_token},
    )
    assert subsequent_resp.status_code == 200
    assert "access_token" in subsequent_resp.json()


@pytest.mark.asyncio
async def test_logout_with_valid_refresh_token(client: AsyncClient, db_session: AsyncSession):
    """Verifies that calling logout with a valid refresh token revokes it."""
    email = f"logout_valid_{uuid.uuid4().hex[:6]}@akshayavana.com"
    user = await create_user_in_db(db_session, email=email, password="Password123!")

    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Password123!"},
    )
    access_token = login_resp.json()["access_token"]
    refresh_token = login_resp.json()["refresh_token"]

    # Logout
    logout_resp = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"refresh_token": refresh_token},
    )
    assert logout_resp.status_code == 200
    assert "logged out" in logout_resp.json()["message"].lower()

    # Attempt to refresh with revoked token
    refresh_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_resp.status_code == 401
    assert refresh_resp.json()["detail"]["error_code"] == "TOKEN_REVOKED"


@pytest.mark.asyncio
async def test_repeated_logout(client: AsyncClient, db_session: AsyncSession):
    """Verifies that repeated logout calls are safe and idempotent."""
    email = f"repeat_logout_{uuid.uuid4().hex[:6]}@akshayavana.com"
    user = await create_user_in_db(db_session, email=email, password="Password123!")

    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Password123!"},
    )
    access_token = login_resp.json()["access_token"]
    refresh_token = login_resp.json()["refresh_token"]

    # First logout
    logout_resp1 = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"refresh_token": refresh_token},
    )
    assert logout_resp1.status_code == 200

    # Second logout (with same access token)
    logout_resp2 = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"refresh_token": refresh_token},
    )
    assert logout_resp2.status_code == 200


@pytest.mark.asyncio
async def test_logout_with_expired_token(client: AsyncClient, db_session: AsyncSession):
    """Verifies that logout succeeds gracefully even if the supplied refresh token is expired."""
    email = f"expired_logout_{uuid.uuid4().hex[:6]}@akshayavana.com"
    user = await create_user_in_db(db_session, email=email)
    access_token = create_access_token(subject=str(user.id), role=user.role)
    expired_refresh_token = create_refresh_token(subject=str(user.id), expires_delta=timedelta(days=-1))

    logout_resp = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"refresh_token": expired_refresh_token},
    )
    assert logout_resp.status_code == 200


@pytest.mark.asyncio
async def test_logout_invalidates_all_prior_refresh_tokens(client: AsyncClient, db_session: AsyncSession):
    """
    Verifies that calling logout creates a USER_LOGOUT barrier that invalidates
    any refresh token issued before that logout timestamp.
    """
    email = f"barrier_{uuid.uuid4().hex[:6]}@akshayavana.com"
    user = await create_user_in_db(db_session, email=email, password="Password123!")

    # Login session 1
    resp1 = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Password123!"},
    )
    access_token1 = resp1.json()["access_token"]
    refresh_token1 = resp1.json()["refresh_token"]

    # Logout (even without passing refresh_token in body)
    logout_resp = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {access_token1}"},
    )
    assert logout_resp.status_code == 200

    # Attempt to use refresh_token1 after the logout barrier
    refresh_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token1},
    )
    assert refresh_resp.status_code == 401
    assert refresh_resp.json()["detail"]["error_code"] == "TOKEN_REVOKED"
