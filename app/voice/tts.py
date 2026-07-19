"""Outbound voice: OpenAI TTS."""

from __future__ import annotations

from app.llm import client

TTS_MODEL = "gpt-4o-mini-tts"
VOICE = "shimmer"


_INSTRUCTIONS = {
    "hi": "Speak in warm, clear, slow Hindi, like a helpful younger relative "
          "explaining something to an elder in a village. Natural Devanagari pronunciation.",
    "en": "Speak in warm, clear, unhurried Indian English, like a helpful younger "
          "relative explaining something patiently.",
}


async def speak(text: str, language_code: str = "hi") -> bytes:
    """Render text to OGG/Opus bytes (WhatsApp's native voice-note format)."""
    kwargs = {"model": TTS_MODEL, "voice": VOICE, "input": text, "response_format": "opus"}
    if TTS_MODEL.startswith("gpt-4o"):
        kwargs["instructions"] = _INSTRUCTIONS.get(language_code, _INSTRUCTIONS["hi"])
    response = await client().audio.speech.create(**kwargs)
    return response.content
