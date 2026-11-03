import uuid
from typing import Any, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.domains.audit.models import AuditLog

# Keys that must NEVER be persisted in audit log state diffs
SENSITIVE_KEYS = {
    "password",
    "hashed_password",
    "token",
    "access_token",
    "refresh_token",
    "secret",
    "jwt",
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
            cleaned[key] = str(val)
        else:
            cleaned[key] = val
    return cleaned


async def record_audit_log(
    db: AsyncSession,
    action_type: str,
    entity_type: str,
    entity_id: uuid.UUID,
    actor_id: Optional[uuid.UUID] = None,
    previous_state: Optional[Dict[str, Any]] = None,
    new_state: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
) -> AuditLog:
    """Creates and persists an immutable audit log record for state mutations."""
    audit_entry = AuditLog(
        id=uuid.uuid4(),
        actor_id=actor_id,
        action_type=action_type,
        entity_type=entity_type,
        entity_id=entity_id,
        previous_state=sanitize_state(previous_state),
        new_state=sanitize_state(new_state),
        ip_address=ip_address,
    )
    db.add(audit_entry)
    # Flushes so the audit entry is queued within the transaction
    await db.flush()
    return audit_entry
