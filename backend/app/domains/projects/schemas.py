"""
VANA — Project & Environmental Target Pydantic Schemas
Validates project lifecycle metadata, coordinates, GeoJSON polygons, and environmental targets.
"""

import enum
import math
import re
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from app.domains.projects.metrics import APPROVED_METRIC_CATALOG, validate_metric_and_unit


class ProjectStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"


# Valid status transition graph
VALID_STATUS_TRANSITIONS: Dict[str, List[str]] = {
    "DRAFT": ["ACTIVE", "ARCHIVED"],
    "ACTIVE": ["COMPLETED", "ARCHIVED", "DRAFT"],
    "COMPLETED": ["ACTIVE", "ARCHIVED"],
    "ARCHIVED": ["ACTIVE"],
}


def validate_geojson_polygon(value: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Validates standard GeoJSON Polygon format according to RFC 7946.
    Ensures correct structure, closed linear rings, coordinate validity, and minimum vertices.
    """
    if value is None:
        return None

    if not isinstance(value, dict):
        raise ValueError("boundary_geojson must be a JSON object.")

    geom_type = value.get("type")
    if geom_type != "Polygon":
        raise ValueError(f"boundary_geojson type must be 'Polygon', received '{geom_type}'.")

    coordinates = value.get("coordinates")
    if not isinstance(coordinates, list) or len(coordinates) == 0:
        raise ValueError("Polygon coordinates must be a non-empty list of linear rings.")

    for ring_idx, ring in enumerate(coordinates):
        if not isinstance(ring, list):
            raise ValueError(f"Ring {ring_idx} in coordinates must be a list of coordinate pairs.")

        if len(ring) < 4:
            raise ValueError(
                f"Ring {ring_idx} must contain at least 4 coordinate positions (got {len(ring)})."
            )

        # Ring closure check (first position must equal last position)
        first_pt = ring[0]
        last_pt = ring[-1]
        if not (isinstance(first_pt, list) and isinstance(last_pt, list) and len(first_pt) >= 2 and len(last_pt) >= 2):
            raise ValueError(f"Invalid coordinate format in ring {ring_idx}.")

        if first_pt[0] != last_pt[0] or first_pt[1] != last_pt[1]:
            raise ValueError(
                f"Linear ring {ring_idx} is not closed: first coordinate {first_pt} does not match last coordinate {last_pt}."
            )

        # Coordinate range checks [lng, lat]
        for pt_idx, pt in enumerate(ring):
            if not isinstance(pt, (list, tuple)) or len(pt) < 2:
                raise ValueError(f"Position {pt_idx} in ring {ring_idx} must be a [longitude, latitude] pair.")
            lng, lat = pt[0], pt[1]
            if not isinstance(lng, (int, float)) or not isinstance(lat, (int, float)):
                raise ValueError(f"Coordinates at position {pt_idx} in ring {ring_idx} must be numeric.")
            if not math.isfinite(lng) or not math.isfinite(lat):
                raise ValueError(f"Coordinates at position {pt_idx} in ring {ring_idx} must be finite numbers.")
            if not (-180.0 <= lng <= 180.0):
                raise ValueError(f"Longitude {lng} at position {pt_idx} in ring {ring_idx} out of range [-180, 180].")
            if not (-90.0 <= lat <= 90.0):
                raise ValueError(f"Latitude {lat} at position {pt_idx} in ring {ring_idx} out of range [-90, 90].")

    return value


class ProjectBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=255, description="Official project name")
    description: Optional[str] = Field(None, max_length=4000, description="Detailed project description")
    status: ProjectStatus = Field(default=ProjectStatus.ACTIVE, description="Lifecycle status")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Center latitude (-90 to 90)")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Center longitude (-180 to 180)")
    boundary_geojson: Optional[Dict[str, Any]] = Field(None, description="GeoJSON Polygon boundary")

    @field_validator("boundary_geojson")
    @classmethod
    def check_boundary_geojson(cls, v: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        return validate_geojson_polygon(v)


class ProjectCreate(ProjectBase):
    code: Optional[str] = Field(
        None,
        min_length=2,
        max_length=64,
        description="Unique uppercase identifier (e.g. VANA-SUNDAR-01)",
    )

    @field_validator("code")
    @classmethod
    def validate_code_format(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v_cleaned = v.strip().upper()
            if not re.match(r"^[A-Z0-9_\-]+$", v_cleaned):
                raise ValueError("Project code must contain only uppercase alphanumeric characters, dashes, or underscores.")
            return v_cleaned
        return v


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = Field(None, max_length=4000)
    status: Optional[ProjectStatus] = None
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)
    boundary_geojson: Optional[Dict[str, Any]] = None

    @field_validator("boundary_geojson")
    @classmethod
    def check_boundary_geojson(cls, v: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        return validate_geojson_polygon(v)


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    code: str
    description: Optional[str] = None
    status: str
    latitude: float
    longitude: float
    boundary_geojson: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    targets_count: int = 0
    team_count: int = 0


# --- Environmental Target Schemas ---

class ProjectTargetCreate(BaseModel):
    metric_code: str = Field(..., description="Unique metric code from approved catalog")
    target_quantity: Decimal = Field(..., gt=0, decimal_places=2, description="Target numerical quantity (> 0)")
    target_unit: str = Field(..., description="Unit of measurement compatible with metric code")
    target_date: date = Field(..., description="Target completion deadline")
    milestone_id: Optional[uuid.UUID] = Field(None, description="Optional phase milestone ID")

    @model_validator(mode="after")
    def validate_metric_and_units(self) -> "ProjectTargetCreate":
        metric_code = self.metric_code.strip().upper()
        self.metric_code = metric_code
        # Validate metric exists and unit is compatible
        validate_metric_and_unit(metric_code, self.target_unit)
        return self


class ProjectTargetUpdate(BaseModel):
    target_quantity: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    target_unit: Optional[str] = None
    target_date: Optional[date] = None


class ProjectTargetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    metric_code: str
    display_name: str
    category: str
    dimension: str
    canonical_unit: str
    target_quantity: Decimal
    target_unit: str
    target_date: date
    milestone_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime


class ProjectDetailResponse(ProjectResponse):
    targets: List[ProjectTargetResponse] = []
    assignments: List[Any] = []
