"""Agent 3 — Story (GPT-4o text): craft JSON + GI record → Meesho listing copy."""

from __future__ import annotations

import json

from app.llm import chat_json, load_prompt


async def write_listing(craft_json: dict, gi_record: dict | None, language_code: str = "hi") -> dict:
    payload = {
        "craft_analysis": {
            k: craft_json.get(k) for k in ("craft", "style", "motifs", "authenticity_verdict")
        },
        "gi_record": gi_record,
        "artisan_language": language_code,
    }
    result = await chat_json(
        load_prompt("story_listing"),
        json.dumps(payload, ensure_ascii=False),
        what="story.write_listing",
    )
    result["gi_status"] = "verified" if gi_record else "unverified"
    return result
