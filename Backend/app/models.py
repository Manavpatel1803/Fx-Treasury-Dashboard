from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean

from app.database import Base


class RateSnapshot(Base):
    __tablename__ = "rate_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    pair = Column(String(20), index=True, nullable=False)
    base_currency = Column(String(3), nullable=False)
    quote_currency = Column(String(3), nullable=False)
    rate = Column(Float, nullable=False)
    bid_rate = Column(Float, nullable=False)
    ask_rate = Column(Float, nullable=False)
    spread = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id = Column(Integer, primary_key=True, index=True)
    pair = Column(String(20), index=True, nullable=False)
    threshold_percent = Column(Float, nullable=False)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AlertEvent(Base):
    __tablename__ = "alert_events"

    id = Column(Integer, primary_key=True, index=True)
    pair = Column(String(20), index=True, nullable=False)
    movement_percent = Column(Float, nullable=False)
    message = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class Exposure(Base):
    __tablename__ = "exposures"

    id = Column(Integer, primary_key=True, index=True)
    business_unit = Column(String(100), nullable=False)
    currency = Column(String(3), nullable=False)
    amount = Column(Float, nullable=False)
    direction = Column(String(20), nullable=False)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)