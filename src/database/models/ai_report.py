from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class ReportType(str, Enum):
    MARKET = "MARKET"
    FUNDAMENTAL = "FUNDAMENTAL"
    RISK = "RISK"
    SYNTHESIS = "SYNTHESIS"


class AIReportBase(BaseModel):
    asset: str = Field(..., max_length=20, description="Asset ticker, e.g. BTC, ETH")
    report_type: ReportType
    content: Dict[str, Any] = Field(..., description="Structured report from the sub-agent")
    model_used: str = Field(..., max_length=50, description="LLM model identifier")
    confidence: Optional[Decimal] = Field(default=None, ge=0, le=100, description="Confidence score 0-100")


class AIReportCreate(AIReportBase):
    pass


class AIReportResponse(AIReportBase):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
