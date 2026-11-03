"""
VANA — Dashboard & Environmental Analytics API Routers
Exposes endpoints for dashboard overview, project portfolio progress, recent operational activity,
project impact details, and verified time-series trends.
"""

from datetime import date
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.domains.auth.dependencies import get_current_active_user
from app.domains.auth.models import User
from app.domains.analytics.schemas import (
    DashboardOverviewResponse,
    DashboardProjectsResponse,
    MetricCatalogSummaryItem,
    ProjectImpactDetailResponse,
    ProjectTrendsResponse,
    RecentActivityItem,
)
from app.domains.analytics.services import EnvironmentalLedgerService

# Dashboard Router (mounted under /dashboard)
dashboard_router = APIRouter(prefix="/dashboard", tags=["Dashboard & Environmental Overview"])

# Analytics Router (mounted under /analytics)
analytics_router = APIRouter(prefix="/analytics", tags=["Environmental Impact Analytics"])


# ============================================================================
# Dashboard Endpoints
# ============================================================================

@dashboard_router.get(
    "/overview",
    response_model=DashboardOverviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Dashboard Overview",
)
async def get_dashboard_overview(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> DashboardOverviewResponse:
    """
    Retrieves high-level portfolio or scoped KPIs, metric-by-metric verified achievements,
    attention project alerts, and pending verification counts.
    - ADMIN: Portfolio-wide aggregation.
    - PROJECT_MANAGER / FIELD_OFFICER: Aggregation restricted strictly to assigned projects.
    """
    return await EnvironmentalLedgerService.get_dashboard_overview(
        db=db, current_user=current_user
    )


@dashboard_router.get(
    "/projects",
    response_model=DashboardProjectsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Dashboard Projects Progress",
)
async def get_dashboard_projects(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by project status"),
    search: Optional[str] = Query(None, description="Search by name, code, or biome"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> DashboardProjectsResponse:
    """
    Retrieves project cards with target progress, verified quantity, and pending adjustment.
    Scoped to assigned projects for non-admin users.
    """
    return await EnvironmentalLedgerService.get_dashboard_projects(
        db=db,
        current_user=current_user,
        status_filter=status_filter,
        search=search,
    )


@dashboard_router.get(
    "/recent-activity",
    response_model=List[RecentActivityItem],
    status_code=status.HTTP_200_OK,
    summary="Get Recent Operational Activity",
)
async def get_recent_activity(
    limit: int = Query(default=15, ge=1, le=50, description="Number of recent events to retrieve"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> List[RecentActivityItem]:
    """
    Retrieves recent operational events (submissions, verifications, rejections, amendments).
    Scoped to authorized projects.
    """
    return await EnvironmentalLedgerService.get_recent_activity(
        db=db, current_user=current_user, limit=limit
    )


# ============================================================================
# Analytics Endpoints
# ============================================================================

@analytics_router.get(
    "/projects/{project_id}/impact",
    response_model=ProjectImpactDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Project Impact Detail",
)
async def get_project_impact(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectImpactDetailResponse:
    """
    Retrieves detailed environmental impact balance sheet for a project.
    Reconciles targets, verified quantities, remaining amounts, and pending adjustments.
    Requires ADMIN or explicit project assignment.
    """
    return await EnvironmentalLedgerService.get_project_impact_detail(
        db=db, project_id=project_id, current_user=current_user
    )


@analytics_router.get(
    "/projects/{project_id}/trends",
    response_model=ProjectTrendsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Project Activity Trends",
)
async def get_project_trends(
    project_id: uuid.UUID,
    metric_code: Optional[str] = Query(None, description="Filter trends by specific metric code"),
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectTrendsResponse:
    """
    Retrieves time-series data points of verified activities for charting.
    Requires ADMIN or explicit project assignment.
    """
    return await EnvironmentalLedgerService.get_project_trends(
        db=db,
        project_id=project_id,
        current_user=current_user,
        metric_code=metric_code,
        start_date=start_date,
        end_date=end_date,
    )


@analytics_router.get(
    "/metrics",
    response_model=List[MetricCatalogSummaryItem],
    status_code=status.HTTP_200_OK,
    summary="Get Metrics Catalog Summary",
)
async def get_metrics_catalog_summary(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> List[MetricCatalogSummaryItem]:
    """
    Retrieves active metric definitions with their scoped portfolio achievements.
    """
    return await EnvironmentalLedgerService.get_metrics_catalog_summary(
        db=db, current_user=current_user
    )
