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