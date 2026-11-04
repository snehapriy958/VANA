import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, Optional
from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.domains.audit.hashing import GENESIS_HASH

if TYPE_CHECKING:
    from app.domains.auth.models import User
    from app.domains.projects.models import Project


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("idx_audit_logs_entity", "entity_type", "entity_id"),
        Index("idx_audit_logs_created_at_desc", "created_at"),
        Index("idx_audit_logs_project_created", "project_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    sequence_number: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entity_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    previous_state: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    new_state: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    canonical_payload: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    previous_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    current_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    hash_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    correlation_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    is_backfilled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    actor: Mapped[Optional["User"]] = relationship("User", back_populates="audit_events")
    project: Mapped[Optional["Project"]] = relationship("Project")


class AuditChainHead(Base):
    __tablename__ = "audit_chain_head"
    __table_args__ = (
        CheckConstraint("id = 1", name="chk_audit_chain_head_single_row"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    last_sequence_number: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    last_event_hash: Mapped[str] = mapped_column(String(64), nullable=False, default=GENESIS_HASH)
    total_events: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
