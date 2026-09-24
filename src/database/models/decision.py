from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class DecisionAction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class DecisionBase(BaseModel):
    asset: str = Field(..., max_length=20)
    action: DecisionAction
    target_allocation_pct: Optional[Decimal] = Field(default=None, ge=0, le=100)
    confidence: Decimal = Field(..., ge=0, le=100, description="Confidence rating from 0 to 100")
    reason: str = Field(..., description="LLM reasoning summary")
    model_used: str = Field(..., max_length=50, description="e.g. glm-5, gpt-4o, claude-3-5-sonnet")
    raw_analysis: Optional[Dict[str, Any]] = Field(default=None, description="Sub-agents JSON reports")


class DecisionCreate(DecisionBase):
    pass


class DecisionResponse(DecisionBase):
    id: UUID
    executed: bool = False
    performance_score: Optional[Decimal] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)