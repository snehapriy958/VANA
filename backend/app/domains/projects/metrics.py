"""
VANA — Environmental Metric Catalog & Dimensionality Rules
Specifies approved environmental metrics, categories, canonical base units,
supported units, and unit conversion factors per ADR-003 and 06_ENVIRONMENTAL_IMPACT_LOGIC.md.
"""

from typing import Any, Dict, List, Optional
from decimal import Decimal
from pydantic import BaseModel


class MetricDefinition(BaseModel):
    metric_code: str
    display_name: str
    category: str
    dimension: str
    canonical_unit: str
    supported_units: List[str]
    conversion_factors_to_base: Dict[str, float]
    aggregation_eligible: bool
    methodology_summary: str


METRIC_CATEGORIES = [
    "VEGETATION_PLANTING",
    "LAND_RESTORATION",
    "WATER_CONSERVATION",
    "SOIL_CONSERVATION",
    "WASTE_REMOVAL",
]

APPROVED_METRIC_CATALOG: Dict[str, MetricDefinition] = {
    "TREES_PLANTED": MetricDefinition(
        metric_code="TREES_PLANTED",
        display_name="Trees Planted",
        category="VEGETATION_PLANTING",
        dimension="COUNT",
        canonical_unit="trees",
        supported_units=["trees"],
        conversion_factors_to_base={"trees": 1.0},
        aggregation_eligible=True,
        methodology_summary="Direct physical count of established native trees planted on site; tagged and geotagged.",
    ),
    "SAPLINGS_PLANTED": MetricDefinition(
        metric_code="SAPLINGS_PLANTED",
        display_name="Saplings Planted",
        category="VEGETATION_PLANTING",
        dimension="COUNT",
        canonical_unit="saplings",
        supported_units=["saplings"],
        conversion_factors_to_base={"saplings": 1.0},
        aggregation_eligible=True,
        methodology_summary="Physical tally of nursery saplings transplanted into soil plots; tagged with nursery lot number.",
    ),
    "AREA_RESTORED": MetricDefinition(
        metric_code="AREA_RESTORED",
        display_name="Area Restored",
        category="LAND_RESTORATION",
        dimension="AREA",
        canonical_unit="hectares",
        supported_units=["hectares", "m2", "acres"],
        conversion_factors_to_base={"hectares": 1.0, "m2": 0.0001, "acres": 0.404686},
        aggregation_eligible=True,
        methodology_summary="GPS boundary walking or polygon mapping of degraded land brought under active soil/vegetation restoration.",
    ),
    "AREA_REVEGETATED": MetricDefinition(
        metric_code="AREA_REVEGETATED",
        display_name="Area Revegetated",
        category="LAND_RESTORATION",
        dimension="AREA",
        canonical_unit="hectares",
        supported_units=["hectares", "m2", "acres"],
        conversion_factors_to_base={"hectares": 1.0, "m2": 0.0001, "acres": 0.404686},
        aggregation_eligible=True,
        methodology_summary="Direct measurement of canopy coverage or ground re-seeding within designated conservation boundaries.",
    ),
    "RAINWATER_HARVESTED": MetricDefinition(
        metric_code="RAINWATER_HARVESTED",
        display_name="Rainwater Harvested",
        category="WATER_CONSERVATION",
        dimension="VOLUME",
        canonical_unit="liters",
        supported_units=["liters", "m3"],
        conversion_factors_to_base={"liters": 1.0, "m3": 1000.0},
        aggregation_eligible=True,
        methodology_summary="Water meter reading or calculated volume from certified percolation pits and check dams during rain events.",
    ),
    "RESERVOIR_CAPACITY_CREATED": MetricDefinition(
        metric_code="RESERVOIR_CAPACITY_CREATED",
        display_name="Reservoir Capacity Created",
        category="WATER_CONSERVATION",
        dimension="VOLUME",
        canonical_unit="cubic_meters",
        supported_units=["cubic_meters", "liters"],
        conversion_factors_to_base={"cubic_meters": 1.0, "liters": 0.001},
        aggregation_eligible=True,
        methodology_summary="Civil engineering survey of excavated trench, bund, or farm pond storage volume capacity.",
    ),
    "WASTE_REMOVED": MetricDefinition(
        metric_code="WASTE_REMOVED",
        display_name="Waste Removed",
        category="WASTE_REMOVAL",
        dimension="MASS",
        canonical_unit="kilograms",
        supported_units=["kilograms", "metric_tons"],
        conversion_factors_to_base={"kilograms": 1.0, "metric_tons": 1000.0},
        aggregation_eligible=True,
        methodology_summary="Certified weighbridge or hand-scale slip for physical non-biodegradable waste collected from site.",
    ),
}


def validate_metric_and_unit(metric_code: str, unit: str) -> MetricDefinition:
    """
    Validates that metric_code exists in the approved catalog and that the unit is supported.
    Raises ValueError if invalid.
    """
    if metric_code not in APPROVED_METRIC_CATALOG:
        valid_codes = ", ".join(APPROVED_METRIC_CATALOG.keys())
        raise ValueError(f"Unknown metric code '{metric_code}'. Approved metric codes are: {valid_codes}")

    metric = APPROVED_METRIC_CATALOG[metric_code]
    normalized_unit = unit.strip().lower()
    supported_normalized = [u.lower() for u in metric.supported_units]

    if normalized_unit not in supported_normalized:
        raise ValueError(
            f"Unsupported unit '{unit}' for metric '{metric_code}'. "
            f"Supported units are: {', '.join(metric.supported_units)}"
        )

    return metric


def convert_to_canonical(metric_code: str, quantity: Decimal, from_unit: str) -> Decimal:
    """Converts a quantity in a supported unit to the canonical base unit of the metric."""
    metric = validate_metric_and_unit(metric_code, from_unit)
    norm_unit = from_unit.strip().lower()
    factor = metric.conversion_factors_to_base.get(norm_unit, 1.0)
    return quantity * Decimal(str(factor))


def convert_between_units(
    metric_code: str, quantity: Decimal, from_unit: str, to_unit: str
) -> Decimal:
    """Converts a quantity between two supported units within the same metric code."""
    metric = validate_metric_and_unit(metric_code, from_unit)
    validate_metric_and_unit(metric_code, to_unit)
    norm_from = from_unit.strip().lower()
    norm_to = to_unit.strip().lower()
    if norm_from == norm_to:
        return quantity
    from_factor = metric.conversion_factors_to_base.get(norm_from, 1.0)
    to_factor = metric.conversion_factors_to_base.get(norm_to, 1.0)
    canonical = quantity * Decimal(str(from_factor))
    return canonical / Decimal(str(to_factor))

