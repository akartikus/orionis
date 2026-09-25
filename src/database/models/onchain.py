from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class OnchainDataBase(BaseModel):
    asset: str = Field(..., max_length=20, description="Asset ticker, e.g. BTC, ETH")
    metric_name: str = Field(..., max_length=50, description="e.g. 'active_addresses', 'hash_rate', 'whale_inflow'")
    value: Decimal = Field(..., description="On-chain metric value")
    source: str = Field(..., max_length=100, description="Data source, e.g. 'Glassnode', 'CryptoQuant'")


class OnchainDataCreate(OnchainDataBase):
    timestamp: Optional[datetime] = Field(default=None, description="Observation timestamp (defaults to NOW)")


class OnchainDataResponse(OnchainDataBase):
    id: UUID
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)
