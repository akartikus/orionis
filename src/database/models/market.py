from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class MarketSnapshotBase(BaseModel):
    asset: str = Field(..., max_length=20)
    price: Decimal
    volume_24h: Optional[Decimal] = None
    market_cap: Optional[Decimal] = None
    indicators: Optional[Dict[str, Any]] = Field(default=None, description="RSI, MACD, Moving Averages")


class MarketSnapshotCreate(MarketSnapshotBase):
    pass


class MarketSnapshotResponse(MarketSnapshotBase):
    id: UUID
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)