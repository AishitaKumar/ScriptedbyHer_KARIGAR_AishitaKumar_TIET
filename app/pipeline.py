"""The listing pipeline: Vision → [Photo ∥ (GI → Story) ∥ Pricing] → listing package."""

from __future__ import annotations

import asyncio
import logging

from app.agents import photo, pricing, story, vision
from app.mocks import gi_registry

logger = logging.getLogger("karigar.pipeline")

AUTHENTICITY_PASS_VERDICTS = {"handmade", "likely_handmade"}
AUTHENTICITY_REJECT_VERDICTS = {"print", "likely_print"}


def triage_batch(analyses: list[dict]) -> dict:
    """Split per-image Vision results into usable / dropped / suspect / rejected."""
    usable, dropped, suspect = [], [], []
    rejected_reasons: list[str] = []
    for i, a in enumerate(analyses):
        verdict = a.get("authenticity_verdict")
        if verdict in AUTHENTICITY_REJECT_VERDICTS:
            rejected_reasons.extend(a.get("reasons", []))
        elif verdict == "suspect_downloaded_image":
            suspect.append(i)
        elif a.get("quality_score") == "pass" and verdict in AUTHENTICITY_PASS_VERDICTS:
            usable.append(i)
        else:
            dropped.append(i)
    if rejected_reasons:
        return {"outcome": "rejected", "usable": [], "dropped": dropped,
                "suspect": suspect, "reasons": rejected_reasons}
    if not usable:
        outcome = "all_suspect" if suspect and not dropped else "all_failed"
        return {"outcome": outcome, "usable": [], "dropped": dropped,
                "suspect": suspect, "reasons": []}
    return {"outcome": "ok", "usable": usable, "dropped": dropped + suspect,
            "suspect": suspect, "reasons": []}


async def build_listing_package(
    images: list[tuple[bytes, str]], language_code: str = "hi"
) -> dict:
    """Run the full pipeline over a photo batch."""
    analyses = await vision.analyze_batch(images, language_code)
    triage = triage_batch(analyses)
    if triage["outcome"] != "ok":
        return {**triage, "analyses": analyses}

    rep_index = triage["usable"][0]
    craft_json = analyses[rep_index]

    gi_record = gi_registry.lookup(craft_json.get("craft"))

    enhanced_bytes, story_result, price_result = await asyncio.gather(
        asyncio.to_thread(photo.enhance, images[rep_index][0]),
        story.write_listing(craft_json, gi_record, language_code),
        pricing.recommend_price(craft_json),
    )

    return {
        "outcome": "ok",
        "analyses": analyses,
        "usable_indices": triage["usable"],
        "dropped_indices": triage["dropped"],
        "craft_json": craft_json,
        "gi_record": gi_record,
        "enhanced_photo": enhanced_bytes,
        "listing": {
            "craft_type": craft_json.get("craft"),
            "style": craft_json.get("style"),
            "motifs": craft_json.get("motifs", []),
            "title": story_result.get("title"),
            "title_hi": story_result.get("title_hi"),
            "description": story_result.get("description"),
            "gi_status": story_result.get("gi_status", "unverified"),
            "price": price_result["price"],
            "original_price": price_result["original_price"],
            "in_hand": price_result["in_hand"],
            "quality_score": craft_json.get("quality_score"),
            "authenticity_score": craft_json.get("authenticity_score"),
            "authenticity_reasons": craft_json.get("reasons", []),
        },
    }
