"""Agent 1 — Vision (GPT-4o Vision)."""

from __future__ import annotations

import asyncio

from app.llm import VISION_MODEL, chat_json, image_content, load_prompt


def _lang_note(language_code: str) -> str:
    return ("Write reasons[] in simple English." if language_code == "en"
            else "Write reasons[] in simple Hindi (Devanagari).")


async def analyze_photo(image_bytes: bytes, mime: str = "image/jpeg",
                        language_code: str = "hi") -> dict:
    """Layer-1 authenticity + craft identification for one photo."""
    return await chat_json(
        load_prompt("vision_authenticity"),
        [
            {"type": "text", "text": f"Analyse this product photo. {_lang_note(language_code)}"},
            image_content(image_bytes, mime),
        ],
        model=VISION_MODEL,
        what="vision.analyze_photo",
    )


async def analyze_batch(images: list[tuple[bytes, str]], language_code: str = "hi") -> list[dict]:
    """Analyse a photo batch concurrently. Returns per-image results in order."""
    return list(
        await asyncio.gather(*(analyze_photo(data, mime, language_code) for data, mime in images))
    )


async def evaluate_back_challenge(image_bytes: bytes, mime: str = "image/jpeg",
                                  language_code: str = "hi") -> dict:
    """Layer-2: evaluate the back-of-painting challenge photo."""
    return await chat_json(
        load_prompt("vision_challenge_back"),
        [
            {"type": "text",
             "text": f"This is the challenge photo the sender submitted. {_lang_note(language_code)}"},
            image_content(image_bytes, mime),
        ],
        model=VISION_MODEL,
        what="vision.back_challenge",
    )


async def cluster_batch(images: list[tuple[bytes, str]]) -> dict:
    """Tier-2 Mechanic A: ONE Vision call over all images → JSON groups of indices."""
    content: list[dict] = [
        {"type": "text", "text": f"Batch of {len(images)} photos, in order (index 0 first)."}
    ]
    for data, mime in images:
        content.append(image_content(data, mime, detail="low"))
    result = await chat_json(
        load_prompt("vision_clustering"), content, model=VISION_MODEL, what="vision.cluster"
    )
    seen: set[int] = set()
    groups = []
    for group in result.get("groups", []):
        indices = [i for i in group.get("image_indices", []) if 0 <= i < len(images) and i not in seen]
        seen.update(indices)
        if indices:
            groups.append({"image_indices": indices, "label": group.get("label", "design")})
    leftover = [i for i in range(len(images)) if i not in seen]
    if leftover:
        groups.append({"image_indices": leftover, "label": "ungrouped"})
    return {"groups": groups}
