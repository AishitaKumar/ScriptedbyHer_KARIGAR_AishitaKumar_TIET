"""Small classifiers used across all flows: confirm/deny, Hindi spoken digits."""

from __future__ import annotations

import re

from app.llm import chat_json, load_prompt

_DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")

_HINDI_NUMBER_WORDS = {
    "शून्य": "0", "जीरो": "0", "zero": "0",
    "एक": "1", "इक": "1", "one": "1", "ek": "1",
    "दो": "2", "two": "2", "do": "2",
    "तीन": "3", "three": "3", "teen": "3", "tin": "3",
    "चार": "4", "four": "4", "char": "4", "chaar": "4",
    "पांच": "5", "पाँच": "5", "five": "5", "panch": "5", "paanch": "5",
    "छह": "6", "छे": "6", "छः": "6", "six": "6", "chhah": "6", "che": "6", "chhe": "6",
    "सात": "7", "साथ": "7", "seven": "7", "saat": "7", "sat": "7", "sath": "7", "saath": "7",
    "आठ": "8", "eight": "8", "aath": "8", "ath": "8",
    "नौ": "9", "nine": "9", "nau": "9",
}


def parse_spoken_digits(text: str, expected_length: int | None = None) -> str | None:
    """Parse spoken/typed digits: "चार सात दो एक" -> "4721", "८४७२१४" -> "847214"."""
    text = text.translate(_DEVANAGARI_DIGITS)
    digits: list[str] = []
    for token in re.split(r"[\s,\-–.।]+", text.strip()):
        if not token:
            continue
        if token.isdigit():
            digits.extend(token)
        else:
            word = _HINDI_NUMBER_WORDS.get(token.lower())
            if word is not None:
                digits.append(word)
    result = "".join(digits)
    if not result:
        return None
    if expected_length is not None and len(result) != expected_length:
        return None
    return result


async def classify_yes_no(text: str) -> str:
    """Classify a reply as 'yes' | 'no' | 'unclear'. Fast path for obvious cases."""
    stripped = text.strip().lower().strip("!।.")
    if stripped in {"1", "हाँ", "हां", "haan", "ha", "yes", "ji", "जी", "👍", "ठीक है", "theek hai"}:
        return "yes"
    if stripped in {"2", "नहीं", "नही", "ना", "nahi", "na", "no", "👎"}:
        return "no"
    result = await chat_json(load_prompt("confirm_deny"), text, what="classify.yes_no")
    intent = result.get("intent", "unclear")
    return intent if intent in {"yes", "no"} else "unclear"
