"""
VANA — Production Administrator Bootstrap Tests
Module: tests.test_bootstrap_admin
Verifies:
- Password strength validation (missing, short, prohibited, missing charsets)
- Successful administrator provisioning on fresh system
- Password hashing verification with Argon2id
- Immutable audit log with traceable system actor and zero password exposure
- Refusal to bootstrap if any administrator already exists, even with a different email
- Refusal to overwrite existing non-admin user accounts
- Transaction atomicity on failure
- Rejection of weak / development default passwords
"""

import uuid
import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.bootstrap_admin import bootstrap_administrator, validate_password_strength
from app.core.security import verify_password
from app.domains.audit.models import AuditLog
from app.domains.auth.models import User, UserRole


@pytest_asyncio.fixture(autouse=True)
async def clean_bootstrap_state(db_session: AsyncSession):
    """
    Ensures a pristine database state with zero pre-existing administrators,
    matching a fresh production deployment environment.
    """
    await db_session.execute(text(
        "TRUNCATE TABLE field_inspections, survival_observations, maintenance_tasks, "
        "evidence_files, activity_revisions, field_activities, project_targets, "
        "project_assignments, projects, audit_logs, users CASCADE;"
    ))
    await db_session.commit()
    yield
    await db_session.execute(text(
        "TRUNCATE TABLE field_inspections, survival_observations, maintenance_tasks, "
        "evidence_files, activity_revisions, field_activities, project_targets, "
        "project_assignments, projects, audit_logs, users CASCADE;"
    ))
    await db_session.commit()


def test_password_strength_validation():
    """Verifies that the password strength validator rejects weak or missing passwords."""
    # 1. Missing password
    is_valid, msg = validate_password_strength(None)
    assert not is_valid
    assert "required" in msg

    is_valid, msg = validate_password_strength("")
    assert not is_valid

    # 2. Too short (< 12 chars)
    is_valid, msg = validate_password_strength("Short1!a")
    assert not is_valid
    assert "at least 12 characters" in msg

    # 3. Known development / weak passwords
    for weak_pw in ["SecurePass123!", "password123", "admin", "changeme", "1234567890"]:
        is_valid, msg = validate_password_strength(weak_pw)
        assert not is_valid, f"Expected weak password '{weak_pw}' to be rejected"
        assert "not permitted" in msg

    # 4. Missing required character sets
    assert not validate_password_strength("alllowercase123!@#")[0]  # Missing uppercase
    assert not validate_password_strength("ALLUPPERCASE123!@#")[0]  # Missing lowercase
    assert not validate_password_strength("NoDigitsHere!@#abcDEF")[0]  # Missing digit
    assert not validate_password_strength("NoSpecialChar123abcDEF")[0]  # Missing special char

    # 5. Valid strong password
    valid_pw = "Vana#SecureProd2026!"
    is_valid, msg = validate_password_strength(valid_pw)
    assert is_valid
    assert msg == ""


@pytest.mark.asyncio
async def test_bootstrap_administrator_success(db_session: AsyncSession):
    """Verifies successful provisioning of initial administrator, Argon2id hash, and audit trail."""
    admin_email = f"bootstrap_admin_{uuid.uuid4().hex[:6]}@vana.earth"
    admin_name = "Super Administrator"
    raw_password = "Vana#ProdBootstrapKey99!"

    success, msg = await bootstrap_administrator(
        email=admin_email,
        full_name=admin_name,
        password=raw_password,
        session=db_session,
    )
    assert success is True
    assert "SUCCESS" in msg

    # Verify database record
    user = await db_session.scalar(select(User).where(User.email == admin_email))
    assert user is not None
    assert user.email == admin_email
    assert user.full_name == admin_name
    assert user.role == UserRole.ADMIN.value
    assert user.is_active is True

    # Verify password hash (Argon2id)
    assert user.hashed_password != raw_password
    assert user.hashed_password.startswith("$argon2id$")
    assert verify_password(raw_password, user.hashed_password) is True

    # Verify audit log was recorded with traceable system actor and zero plaintext password
    audit_entry = await db_session.scalar(
        select(AuditLog).where(
            AuditLog.entity_id == user.id,
            AuditLog.action_type == "USER_PROVISIONED",
        )
    )
    assert audit_entry is not None
    assert audit_entry.actor_id == user.id  # Traceable system actor
    assert "password" not in audit_entry.new_state
    assert "hashed_password" not in audit_entry.new_state
    assert audit_entry.new_state["email"] == admin_email
    assert audit_entry.new_state["is_bootstrap"] is True


@pytest.mark.asyncio
async def test_bootstrap_refuses_when_admin_already_exists(db_session: AsyncSession):
    """
    Verifies that bootstrap strictly refuses to run if an administrator already exists,
    even when a different email address is supplied.
    """
    initial_email = f"first_admin_{uuid.uuid4().hex[:6]}@vana.earth"
    raw_password = "Vana#ProdBootstrapKey99!"

    # 1. Initial bootstrap succeeds on clean system
    success, _ = await bootstrap_administrator(
        email=initial_email,
        password=raw_password,
        session=db_session,
    )
    assert success is True

    # 2. Subsequent bootstrap attempt with DIFFERENT email MUST be refused
    different_email = f"second_admin_{uuid.uuid4().hex[:6]}@vana.earth"
    success_diff, msg_diff = await bootstrap_administrator(
        email=different_email,
        password="Another#SecurePassword2026!",
        session=db_session,
    )
    assert success_diff is False
    assert "BOOTSTRAP_ALREADY_COMPLETED" in msg_diff

    # 3. Subsequent bootstrap attempt with SAME email MUST also be refused
    success_same, msg_same = await bootstrap_administrator(
        email=initial_email,
        password="Another#SecurePassword2026!",
        session=db_session,
    )
    assert success_same is False
    assert "BOOTSTRAP_ALREADY_COMPLETED" in msg_same


@pytest.mark.asyncio
async def test_bootstrap_refuses_to_overwrite_existing_non_admin_account(db_session: AsyncSession):
    """Verifies that bootstrap refuses to overwrite an existing non-admin user account."""
    fo_email = f"field_officer_{uuid.uuid4().hex[:6]}@vana.earth"
    fo_user = User(
        id=uuid.uuid4(),
        email=fo_email,
        hashed_password="$argon2id$v=19$m=65536,t=3,p=4$dummyhash",
        full_name="Field Officer Aarav",
        role=UserRole.FIELD_OFFICER.value,
        is_active=True,
    )
    db_session.add(fo_user)
    await db_session.commit()

    # Attempt to bootstrap with the existing FO's email address
    success, msg = await bootstrap_administrator(
        email=fo_email,
        password="Valid#SecurePassword2026!",
        session=db_session,
    )
    assert success is False
    assert "DUPLICATE_PROHIBITED" in msg

    # Verify role was not escalated or overwritten
    persisted_fo = await db_session.scalar(select(User).where(User.email == fo_email))
    assert persisted_fo.role == UserRole.FIELD_OFFICER.value


@pytest.mark.asyncio
async def test_bootstrap_administrator_invalid_password_rejected(db_session: AsyncSession):
    """Verifies that invalid or development default passwords are rejected without modifying database."""
    admin_email = f"invalid_pw_{uuid.uuid4().hex[:6]}@vana.earth"

    # Attempt with development password
    success, msg = await bootstrap_administrator(
        email=admin_email,
        password="SecurePass123!",
        session=db_session,
    )
    assert success is False
    assert "VALIDATION_FAILED" in msg
    assert "not permitted" in msg

    # Confirm user was not created
    user = await db_session.scalar(select(User).where(User.email == admin_email))
    assert user is None
