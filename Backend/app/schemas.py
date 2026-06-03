from datetime import datetime
from pydantic import BaseModel, Field


class RateSnapshotOut(BaseModel):
    id: int
    pair: str
    base_currency: str
    quote_currency: str
    rate: float
    bid_rate: float
    ask_rate: float
    spread: float
    created_at: datetime

    class Config:
        from_attributes = True


class PairSummaryOut(BaseModel):
    pair: str
    latest_rate: float | None
    previous_rate: float | None
    daily_movement: float | None
    percentage_change: float | None
    spread: float | None
    status: str


class AlertRuleCreate(BaseModel):
    pair: str = Field(..., examples=["GBP/USD"])
    threshold_percent: float = Field(1.0, gt=0)


class AlertRuleOut(BaseModel):
    id: int
    pair: str
    threshold_percent: float
    active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class AlertEventOut(BaseModel):
    id: int
    pair: str
    movement_percent: float
    message: str
    created_at: datetime

    class Config:
        from_attributes = True


class ExposureCreate(BaseModel):
    business_unit: str = "Operations"
    currency: str = "INR"
    amount: float = 1000000
    direction: str = "payable"
    description: str | None = "Supplier payment"


class ExposureOut(BaseModel):
    id: int
    business_unit: str
    currency: str
    amount: float
    direction: str
    description: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class TreasurySummaryOut(BaseModel):
    total_exposures: int
    exposure_notes: list[str]
    fx_notes: list[str]
    alerts: list[str]

class LiveRateOut(BaseModel):
    pair: str
    rate: float
    bid_rate: float
    ask_rate: float
    spread: float