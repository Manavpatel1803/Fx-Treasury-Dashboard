"""Produce a plain-English explanation of why an FX pair moved.

Flow: detect the recent move -> gather relevant news -> ask an LLM to explain
the move using ONLY those headlines (so it can't invent reasons) -> cache the
result so we don't re-call the LLM on every page load.

LLM provider is configurable (Gemini free tier by default, Anthropic optional).
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.fx_service import build_pair_summary, fetch_daily_change, parse_pair
from app.models import Explanation
from app.news_service import fetch_pair_news


logger = logging.getLogger(__name__)


def _direction_from_change(change: float | None) -> str:
    if change is None:
        return "flat"
    if change > 0.05:
        return "up"
    if change < -0.05:
        return "down"
    return "flat"


def _build_prompt(pair: str, change: float | None, direction: str, headlines: list[dict]) -> str:
    if headlines:
        news_block = "\n".join(f"- {item['title']}" for item in headlines)
    else:
        news_block = "(no relevant headlines found)"

    move_text = (
        f"moved {direction} by {abs(change):.2f}%"
        if change is not None
        else "showed little measurable movement"
    )

    return (
        "You are an FX market analyst writing for retail traders.\n"
        f"The currency pair {pair} has {move_text} recently.\n\n"
        "Recent news headlines relevant to these two currencies:\n"
        f"{news_block}\n\n"
        "In ONE clear sentence, explain the most likely driver of this move using "
        "ONLY the headlines above. If the headlines do not plausibly explain the "
        "move, say the specific drivers are unclear from available news. "
        "Do NOT give trading advice or predictions. Do not invent facts."
    )


async def _explain_with_gemini(prompt: str) -> str:
    url = (
        f"{settings.GEMINI_BASE_URL}/models/{settings.GEMINI_MODEL}:generateContent"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 300,
            # gemini-2.5-* are "thinking" models; disable internal reasoning so
            # the token budget goes to the visible one-sentence answer.
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            url,
            params={"key": settings.GEMINI_API_KEY},
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

    return data["candidates"][0]["content"]["parts"][0]["text"].strip()


async def _explain_with_anthropic(prompt: str) -> str:
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": settings.ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": settings.ANTHROPIC_MODEL,
        "max_tokens": 200,
        "messages": [{"role": "user", "content": prompt}],
    }

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

    return data["content"][0]["text"].strip()


async def _generate_explanation_text(prompt: str) -> str:
    provider = settings.LLM_PROVIDER.lower()

    try:
        if provider == "anthropic" and settings.ANTHROPIC_API_KEY:
            return await _explain_with_anthropic(prompt)
        if provider == "gemini" and settings.GEMINI_API_KEY:
            return await _explain_with_gemini(prompt)
    except Exception as error:
        logger.warning("LLM explanation failed (%s): %s", provider, error)
        return ""

    # No key configured for the selected provider.
    return ""


def _get_cached(db: Session, pair: str) -> Explanation | None:
    cutoff = datetime.utcnow() - timedelta(minutes=settings.EXPLANATION_CACHE_MINUTES)
    return (
        db.query(Explanation)
        .filter(Explanation.pair == pair, Explanation.created_at >= cutoff)
        .order_by(Explanation.created_at.desc())
        .first()
    )


async def explain_pair(db: Session, pair: str, force: bool = False) -> dict:
    """Return a cached-or-fresh explanation for why the pair moved."""
    pair = pair.upper()
    parse_pair(pair)  # validates format, raises ValueError if bad

    if not force:
        cached = _get_cached(db, pair)
        if cached:
            return {
                "pair": cached.pair,
                "move_percent": cached.move_percent,
                "direction": cached.direction,
                "explanation": cached.explanation_text,
                "sources": json.loads(cached.sources_json) if cached.sources_json else [],
                "generated_at": cached.created_at,
                "cached": True,
            }

    # Prefer a real intraday move from the market-data provider; fall back to
    # the change computed from stored snapshots.
    change = await fetch_daily_change(pair)
    if change is None:
        change = build_pair_summary(db, pair).get("percentage_change")
    direction = _direction_from_change(change)

    headlines = await fetch_pair_news(pair)
    prompt = _build_prompt(pair, change, direction, headlines)

    text = await _generate_explanation_text(prompt)
    if not text:
        text = (
            "Explanation unavailable — no LLM API key is configured, or the news "
            "service returned nothing. Add GEMINI_API_KEY to enable this feature."
        )

    sources = [{"title": h["title"], "url": h["url"], "source": h["source"]} for h in headlines]

    record = Explanation(
        pair=pair,
        move_percent=change,
        direction=direction,
        explanation_text=text[:1000],
        sources_json=json.dumps(sources),
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "pair": pair,
        "move_percent": change,
        "direction": direction,
        "explanation": record.explanation_text,
        "sources": sources,
        "generated_at": record.created_at,
        "cached": False,
    }
