from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class SentimentLabel(str, Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


class NewsBase(BaseModel):
    title: str = Field(..., description="Article title")
    summary: Optional[str] = Field(default=None, description="Short snippet/summary")
    url: str = Field(..., description="Unique article URL")
    source: str = Field(..., max_length=255, description="RSS feed source URL")
    sentiment_label: SentimentLabel = Field(default=SentimentLabel.NEUTRAL)
    sentiment_score: float = Field(default=0.0, ge=-1.0, le=1.0)
    published_at: datetime


class NewsCreate(NewsBase):
    pass


class NewsResponse(NewsBase):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)