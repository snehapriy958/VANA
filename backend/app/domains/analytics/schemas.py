"""
VANA — Environmental Impact Analytics & Dashboard Schemas
Defines request and response schemas for dashboard overview, project-level impact intelligence,
activity trends, and metric catalog summaries.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field


class MetricProgressSummary(BaseModel):
    """Aggregate progress for a specific environmental metric."""
    model_config = ConfigDict(from_attributes=True)

    metric_code: str
    display_name: str
    category: str
    canonical_unit: str
    total_verified_quantity: Decimal = Decimal("0.0")
    total_pending_adjustment: Decimal = Decimal("0.0")
    total_target_quantity: Optional[Decimal] = None
    overall_achievement_percentage: Optional[float] = None
    active_projects_count: int = 0
    activities_count: int = 0


class AttentionProjectItem(BaseModel):
    """A project requiring operational or administrative attention."""
    model_config = ConfigDict(from_attributes=True)

    project_id: uuid.UUID
    project_name: str
    project_code: str
    status: str
    reason: str
    severity: str  # "HIGH", "MEDIUM", "LOW"
    pending_verifications_count: int = 0
    days_until_deadline: Optional[int] = None
    lowest_target_achievement_percentage: Optional[float] = None


class TargetProgressItem(BaseModel):
    """Progress for an individual target on a project."""
    model_config = ConfigDict(from_attributes=True)

    target_id: uuid.UUID
    metric_code: str
    metric_name: str
    target_quantity: Decimal
    target_unit: str
    verified_quantity: Decimal
    net_pending_adjustment: Decimal
    remaining_quantity: Decimal
    achievement_percentage: float
    target_date: date
    milestone_id: Optional[uuid.UUID] = None


class DashboardOverviewResponse(BaseModel):
    """High-level portfolio or scoped dashboard overview."""
    model_config = ConfigDict(from_attributes=True)

    total_projects: int
    active_projects: int
    completed_projects: int
    draft_projects: int
    total_pending_verifications: int
    metric_achievements: List[MetricProgressSummary]
    attention_projects: List[AttentionProjectItem]
    user_role: str
    is_portfolio_wide: bool


class ProjectProgressItem(BaseModel):
    """Project progress entry for dashboard project portfolio table/grid."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    code: str
    status: str
    description: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    targets: List[TargetProgressItem] = Field(default_factory=list)
    overall_achievement_percentage: Optional[float] = None
    pending_verifications_count: int = 0
    last_activity_date: Optional[date] = None
    has_coordinates: bool = False


class DashboardProjectsResponse(BaseModel):
    """List of projects with impact metrics for dashboard."""
    model_config = ConfigDict(from_attributes=True)

    total: int
    projects: List[ProjectProgressItem]


class RecentActivityItem(BaseModel):
    """Operational event entry for dashboard activity stream."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    event_type: str  # "SUBMISSION", "VERIFICATION", "REJECTION", "AMENDMENT", "PROJECT_UPDATE"
    title: str
    description: str
    timestamp: datetime
    actor_id: Optional[uuid.UUID] = None
    actor_name: Optional[str] = None
    project_id: uuid.UUID
    project_name: str
    project_code: str
    metric_code: Optional[str] = None
    quantity: Optional[Decimal] = None
    unit: Optional[str] = None
    status: Optional[str] = None


class ProjectImpactDetailResponse(BaseModel):
    """Detailed environmental impact summary for a single project."""
    model_config = ConfigDict(from_attributes=True)

    project_id: uuid.UUID
    project_name: str
    project_code: str
    project_status: str
    description: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    boundary_geojson: Optional[Dict[str, Any]] = None
    targets: List[TargetProgressItem] = Field(default_factory=list)
    overall_achievement_percentage: Optional[float] = None
    activities_summary: Dict[str, Any]
    historical_rejected_count: int = 0
    last_activity_date: Optional[date] = None


class ProjectTrendPoint(BaseModel):
    """Data point in a project's verified activity time-series."""
    model_config = ConfigDict(from_attributes=True)

    date: str  # YYYY-MM-DD
    metric_code: str
    metric_name: str
    unit: str
    period_quantity: Decimal
    cumulative_quantity: Decimal
    activities_count: int


class ProjectTrendsResponse(BaseModel):
    """Time-series verified metrics response for charting."""
    model_config = ConfigDict(from_attributes=True)

    project_id: uuid.UUID
    project_name: str
    trends: List[ProjectTrendPoint]
    available_metrics: List[str]


class MetricCatalogSummaryItem(BaseModel):
    """Catalog summary entry for /analytics/metrics."""
    model_config = ConfigDict(from_attributes=True)

    metric_code: str
    display_name: str
    category: str
    canonical_unit: str
    supported_units: List[str]
    total_verified_quantity: Decimal
    total_pending_adjustment: Decimal
    total_target_quantity: Optional[Decimal] = None
    overall_achievement_percentage: Optional[float] = None
    projects_count: int
