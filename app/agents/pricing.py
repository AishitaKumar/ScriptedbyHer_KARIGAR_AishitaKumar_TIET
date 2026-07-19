"""Agent 4 — Pricing (GPT-4o text)."""

from __future__ import annotations

import json

from app.llm import chat_json, load_prompt
from app.services import meesho

FLAT_DEDUCTION = 60

PRICE_CAP = 1700


def in_hand_amount(price: int) -> int:
    return max(price - FLAT_DEDUCTION, 0)


def _tier_price(band: dict, intricacy: str) -> int:
    """Deterministic mapping: intricacy class → price point in the band, ending in 9."""
    low, high = band["low"], band["high"]
    raw = {"low": low, "medium": (low + high) // 2, "high": high}.get(intricacy, (low + high) // 2)
    price = (raw // 10) * 10 - 1
    if price < low:
        price = low
    return min(price, PRICE_CAP)


async def recommend_price(craft_json: dict) -> dict:
    from app.services import market_prices

    craft = craft_json.get("craft")
    live_band = await market_prices.comparable_band(craft, craft_json.get("style"))
    if live_band:
        band = {"low": live_band["low"], "high": live_band["high"]}
        comparables = {"price_band": band, "source": "meesho web search",
                       "market_source": live_band.get("source")}
    else:
        comparables = await meesho.get_category_comparables(craft)
        band = comparables["price_band"]
    payload = {
        "craft_analysis": {
            k: craft_json.get(k)
            for k in ("craft", "style", "motifs", "quality_score", "authenticity_score", "reasons")
        },
        "category_comparables": comparables,
    }
    result = await chat_json(
        load_prompt("pricing"), json.dumps(payload, ensure_ascii=False),
        what="pricing.recommend", temperature=0,
    )
    intricacy = result.get("intricacy_level", "medium")
    price = _tier_price(band, intricacy)
    return {
        "price": price,
        "original_price": min(int(price * 1.5), int(price * 1.6)),
        "in_hand": in_hand_amount(price),
        "intricacy": intricacy,
        "reasoning": result.get("reasoning", ""),
    }
