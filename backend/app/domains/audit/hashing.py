"""VANA Audit Domain — Cryptographic Hashing Engine.

Implements deterministic canonical JSON serialization and SHA-256 event hash
chaining for the tamper-evident Immutability Ledger (Milestone 8).
"""

from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from typing import Any, Dict, Optional
import uuid

GENESIS_HASH: str = "0" * 64
CURRENT_HASH_VERSION: int = 1


def _canonical_serializer(obj: Any) -> Any:
    """Deterministic JSON serializer for canonical hash envelopes.

    Serialization Conventions (Hash Version 1):
    - UUID: normalized to lowercase standard 36-char string representation.
    - datetime: normalized to UTC ISO 8601 representation (+00:00 offset).
    - Decimal: mapped to IEEE 754 64-bit float (`float(obj)`).
      Accommodates all VANA environmental quantities (Decimal(12, 4)) with exact
      precision up to 15-17 significant digits while normalizing equivalent representations
      (e.g., Decimal('10.0') and Decimal('10.00') both serialize as 10.0).
      Future hash_versions (> 1) may introduce normalized Decimal string representation
      if arbitrary precision beyond 53 mantissa bits is required.
    - set: converted to lexicographically sorted list.
    - bytes: converted to lowercase hexadecimal string.
    """
    if isinstance(obj, uuid.UUID):
        return str(obj).lower()
    if isinstance(obj, datetime):
        # Guarantee strict UTC ISO 8601 formatting with microsecond precision and +00:00 offset
        dt_utc = obj.astimezone(timezone.utc) if obj.tzinfo else obj.replace(tzinfo=timezone.utc)
        return dt_utc.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, set):
        return sorted(list(obj))
    if isinstance(obj, bytes):
        return obj.hex()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable in canonical audit hash")


def canonical_json_dumps(data: Any) -> str:
    """Serializes arbitrary dictionary/data structures into a deterministic canonical string.

    Properties:
    - Strictly sorted dictionary keys at all nesting levels.
    - Zero superfluous whitespace (`separators=(',', ':')`).
    - Explicit UTF-8 character preservation (`ensure_ascii=False`).
    - Normalized UUID string lowercase formatting.
    - Normalized UTC ISO 8601 datetime representations.
    """
    return json.dumps(
        data,
        default=_canonical_serializer,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def build_canonical_payload(
    action_type: str,
    entity_type: str,
    entity_id: uuid.UUID,
    actor_id: Optional[uuid.UUID] = None,
    project_id: Optional[uuid.UUID] = None,
    previous_state: Optional[Dict[str, Any]] = None,
    new_state: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    correlation_id: Optional[str] = None,
    is_backfilled: bool = False,
) -> Dict[str, Any]:
    """Constructs the canonical payload dictionary stored in audit_logs.canonical_payload."""
    return {
        "action_type": action_type,
        "actor_id": str(actor_id).lower() if actor_id else None,
        "correlation_id": correlation_id,
        "entity_id": str(entity_id).lower(),
        "entity_type": entity_type,
        "ip_address": ip_address,
        "is_backfilled": is_backfilled,
        "new_state": new_state,
        "previous_state": previous_state,
        "project_id": str(project_id).lower() if project_id else None,
    }


def compute_event_hash(
    sequence_number: int,
    event_id: uuid.UUID,
    timestamp: datetime,
    action_type: str,
    entity_type: str,
    entity_id: uuid.UUID,
    previous_hash: str,
    canonical_payload: Dict[str, Any],
    actor_id: Optional[uuid.UUID] = None,
    project_id: Optional[uuid.UUID] = None,
    correlation_id: Optional[str] = None,
    hash_version: int = CURRENT_HASH_VERSION,
) -> str:
    """Computes the SHA-256 cryptographic digest for an audit ledger event.

    Formula (Version 1):
        Envelope = {
            "action_type": str,
            "actor_id": str | null,
            "canonical_payload": dict,
            "correlation_id": str | null,
            "entity_id": str,
            "entity_type": str,
            "event_id": str,
            "hash_version": int,
            "previous_hash": str,
            "project_id": str | null,
            "sequence_number": int,
            "timestamp": str (ISO 8601 UTC)
        }
        current_hash = SHA256(canonical_json_dumps(Envelope).encode('utf-8')).hexdigest().lower()
    """
    dt_utc = timestamp.astimezone(timezone.utc) if timestamp.tzinfo else timestamp.replace(tzinfo=timezone.utc)

    envelope: Dict[str, Any] = {
        "action_type": action_type,
        "actor_id": str(actor_id).lower() if actor_id else None,
        "canonical_payload": canonical_payload,
        "correlation_id": correlation_id,
        "entity_id": str(entity_id).lower(),
        "entity_type": entity_type,
        "event_id": str(event_id).lower(),
        "hash_version": hash_version,
        "previous_hash": previous_hash.lower(),
        "project_id": str(project_id).lower() if project_id else None,
        "sequence_number": sequence_number,
        "timestamp": dt_utc.isoformat(),
    }

    serialized = canonical_json_dumps(envelope).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest().lower()
