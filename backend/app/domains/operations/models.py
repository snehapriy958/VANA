import enum
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

if TYPE_CHECKING:
    from app.domains.auth.models import User
    from app.domains.projects.models import Project
    from app.domains.monitoring.models import FieldInspection


class ActivityStatus(str, enum.Enum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


class RejectionReasonCode(str, enum.Enum):
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    COORDINATES_MISMATCH = "COORDINATES_MISMATCH"
    INCORRECT_UNIT_OR_QUANTITY = "INCORRECT_UNIT_OR_QUANTITY"
    DUPLICATE_SUBMISSION = "DUPLICATE_SUBMISSION"
    DATA_ENTRY_ERROR = "DATA_ENTRY_ERROR"


class FieldActivity(Base):
    __tablename__ = "field_activities"
    __table_args__ = (
        UniqueConstraint("id", "project_id", name="uq_field_activities_id_project"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    metric_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    current_revision_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="activities")
    created_by: Mapped["User"] = relationship("User", back_populates="submitted_activities")
    revisions: Mapped[List["ActivityRevision"]] = relationship(
        "ActivityRevision", back_populates="activity", cascade="all, delete-orphan"
    )
    evidence_files: Mapped[List["EvidenceFile"]] = relationship(
        "EvidenceFile", back_populates="activity", cascade="all, delete-orphan"
    )


class ActivityRevision(Base):
    __tablename__ = "activity_revisions"
    __table_args__ = (
        UniqueConstraint("activity_id", "revision_number", name="uq_activity_revision_number"),
        CheckConstraint("revision_number >= 1", name="chk_revision_number_positive"),
        CheckConstraint("quantity > 0", name="chk_revision_quantity_positive"),
        CheckConstraint(
            "latitude IS NULL OR (latitude >= -90.0 AND latitude <= 90.0)",
            name="chk_revision_latitude",
        ),
        CheckConstraint(
            "longitude IS NULL OR (longitude >= -180.0 AND longitude <= 180.0)",
            name="chk_revision_longitude",
        ),
        CheckConstraint(
            "gps_accuracy_meters IS NULL OR gps_accuracy_meters >= 0",
            name="chk_revision_gps_accuracy",
        ),
        CheckConstraint(
            "(is_active_ledger_entry = FALSE) OR (is_active_ledger_entry = TRUE AND status = 'VERIFIED')",
            name="chk_active_ledger_verified",
        ),
        CheckConstraint(
            "(status != 'REJECTED') OR (status = 'REJECTED' AND rejection_reason_code IS NOT NULL AND review_notes IS NOT NULL)",
            name="chk_rejection_reason_required",
        ),
        CheckConstraint(
            "(status != 'VERIFIED') OR (status = 'VERIFIED' AND verifier_id IS NOT NULL AND verified_at IS NOT NULL)",
            name="chk_verification_signature_required",
        ),
        Index(
            "uq_activity_single_active_ledger",
            "activity_id",
            unique=True,
            postgresql_where=text("is_active_ledger_entry = TRUE"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    activity_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("field_activities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    activity_date: Mapped[date] = mapped_column(Date, nullable=False)
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    gps_accuracy_meters: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    field_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), default=ActivityStatus.PENDING.value, nullable=False, index=True
    )
    is_active_ledger_entry: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True
    )
    verifier_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    activity: Mapped["FieldActivity"] = relationship("FieldActivity", back_populates="revisions")
    verifier: Mapped[Optional["User"]] = relationship("User", back_populates="verified_revisions")
    evidence_files: Mapped[List["EvidenceFile"]] = relationship(
        "EvidenceFile", back_populates="revision", cascade="all, delete-orphan"
    )


class EvidenceFile(Base):
    __tablename__ = "evidence_files"
    __table_args__ = (
        CheckConstraint("file_size_bytes > 0", name="chk_evidence_file_size_positive"),
        CheckConstraint(
            "(activity_id IS NOT NULL AND revision_id IS NOT NULL AND inspection_id IS NULL) OR "
            "(inspection_id IS NOT NULL AND activity_id IS NULL AND revision_id IS NULL)",
            name="chk_evidence_target",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    activity_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("field_activities.id", ondelete="CASCADE"), nullable=True, index=True
    )
    revision_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("activity_revisions.id", ondelete="CASCADE"), nullable=True, index=True
    )
    inspection_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("field_inspections.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    file_storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(64), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    caption: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    activity: Mapped[Optional["FieldActivity"]] = relationship("FieldActivity", back_populates="evidence_files")
    revision: Mapped[Optional["ActivityRevision"]] = relationship("ActivityRevision", back_populates="evidence_files")
    inspection: Mapped[Optional["FieldInspection"]] = relationship("FieldInspection", back_populates="evidence_files")
