"""Fetch recent, relevant news headlines for a currency pair.

Two sources, combined and de-duplicated:
  * Financial RSS feeds (ForexLive, CNBC Currencies, WSJ Markets) — free, no key,
    and reliable from cloud IPs. This is the backbone.
  * GDELT 2.0 DOC API — free, query-specific, but rate-limits shared/cloud IPs
    aggressively, so it's best-effort only.

Both sources return noisy headlines (feeds mix in unrelated stories), so every
article is scored by whether its *headline* actually mentions one of the pair's
currencies; anything that doesn't is dropped. This is what makes explanations
grounded in genuinely relevant news instead of whatever mentioned "dollar".
"""
from __future__ import annotations

import asyncio
import logging
import xml.etree.ElementTree as ET
from urllib.parse import urlparse

import httpx

from app.config import settings
from app.fx_service import parse_pair


logger = logging.getLogger(__name__)


GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"

# Reliable, key-free financial news feeds (RSS 2.0).
RSS_FEEDS = [
    "https://www.forexlive.com/feed/",
    "https://www.cnbc.com/id/10000664/device/rss/rss.html",  # CNBC Currencies
    "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",         # WSJ Markets
]

HTTP_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; FXDashboard/1.0)"}


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
    unrelated markets/tech noise that merely mentions "currency" scores low and
    is dropped, while "Rupee slips as dollar firms after Fed" scores high.
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


async def _fetch_gdelt(client: httpx.AsyncClient, base: str, quote: str) -> list[dict]:
    """Best-effort GDELT fetch. Returns [] on throttle/error."""
    params = {
        "query": _build_query(base, quote),
        "mode": "artlist",
        "format": "json",
        "maxrecords": 40,
        "sort": "datedesc",
        "timespan": "3d",
    }
    try:
        response = await client.get(GDELT_URL, params=params, headers=HTTP_HEADERS)
        response.raise_for_status()
        # GDELT returns HTTP 200 with a plain-text notice when rate-limited.
        if "application/json" not in response.headers.get("content-type", ""):
            logger.info("GDELT throttled/non-JSON: %s", response.text[:100])
            return []
        articles = response.json().get("articles", []) or []
    except Exception as error:
        logger.info("GDELT fetch skipped: %s", error)
        return []

    return [
        {
            "title": (a.get("title") or "").strip(),
            "url": a.get("url", ""),
            "source": a.get("domain", ""),
            "published": a.get("seendate", ""),
        }
        for a in articles
        if (a.get("title") or "").strip()
    ]


async def _fetch_rss(client: httpx.AsyncClient, url: str) -> list[dict]:
    """Fetch and parse a single RSS 2.0 feed. Returns [] on error."""
    try:
        response = await client.get(url, headers=HTTP_HEADERS, follow_redirects=True)
        response.raise_for_status()
        # Parse bytes (not str) so an XML encoding declaration doesn't error.
        root = ET.fromstring(response.content)
    except Exception as error:
        logger.info("RSS fetch failed for %s: %s", url, error)
        return []

    items: list[dict] = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        if not title:
            continue
        items.append(
            {
                "title": title,
                "url": link,
                "source": urlparse(link).netloc or urlparse(url).netloc,
                "published": (item.findtext("pubDate") or "").strip(),
            }
        )
    return items


async def fetch_pair_news(pair: str) -> list[dict]:
    """Return recent, headline-relevant articles for the pair.

    Each item: {title, url, source, published, score}. Returns [] on total
    failure so the explanation flow degrades gracefully rather than erroring.
    """
    base, quote = parse_pair(pair)

    async with httpx.AsyncClient(timeout=12) as client:
        tasks = [_fetch_gdelt(client, base, quote)]
        tasks += [_fetch_rss(client, url) for url in RSS_FEEDS]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    raw: list[dict] = []
    for res in results:
        if isinstance(res, list):
            raw.extend(res)

    scored: list[dict] = []
    seen_titles: set[str] = set()

    for article in raw:
        title = article["title"]
        key = title.lower()
        if key in seen_titles:
            continue

        score = _relevance_score(title, base, quote)
        if score < 3:
            # Headline doesn't clearly mention either currency — drop the noise.
            continue

        seen_titles.add(key)
        scored.append({**article, "score": score})

    # Most relevant first.
    scored.sort(key=lambda a: a["score"], reverse=True)

    return scored[: settings.NEWS_MAX_ARTICLES]
