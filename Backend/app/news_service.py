"""Fetch recent, relevant news headlines for a currency pair.

Uses the GDELT 2.0 DOC API (free, no key). GDELT matches article *bodies*, so a
raw query returns lots of off-topic pieces that merely mention "dollar" somewhere.
To fix relevance we fetch broad, then keep only articles whose *headline* actually
mentions one of the pair's currencies (or an explicit FX term), ranked by how
directly the headline is about the pair.

Docs: https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/
"""
from __future__ import annotations

import logging

import httpx

from app.config import settings
from app.fx_service import parse_pair


logger = logging.getLogger(__name__)


GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"


# GDELT search phrases per currency (currency name + central bank).
CURRENCY_TERMS: dict[str, list[str]] = {
    "USD": ['"US dollar"', '"Federal Reserve"'],
    "EUR": ['"euro"', '"European Central Bank"'],
    "GBP": ['"British pound"', '"Bank of England"'],
    "INR": ['"Indian rupee"', '"Reserve Bank of India"'],
    "JPY": ['"Japanese yen"', '"Bank of Japan"'],
    "AUD": ['"Australian dollar"', '"Reserve Bank of Australia"'],
    "CAD": ['"Canadian dollar"', '"Bank of Canada"'],
    "CHF": ['"Swiss franc"', '"Swiss National Bank"'],
    "CNY": ['"Chinese yuan"', '"People\'s Bank of China"'],
}

# Lowercase substrings used to decide if a *headline* is really about a currency.
CURRENCY_TITLE_KEYWORDS: dict[str, list[str]] = {
    "USD": ["dollar", "greenback", "fed ", "federal reserve", "u.s. rate", "us rate"],
    "EUR": ["euro", "ecb", "eurozone"],
    "GBP": ["pound", "sterling", "boe", "bank of england"],
    "INR": ["rupee", "rbi", "reserve bank of india"],
    "JPY": ["yen", "boj", "bank of japan"],
    "AUD": ["aussie", "australian dollar", "rba"],
    "CAD": ["loonie", "canadian dollar"],
    "CHF": ["franc", "snb"],
    "CNY": ["yuan", "renminbi", "pboc"],
}

# General FX signals in a headline (weaker than a specific currency mention).
FX_TITLE_KEYWORDS = [
    "forex", "fx ", "exchange rate", "currency", "currencies",
    "dollar index", "central bank", "interest rate", "rate cut", "rate hike",
    "inflation", "cpi",
]


def _build_query(base: str, quote: str) -> str:
    """Broad GDELT query: any of the two currencies' phrases, English only."""
    terms: list[str] = []
    for code in (base, quote):
        terms.extend(CURRENCY_TERMS.get(code, [f'"{code}"']))

    return "(" + " OR ".join(terms) + ") sourcelang:english"


def _relevance_score(title: str, base: str, quote: str) -> int:
    """Score a headline's relevance to the pair. Higher = more on-topic.

    A specific currency mention is worth far more than a generic FX word, so
    copper/tech/markets noise that merely mentions "currency" scores 0 and is
    dropped, while "Rupee slips as dollar firms after Fed" scores high.
    """
    low = f" {title.lower()} "
    score = 0

    if any(kw in low for kw in CURRENCY_TITLE_KEYWORDS.get(base, [base.lower()])):
        score += 3
    if any(kw in low for kw in CURRENCY_TITLE_KEYWORDS.get(quote, [quote.lower()])):
        score += 3
    if any(kw in low for kw in FX_TITLE_KEYWORDS):
        score += 1
    if f"{base.lower()}/{quote.lower()}" in low or f"{base.lower()}{quote.lower()}" in low:
        score += 4

    return score


async def fetch_pair_news(pair: str) -> list[dict]:
    """Return recent, headline-relevant articles for the pair.

    Each item: {title, url, source, published, score}. Returns [] on any
    failure so the explanation flow degrades gracefully rather than erroring.
    """
    base, quote = parse_pair(pair)

    params = {
        "query": _build_query(base, quote),
        "mode": "artlist",
        "format": "json",
        # Fetch broad so the headline filter has material to rank.
        "maxrecords": 40,
        "sort": "datedesc",
        "timespan": "3d",
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(GDELT_URL, params=params)
            response.raise_for_status()
            # GDELT returns HTTP 200 with a plain-text notice when rate-limited,
            # which is not JSON — surface that clearly instead of a decode error.
            if "application/json" not in response.headers.get("content-type", ""):
                logger.warning(
                    "GDELT throttled/non-JSON for %s: %s", pair, response.text[:120]
                )
                return []
            data = response.json()
    except Exception as error:
        logger.warning("GDELT news fetch failed for %s: %s", pair, error)
        return []

    articles = data.get("articles", []) or []

    scored: list[dict] = []
    seen_titles: set[str] = set()

    for article in articles:
        title = (article.get("title") or "").strip()
        if not title:
            continue

        # De-duplicate near-identical syndicated headlines.
        key = title.lower()
        if key in seen_titles:
            continue

        score = _relevance_score(title, base, quote)
        if score < 3:
            # Headline doesn't clearly mention either currency — drop the noise.
            continue

        seen_titles.add(key)
        scored.append(
            {
                "title": title,
                "url": article.get("url", ""),
                "source": article.get("domain", ""),
                "published": article.get("seendate", ""),
                "score": score,
            }
        )

    # Most relevant first; stable sort keeps GDELT's recency order within a tier.
    scored.sort(key=lambda a: a["score"], reverse=True)

    return scored[: settings.NEWS_MAX_ARTICLES]
