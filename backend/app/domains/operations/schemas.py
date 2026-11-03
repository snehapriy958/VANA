"""
VANA — Field Operations & Activity Verification Schemas
Defines request/response contracts for field activities, revision lineages,
evidence files, and verification queue items.
"""

from datetime import date, datetime
from decimal import Decimal
import math
from typing import List, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from app.domains.operations.models import ActivityStatus, RejectionReasonCode


class EvidenceFileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    activity_id: uuid.UUID
    revision_id: uuid.UUID
    original_filename: str
    mime_type: str
    file_size_bytes: int
    download_url: str
    uploaded_at: datetime


class ActivityRevisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    activity_id: uuid.UUID
    revision_number: int
    quantity: Decimal
    activity_date: date
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    gps_accuracy_meters: Optional[float] = None
    field_notes: Optional[str] = None
    status: str
    is_active_ledger_entry: bool
    verifier_id: Optional[uuid.UUID] = None
    verifier_name: Optional[str] = None
    verified_at: Optional[datetime] = None
    rejection_reason_code: Optional[str] = None
    review_notes: Optional[str] = None
    created_at: datetime
    evidence_files: List[EvidenceFileResponse] = Field(default_factory=list)


class FieldActivityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    project_name: Optional[str] = None
    project_code: Optional[str] = None
    created_by_id: uuid.UUID
    created_by_name: Optional[str] = None
    metric_code: str
    unit: str
    is_archived: bool
    current_revision_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime
    current_revision: Optional[ActivityRevisionResponse] = None
    active_ledger_revision: Optional[ActivityRevisionResponse] = None
    active_verified_quantity: Decimal = Decimal("0.0")
    net_pending_adjustment: Optional[Decimal] = None
    revisions_count: int = 0
    revisions: Optional[List[ActivityRevisionResponse]] = None


class ActivityCreate(BaseModel):
    project_id: uuid.UUID
    metric_code: str
    quantity: Decimal = Field(..., gt=0, description="Quantity must be strictly positive")
    unit: str
    activity_date: date
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)
    gps_accuracy_meters: Optional[float] = Field(None, ge=0)
    field_notes: Optional[str] = None

    @field_validator("latitude", "longitude", "gps_accuracy_meters")
    @classmethod
    def validate_finite_coords(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and (math.isnan(v) or math.isinf(v)):
            raise ValueError("Coordinates and accuracy must be finite numbers")
        return v


class ActivityRevisionCreate(BaseModel):
    quantity: Decimal = Field(..., gt=0, description="Amended quantity must be strictly positive")
    activity_date: date
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)
    gps_accuracy_meters: Optional[float] = Field(None, ge=0)
    field_notes: Optional[str] = None
    amendment_reason: Optional[str] = None

    @field_validator("latitude", "longitude", "gps_accuracy_meters")
    @classmethod
    def validate_finite_coords(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and (math.isnan(v) or math.isinf(v)):
            raise ValueError("Coordinates and accuracy must be finite numbers")
        return v


class VerificationDecisionRequest(BaseModel):
    decision: str = Field(..., description="Either 'VERIFIED' (or 'APPROVED') or 'REJECTED'")
    rejection_reason_code: Optional[str] = None
    review_notes: Optional[str] = None

    @model_validator(mode="after")
    def validate_decision_rules(self) -> "VerificationDecisionRequest":
        canonical_decision = self.decision.strip().upper()
        if canonical_decision == "APPROVED":
            canonical_decision = ActivityStatus.VERIFIED.value
        self.decision = canonical_decision

        if self.decision not in (ActivityStatus.VERIFIED.value, ActivityStatus.REJECTED.value):
            raise ValueError("decision must be either 'VERIFIED' (or 'APPROVED') or 'REJECTED'")

        if self.decision == ActivityStatus.REJECTED.value:
            if not self.rejection_reason_code:
                raise ValueError("rejection_reason_code is required when rejecting an activity")
            valid_codes = {c.value for c in RejectionReasonCode}
            if self.rejection_reason_code not in valid_codes:
                raise ValueError(
                    f"rejection_reason_code must be one of {sorted(list(valid_codes))}"
                )
            if not self.review_notes or not self.review_notes.strip():
                raise ValueError("review_notes are mandatory when rejecting an activity")
        elif self.decision == ActivityStatus.VERIFIED.value:
            # Rejection reason code should be cleared for approvals
            self.rejection_reason_code = None

        return self


class VerificationDecisionResponse(BaseModel):
    revision_id: uuid.UUID
    activity_id: uuid.UUID
    status: str
    is_active_ledger_entry: bool
    verifier_id: uuid.UUID
    verifier_name: Optional[str] = None
    verified_at: datetime
    review_notes: Optional[str] = None
    rejection_reason_code: Optional[str] = None
    project_verified_total_recalculated: Decimal


class VerificationQueueItem(BaseModel):
    revision_id: uuid.UUID
    activity_id: uuid.UUID
    project_id: uuid.UUID
    project_name: str
    project_code: str
    creator_id: uuid.UUID
    creator_name: str
    metric_code: str
    unit: str
    quantity: Decimal
    activity_date: date
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    gps_accuracy_meters: Optional[float] = None
    field_notes: Optional[str] = None
    revision_number: int
    is_amendment: bool
    previously_verified_quantity: Optional[Decimal] = None
    net_adjustment: Optional[Decimal] = None
    evidence_files: List[EvidenceFileResponse] = Field(default_factory=list)
    created_at: datetime
    can_verify: bool
