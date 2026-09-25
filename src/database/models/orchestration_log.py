from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class WorkflowStatus(str, Enum):
    STARTED = "STARTED"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class OrchestrationLogBase(BaseModel):
    workflow_name: str = Field(..., max_length=50, description="e.g. 'daily_analysis', 'urgent_analysis'")
    status: WorkflowStatus
    finished_at: Optional[datetime] = Field(default=None, description="Workflow end timestamp")
    duration_ms: Optional[int] = Field(default=None, ge=0, description="Duration in milliseconds")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Step summary / errors")
    error_message: Optional[str] = Field(default=None, description="Error message if status=FAILED")


class OrchestrationLogCreate(OrchestrationLogBase):
    started_at: Optional[datetime] = Field(default=None, description="Workflow start timestamp (defaults to NOW)")


class OrchestrationLogResponse(OrchestrationLogBase):
    id: UUID
    started_at: datetime

    model_config = ConfigDict(from_attributes=True)
