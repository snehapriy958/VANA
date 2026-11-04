import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.auth.models import User, UserRole
from app.domains.projects.models import Project, ProjectStatus, ProjectTarget
from app.domains.teams.models import ProjectAssignment, ProjectRole
from app.domains.operations.models import (
    FieldActivity,
    ActivityRevision,
    ActivityStatus,
    RejectionReasonCode,
    EvidenceFile,
)
from app.domains.audit.models import AuditLog
from app.domains.audit.services import record_audit_log


@pytest.mark.asyncio
async def test_insert_and_query_all_tables(db_session: AsyncSession):
    """Verifies that records can be inserted and queried across all 8 tables."""
    # 1. User (Admin)
    admin_user = User(
        email=f"admin_{uuid.uuid4().hex[:6]}@test.vana",
        hashed_password="argon2id$mockhash",
        full_name="Admin Test",
        role=UserRole.ADMIN.value,
    )
    # 2. User (Field Officer)
    officer_user = User(
        email=f"officer_{uuid.uuid4().hex[:6]}@test.vana",
        hashed_password="argon2id$mockhash",
        full_name="Officer Test",
        role=UserRole.FIELD_OFFICER.value,
    )
    db_session.add_all([admin_user, officer_user])
    await db_session.flush()

    # 3. Project
    project = Project(
        name="Sundarbans Conservation",
        code=f"PRJ-{uuid.uuid4().hex[:6].upper()}",
        status=ProjectStatus.ACTIVE.value,
        latitude=21.9497,
        longitude=89.1833,
    )
    db_session.add(project)
    await db_session.flush()

    # 4. Project Assignment
    assignment = ProjectAssignment(
        project_id=project.id,
        user_id=officer_user.id,
        assigned_role=ProjectRole.FIELD_OFFICER.value,
    )
    db_session.add(assignment)

    # 5. Project Target
    target = ProjectTarget(
        project_id=project.id,
        metric_code="TREES_PLANTED",
        target_quantity=Decimal("1000.00"),
        target_unit="trees",
        target_date=date(2027, 12, 31),
    )
    db_session.add(target)
    await db_session.flush()

    # 6. Field Activity
    activity = FieldActivity(
        project_id=project.id,
        created_by_id=officer_user.id,
        metric_code="TREES_PLANTED",
        unit="trees",
    )
    db_session.add(activity)
    await db_session.flush()

    # 7. Activity Revision
    revision = ActivityRevision(
        activity_id=activity.id,
        revision_number=1,
        quantity=Decimal("200.00"),
        activity_date=date(2026, 11, 2),
        status=ActivityStatus.PENDING.value,
        is_active_ledger_entry=False,
    )
    db_session.add(revision)
    await db_session.flush()

    # Link current_revision_id
    activity.current_revision_id = revision.id

    # 8. Evidence File
    evidence = EvidenceFile(
        activity_id=activity.id,
        revision_id=revision.id,
        file_storage_key="test_evidence.jpg",
        original_filename="field_photo.jpg",
        mime_type="image/jpeg",
        file_size_bytes=1024,
    )
    db_session.add(evidence)

    # 9. Audit Log
    audit = await record_audit_log(
        db=db_session,
        actor_id=admin_user.id,
        action_type="TEST_INITIALIZATION",
        entity_type="PROJECT",
        entity_id=project.id,
        new_state={"status": "ACTIVE"},
    )

    # Query back
    result = await db_session.execute(select(Project).where(Project.id == project.id))
    fetched_project = result.scalar_one()
    assert fetched_project.name == "Sundarbans Conservation"


@pytest.mark.asyncio
async def test_partial_unique_index_active_ledger_prevents_double_counting(db_session: AsyncSession):
    """Verifies that PostgreSQL engine strictly prevents two active revisions for the same activity."""
    user = User(email=f"u_{uuid.uuid4().hex[:6]}@test.vana", hashed_password="h", full_name="U", role="ADMIN")
    project = Project(name="P", code=f"C-{uuid.uuid4().hex[:6]}", latitude=10.0, longitude=20.0)
    db_session.add_all([user, project])
    await db_session.flush()

    activity = FieldActivity(project_id=project.id, created_by_id=user.id, metric_code="TREES_PLANTED", unit="trees")
    db_session.add(activity)
    await db_session.flush()

    # Revision 1 (Active, Verified)
    now = datetime.now(timezone.utc)
    rev1 = ActivityRevision(
        activity_id=activity.id,
        revision_number=1,
        quantity=Decimal("200.00"),
        activity_date=date(2026, 11, 2),
        status=ActivityStatus.VERIFIED.value,
        is_active_ledger_entry=True,
        verifier_id=user.id,
        verified_at=now,
    )
    db_session.add(rev1)
    await db_session.flush()

    # Attempt to insert Revision 2 as active ledger entry for the same activity
    rev2 = ActivityRevision(
        activity_id=activity.id,
        revision_number=2,
        quantity=Decimal("250.00"),
        activity_date=date(2026, 11, 3),
        status=ActivityStatus.VERIFIED.value,
        is_active_ledger_entry=True,  # VIOLATION: Cannot have two active entries!
        verifier_id=user.id,
        verified_at=now,
    )
    db_session.add(rev2)
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_check_constraint_active_ledger_must_be_verified(db_session: AsyncSession):
    """Verifies check constraint: an active ledger entry MUST have status='VERIFIED'."""
    user = User(email=f"u_{uuid.uuid4().hex[:6]}@test.vana", hashed_password="h", full_name="U", role="ADMIN")
    project = Project(name="P", code=f"C-{uuid.uuid4().hex[:6]}", latitude=10.0, longitude=20.0)
    db_session.add_all([user, project])
    await db_session.flush()

    activity = FieldActivity(project_id=project.id, created_by_id=user.id, metric_code="TREES_PLANTED", unit="trees")
    db_session.add(activity)
    await db_session.flush()

    # Attempt to set is_active_ledger_entry=True when status is 'PENDING'
    invalid_rev = ActivityRevision(
        activity_id=activity.id,
        revision_number=1,
        quantity=Decimal("100.00"),
        activity_date=date(2026, 11, 2),
        status=ActivityStatus.PENDING.value,
        is_active_ledger_entry=True,  # VIOLATION of chk_active_ledger_verified
    )
    db_session.add(invalid_rev)
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_check_constraint_rejection_requires_reason_and_notes(db_session: AsyncSession):
    """Verifies check constraint: REJECTED status requires reason code and review notes."""
    user = User(email=f"u_{uuid.uuid4().hex[:6]}@test.vana", hashed_password="h", full_name="U", role="ADMIN")
    project = Project(name="P", code=f"C-{uuid.uuid4().hex[:6]}", latitude=10.0, longitude=20.0)
    db_session.add_all([user, project])
    await db_session.flush()

    activity = FieldActivity(project_id=project.id, created_by_id=user.id, metric_code="TREES_PLANTED", unit="trees")
    db_session.add(activity)
    await db_session.flush()

    # Attempt to set status='REJECTED' without rejection_reason_code
    invalid_rejection = ActivityRevision(
        activity_id=activity.id,
        revision_number=1,
        quantity=Decimal("100.00"),
        activity_date=date(2026, 11, 2),
        status=ActivityStatus.REJECTED.value,
        rejection_reason_code=None,  # VIOLATION
        review_notes=None,
    )
    db_session.add(invalid_rejection)
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_foreign_key_delete_restrict_on_activity_creator(db_session: AsyncSession):
    """Verifies that a user cannot be deleted while they own submitted activities (ON DELETE RESTRICT)."""
    user = User(email=f"u_{uuid.uuid4().hex[:6]}@test.vana", hashed_password="h", full_name="U", role="FIELD_OFFICER")
    project = Project(name="P", code=f"C-{uuid.uuid4().hex[:6]}", latitude=10.0, longitude=20.0)
    db_session.add_all([user, project])
    await db_session.flush()

    activity = FieldActivity(project_id=project.id, created_by_id=user.id, metric_code="TREES_PLANTED", unit="trees")
    db_session.add(activity)
    await db_session.flush()

    # Attempt to delete user
    await db_session.delete(user)
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()
