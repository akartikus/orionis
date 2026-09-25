from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class AlertType(str, Enum):
    PRICE_DROP = "PRICE_DROP"
    PRICE_SURGE = "PRICE_SURGE"
    NEWS_CRITICAL = "NEWS_CRITICAL"
    THRESHOLD = "THRESHOLD"
    MANUAL = "MANUAL"


class AlertSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class AlertBase(BaseModel):
    alert_type: AlertType
    asset: Optional[str] = Field(default=None, max_length=20, description="Asset ticker, e.g. BTC")
    severity: AlertSeverity = Field(default=AlertSeverity.INFO)
    message: str = Field(..., description="Human-readable alert message")
    payload: Optional[Dict[str, Any]] = Field(default=None, description="Contextual data")
    triggered: bool = Field(default=False, description="Whether Orionis Core processed this alert")
    resolved: bool = Field(default=False, description="Whether the alert has been resolved")


class AlertCreate(AlertBase):
    pass


class AlertResponse(AlertBase):
    id: UUID
    created_at: datetime
    resolved_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
