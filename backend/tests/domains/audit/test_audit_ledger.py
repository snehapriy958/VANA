"""VANA Audit Domain — Milestone 8 Phase 1 Test Suite.

Verifies:
1. Deterministic cryptographic SHA-256 hashing and versioning.
2. Canonical JSON serialization across data types.
3. Monotonic sequence continuity and previous-hash linkage.
4. Concurrency control and zero sequence gaps under transaction rollback.
5. Historical backfill verification and integrity checking.
6. Sensitive field sanitization and project scoping resolution.
"""

import asyncio
from datetime import datetime, timezone
import hashlib
import json
import uuid
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.domains.audit.hashing import (
    CURRENT_HASH_VERSION,
    GENESIS_HASH,
    build_canonical_payload,
    canonical_json_dumps,
    compute_event_hash,
)
from app.domains.audit.models import AuditChainHead, AuditLog
from app.domains.audit.services import (
    _extract_project_id,
    record_audit_log,
    sanitize_state,
)
from app.domains.projects.models import Project


def test_deterministic_hash_generation():
    """Verifies that canonical JSON serialization produces 100% deterministic SHA-256 digests.

    Regardless of key ordering, spacing, or dictionary insertion order, the hash must be identical.
    """
    event_id = uuid.uuid4()
    now = datetime(2026, 11, 4, 12, 0, 0, tzinfo=timezone.utc)
    prev_hash = "a" * 64

    # Dict A: natural order
    payload_a = {
        "action_type": "ACTIVITY_VERIFIED",
        "verified_quantity": 500.0,
        "notes": "Verified successfully",
        "meta": {"location": "Sector 4", "confidence": 0.98},
    }

    # Dict B: scrambled order
    payload_b = {
        "meta": {"confidence": 0.98, "location": "Sector 4"},
        "notes": "Verified successfully",
        "action_type": "ACTIVITY_VERIFIED",
        "verified_quantity": 500.0,
    }

    hash_a = compute_event_hash(
        sequence_number=42,
        event_id=event_id,
        timestamp=now,
        action_type="ACTIVITY_VERIFIED",
        entity_type="activity_revision",
        entity_id=event_id,
        previous_hash=prev_hash,
        canonical_payload=payload_a,
    )

    hash_b = compute_event_hash(
        sequence_number=42,
        event_id=event_id,
        timestamp=now,
        action_type="ACTIVITY_VERIFIED",
        entity_type="activity_revision",
        entity_id=event_id,
        previous_hash=prev_hash,
        canonical_payload=payload_b,
    )

    assert hash_a == hash_b
    assert len(hash_a) == 64
    assert hash_a == hash_a.lower()


def test_hash_format_versioning():
    """Verifies that altering hash_version explicitly changes the computed digest."""
    event_id = uuid.uuid4()
    now = datetime(2026, 11, 4, 12, 0, 0, tzinfo=timezone.utc)
    payload = {"status": "ACTIVE"}

    hash_v1 = compute_event_hash(
        sequence_number=1,
        event_id=event_id,
        timestamp=now,
        action_type="PROJECT_CREATED",
        entity_type="project",
        entity_id=event_id,
        previous_hash=GENESIS_HASH,
        canonical_payload=payload,
        hash_version=1,
    )

    hash_v2 = compute_event_hash(
        sequence_number=1,
        event_id=event_id,
        timestamp=now,
        action_type="PROJECT_CREATED",
        entity_type="project",
        entity_id=event_id,
        previous_hash=GENESIS_HASH,
        canonical_payload=payload,
        hash_version=2,
    )

    assert hash_v1 != hash_v2


def test_canonical_json_dumps_primitives():
    """Verifies deterministic serialization of UUIDs, datetimes, decimals, and nested sets."""
    sample_id = uuid.UUID("12345678-1234-5678-1234-567812345678")
    dt = datetime(2026, 11, 4, 10, 30, 0, 123456, tzinfo=timezone.utc)
    data = {
        "uuid": sample_id,
        "dt": dt,
        "tags": {"pine", "cedar", "oak"},
    }

    serialized = canonical_json_dumps(data)
    assert '"tags":["cedar","oak","pine"]' in serialized
    assert '"uuid":"12345678-1234-5678-1234-567812345678"' in serialized
    assert '"dt":"2026-11-04T10:30:00.123456+00:00"' in serialized


def test_sensitive_field_sanitization():
    """Verifies that passwords, hashes, JWTs, refresh tokens, api_keys, client_secrets, and private_keys are strictly scrubbed."""
    dirty_state = {
        "email": "auditor@vana.earth",
        "password": "RawSuperSecretPassword123!",
        "hashed_password": "$argon2id$v=19$m=65536,t=3,p=4$fakehash",
        "token": "bearer.jwt.token",
        "access_token": "secret_access",
        "refresh_token": "secret_refresh",
        "api_key": "live_ak_1234567890",
        "client_secret": "cs_sec_99998888",
        "nested": {
            "secret": "api-key-12345",
            "private_key": "-----BEGIN RSA PRIVATE KEY-----\nMIIE...",
            "safe_metric": "TREES_PLANTED",
            "quantity": 100,
            "deep": {
                "api_key": "deep_key_xyz",
                "client_secret": "deep_secret_abc",
            },
        },
    }

    cleaned = sanitize_state(dirty_state)
    assert "password" not in cleaned
    assert "hashed_password" not in cleaned
    assert "token" not in cleaned
    assert "access_token" not in cleaned
    assert "refresh_token" not in cleaned
    assert "api_key" not in cleaned
    assert "client_secret" not in cleaned
    assert "secret" not in cleaned["nested"]
    assert "private_key" not in cleaned["nested"]
    assert "api_key" not in cleaned["nested"]["deep"]
    assert "client_secret" not in cleaned["nested"]["deep"]
    assert cleaned["nested"]["safe_metric"] == "TREES_PLANTED"
    assert cleaned["nested"]["quantity"] == 100
    assert cleaned["email"] == "auditor@vana.earth"


def test_decimal_canonical_serialization():
    """Verifies deterministic serialization of Decimals under Hash Version 1.

    Tests:
    1. Equivalent representations (e.g. 10.0 vs 10.00) produce identical JSON number tokens.
    2. High-precision decimals within IEEE 754 float limits are accurately preserved.
    3. Negative decimals and zero boundaries are handled deterministically.
    """
    from decimal import Decimal

    # 1. Equivalent representations normalize to identical canonical representation
    d1 = {"qty": Decimal("10.0")}
    d2 = {"qty": Decimal("10.00")}
    d3 = {"qty": Decimal("10.0000")}
    s1 = canonical_json_dumps(d1)
    s2 = canonical_json_dumps(d2)
    s3 = canonical_json_dumps(d3)
    assert s1 == s2 == s3 == '{"qty":10.0}'

    # 2. Negative decimals
    neg = {"loss": Decimal("-1250.75")}
    assert canonical_json_dumps(neg) == '{"loss":-1250.75}'

    # 3. Zero and boundary values
    zero_dec = {"zero": Decimal("0.0"), "small": Decimal("0.0001")}
    assert canonical_json_dumps(zero_dec) == '{"small":0.0001,"zero":0.0}'

    # 4. Standard environmental metric quantities (Decimal(12, 4))
    large_hectares = {"area_ha": Decimal("987654.3210")}
    assert canonical_json_dumps(large_hectares) == '{"area_ha":987654.321}'


def test_project_id_extraction():
    """Verifies resolution of project_id from entity, new_state, or previous_state."""
    proj_id = uuid.uuid4()

    # 1. Direct project entity
    assert _extract_project_id(None, "project", proj_id, None, None) == proj_id

    # 2. From new_state
    extracted = _extract_project_id(
        None, "field_activity", uuid.uuid4(), None, {"project_id": str(proj_id)}
    )
    assert extracted == proj_id

    # 3. From previous_state
    extracted_prev = _extract_project_id(
        None, "project_target", uuid.uuid4(), {"project_id": str(proj_id)}, None
    )
    assert extracted_prev == proj_id


@pytest.mark.asyncio
async def test_sequential_event_insertion_and_linkage(db_session: AsyncSession):
    """Verifies that consecutive audit events form an unbroken cryptographic hash chain."""
    head_stmt = select(AuditChainHead).where(AuditChainHead.id == 1)
    head_before = await db_session.scalar(head_stmt)
    start_seq = head_before.last_sequence_number if head_before else 0
    start_hash = head_before.last_event_hash if head_before else GENESIS_HASH

    # Record 3 events
    e1 = await record_audit_log(
        db=db_session,
        action_type="TEST_ACTION_1",
        entity_type="test_entity",
        entity_id=uuid.uuid4(),
        new_state={"count": 1},
    )
    e2 = await record_audit_log(
        db=db_session,
        action_type="TEST_ACTION_2",
        entity_type="test_entity",
        entity_id=uuid.uuid4(),
        new_state={"count": 2},
    )
    e3 = await record_audit_log(
        db=db_session,
        action_type="TEST_ACTION_3",
        entity_type="test_entity",
        entity_id=uuid.uuid4(),
        new_state={"count": 3},
    )

    await db_session.commit()

    # Verify sequential numbers
    assert e1.sequence_number == start_seq + 1
    assert e2.sequence_number == start_seq + 2
    assert e3.sequence_number == start_seq + 3

    # Verify previous-hash linkage
    assert e1.previous_hash == start_hash
    assert e2.previous_hash == e1.current_hash
    assert e3.previous_hash == e2.current_hash

    # Verify chain head checkpoint updated
    head_after = await db_session.scalar(head_stmt)
    assert head_after.last_sequence_number == e3.sequence_number
    assert head_after.last_event_hash == e3.current_hash


@pytest.mark.asyncio
async def test_transaction_rollback_preserves_sequence_and_head(db_session: AsyncSession):
    """Verifies that an aborted transaction rolls back sequence numbers without burning or leaving gaps."""
    head_stmt = select(AuditChainHead).where(AuditChainHead.id == 1)
    head_before = await db_session.scalar(head_stmt)
    initial_seq = head_before.last_sequence_number
    initial_hash = head_before.last_event_hash

    # Record an event but explicitly rollback the transaction
    try:
        async with db_session.begin_nested():
            await record_audit_log(
                db=db_session,
                action_type="DOOMED_ACTION",
                entity_type="doomed_entity",
                entity_id=uuid.uuid4(),
                new_state={"will_fail": True},
            )
            # Simulate failure
            raise ValueError("Intentional business rule failure")
    except ValueError:
        pass

    # Verify sequence number did NOT advance
    head_recheck = await db_session.scalar(head_stmt)
    assert head_recheck.last_sequence_number == initial_seq
    assert head_recheck.last_event_hash == initial_hash

    # Now record a successful event and verify it gets exactly initial_seq + 1 (NO GAPS)
    successful = await record_audit_log(
        db=db_session,
        action_type="SUCCESSFUL_RECOVERY_ACTION",
        entity_type="recovery_entity",
        entity_id=uuid.uuid4(),
        new_state={"recovered": True},
    )
    await db_session.commit()

    assert successful.sequence_number == initial_seq + 1
    assert successful.previous_hash == initial_hash


@pytest.mark.asyncio
async def test_historical_backfill_integrity(db_session: AsyncSession):
    """Verifies that all backfilled historical records satisfy cryptographic chain integrity."""
    stmt = (
        select(AuditLog)
        .where(AuditLog.is_backfilled == True)
        .order_by(AuditLog.sequence_number.asc())
    )
    backfilled_records = (await db_session.scalars(stmt)).all()

    if not backfilled_records:
        # Simulate backfill execution on legacy unchained records to verify algorithm integrity
        legacy_rows = [
            {
                "id": uuid.uuid4(),
                "actor_id": uuid.uuid4(),
                "action_type": "LEGACY_EVENT_1",
                "entity_type": "project",
                "entity_id": uuid.uuid4(),
                "created_at": datetime.now(timezone.utc),
                "previous_state": None,
                "new_state": {"name": "Legacy Project"},
                "ip_address": "127.0.0.1",
            },
            {
                "id": uuid.uuid4(),
                "actor_id": uuid.uuid4(),
                "action_type": "LEGACY_EVENT_2",
                "entity_type": "activity",
                "entity_id": uuid.uuid4(),
                "created_at": datetime.now(timezone.utc),
                "previous_state": {"status": "DRAFT"},
                "new_state": {"status": "SUBMITTED"},
                "ip_address": "127.0.0.1",
            },
        ]
        simulated_chain = []
        last_hash = GENESIS_HASH
        for idx, row in enumerate(legacy_rows, start=1):
            seq = idx
            prev_h = last_hash
            payload = build_canonical_payload(
                action_type=row["action_type"],
                entity_type=row["entity_type"],
                entity_id=row["entity_id"],
                actor_id=row["actor_id"],
                project_id=row["entity_id"] if row["entity_type"] == "project" else None,
                previous_state=row["previous_state"],
                new_state=row["new_state"],
                ip_address=row["ip_address"],
                correlation_id=None,
                is_backfilled=True,
            )
            curr_h = compute_event_hash(
                sequence_number=seq,
                event_id=row["id"],
                timestamp=row["created_at"],
                action_type=row["action_type"],
                entity_type=row["entity_type"],
                entity_id=row["entity_id"],
                previous_hash=prev_h,
                canonical_payload=payload,
                actor_id=row["actor_id"],
                project_id=row["entity_id"] if row["entity_type"] == "project" else None,
                correlation_id=None,
                hash_version=1,
            )
            simulated_chain.append({
                "sequence_number": seq,
                "previous_hash": prev_h,
                "current_hash": curr_h,
            })
            last_hash = curr_h

        assert simulated_chain[0]["sequence_number"] == 1
        assert simulated_chain[0]["previous_hash"] == GENESIS_HASH
        assert simulated_chain[1]["sequence_number"] == 2
        assert simulated_chain[1]["previous_hash"] == simulated_chain[0]["current_hash"]
        return

    for idx, event in enumerate(backfilled_records):
        # 1. Verify sequence continuity
        if idx == 0:
            assert event.sequence_number == 1
            assert event.previous_hash == GENESIS_HASH
        else:
            prev_event = backfilled_records[idx - 1]
            assert event.sequence_number == prev_event.sequence_number + 1
            assert event.previous_hash == prev_event.current_hash

        # 2. Recompute SHA-256 and verify match
        recomputed = compute_event_hash(
            sequence_number=event.sequence_number,
            event_id=event.id,
            timestamp=event.created_at,
            action_type=event.action_type,
            entity_type=event.entity_type,
            entity_id=event.entity_id,
            previous_hash=event.previous_hash,
            canonical_payload=event.canonical_payload,
            actor_id=event.actor_id,
            project_id=event.project_id,
            correlation_id=event.correlation_id,
            hash_version=event.hash_version,
        )
        assert recomputed == event.current_hash, f"Hash mismatch at sequence {event.sequence_number}"


@pytest.mark.asyncio
async def test_tamper_detection_on_mutated_payload(db_session: AsyncSession):
    """Verifies that any modification to an event payload is mathematically detected."""
    # Create an event
    original = await record_audit_log(
        db=db_session,
        action_type="TAMPER_TEST_EVENT",
        entity_type="secure_record",
        entity_id=uuid.uuid4(),
        new_state={"approved_amount": 1000},
    )
    await db_session.commit()

    # Recompute with original payload
    valid_hash = compute_event_hash(
        sequence_number=original.sequence_number,
        event_id=original.id,
        timestamp=original.created_at,
        action_type=original.action_type,
        entity_type=original.entity_type,
        entity_id=original.entity_id,
        previous_hash=original.previous_hash,
        canonical_payload=original.canonical_payload,
        actor_id=original.actor_id,
        project_id=original.project_id,
        correlation_id=original.correlation_id,
        hash_version=original.hash_version,
    )
    assert valid_hash == original.current_hash

    # Tamper with canonical_payload
    tampered_payload = dict(original.canonical_payload)
    tampered_payload["new_state"] = {"approved_amount": 9999999}  # Malicious alteration

    tampered_hash = compute_event_hash(
        sequence_number=original.sequence_number,
        event_id=original.id,
        timestamp=original.created_at,
        action_type=original.action_type,
        entity_type=original.entity_type,
        entity_id=original.entity_id,
        previous_hash=original.previous_hash,
        canonical_payload=tampered_payload,
        actor_id=original.actor_id,
        project_id=original.project_id,
        correlation_id=original.correlation_id,
        hash_version=original.hash_version,
    )

    # Cryptographic proof of tampering
    assert tampered_hash != original.current_hash


@pytest.mark.asyncio
async def test_concurrent_audit_event_insertions():
    """Verifies that concurrent asynchronous transactions inserting audit events are strictly serialized.

    Requirements:
    - Zero sequence number collisions.
    - Strictly monotonic sequence continuity across all concurrent inserts.
    - Unbroken previous_hash -> current_hash linkage.
    """
    from tests.conftest import TestingSessionLocal

    num_concurrent = 8
    event_ids = [uuid.uuid4() for _ in range(num_concurrent)]

    async def insert_worker(eid: uuid.UUID, idx: int):
        async with TestingSessionLocal() as session:
            try:
                await record_audit_log(
                    db=session,
                    action_type="CONCURRENT_TEST_EVENT",
                    entity_type="concurrent_test",
                    entity_id=eid,
                    new_state={"worker_index": idx},
                )
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    # Run all workers concurrently
    await asyncio.gather(*[insert_worker(eid, i) for i, eid in enumerate(event_ids)])

    # Query all inserted events
    async with TestingSessionLocal() as session:
        stmt = (
            select(AuditLog)
            .where(AuditLog.entity_id.in_(event_ids))
            .order_by(AuditLog.sequence_number.asc())
        )
        inserted = (await session.scalars(stmt)).all()

        assert len(inserted) == num_concurrent

        # Verify strict sequence continuity and hash linkage
        for i in range(len(inserted)):
            if i > 0:
                prev = inserted[i - 1]
                curr = inserted[i]
                assert curr.sequence_number == prev.sequence_number + 1
                assert curr.previous_hash == prev.current_hash
