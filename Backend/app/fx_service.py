from __future__ import annotations

import random
import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.models import RateSnapshot, AlertRule, AlertEvent, Exposure


FALLBACK_RATES = {
    "GBP/USD": 1.27,
    "EUR/USD": 1.08,
    "USD/INR": 83.25,
    "EUR/GBP": 0.85,
}


def parse_pair(pair: str) -> tuple[str, str]:
    clean = pair.upper().replace("-", "/").strip()

    if "/" not in clean:
        raise ValueError("Pair must be in format BASE/QUOTE, example GBP/USD")

    base, quote = clean.split("/", 1)

    if len(base) != 3 or len(quote) != 3:
        raise ValueError("Currency codes must be 3 letters")

    return base, quote


async def fetch_rate(pair: str) -> float:
    base, quote = parse_pair(pair)

    url = f"{settings.FX_API_BASE_URL}/rates/latest"
    params = {
        "base": base,
        "symbols": quote
    }

    try:
        async with httpx.AsyncClient(timeout=8) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            return float(data["rates"][quote])

    except Exception:
        base_rate = FALLBACK_RATES.get(f"{base}/{quote}", 1.0)
        movement = random.uniform(-0.005, 0.005)
        return round(base_rate * (1 + movement), 6)
    
def calculate_spread(mid_rate: float) -> tuple[float, float, float]:
    spread = mid_rate * 0.0008

    bid = mid_rate - spread / 2
    ask = mid_rate + spread / 2

    return round(bid, 6), round(ask, 6), round(spread, 6)

def save_snapshot(db: Session, pair: str, rate: float) -> RateSnapshot:
    base, quote = parse_pair(pair)

    bid, ask, spread = calculate_spread(rate)

    snapshot = RateSnapshot(
        pair=f"{base}/{quote}",
        base_currency=base,
        quote_currency=quote,
        rate=rate,
        bid_rate=bid,
        ask_rate=ask,
        spread=spread,
    )

    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)

    return snapshot
def get_latest_two(db: Session, pair: str) -> list[RateSnapshot]:
    return (
        db.query(RateSnapshot)
        .filter(RateSnapshot.pair == pair.upper())
        .order_by(RateSnapshot.created_at.desc())
        .limit(2)
        .all()
    )
def build_pair_summary(db: Session, pair: str) -> dict:
    pair = pair.upper()

    rows = get_latest_two(db, pair)

    if not rows:
        return {
            "pair": pair,
            "latest_rate": None,
            "previous_rate": None,
            "daily_movement": None,
            "percentage_change": None,
            "spread": None,
            "status": "No data yet",
        }

    latest = rows[0]
    previous = rows[1] if len(rows) > 1 else None

    if previous:
        movement = latest.rate - previous.rate
        percentage_change = (movement / previous.rate) * 100 if previous.rate else 0

        if movement > 0:
            status = "Up"
        elif movement < 0:
            status = "Down"
        else:
            status = "Flat"
    else:
        movement = None
        percentage_change = None
        status = "First snapshot"

    return {
        "pair": pair,
        "latest_rate": latest.rate,
        "previous_rate": previous.rate if previous else None,
        "daily_movement": round(movement, 6) if movement is not None else None,
        "percentage_change": round(percentage_change, 4) if percentage_change is not None else None,
        "spread": latest.spread,
        "status": status,
    }
def check_alerts(db: Session, pair: str) -> list[AlertEvent]:
    summary = build_pair_summary(db, pair)

    percentage_change = summary["percentage_change"]

    if percentage_change is None:
        return []

    rules = (
        db.query(AlertRule)
        .filter(AlertRule.pair == pair.upper(), AlertRule.active == True)
        .all()
    )

    created_alerts = []

    for rule in rules:
        if abs(percentage_change) >= rule.threshold_percent:
            message = (
                f"{pair.upper()} moved by {percentage_change:.2f}% "
                f"which crossed the {rule.threshold_percent:.2f}% threshold."
            )

            event = AlertEvent(
                pair=pair.upper(),
                movement_percent=percentage_change,
                message=message
            )

            db.add(event)
            created_alerts.append(event)

    db.commit()

    return created_alerts

async def collect_snapshot_for_pair(db: Session, pair: str) -> RateSnapshot:
    rate = await fetch_rate(pair)

    snapshot = save_snapshot(db, pair, rate)

    check_alerts(db, snapshot.pair)

    return snapshot
def get_default_pairs() -> list[str]:
    return [
        pair.strip().upper()
        for pair in settings.DEFAULT_PAIRS.split(",")
        if pair.strip()
    ]
def build_treasury_summary(db: Session) -> dict:
    pairs = get_default_pairs()

    fx_notes = []

    for pair in pairs:
        summary = build_pair_summary(db, pair)

        if summary["latest_rate"] is None:
            fx_notes.append(f"{pair}: No rate snapshot available yet.")
        else:
            change = summary["percentage_change"]

            if change is None:
                fx_notes.append(
                    f"{pair}: Latest rate {summary['latest_rate']}. First snapshot captured."
                )
            else:
                fx_notes.append(
                    f"{pair}: Latest {summary['latest_rate']}, "
                    f"movement {change:.2f}% ({summary['status']})."
                )

    exposures = db.query(Exposure).order_by(Exposure.created_at.desc()).all()

    exposure_notes = []

    for exposure in exposures:
        note = (
            f"{exposure.business_unit}: {exposure.direction} exposure of "
            f"{exposure.amount:,.2f} {exposure.currency}"
        )

        if exposure.description:
            note += f" for {exposure.description}"

        exposure_notes.append(note)

    alerts = (
        db.query(AlertEvent)
        .order_by(AlertEvent.created_at.desc())
        .limit(5)
        .all()
    )

    alert_notes = [alert.message for alert in alerts]

    return {
        "total_exposures": len(exposures),
        "exposure_notes": exposure_notes,
        "fx_notes": fx_notes,
        "alerts": alert_notes,
    }