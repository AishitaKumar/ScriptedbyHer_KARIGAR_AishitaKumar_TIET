"""Pincode/OTP spoken-digit parsing — a wrong digit here is a wrong bank/village."""

from app.voice.classify import parse_spoken_digits


def test_hindi_words():
    assert parse_spoken_digits("चार सात दो एक", 4) == "4721"


def test_whisper_homophone_saath():
    assert parse_spoken_digits("चार साथ दो एक साथ दो", 6) == "472172"


def test_devanagari_digits():
    assert parse_spoken_digits("८४७२१४", 6) == "847214"


def test_ascii_digits_with_filler():
    assert parse_spoken_digits("OTP है 472172", 6) == "472172"


def test_mixed_words_and_digits():
    assert parse_spoken_digits("8 चार 7 दो 1 चार", 6) == "847214"


def test_wrong_length_returns_none():
    assert parse_spoken_digits("चार सात दो", 6) is None


def test_no_digits_returns_none():
    assert parse_spoken_digits("मुझे नहीं पता") is None


def test_spaced_out_number():
    assert parse_spoken_digits("8 4 7 2 1 4", 6) == "847214"
