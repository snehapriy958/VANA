"""VANA Audit Domain — Service Layer.

Implements immutable, tamper-evident audit event recording with transactional
row locking on audit_chain_head and deterministic cryptographic SHA-256 hash chaining.
"""

from datetime import datetime, timezone
import math
from typing import Any, Dict, List, Optional
import uuid
from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.domains.audit.hashing import (
    CURRENT_HASH_VERSION,
    GENESIS_HASH,
    build_canonical_payload,
    compute_event_hash,
)
from app.domains.audit.models import AuditChainHead, AuditLog
from app.domains.audit.schemas import (
    AuditChainVerificationResponse,
    AuditLogListResponse,
    AuditLogRead,
    AuditVerificationError,
    AuditVerificationHistoryResponse,
    AuditVerificationItem,
)
from app.domains.auth.models import User, UserRole
from app.domains.teams.models import ProjectAssignment

# Keys that must NEVER be persisted in audit log state diffs
SENSITIVE_KEYS = {
    "password",
    "hashed_password",
    "token",
    "access_token",
    "refresh_token",
    "secret",
    "jwt",
    "api_key",
    "client_secret",
    "private_key",
}


def sanitize_state(state: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Recursively removes sensitive credentials and hashes from audit payloads."""
    if not state or not isinstance(state, dict):
        return state

    cleaned: Dict[str, Any] = {}
    for key, val in state.items():
        if key.lower() in SENSITIVE_KEYS:
            continue
        if isinstance(val, dict):
            cleaned[key] = sanitize_state(val)
        elif isinstance(val, uuid.UUID):
            cleaned[key] = str(val).lower()
        elif isinstance(val, datetime):
            dt_utc = val.astimezone(timezone.utc) if val.tzinfo else val.replace(tzinfo=timezone.utc)
            cleaned[key] = dt_utc.isoformat()
        else:
            cleaned[key] = val
    return cleaned


def _extract_project_id(
    project_id: Optional[uuid.UUID],
    entity_type: str,
    entity_id: uuid.UUID,
    previous_state: Optional[Dict[str, Any]],
    new_state: Optional[Dict[str, Any]],
) -> Optional[uuid.UUID]:
    """Resolves project_id from argument, entity context, or payload snapshots."""
    if project_id:
        return project_id

    # If entity is directly a project
    if entity_type.lower() == "project":
        return entity_id

    # Try new_state
    if new_state and isinstance(new_state, dict):
        val = new_state.get("project_id")
        if val:
            try:
                return uuid.UUID(str(val))
            except (ValueError, TypeError):
                pass

    # Try previous_state
    if previous_state and isinstance(previous_state, dict):
        val = previous_state.get("project_id")
        if val:
            try:
                return uuid.UUID(str(val))
            except (ValueError, TypeError):
                pass

    return None


async def record_audit_log(
    db: AsyncSession,
    action_type: str,
    entity_type: str,
    entity_id: uuid.UUID,
    actor_id: Optional[uuid.UUID] = None,
    project_id: Optional[uuid.UUID] = None,
    previous_state: Optional[Dict[str, Any]] = None,
    new_state: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    correlation_id: Optional[str] = None,
) -> AuditLog:
    """Creates and persists a tamper-evident, cryptographically chained audit log record.

    Transactional Invariants:
    1. Row lock: Acquires `SELECT FOR UPDATE` on `audit_chain_head` within caller's transaction.
    2. Zero sequence gaps: If the caller transaction aborts/rolls back, sequence assignment rolls back.
    3. Deterministic Hash: Computes SHA-256 digest over canonical payload and previous event hash.
    4. Never commits: Enlists in caller's transaction via `await db.flush()`.
    """
    # 1. Resolve project_id
    resolved_project_id = _extract_project_id(
        project_id=project_id,
        entity_type=entity_type,
        entity_id=entity_id,
        previous_state=previous_state,
        new_state=new_state,
    )

    # 2. Acquire exclusive row lock on chain head for serialization
    stmt = select(AuditChainHead).where(AuditChainHead.id == 1).with_for_update()
    chain_head = await db.scalar(stmt)
    if chain_head is None:
        # Initialize if first call ever
        chain_head = AuditChainHead(
            id=1,
            last_sequence_number=0,
            last_event_hash=GENESIS_HASH,
            total_events=0,
            updated_at=datetime.now(timezone.utc),
        )
        db.add(chain_head)
        await db.flush()
        chain_head = await db.scalar(stmt)

    next_sequence = chain_head.last_sequence_number + 1
    previous_hash = chain_head.last_event_hash

    # 3. Sanitize states
    clean_prev = sanitize_state(previous_state)
    clean_new = sanitize_state(new_state)

    # 4. Construct canonical payload and hash envelope
    entry_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    canonical_payload = build_canonical_payload(
        action_type=action_type,
        entity_type=entity_type,
        entity_id=entity_id,
        actor_id=actor_id,
        project_id=resolved_project_id,
        previous_state=clean_prev,
        new_state=clean_new,
        ip_address=ip_address,
        correlation_id=correlation_id,
        is_backfilled=False,
    )

    current_hash = compute_event_hash(
        sequence_number=next_sequence,
        event_id=entry_id,
        timestamp=now,
        action_type=action_type,
        entity_type=entity_type,
        entity_id=entity_id,
        previous_hash=previous_hash,
        canonical_payload=canonical_payload,
        actor_id=actor_id,
        project_id=resolved_project_id,
        correlation_id=correlation_id,
        hash_version=CURRENT_HASH_VERSION,
    )

    # 5. Persist audit log record
    audit_entry = AuditLog(
        id=entry_id,
        sequence_number=next_sequence,
        actor_id=actor_id,
        project_id=resolved_project_id,
        action_type=action_type,
        entity_type=entity_type,
        entity_id=entity_id,
        previous_state=clean_prev,
        new_state=clean_new,
        canonical_payload=canonical_payload,
        previous_hash=previous_hash,
        current_hash=current_hash,
        hash_version=CURRENT_HASH_VERSION,
        correlation_id=correlation_id,
        is_backfilled=False,
        ip_address=ip_address,
        created_at=now,
    )
    db.add(audit_entry)

    # 6. Update chain head state
    chain_head.last_sequence_number = next_sequence
    chain_head.last_event_hash = current_hash
    chain_head.total_events += 1
    chain_head.updated_at = now

    # Flushes so the audit entry and chain head update are queued within caller's transaction
    await db.flush()
    return audit_entry


async def get_assigned_project_ids(db: AsyncSession, user_id: uuid.UUID) -> List[uuid.UUID]:
    """Retrieves all project IDs assigned to the given user."""
    stmt = select(ProjectAssignment.project_id).where(ProjectAssignment.user_id == user_id)
    result = await db.scalars(stmt)
    return list(result.all())


async def list_audit_events(
    db: AsyncSession,
    current_user: User,
    page: int = 1,
    page_size: int = 50,
    action_type: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[uuid.UUID] = None,
    actor_id: Optional[uuid.UUID] = None,
    project_id: Optional[uuid.UUID] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
) -> AuditLogListResponse:
    """Queries paginated audit events with strict multi-tenant project isolation and RBAC.

    RBAC Rules:
    - ADMIN: organization-wide access; optional project_id filter.
    - PROJECT_MANAGER: scoped strictly to assigned projects.
    - FIELD_OFFICER: 403 Forbidden.
    """
    if current_user.role == UserRole.FIELD_OFFICER.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="INSUFFICIENT_PERMISSIONS: Field Officers do not have permission to access audit ledger records",
        )

    filters = []

    if current_user.role == UserRole.PROJECT_MANAGER.value:
        assigned_pids = await get_assigned_project_ids(db, current_user.id)
        if project_id:
            if project_id not in assigned_pids:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="FORBIDDEN_PROJECT_ACCESS: You do not have access to this project's audit records",
                )
            filters.append(AuditLog.project_id == project_id)
        else:
            if not assigned_pids:
                return AuditLogListResponse(
                    items=[], total=0, page=page, page_size=page_size, total_pages=0
                )
            filters.append(AuditLog.project_id.in_(assigned_pids))
    elif current_user.role == UserRole.ADMIN.value:
        if project_id:
            filters.append(AuditLog.project_id == project_id)

    if action_type:
        filters.append(AuditLog.action_type == action_type)
    if entity_type:
        filters.append(AuditLog.entity_type == entity_type)
    if entity_id:
        filters.append(AuditLog.entity_id == entity_id)
    if actor_id:
        filters.append(AuditLog.actor_id == actor_id)
    if from_date:
        filters.append(AuditLog.created_at >= from_date)
    if to_date:
        filters.append(AuditLog.created_at <= to_date)

    count_stmt = select(func.count(AuditLog.id)).where(*filters)
    total = (await db.scalar(count_stmt)) or 0
    total_pages = math.ceil(total / page_size) if total > 0 else 0

    stmt = (
        select(AuditLog)
        .where(*filters)
        .order_by(AuditLog.sequence_number.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = (await db.scalars(stmt)).all()

    return AuditLogListResponse(
        items=[AuditLogRead.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


async def get_audit_event_by_id(
    db: AsyncSession,
    current_user: User,
    event_id: uuid.UUID,
) -> AuditLogRead:
    """Retrieves a single audit log event by ID with RBAC and project scoping."""
    if current_user.role == UserRole.FIELD_OFFICER.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="INSUFFICIENT_PERMISSIONS: Field Officers do not have permission to access audit ledger records",
        )

    stmt = select(AuditLog).where(AuditLog.id == event_id)
    event = await db.scalar(stmt)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AUDIT_EVENT_NOT_FOUND: Audit event record does not exist",
        )

    if current_user.role == UserRole.PROJECT_MANAGER.value:
        assigned_pids = await get_assigned_project_ids(db, current_user.id)
        if not event.project_id or event.project_id not in assigned_pids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="FORBIDDEN_PROJECT_ACCESS: You do not have access to this audit event",
            )

    return AuditLogRead.model_validate(event)


async def get_verification_history(
    db: AsyncSession,
    current_user: User,
    activity_id: Optional[uuid.UUID] = None,
    project_id: Optional[uuid.UUID] = None,
    page: int = 1,
    page_size: int = 50,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
) -> AuditVerificationHistoryResponse:
    """Retrieves immutable verification lifecycle decisions with RBAC."""
    if current_user.role == UserRole.FIELD_OFFICER.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="INSUFFICIENT_PERMISSIONS: Field Officers do not have permission to access audit records",
        )

    verification_actions = [
        "ACTIVITY_CREATED",
        "ACTIVITY_AMENDED",
        "ACTIVITY_VERIFIED",
        "ACTIVITY_REJECTED",
        "ACTIVITY_ARCHIVED",
    ]

    filters = [AuditLog.action_type.in_(verification_actions)]

    if current_user.role == UserRole.PROJECT_MANAGER.value:
        assigned_pids = await get_assigned_project_ids(db, current_user.id)
        if project_id:
            if project_id not in assigned_pids:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="FORBIDDEN_PROJECT_ACCESS: You do not have access to this project's audit records",
                )
            filters.append(AuditLog.project_id == project_id)
        else:
            if not assigned_pids:
                return AuditVerificationHistoryResponse(
                    items=[], total=0, page=page, page_size=page_size, total_pages=0
                )
            filters.append(AuditLog.project_id.in_(assigned_pids))
    elif current_user.role == UserRole.ADMIN.value:
        if project_id:
            filters.append(AuditLog.project_id == project_id)

    if activity_id:
        filters.append(
            or_(
                AuditLog.entity_id == activity_id,
                AuditLog.canonical_payload["activity_id"].astext == str(activity_id),
                AuditLog.canonical_payload["new_state"]["activity_id"].astext == str(activity_id),
            )
        )
    if from_date:
        filters.append(AuditLog.created_at >= from_date)
    if to_date:
        filters.append(AuditLog.created_at <= to_date)

    count_stmt = select(func.count(AuditLog.id)).where(*filters)
    total = (await db.scalar(count_stmt)) or 0
    total_pages = math.ceil(total / page_size) if total > 0 else 0

    stmt = (
        select(AuditLog)
        .where(*filters)
        .order_by(AuditLog.sequence_number.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    records = (await db.scalars(stmt)).all()

    items: List[AuditVerificationItem] = []
    for r in records:
        ns = r.new_state or {}
        act_id = None
        if r.entity_type == "field_activity":
            act_id = r.entity_id
        elif ns.get("activity_id"):
            try:
                act_id = uuid.UUID(str(ns["activity_id"]))
            except (ValueError, TypeError):
                pass

        rev_id = None
        if r.entity_type == "activity_revision":
            rev_id = r.entity_id
        elif ns.get("revision_id"):
            try:
                rev_id = uuid.UUID(str(ns["revision_id"]))
            except (ValueError, TypeError):
                pass

        v_qty = ns.get("verified_quantity")
        if v_qty is None:
            v_qty = ns.get("amended_quantity") or ns.get("quantity")
        if v_qty is not None:
            try:
                v_qty = float(v_qty)
            except (ValueError, TypeError):
                v_qty = None

        verifier_id = None
        if ns.get("verifier_id"):
            try:
                verifier_id = uuid.UUID(str(ns["verifier_id"]))
            except (ValueError, TypeError):
                pass

        items.append(
            AuditVerificationItem(
                sequence_number=r.sequence_number,
                event_id=r.id,
                action_type=r.action_type,
                entity_type=r.entity_type,
                activity_id=act_id,
                revision_id=rev_id,
                revision_number=ns.get("revision_number"),
                project_id=r.project_id,
                actor_id=r.actor_id,
                verifier_id=verifier_id,
                status=ns.get("status"),
                verified_quantity=v_qty,
                rejection_reason_code=ns.get("rejection_reason_code"),
                review_notes=ns.get("review_notes"),
                current_hash=r.current_hash,
                previous_hash=r.previous_hash,
                created_at=r.created_at,
            )
        )

    return AuditVerificationHistoryResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


async def get_entity_audit_trail(
    db: AsyncSession,
    current_user: User,
    entity_type: str,
    entity_id: uuid.UUID,
    page: int = 1,
    page_size: int = 50,
) -> AuditLogListResponse:
    """Retrieves full audit trail for a specific entity."""
    if current_user.role == UserRole.FIELD_OFFICER.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="INSUFFICIENT_PERMISSIONS: Field Officers do not have permission to access audit records",
        )

    filters = [
        AuditLog.entity_type == entity_type,
        AuditLog.entity_id == entity_id,
    ]

    if current_user.role == UserRole.PROJECT_MANAGER.value:
        assigned_pids = await get_assigned_project_ids(db, current_user.id)
        if not assigned_pids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="FORBIDDEN_PROJECT_ACCESS: You do not have access to this entity's audit records",
            )
        filters.append(AuditLog.project_id.in_(assigned_pids))

    count_stmt = select(func.count(AuditLog.id)).where(*filters)
    total = (await db.scalar(count_stmt)) or 0
    total_pages = math.ceil(total / page_size) if total > 0 else 0

    stmt = (
        select(AuditLog)
        .where(*filters)
        .order_by(AuditLog.sequence_number.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = (await db.scalars(stmt)).all()

    if total == 0 and current_user.role == UserRole.PROJECT_MANAGER.value:
        # Check if entity exists in unassigned project
        unscoped_exists = await db.scalar(
            select(AuditLog.id).where(
                AuditLog.entity_type == entity_type, AuditLog.entity_id == entity_id
            ).limit(1)
        )
        if unscoped_exists:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="FORBIDDEN_PROJECT_ACCESS: You do not have access to this entity's audit records",
            )

    return AuditLogListResponse(
        items=[AuditLogRead.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


async def verify_audit_chain(
    db: AsyncSession,
    from_sequence: int = 1,
    to_sequence: Optional[int] = None,
) -> AuditChainVerificationResponse:
    """Performs read-only cryptographic chain integrity and state consistency verification.

    Checks:
    1. Sequence continuity: strictly contiguous (seq_i = seq_{i-1} + 1).
    2. Previous-hash linkage: prev_i equals curr_{i-1} (with prev_1 == GENESIS_HASH).
    3. Recomputed event hashes: SHA-256 over envelope matches current_hash.
    4. Canonical payload state consistency: previous_state & new_state in audit_logs match canonical_payload.
    5. Chain head consistency: chain head checkpoint matches latest ledger event.
    """
    now = datetime.now(timezone.utc)
    errors: List[AuditVerificationError] = []

    # 1. Fetch chain head
    chain_head = await db.scalar(select(AuditChainHead).where(AuditChainHead.id == 1))
    head_seq = chain_head.last_sequence_number if chain_head else 0
    head_hash = chain_head.last_event_hash if chain_head else GENESIS_HASH

    # 2. Query target events
    query = select(AuditLog).where(AuditLog.sequence_number >= from_sequence)
    if to_sequence:
        query = query.where(AuditLog.sequence_number <= to_sequence)
    query = query.order_by(AuditLog.sequence_number.asc())

    events = (await db.scalars(query)).all()

    if not events:
        if head_seq > 0 and from_sequence <= head_seq:
            errors.append(
                AuditVerificationError(
                    error_type="MISSING_EVENTS",
                    message=f"No events found in range {from_sequence}..{to_sequence or head_seq} but chain head reports {head_seq} total events",
                    expected=f"Events starting at sequence {from_sequence}",
                    actual="0 events retrieved",
                )
            )
        status_val = "EMPTY" if head_seq == 0 else "COMPROMISED"
        return AuditChainVerificationResponse(
            is_valid=len(errors) == 0,
            status=status_val,
            total_events_checked=0,
            chain_head_sequence=head_seq,
            chain_head_hash=head_hash,
            last_verified_sequence=0 if head_seq == 0 else None,
            first_failure_sequence=errors[0].sequence_number if errors else None,
            failure_category=errors[0].error_type if errors else None,
            errors=errors,
            verified_at=now,
        )

    expected_prev_hash: Optional[str] = None
    if from_sequence > 1:
        prev_record = await db.scalar(
            select(AuditLog).where(AuditLog.sequence_number == from_sequence - 1)
        )
        if prev_record:
            expected_prev_hash = prev_record.current_hash
        else:
            errors.append(
                AuditVerificationError(
                    sequence_number=from_sequence,
                    error_type="MISSING_PREDECESSOR",
                    message=f"Predecessor record at sequence {from_sequence - 1} not found",
                )
            )

    expected_seq = from_sequence
    for idx, event in enumerate(events):
        # Check 1: Sequence continuity
        if event.sequence_number != expected_seq:
            errors.append(
                AuditVerificationError(
                    sequence_number=event.sequence_number,
                    event_id=event.id,
                    error_type="SEQUENCE_GAP",
                    message=f"Sequence discontinuity: expected sequence {expected_seq}, found {event.sequence_number}",
                    expected=str(expected_seq),
                    actual=str(event.sequence_number),
                )
            )
            expected_seq = event.sequence_number

        # Check 2: Previous hash linkage
        if expected_seq == 1:
            if event.previous_hash != GENESIS_HASH:
                errors.append(
                    AuditVerificationError(
                        sequence_number=event.sequence_number,
                        event_id=event.id,
                        error_type="PREV_HASH_MISMATCH",
                        message=f"Genesis event at sequence 1 does not link to GENESIS_HASH",
                        expected=GENESIS_HASH,
                        actual=event.previous_hash,
                    )
                )
        elif expected_prev_hash is not None:
            if event.previous_hash.lower() != expected_prev_hash.lower():
                errors.append(
                    AuditVerificationError(
                        sequence_number=event.sequence_number,
                        event_id=event.id,
                        error_type="PREV_HASH_MISMATCH",
                        message=f"Broken hash link at sequence {event.sequence_number}: previous_hash does not match predecessor digest",
                        expected=expected_prev_hash.lower(),
                        actual=event.previous_hash.lower(),
                    )
                )

        # Check 3: Canonical payload structure
        if not isinstance(event.canonical_payload, dict):
            errors.append(
                AuditVerificationError(
                    sequence_number=event.sequence_number,
                    event_id=event.id,
                    error_type="CANONICAL_PAYLOAD_CORRUPTED",
                    message=f"Canonical payload at sequence {event.sequence_number} is corrupted or not a valid JSON object",
                )
            )

        # Check 4: Recompute event hash
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
        if recomputed != event.current_hash.lower():
            errors.append(
                AuditVerificationError(
                    sequence_number=event.sequence_number,
                    event_id=event.id,
                    error_type="HASH_MISMATCH",
                    message=f"Cryptographic digest mismatch at sequence {event.sequence_number}. Payload or metadata altered.",
                    expected=event.current_hash.lower(),
                    actual=recomputed,
                )
            )

        # Check 5: Canonical payload state consistency
        payload_prev = event.canonical_payload.get("previous_state") if isinstance(event.canonical_payload, dict) else None
        payload_new = event.canonical_payload.get("new_state") if isinstance(event.canonical_payload, dict) else None

        if event.previous_state != payload_prev:
            errors.append(
                AuditVerificationError(
                    sequence_number=event.sequence_number,
                    event_id=event.id,
                    error_type="STATE_DIVERGENCE",
                    message=f"previous_state column has diverged from canonical_payload at sequence {event.sequence_number}",
                )
            )
        if event.new_state != payload_new:
            errors.append(
                AuditVerificationError(
                    sequence_number=event.sequence_number,
                    event_id=event.id,
                    error_type="STATE_DIVERGENCE",
                    message=f"new_state column has diverged from canonical_payload at sequence {event.sequence_number}",
                )
            )

        expected_prev_hash = event.current_hash
        expected_seq += 1

    # Check 6: Chain head consistency if verifying up to latest record
    last_event = events[-1]
    if (to_sequence is None or to_sequence >= head_seq) and last_event.sequence_number == head_seq:
        if chain_head and (chain_head.last_event_hash.lower() != last_event.current_hash.lower()):
            errors.append(
                AuditVerificationError(
                    sequence_number=head_seq,
                    event_id=last_event.id,
                    error_type="CHAIN_HEAD_MISMATCH",
                    message=f"Chain head checkpoint hash does not match latest event hash",
                    expected=last_event.current_hash.lower(),
                    actual=chain_head.last_event_hash.lower(),
                )
            )

    is_valid = len(errors) == 0
    first_failure_seq: Optional[int] = None
    failure_cat: Optional[str] = None
    last_verified_seq: Optional[int] = None

    if errors:
        status_val = "COMPROMISED"
        first_failure_seq = errors[0].sequence_number
        failure_cat = errors[0].error_type
        if first_failure_seq and first_failure_seq > from_sequence:
            last_verified_seq = first_failure_seq - 1
        else:
            last_verified_seq = None
    else:
        status_val = "VALID"
        last_verified_seq = events[-1].sequence_number

    return AuditChainVerificationResponse(
        is_valid=is_valid,
        status=status_val,
        total_events_checked=len(events),
        chain_head_sequence=head_seq,
        chain_head_hash=head_hash,
        last_verified_sequence=last_verified_seq,
        first_failure_sequence=first_failure_seq,
        failure_category=failure_cat,
        errors=errors,
        verified_at=now,
    )
