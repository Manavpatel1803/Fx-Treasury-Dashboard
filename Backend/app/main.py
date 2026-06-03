from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.config import settings
from app.database import Base, engine, get_db
from app.models import AlertRule, Exposure, RateSnapshot, AlertEvent
from app.schemas import (
    AlertRuleCreate,
    AlertRuleOut,
    AlertEventOut,
    ExposureCreate,
    ExposureOut,
    PairSummaryOut,
    RateSnapshotOut,
    TreasurySummaryOut,
    LiveRateOut,
)
from app.fx_service import (
    collect_snapshot_for_pair,
    build_pair_summary,
    build_treasury_summary,
    get_default_pairs,
    parse_pair,
    fetch_rate,
    calculate_spread,
)
from app.scheduler import start_scheduler, stop_scheduler


Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="FX Rate Monitor & Treasury Dashboard API",
    description="FastAPI backend for FX snapshots, treasury summaries, exposures, and alerts.",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_ORIGIN,
        "http://localhost:3000",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {
        "message": "FX Treasury Dashboard API is running",
        "docs": "/docs",
        "default_pairs": get_default_pairs(),
    }

@app.get("/pairs")
def get_pairs():
    return {
        "pairs": get_default_pairs()
    }

@app.post("/rates/snapshot/{pair:path}", response_model=RateSnapshotOut)
async def create_snapshot(pair: str, db: Session = Depends(get_db)):
    try:
        parse_pair(pair)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    return await collect_snapshot_for_pair(db, pair)

@app.post("/rates/snapshot-all")
async def create_all_snapshots(db: Session = Depends(get_db)):
    rows = []

    for pair in get_default_pairs():
        rows.append(await collect_snapshot_for_pair(db, pair))

    return {
        "created": len(rows),
        "pairs": [row.pair for row in rows],
    }
@app.get("/rates/latest", response_model=list[PairSummaryOut])
def latest_summaries(db: Session = Depends(get_db)):
    return [
        build_pair_summary(db, pair)
        for pair in get_default_pairs()
    ]
@app.get("/rates/history/{pair:path}", response_model=list[RateSnapshotOut])
def rate_history(pair: str, limit: int = 50, db: Session = Depends(get_db)):
    normalized = pair.upper()

    rows = (
        db.query(RateSnapshot)
        .filter(RateSnapshot.pair == normalized)
        .order_by(RateSnapshot.created_at.desc())
        .limit(limit)
        .all()
    )

    return list(reversed(rows))

@app.post("/alerts", response_model=AlertRuleOut)
def create_alert_rule(payload: AlertRuleCreate, db: Session = Depends(get_db)):
    pair = payload.pair.upper()

    try:
        parse_pair(pair)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    rule = AlertRule(
        pair=pair,
        threshold_percent=payload.threshold_percent
    )

    db.add(rule)
    db.commit()
    db.refresh(rule)

    return rule

@app.get("/alerts/rules", response_model=list[AlertRuleOut])
def list_alert_rules(db: Session = Depends(get_db)):
    return (
        db.query(AlertRule)
        .order_by(AlertRule.created_at.desc())
        .all()
    )
@app.get("/alerts/events", response_model=list[AlertEventOut])
def list_alert_events(db: Session = Depends(get_db)):
    return (
        db.query(AlertEvent)
        .order_by(AlertEvent.created_at.desc())
        .limit(20)
        .all()
    )
@app.post("/exposures", response_model=ExposureOut)
def create_exposure(payload: ExposureCreate, db: Session = Depends(get_db)):
    if payload.direction.lower() not in ["payable", "receivable"]:
        raise HTTPException(
            status_code=400,
            detail="direction must be payable or receivable"
        )

    exposure = Exposure(
        business_unit=payload.business_unit,
        currency=payload.currency.upper(),
        amount=payload.amount,
        direction=payload.direction.lower(),
        description=payload.description,
    )

    db.add(exposure)
    db.commit()
    db.refresh(exposure)

    return exposure
@app.get("/exposures", response_model=list[ExposureOut])
def list_exposures(db: Session = Depends(get_db)):
    return (
        db.query(Exposure)
        .order_by(Exposure.created_at.desc())
        .all()
    )
@app.get("/treasury-summary", response_model=TreasurySummaryOut)
def treasury_summary(db: Session = Depends(get_db)):
    return build_treasury_summary(db)

@app.get("/rates/live", response_model=list[LiveRateOut])
async def live_rates():
    live_data = []

    for pair in get_default_pairs():
        rate = await fetch_rate(pair)
        bid_rate, ask_rate, spread = calculate_spread(rate)

        live_data.append({
            "pair": pair,
            "rate": rate,
            "bid_rate": bid_rate,
            "ask_rate": ask_rate,
            "spread": spread,
        })

    return live_data