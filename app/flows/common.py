"""Shared flow helpers: speak+send, inbound normalization, name matching."""

from __future__ import annotations

import asyncio
import logging
import re

from app.agentlog import log_event
from app.db import queries
from app.db.client import upload_media
from app.jobs.queue import enqueue
from app.llm import LLMError
from app.transports.base import Button, InboundMessage, OutboundMessage, Transport
from app.voice import stt, tts

logger = logging.getLogger("karigar.flows")

_DIGIT_WORDS = {
    "hi": ["शून्य", "एक", "दो", "तीन", "चार", "पाँच", "छह", "सात", "आठ", "नौ"],
    "en": ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"],
}
_EMOJI_RE = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF✅❤️•]"
)


def spell_digits(text: str, lang: str = "hi") -> str:
    """Replace every digit with its spoken word so TTS voices it individually."""
    words = _DIGIT_WORDS.get(lang, _DIGIT_WORDS["hi"])
    return re.sub(r"\d", lambda m: f" {words[int(m.group())]} ", text)


def voice_of(display_text: str, lang: str = "hi") -> str:
    """Turn an on-screen identifier card into a voice script: strip emoji/bullets and spell out digits so the voice note reads the details aloud, correctly."""
    cleaned = _EMOJI_RE.sub("", display_text)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    return spell_digits(cleaned, lang).strip()


async def say(
    transport: Transport,
    to: str,
    text: str,
    *,
    buttons: list[Button] | None = None,
    image_url: str | None = None,
    voice: bool = True,
    voice_text: str | None = None,
    language_code: str | None = None,
    artisan_id: str | None = None,
    meta: dict | None = None,
) -> None:
    """Every bot message = voice note (TTS) + matching text."""
    from app.flows.messages import current_lang

    if language_code is None:
        language_code = current_lang()
    if buttons and not transport.supports_buttons():
        fallback = " | ".join(f"{i} = {b.label}" for i, b in enumerate(buttons, 1))
        text = f"{text}\nजवाब में नंबर भेजें: {fallback}"
    audio_url = None
    if voice:
        try:
            audio = await tts.speak(voice_text or text, language_code)
            audio_url = await asyncio.to_thread(
                upload_media, audio, ".ogg", "audio/ogg", "voice"
            )
        except (LLMError, Exception):  # noqa: BLE001 — text must still go out
            logger.exception("TTS failed; sending text only")
    await transport.send(
        OutboundMessage(
            to=to, text=text, audio_url=audio_url,
            image_url=image_url, buttons=buttons or [], meta=meta or {},
        )
    )
    if artisan_id:
        enqueue(queries.log_voice_message(
            {"artisan_id": artisan_id, "direction": "outbound", "transcript": text,
             "audio_url": audio_url, "language_code": language_code}), name="voicelog")


async def incoming_text(msg: InboundMessage, artisan: dict | None = None) -> str | None:
    """Normalize inbound to text: transcribe voice notes, pass text/buttons through."""
    if msg.type in {"text", "button"}:
        return msg.text
    if msg.type == "audio" and msg.media:
        transcript = await stt.transcribe(msg.media, language_code=(artisan or {}).get("language_code", "hi"))
        log_event("whisper", "voice note transcribed", {"transcript": transcript})
        if artisan:
            enqueue(queries.log_voice_message(
                {"artisan_id": artisan["id"], "direction": "inbound",
                 "transcript": transcript, "language_code": artisan.get("language_code", "hi")}),
                name="voicelog")
        return transcript
    return None


_HONORIFICS = {"shri", "smt", "श्री", "श्रीमती", "kumari", "mr", "mrs", "ms", "जी"}


def normalize_name(name: str) -> list[str]:
    tokens = re.split(r"[\s.]+", name.strip().lower())
    return [t for t in tokens if t and t not in _HONORIFICS]


from difflib import SequenceMatcher

_FUZZY_RATIO = 0.72


def _tokens_close(x: str, y: str) -> bool:
    if x == y:
        return True
    if len(x) == 1 or len(y) == 1:
        return x[0] == y[0]
    if min(len(x), len(y)) >= 5:
        return SequenceMatcher(None, x, y).ratio() >= _FUZZY_RATIO
    return False


def names_match(a: str | None, b: str | None) -> bool:
    """Identity Anchor name check: same person across PAN / passbook."""
    if not a or not b:
        return False
    ta, tb = normalize_name(a), normalize_name(b)
    if not ta or not tb:
        return False
    smaller, larger = (ta, tb) if len(ta) <= len(tb) else (tb, ta)
    remaining = list(larger)
    for token in smaller:
        hit = next((r for r in remaining if _tokens_close(token, r)), None)
        if hit is None:
            return False
        remaining.remove(hit)
    return True


def yes_no_buttons() -> list[Button]:
    from app.flows.messages import t

    return [Button("yes", t("yes_label")), Button("no", t("no_label"))]


async def names_match_smart(a: str | None, b: str | None) -> bool:
    """Identity-anchor name check that also survives cross-script names."""
    if names_match(a, b):
        return True
    if not a or not b:
        return False
    import json

    from app.llm import LLMError, chat_json, load_prompt

    try:
        r = await chat_json(
            load_prompt("name_equivalence"),
            json.dumps({"name_a": a, "name_b": b}, ensure_ascii=False),
            what="name.equivalence",
        )
        return bool(r.get("same"))
    except LLMError:
        return False


async def validate_answer(field: str, text: str, language_code: str = "hi") -> dict:
    """Check a free-text onboarding answer is a real answer to the question asked (not a refusal / gibberish)."""
    import json

    from app.llm import chat_json, load_prompt

    return await chat_json(
        load_prompt("input_validation"),
        json.dumps({"field": field, "answer": text, "language": language_code}, ensure_ascii=False),
        what=f"validate.{field}",
    )
