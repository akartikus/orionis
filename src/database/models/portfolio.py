from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field


class PortfolioBase(BaseModel):
    asset: str = Field(..., max_length=20, description="Asset ticker, e.g. BTC, ETH, EUR")
    total_quantity: Decimal = Field(default=Decimal("0"), description="Total balance on exchange")
    average_buy_price: Decimal = Field(default=Decimal("0"), description="Break-even buy price in EUR")
    current_price: Decimal = Field(default=Decimal("0"), description="Latest market price in EUR")


class PortfolioCreate(PortfolioBase):
    pass


class PortfolioResponse(PortfolioBase):
    total_value: Decimal = Field(default=Decimal("0"), description="Calculated total value in EUR")
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BotManagedAssetBase(BaseModel):
    asset: str = Field(..., max_length=20, description="Asset ticker, e.g. BTC, ETH")
    allocated_quantity: Decimal = Field(default=Decimal("0"), description="Quantity managed by ORIONIS")
    total_invested_eur: Decimal = Field(default=Decimal("0"), description="Total EUR capital allocated")
    current_price: Decimal = Field(default=Decimal("0"), description="Latest market price in EUR")


class BotManagedAssetResponse(BotManagedAssetBase):
    current_value: Decimal = Field(default=Decimal("0"), description="Calculated bot portfolio value")
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)