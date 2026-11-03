"""
VANA — Environmental Metrics Catalog API Router
Exposes the approved metric catalog, units, and methodology definitions.
"""

from typing import List
from fastapi import APIRouter, Depends, status
from app.domains.auth.dependencies import get_current_active_user
from app.domains.auth.models import User
from app.domains.projects.metrics import APPROVED_METRIC_CATALOG, MetricDefinition

router = APIRouter(prefix="/metrics", tags=["Environmental Metrics"])


@router.get("/catalog", response_model=List[MetricDefinition], status_code=status.HTTP_200_OK)
async def get_metrics_catalog(
    current_user: User = Depends(get_current_active_user),
) -> List[MetricDefinition]:
    """Returns all approved environmental metric definitions, dimensions, and supported units."""
    return list(APPROVED_METRIC_CATALOG.values())
