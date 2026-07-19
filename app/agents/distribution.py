"""Agent 5 — Distribution: publishing + order lifecycle + returns classification."""

from __future__ import annotations

import json

from app.agentlog import log_event
from app.llm import chat_json, load_prompt


async def appreciation_message(artisan_name: str, title: str, rating: int,
                               comment: str, language_code: str = "hi") -> str:
    """Warm per-review notification for the artisan (real GPT-4o, Distribution)."""
    result = await chat_json(
        load_prompt("review_appreciation"),
        json.dumps({"artisan_name": artisan_name, "title": title, "rating": rating,
                    "comment": comment or "", "language": language_code}, ensure_ascii=False),
        what="distribution.appreciation",
    )
    msg = result.get("message", "")
    log_event("distribution", f"review appreciation ({rating}★)", {"title": title, "message": msg})
    return msg


async def classify_return(reason_text: str) -> dict:
    result = await chat_json(
        load_prompt("returns_classify"),
        json.dumps({"return_reason": reason_text}, ensure_ascii=False),
        what="distribution.classify_return",
    )
    classification = result.get("classification", "other")
    if classification not in {"rto", "quality", "other"}:
        classification = "other"
    out = {
        "classification": classification,
        "rating_protected": bool(result.get("rating_protected", classification != "quality")),
    }
    log_event("distribution", f"return classified → {classification}", {"reason": reason_text, **out})
    return out
