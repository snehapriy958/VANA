import enum
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List
from sqlalchemy import Boolean, DateTime, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

if TYPE_CHECKING:
    from app.domains.teams.models import ProjectAssignment
    from app.domains.operations.models import FieldActivity, ActivityRevision
    from app.domains.audit.models import AuditLog


class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    PROJECT_MANAGER = "PROJECT_MANAGER"
    FIELD_OFFICER = "FIELD_OFFICER"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    role: Mapped[str] = mapped_column(
        String(32), index=True, nullable=False, default=UserRole.FIELD_OFFICER.value
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
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
    project_assignments: Mapped[List["ProjectAssignment"]] = relationship(
        "ProjectAssignment", back_populates="user", cascade="all, delete-orphan"
    )
    submitted_activities: Mapped[List["FieldActivity"]] = relationship(
        "FieldActivity", back_populates="created_by"
    )
    verified_revisions: Mapped[List["ActivityRevision"]] = relationship(
        "ActivityRevision", back_populates="verifier"
    )
    audit_events: Mapped[List["AuditLog"]] = relationship(
        "AuditLog", back_populates="actor"
    )
