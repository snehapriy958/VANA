"""VANA Audit Domain — Pydantic Schemas.

Defines API data models for read-only audit log queries, verification history,
and cryptographic chain verification responses.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class AuditLogRead(BaseModel):
    """Pydantic model representing a single cryptographically chained audit log record."""

    id: uuid.UUID
    sequence_number: int
    actor_id: Optional[uuid.UUID] = None
    project_id: Optional[uuid.UUID] = None
    action_type: str
    entity_type: str
    entity_id: uuid.UUID
    previous_state: Optional[Dict[str, Any]] = None
    new_state: Optional[Dict[str, Any]] = None
    canonical_payload: Dict[str, Any]
    previous_hash: str
    current_hash: str
    hash_version: int
    correlation_id: Optional[str] = None
    is_backfilled: bool
    ip_address: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuditLogListResponse(BaseModel):
    """Paginated response envelope for audit ledger log records."""

    items: List[AuditLogRead]
    total: int
    page: int
    page_size: int
    total_pages: int


class AuditVerificationItem(BaseModel):
    """Structured view of a verification lifecycle decision event."""

    sequence_number: int
    event_id: uuid.UUID
    action_type: str
    entity_type: str
    activity_id: Optional[uuid.UUID] = None
    revision_id: Optional[uuid.UUID] = None
    revision_number: Optional[int] = None
    project_id: Optional[uuid.UUID] = None
    actor_id: Optional[uuid.UUID] = None
    verifier_id: Optional[uuid.UUID] = None
    status: Optional[str] = None
    verified_quantity: Optional[float] = None
    rejection_reason_code: Optional[str] = None
    review_notes: Optional[str] = None
    current_hash: str
    previous_hash: str
    created_at: datetime


class AuditVerificationHistoryResponse(BaseModel):
    """Paginated response envelope for verification lifecycle events."""

    items: List[AuditVerificationItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class AuditVerificationError(BaseModel):
    """Details of a cryptographic integrity or state consistency error."""

    sequence_number: Optional[int] = None
    event_id: Optional[uuid.UUID] = None
    error_type: str
    message: str
    expected: Optional[str] = None
    actual: Optional[str] = None


class AuditVerifyChainRequest(BaseModel):
    """Optional payload to restrict cryptographic chain verification to a specific sequence interval."""

    from_sequence: Optional[int] = Field(None, ge=1)
    to_sequence: Optional[int] = Field(None, ge=1)


class AuditChainVerificationResponse(BaseModel):
    """Result report of read-only cryptographic chain integrity verification."""

    is_valid: bool
    status: str = Field("VALID", description="'VALID', 'COMPROMISED', or 'EMPTY'")
    total_events_checked: int
    chain_head_sequence: int
    chain_head_hash: str
    last_verified_sequence: Optional[int] = None
    first_failure_sequence: Optional[int] = None
    failure_category: Optional[str] = None
    errors: List[AuditVerificationError] = Field(default_factory=list)
    verified_at: datetime
    disclaimer: str = (
        "Cryptographic SHA-256 hash chaining mathematically proves sequential continuity, "
        "detects state tampering, and surfaces record deletion within the database. It does not, "
        "however, prevent a privileged database administrator with physical table rewrite access "
        "from recalculating the entire chain from scratch unless external cross-anchored signatures "
        "or write-once immutable storage layers are used."
    )
