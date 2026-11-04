import enum
from datetime import date, datetime, timezone
from typing import List, Optional
import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class InspectionStatus(str, enum.Enum):
    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class InspectionType(str, enum.Enum):
    ROUTINE = "ROUTINE"
    SURVIVAL_CHECK = "SURVIVAL_CHECK"
    MAINTENANCE_AUDIT = "MAINTENANCE_AUDIT"
    EMERGENCY = "EMERGENCY"


class CanopyCondition(str, enum.Enum):
    EXCELLENT = "EXCELLENT"
    HEALTHY = "HEALTHY"
    STRESSED = "STRESSED"
    CRITICAL = "CRITICAL"


class SoilMoistureCondition(str, enum.Enum):
    SATURATED = "SATURATED"
    ADEQUATE = "ADEQUATE"
    DRY = "DRY"
    SEVERELY_PARCHED = "SEVERELY_PARCHED"


class TaskCategory(str, enum.Enum):
    IRRIGATION = "IRRIGATION"
    WEEDING = "WEEDING"
    MULCHING = "MULCHING"
    FENCING_REPAIR = "FENCING_REPAIR"
    REPLANTING_PREP = "REPLANTING_PREP"
    PEST_CONTROL = "PEST_CONTROL"
    SOIL_ENRICHMENT = "SOIL_ENRICHMENT"
    OTHER = "OTHER"


class TaskPriority(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"


class TaskStatus(str, enum.Enum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class SurvivalMethodology(str, enum.Enum):
    SAMPLE_PLOT = "SAMPLE_PLOT"
    TRANSECT = "TRANSECT"
    FULL_CENSUS = "FULL_CENSUS"


class FieldInspection(Base):
    __tablename__ = "field_inspections"
    __table_args__ = (
        UniqueConstraint("id", "project_id", name="uq_inspections_id_project"),
        ForeignKeyConstraint(
            ["linked_activity_id", "project_id"],
            ["field_activities.id", "field_activities.project_id"],
            ondelete="SET NULL",
            name="fk_inspections_linked_activity",
        ),
        CheckConstraint(
            "status IN ('SCHEDULED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED')",
            name="chk_inspection_status",
        ),
        CheckConstraint(
            "inspection_type IN ('ROUTINE', 'SURVIVAL_CHECK', 'MAINTENANCE_AUDIT', 'EMERGENCY')",
            name="chk_inspection_type",
        ),
        CheckConstraint(
            "vegetation_health_score IS NULL OR (vegetation_health_score >= 1 AND vegetation_health_score <= 5)",
            name="chk_vegetation_health_score",
        ),
        CheckConstraint(
            "canopy_condition IS NULL OR canopy_condition IN ('EXCELLENT', 'HEALTHY', 'STRESSED', 'CRITICAL')",
            name="chk_canopy_condition",
        ),
        CheckConstraint(
            "soil_moisture_condition IS NULL OR soil_moisture_condition IN ('SATURATED', 'ADEQUATE', 'DRY', 'SEVERELY_PARCHED')",
            name="chk_soil_moisture",
        ),
        Index("idx_inspections_project_status_date", "project_id", "status", "scheduled_date"),
        Index("idx_inspections_assigned", "assigned_to_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    linked_activity_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, nullable=True)
    scheduled_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default=InspectionStatus.SCHEDULED.value, nullable=False)
    inspection_type: Mapped[str] = mapped_column(String(32), default=InspectionType.ROUTINE.value, nullable=False)
    assigned_to_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    findings: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    vegetation_health_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    canopy_condition: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    soil_moisture_condition: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    threats_detected: Mapped[Optional[list]] = mapped_column(JSONB, default=list, nullable=True)
    addenda: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
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
    project: Mapped["Project"] = relationship("Project")
    assigned_to: Mapped[Optional["User"]] = relationship("User")
    linked_activity: Mapped[Optional["FieldActivity"]] = relationship(
        "FieldActivity",
        foreign_keys=[linked_activity_id, project_id],
        primaryjoin="and_(FieldInspection.linked_activity_id == FieldActivity.id, FieldInspection.project_id == FieldActivity.project_id)",
        overlaps="project",
    )
    maintenance_tasks: Mapped[List["MaintenanceTask"]] = relationship(
        "MaintenanceTask",
        back_populates="inspection",
        foreign_keys="[MaintenanceTask.inspection_id, MaintenanceTask.project_id]",
        primaryjoin="and_(FieldInspection.id == MaintenanceTask.inspection_id, FieldInspection.project_id == MaintenanceTask.project_id)",
        passive_deletes=True,
    )
    survival_observations: Mapped[List["SurvivalObservation"]] = relationship(
        "SurvivalObservation",
        back_populates="inspection",
        foreign_keys="[SurvivalObservation.inspection_id, SurvivalObservation.project_id]",
        primaryjoin="and_(FieldInspection.id == SurvivalObservation.inspection_id, FieldInspection.project_id == SurvivalObservation.project_id)",
        passive_deletes=True,
    )
    evidence_files: Mapped[List["EvidenceFile"]] = relationship(
        "EvidenceFile", back_populates="inspection"
    )


class MaintenanceTask(Base):
    __tablename__ = "maintenance_tasks"
    __table_args__ = (
        UniqueConstraint("id", "project_id", name="uq_tasks_id_project"),
        ForeignKeyConstraint(
            ["inspection_id", "project_id"],
            ["field_inspections.id", "field_inspections.project_id"],
            ondelete="SET NULL",
            name="fk_tasks_inspection",
        ),
        ForeignKeyConstraint(
            ["activity_id", "project_id"],
            ["field_activities.id", "field_activities.project_id"],
            ondelete="SET NULL",
            name="fk_tasks_activity",
        ),
        CheckConstraint(
            "category IN ('IRRIGATION', 'WEEDING', 'MULCHING', 'FENCING_REPAIR', 'REPLANTING_PREP', 'PEST_CONTROL', 'SOIL_ENRICHMENT', 'OTHER')",
            name="chk_task_category",
        ),
        CheckConstraint(
            "priority IN ('LOW', 'MEDIUM', 'HIGH', 'URGENT')",
            name="chk_task_priority",
        ),
        CheckConstraint(
            "status IN ('TODO', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED')",
            name="chk_task_status",
        ),
        Index("idx_tasks_project_status_due", "project_id", "status", "due_date"),
        Index("idx_tasks_assigned", "assigned_to_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    inspection_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, nullable=True)
    activity_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    priority: Mapped[str] = mapped_column(String(16), default=TaskPriority.MEDIUM.value, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default=TaskStatus.TODO.value, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    assigned_to_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completion_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
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
    project: Mapped["Project"] = relationship("Project", overlaps="maintenance_tasks")
    assigned_to: Mapped[Optional["User"]] = relationship("User")
    inspection: Mapped[Optional["FieldInspection"]] = relationship(
        "FieldInspection",
        back_populates="maintenance_tasks",
        foreign_keys=[inspection_id, project_id],
        primaryjoin="and_(MaintenanceTask.inspection_id == FieldInspection.id, MaintenanceTask.project_id == FieldInspection.project_id)",
        overlaps="project",
    )
    activity: Mapped[Optional["FieldActivity"]] = relationship(
        "FieldActivity",
        foreign_keys=[activity_id, project_id],
        primaryjoin="and_(MaintenanceTask.activity_id == FieldActivity.id, MaintenanceTask.project_id == FieldActivity.project_id)",
        overlaps="inspection,maintenance_tasks,project",
    )


class SurvivalObservation(Base):
    __tablename__ = "survival_observations"
    __table_args__ = (
        UniqueConstraint("id", "project_id", name="uq_survival_obs_id_project"),
        ForeignKeyConstraint(
            ["inspection_id", "project_id"],
            ["field_inspections.id", "field_inspections.project_id"],
            ondelete="SET NULL",
            name="fk_survival_inspection",
        ),
        ForeignKeyConstraint(
            ["activity_id", "project_id"],
            ["field_activities.id", "field_activities.project_id"],
            ondelete="RESTRICT",
            name="fk_survival_activity",
        ),
        CheckConstraint(
            "methodology IN ('SAMPLE_PLOT', 'TRANSECT', 'FULL_CENSUS')",
            name="chk_survival_methodology",
        ),
        CheckConstraint(
            "sample_size > 0 AND alive_count >= 0 AND dead_count >= 0",
            name="chk_survival_counts_positive",
        ),
        CheckConstraint(
            "(alive_count + dead_count) <= sample_size",
            name="chk_survival_sum_valid",
        ),
        CheckConstraint(
            "superseded_by_id IS NULL OR superseded_by_id != id",
            name="chk_survival_no_self_supersede",
        ),
        Index(
            "uq_active_survival_observation",
            "project_id",
            "plot_identifier",
            "cohort_identifier",
            "observation_date",
            unique=True,
            postgresql_where=text("is_active = TRUE"),
        ),
        Index(
            "idx_survival_project_plot_cohort",
            "project_id",
            "plot_identifier",
            "cohort_identifier",
            "observation_date",
        ),
        Index("idx_survival_active", "project_id", "is_active"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    activity_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, nullable=True)
    inspection_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, nullable=True)
    plot_identifier: Mapped[str] = mapped_column(String(64), nullable=False)
    cohort_identifier: Mapped[str] = mapped_column(String(64), nullable=False)
    methodology: Mapped[str] = mapped_column(
        String(32), default=SurvivalMethodology.SAMPLE_PLOT.value, nullable=False
    )
    coverage_area_sqm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    observation_date: Mapped[date] = mapped_column(Date, nullable=False)
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False)
    alive_count: Mapped[int] = mapped_column(Integer, nullable=False)
    dead_count: Mapped[int] = mapped_column(Integer, nullable=False)
    mortality_causes: Mapped[Optional[list]] = mapped_column(JSONB, default=list, nullable=True)
    is_definitive: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    superseded_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("survival_observations.id", ondelete="RESTRICT", deferrable=True, initially="DEFERRED"),
        nullable=True,
    )
    correction_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", overlaps="survival_observations")
    inspection: Mapped[Optional["FieldInspection"]] = relationship(
        "FieldInspection",
        back_populates="survival_observations",
        foreign_keys=[inspection_id, project_id],
        primaryjoin="and_(SurvivalObservation.inspection_id == FieldInspection.id, SurvivalObservation.project_id == FieldInspection.project_id)",
        overlaps="project",
    )
    activity: Mapped[Optional["FieldActivity"]] = relationship(
        "FieldActivity",
        foreign_keys=[activity_id, project_id],
        primaryjoin="and_(SurvivalObservation.activity_id == FieldActivity.id, SurvivalObservation.project_id == FieldActivity.project_id)",
        overlaps="inspection,project,survival_observations",
    )
    superseded_by: Mapped[Optional["SurvivalObservation"]] = relationship(
        "SurvivalObservation",
        remote_side=[id],
        foreign_keys=[superseded_by_id],
        post_update=True,
    )

    @property
    def survival_rate(self) -> Optional[float]:
        """
        Derives observed sample survival rate on-demand.
        Returns None when assessed denominator (alive_count + dead_count) is zero.
        """
        assessed = self.alive_count + self.dead_count
        if assessed == 0:
            return None
        return round((self.alive_count / assessed) * 100, 2)
