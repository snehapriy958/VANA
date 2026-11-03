"""
VANA — Project Team Assignment Pydantic Schemas
Validates roster allocations of Project Managers and Field Officers.
"""

import enum
import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class ProjectRole(str, enum.Enum):
    PROJECT_MANAGER = "PROJECT_MANAGER"
    FIELD_OFFICER = "FIELD_OFFICER"


class ProjectAssignmentCreate(BaseModel):
    user_id: uuid.UUID = Field(..., description="ID of active user to allocate")
    assigned_role: ProjectRole = Field(..., description="Assigned role within project roster")


class ProjectAssignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    user_id: uuid.UUID
    assigned_role: str
    assigned_at: datetime

    # Denormalized user info for UI presentation
    user_email: Optional[str] = None
    user_full_name: Optional[str] = None
    user_system_role: Optional[str] = None
    user_is_active: Optional[bool] = None
