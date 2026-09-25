from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class StrategyConfigBase(BaseModel):
    is_active: bool = Field(default=False, description="Whether this configuration is the active one")
    initial_capital_eur: Decimal = Field(..., description="Initial capital in EUR")
    max_allocation_per_asset_pct: Decimal = Field(default=Decimal("40.00"), ge=0, le=100, description="Max allocation per asset (%)")
    max_total_exposure_pct: Decimal = Field(default=Decimal("100.00"), ge=0, le=100, description="Max total exposure (%)")
    stop_loss_pct: Optional[Decimal] = Field(default=Decimal("15.00"), ge=0, le=100, description="Stop-loss threshold (%)")
    take_profit_pct: Optional[Decimal] = Field(default=Decimal("30.00"), ge=0, le=100, description="Take-profit threshold (%)")
    max_order_amount_eur: Decimal = Field(default=Decimal("500.00"), description="Max amount per order in EUR")
    daily_trade_limit: int = Field(default=10, ge=0, description="Max number of trades per day")
    min_confidence_threshold: Decimal = Field(default=Decimal("60.00"), ge=0, le=100, description="Min AI confidence to act (%)")
    allowed_assets: Optional[List[str]] = Field(default=None, description="Allowed asset tickers")


class StrategyConfigCreate(StrategyConfigBase):
    pass


class StrategyConfigResponse(StrategyConfigBase):
    id: int
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
