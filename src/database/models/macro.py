from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class MacroIndicatorBase(BaseModel):
    indicator_name: str = Field(..., max_length=50, description="e.g. 'interest_rate', 'inflation_cpi', 'dxy'")
    value: Decimal = Field(..., description="Indicator value")
    unit: Optional[str] = Field(default=None, max_length=20, description="e.g. '%', 'index', 'USD'")
    source: str = Field(..., max_length=100, description="Data source, e.g. 'FRED', 'Yahoo Finance'")


class MacroIndicatorCreate(MacroIndicatorBase):
    timestamp: Optional[datetime] = Field(default=None, description="Observation timestamp (defaults to NOW)")


class MacroIndicatorResponse(MacroIndicatorBase):
    id: UUID
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)
