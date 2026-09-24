from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from database.models.transaction import OperationOrigin


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    LIMIT = "LIMIT"
    MARKET = "MARKET"


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    OPEN = "OPEN"
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    REJECTED = "REJECTED"


class OrderBase(BaseModel):
    exchange_order_id: Optional[str] = Field(default=None, max_length=100)
    symbol: str = Field(..., max_length=20, description="Trading pair, e.g. BTC-EUR")
    side: OrderSide
    type: OrderType = Field(default=OrderType.LIMIT)
    amount: Decimal
    price: Optional[Decimal] = None
    origin: OperationOrigin = Field(default=OperationOrigin.ORIONIS)


class OrderCreate(OrderBase):
    pass


class OrderResponse(OrderBase):
    id: UUID
    filled_amount: Decimal = Field(default=Decimal("0"))
    average_filled_price: Decimal = Field(default=Decimal("0"))
    status: OrderStatus = Field(default=OrderStatus.PENDING)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)