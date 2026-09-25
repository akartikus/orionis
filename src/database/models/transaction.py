from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class TransactionType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    FEE = "FEE"


class OperationOrigin(str, Enum):
    ORIONIS = "ORIONIS"
    MANUAL = "MANUAL"


class TransactionBase(BaseModel):
    exchange_transaction_id: Optional[str] = Field(default=None, max_length=100)
    asset: str = Field(..., max_length=20)
    type: TransactionType
    amount: Decimal
    price: Decimal = Field(default=Decimal("0"))
    fee: Decimal = Field(default=Decimal("0"))
    origin: OperationOrigin = Field(default=OperationOrigin.ORIONIS)


class TransactionCreate(TransactionBase):
    timestamp: Optional[datetime] = None


class TransactionResponse(TransactionBase):
    id: UUID
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"


class TransactionLogBase(BaseModel):
    symbol: str = Field(..., description="Trading pair symbol, e.g., 'BTC/EUR'")
    side: OrderSide
    order_type: OrderType
    amount: float = Field(..., gt=0.0)
    price: float = Field(..., gt=0.0)
    cost: float = Field(..., ge=0.0)
    bitvavo_order_id: Optional[str] = None
    origin: str = Field(default="ORIONIS", description="Origin tag for tracking")


class TransactionLogCreate(TransactionLogBase):
    pass


class TransactionLogResponse(TransactionLogBase):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)



class TradeRequest(BaseModel):
    symbol: str = Field(..., examples=["BTC/EUR"], description="Paire de trading")
    side: OrderSide = Field(..., examples=["buy"], description="Sens de l'ordre : buy ou sell")
    amount: float = Field(..., gt=0.0, examples=[0.001], description="Quantité d'actif")