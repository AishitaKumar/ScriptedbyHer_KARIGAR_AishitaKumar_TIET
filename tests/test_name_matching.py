"""Identity Anchor name matching: PAN vs. passbook holder (spec §8)."""

from app.flows.common import names_match


def test_exact():
    assert names_match("Suresh Kumar", "Suresh Kumar")


def test_case_and_order():
    assert names_match("suresh kumar", "KUMAR SURESH")


def test_honorifics_stripped():
    assert names_match("Shri Suresh Kumar", "Suresh Kumar")


def test_initial_matches_full():
    assert names_match("S Kumar", "Suresh Kumar")


def test_extra_middle_name():
    assert names_match("Suresh Kumar", "Suresh Prasad Kumar")


def test_different_people_rejected():
    assert not names_match("Suresh Kumar", "Ramkali Devi")


def test_partial_overlap_rejected():
    assert not names_match("Suresh Kumar", "Ramesh Chandra")


def test_ocr_variance_tolerated():
    assert names_match("AISHTA KUMAR", "ABHISHTA KUMAR")
    assert names_match("AISHTA KUMAR", "ABHISHA KUMAR")
    assert names_match("Ramkali Devi", "Ramkalee Devi")


def test_short_name_fuzzy_rejected():
    assert not names_match("Sita Devi", "Gita Devi")


def test_ocr_variance_limit():
    assert not names_match("Suresh Kumar", "Ramesh Kumar")


def test_empty_rejected():
    assert not names_match("", "Suresh Kumar")
    assert not names_match("Suresh Kumar", None)
