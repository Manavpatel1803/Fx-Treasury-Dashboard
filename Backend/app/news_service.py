"""Fetch recent, relevant news headlines for a currency pair.

Uses the GDELT 2.0 DOC API, which is free and requires no API key.
Docs: https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/
"""
from __future__ import annotations

import logging

import httpx

from app.config import settings
from app.fx_service import parse_pair


logger = logging.getLogger(__name__)


GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"


# Map ISO currency codes to human search terms (currency name + central bank /
# key driver) so GDELT returns FX-relevant articles rather than random matches.
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


def _build_query(base: str, quote: str) -> str:
    """Build a GDELT boolean query for the two currencies in the pair.

    We OR together currency/central-bank phrases, then AND a forex-context
    clause and restrict to English so results are FX-relevant rather than any
    article that merely mentions "dollar" somewhere in its body.
    """
    terms: list[str] = []
    for code in (base, quote):
        terms.extend(CURRENCY_TERMS.get(code, [f'"{code}"']))

    currency_clause = "(" + " OR ".join(terms) + ")"
    context_clause = '(forex OR "exchange rate" OR currency OR "central bank")'

    return f"{currency_clause} {context_clause} sourcelang:english"


async def fetch_pair_news(pair: str) -> list[dict]:
    """Return a list of recent headlines relevant to the pair.

    Each item: {title, url, source, published}. Returns [] on any failure so
    the explanation flow degrades gracefully rather than erroring.
    """
    base, quote = parse_pair(pair)

    params = {
        "query": _build_query(base, quote),
        "mode": "artlist",
        "format": "json",
        "maxrecords": settings.NEWS_MAX_ARTICLES,
        "sort": "datedesc",
        "timespan": "3d",
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(GDELT_URL, params=params)
            response.raise_for_status()
            data = response.json()
    except Exception as error:
        logger.warning("GDELT news fetch failed for %s: %s", pair, error)
        return []

    articles = data.get("articles", []) or []

    results: list[dict] = []
    for article in articles:
        title = (article.get("title") or "").strip()
        if not title:
            continue
        results.append(
            {
                "title": title,
                "url": article.get("url", ""),
                "source": article.get("domain", ""),
                "published": article.get("seendate", ""),
            }
        )

    return results
