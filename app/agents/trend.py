"""Agent 7 — Trend (Tier 2, committed): weekly coaching from real sales/returns data."""

from __future__ import annotations

import json
from collections import Counter
from datetime import date

from app.agentlog import log_event
from app.db import queries
from app.flows.common import say
from app.llm import chat_json, load_prompt
from app.transports.base import Transport


async def run_for_artisan(artisan: dict, transport: Transport) -> str | None:
    from app.flows.messages import set_lang

    set_lang(artisan.get("language_code"))
    lang = artisan.get("language_code", "hi")
    craft = artisan.get("craft")

    orders = await queries.orders_for_artisan(artisan["id"], days=7)
    sold = [o for o in orders if o["status"] in {"placed", "shipped", "delivered"}]
    returns = await queries.returns_for_artisan(artisan["id"])
    reviews = await queries.reviews_for_artisan(artisan["id"])

    def _htitle(o):
        li = o.get("listings") or {}
        return (li.get("title_hi") if lang == "hi" else None) or li.get("title") or "कला"

    by_title = Counter(_htitle(o) for o in sold)
    ratings = [r["rating"] for r in reviews if r.get("rating")]
    exchange_reasons = [r.get("reason_text") for r in returns if r.get("classification") == "exchange"]
    return_reasons = [
        {"type": r.get("classification"), "reason": r.get("reason_text")}
        for r in returns if r.get("classification") != "exchange"
    ]

    platform = await queries.platform_demand(days=7)
    similar_units = next((p["units_ordered"] for p in platform if p.get("craft") == craft), 0)
    has_own_sales = len(sold) > 0

    data = {
        "artisan_name": artisan.get("name") or "बहन",
        "language": lang,
        "her_craft": craft,
        "today": date.today().isoformat(),
        "has_own_sales": has_own_sales,
        "her_sales_last_7_days": [
            {"title": title, "units": units} for title, units in by_title.most_common()
        ],
        "total_units_sold": len(sold),
        "her_reviews": {
            "count": len(ratings),
            "average_rating": round(sum(ratings) / len(ratings), 1) if ratings else None,
            "comments": [r.get("comment") for r in reviews if r.get("comment")][:8],
        },
        "her_return_reasons": return_reasons,
        "her_exchange_reasons": exchange_reasons,
        "marketplace_demand_all_crafts": platform,
        "similar_craft_units_ordered_marketplace": {"craft": craft, "units": similar_units},
    }
    result = await chat_json(
        load_prompt("trend_advice"), json.dumps(data, ensure_ascii=False),
        what="trend.advice", temperature=0.4,
    )
    advice = result.get("advice_hi")
    log_event("trend", "weekly coaching generated", {"data": data, "advice": advice})
    if advice:
        await say(transport, artisan["whatsapp_phone"], advice, artisan_id=artisan["id"])
    return advice
