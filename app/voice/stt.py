"""Inbound voice: Whisper transcription of WhatsApp voice notes (OGG/Opus)."""

from __future__ import annotations

import io

from app.llm import client


async def transcribe(audio_bytes: bytes, filename: str = "note.ogg", language_code: str = "hi") -> str:
    """Transcribe a voice note. Whisper accepts OGG/Opus directly."""
    file = io.BytesIO(audio_bytes)
    file.name = filename
    result = await client().audio.transcriptions.create(
        model="whisper-1",
        file=file,
        language=language_code,
    )
    return result.text.strip()
