"""Real Meesho comparable prices via OpenAI web search."""

from __future__ import annotations

import asyncio
import json
import logging
import re

from app.agentlog import log_event
from app.llm import client

logger = logging.getLogger("karigar.market_prices")

_cache: dict[str, dict] = {}

_MIN, _MAX = 60, 3000
_SEARCH_TIMEOUT = 8.0


async def prewarm(*crafts: str) -> None:
    """Warm the cache for the demo's common crafts so the first real listing doesn't pay the web-search latency."""
    for craft in crafts:
        try:
            await comparable_band(craft)
        except Exception:  # noqa: BLE001
            pass


async def comparable_band(craft: str | None, style: str | None = None) -> dict | None:
    """Return {"low", "high", "source"} for the craft from live Meesho listings, or None if the search fails / times out / returns something implausible."""
    key = (craft or "").strip().lower()
    if not key:
        return None
    if key in _cache:
        return _cache[key]

    what = f"{style + ' ' if style else ''}{craft}".strip()
    prompt = (
        f"Search Meesho.com for currently listed handmade '{what}' items "
        f"(wall art / painting / decor, unframed). Find the typical SELLING price "
        f"range in Indian rupees across several real listings. "
        f'Reply with ONLY a JSON object: {{"low": <int>, "high": <int>, "source": "<one meesho url>"}} '
        f"— low and high are whole rupees."
    )
    try:
        resp = await asyncio.wait_for(
            client().responses.create(
                model="gpt-4o",
                tools=[{"type": "web_search_preview"}],
                input=prompt,
            ),
            timeout=_SEARCH_TIMEOUT,
        )
        text = resp.output_text or ""
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return None
        data = json.loads(match.group(0))
        low, high = int(data["low"]), int(data["high"])
        if not (_MIN <= low < high <= _MAX):
            logger.warning("market band out of range for %s: %s-%s", key, low, high)
            return None
        band = {"low": low, "high": high, "source": data.get("source", "meesho.com")}
        _cache[key] = band
        log_event("pricing", f"live Meesho price band for {key}: ₹{low}-₹{high}", band)
        return band
    except Exception as e:  # noqa: BLE001 — never block pricing on web search
        logger.warning("web-search pricing failed for %s: %s", key, e)
        return None
