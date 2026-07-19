"""Confirm/deny classifier — offline fast paths (the LLM path is exercised by
scripts/03_voice_roundtrip.py against the live API)."""

import pytest

from app.voice.classify import classify_yes_no


@pytest.mark.asyncio
@pytest.mark.parametrize("text,expected", [
    ("हाँ", "yes"), ("हां", "yes"), ("1", "yes"), ("जी", "yes"),
    ("ठीक है", "yes"), ("👍", "yes"), ("yes", "yes"), ("haan", "yes"),
    ("नहीं", "no"), ("ना", "no"), ("2", "no"), ("nahi", "no"), ("👎", "no"),
    ("हाँ।", "yes"), (" नहीं ", "no"),
])
async def test_fast_path(text, expected):
    assert await classify_yes_no(text) == expected
