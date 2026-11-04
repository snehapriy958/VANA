import enum
from datetime import date, datetime
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domains.monitoring.models import (
    CanopyCondition,
    InspectionStatus,
    InspectionType,
    SoilMoistureCondition,
    SurvivalMethodology,
    TaskCategory,
    TaskPriority,
    TaskStatus,
)


class AlertType(str, enum.Enum):
    OVERDUE_INSPECTION = "OVERDUE_INSPECTION"
    UPCOMING_INSPECTION = "UPCOMING_INSPECTION"
    OVERDUE_TASK = "OVERDUE_TASK"


class AlertSeverity(str, enum.Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


# ============================================================================
# Field Inspection Schemas
# ============================================================================


class FieldInspectionCreate(BaseModel):
    project_id: uuid.UUID
    scheduled_date: date
    inspection_type: InspectionType = InspectionType.ROUTINE
    assigned_to_id: Optional[uuid.UUID] = None
    linked_activity_id: Optional[uuid.UUID] = None


class InspectionStartRequest(BaseModel):
    notes: Optional[str] = None


class InspectionCompleteRequest(BaseModel):
    findings: str = Field(..., min_length=1)
    vegetation_health_score: Optional[int] = Field(None, ge=1, le=5)
    canopy_condition: Optional[CanopyCondition] = None
    soil_moisture_condition: Optional[SoilMoistureCondition] = None
    threats_detected: Optional[List[str]] = None


class InspectionCancelRequest(BaseModel):
    cancellation_reason: str = Field(..., min_length=3)


class InspectionAddendumCreate(BaseModel):
    content: str = Field(..., min_length=3)


class FieldInspectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    linked_activity_id: Optional[uuid.UUID] = None
    scheduled_date: date
    status: str
    inspection_type: str
    assigned_to_id: Optional[uuid.UUID] = None
    completed_at: Optional[datetime] = None
    findings: Optional[str] = None
    vegetation_health_score: Optional[int] = None
    canopy_condition: Optional[str] = None
    soil_moisture_condition: Optional[str] = None
    threats_detected: Optional[List[Any]] = None
    addenda: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


# ============================================================================
# Maintenance Task Schemas
# ============================================================================


class MaintenanceTaskCreate(BaseModel):
    project_id: uuid.UUID
    title: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = None
    category: TaskCategory
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: date
    assigned_to_id: Optional[uuid.UUID] = None
    inspection_id: Optional[uuid.UUID] = None
    activity_id: Optional[uuid.UUID] = None


class TaskStartRequest(BaseModel):
    notes: Optional[str] = None


class TaskCompleteRequest(BaseModel):
    completion_notes: str = Field(..., min_length=3)


class TaskCancelRequest(BaseModel):
    cancellation_reason: str = Field(..., min_length=3)


class TaskReopenRequest(BaseModel):
    justification: str = Field(..., min_length=3)


class MaintenanceTaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    inspection_id: Optional[uuid.UUID] = None
    activity_id: Optional[uuid.UUID] = None
    title: str
    description: Optional[str] = None
    category: str
    priority: str
    status: str
    due_date: date
    assigned_to_id: Optional[uuid.UUID] = None
    completed_at: Optional[datetime] = None
    completion_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ============================================================================
# Survival Observation Schemas
# ============================================================================


class SurvivalObservationCreate(BaseModel):
    project_id: uuid.UUID
    plot_identifier: str = Field(..., min_length=1, max_length=64)
    cohort_identifier: str = Field(..., min_length=1, max_length=64)
    methodology: SurvivalMethodology = SurvivalMethodology.SAMPLE_PLOT
    coverage_area_sqm: Optional[float] = Field(None, gt=0)
    observation_date: date
    sample_size: int = Field(..., gt=0)
    alive_count: int = Field(..., ge=0)
    dead_count: int = Field(..., ge=0)
    mortality_causes: Optional[List[str]] = None
    is_definitive: bool = False
    activity_id: Optional[uuid.UUID] = None
    inspection_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None

    @model_validator(mode="after")
    def validate_counts_sum(self) -> "SurvivalObservationCreate":
        if (self.alive_count + self.dead_count) > self.sample_size:
            raise ValueError(
                f"Sum of alive_count ({self.alive_count}) and dead_count ({self.dead_count}) "
                f"cannot exceed sample_size ({self.sample_size})"
            )
        return self


class SurvivalObservationCorrectionRequest(BaseModel):
    sample_size: int = Field(..., gt=0)
    alive_count: int = Field(..., ge=0)
    dead_count: int = Field(..., ge=0)
    methodology: Optional[SurvivalMethodology] = None
    coverage_area_sqm: Optional[float] = Field(None, gt=0)
    mortality_causes: Optional[List[str]] = None
    is_definitive: Optional[bool] = None
    notes: Optional[str] = None
    correction_notes: str = Field(..., min_length=3)

    @model_validator(mode="after")
    def validate_counts_sum(self) -> "SurvivalObservationCorrectionRequest":
        if (self.alive_count + self.dead_count) > self.sample_size:
            raise ValueError(
                f"Sum of alive_count ({self.alive_count}) and dead_count ({self.dead_count}) "
                f"cannot exceed sample_size ({self.sample_size})"
            )
        return self


class SurvivalObservationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    activity_id: Optional[uuid.UUID] = None
    inspection_id: Optional[uuid.UUID] = None
    plot_identifier: str
    cohort_identifier: str
    methodology: str
    coverage_area_sqm: Optional[float] = None
    observation_date: date
    sample_size: int
    alive_count: int
    dead_count: int
    unassessed_count: int
    survival_rate: Optional[float] = None
    mortality_causes: Optional[List[Any]] = None
    is_definitive: bool
    is_active: bool
    superseded_by_id: Optional[uuid.UUID] = None
    correction_notes: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime


# ============================================================================
# Dynamic Alert Schemas
# ============================================================================


class MonitoringAlertItem(BaseModel):
    alert_type: AlertType
    severity: AlertSeverity
    entity_id: uuid.UUID
    project_id: uuid.UUID
    title: str
    due_date: date
    details: Optional[str] = None


class MonitoringAlertSummaryResponse(BaseModel):
    total_alerts: int
    high_count: int
    medium_count: int
    low_count: int
    alerts: List[MonitoringAlertItem]



# ============================================================================
# Monitoring Evidence & Dashboard Schemas
# ============================================================================


class MonitoringEvidenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    inspection_id: uuid.UUID
    original_filename: str
    mime_type: str
    file_size_bytes: int
    download_url: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    caption: Optional[str] = None
    uploaded_at: datetime


class MonitoringDashboardResponse(BaseModel):
    project_id: Optional[uuid.UUID] = None
    total_inspections: int
    scheduled_inspections: int
    in_progress_inspections: int
    completed_inspections: int
    total_tasks: int
    open_tasks: int
    completed_tasks: int
    overdue_tasks: int
    total_alerts: int
    high_severity_alerts: int
    latest_observations: List[SurvivalObservationResponse]
