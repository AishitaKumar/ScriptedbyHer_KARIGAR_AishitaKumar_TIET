"""Pipeline batch triage: Mechanics A/B/C + fraud rejection (spec §9.2, §7)."""

from app.pipeline import triage_batch


def a(verdict="handmade", quality="pass", reasons=None):
    return {"authenticity_verdict": verdict, "quality_score": quality, "reasons": reasons or []}


def test_all_pass():
    r = triage_batch([a(), a(), a()])
    assert r["outcome"] == "ok" and r["usable"] == [0, 1, 2]


def test_partial_success_mechanic_b():
    r = triage_batch([a(), a(quality="fail"), a()])
    assert r["outcome"] == "ok"
    assert r["usable"] == [0, 2] and r["dropped"] == [1]


def test_total_failure_mechanic_c():
    r = triage_batch([a(quality="fail"), a(verdict="insufficient_evidence", quality="fail")])
    assert r["outcome"] == "all_failed"


def test_print_rejects_whole_batch():
    r = triage_batch([a(), a(verdict="print", reasons=["halftone dots visible"])])
    assert r["outcome"] == "rejected"
    assert "halftone dots visible" in r["reasons"]


def test_all_downloaded_images_get_specific_outcome():
    r = triage_batch([a(verdict="suspect_downloaded_image", reasons=["watermark"])])
    assert r["outcome"] == "all_suspect"


def test_mixed_suspect_is_dropped_not_rejected():
    r = triage_batch([a(), a(verdict="suspect_downloaded_image")])
    assert r["outcome"] == "ok"
    assert r["usable"] == [0] and 1 in r["dropped"]


def test_uncertain_is_dropped_not_rejected():
    r = triage_batch([a(), a(verdict="uncertain")])
    assert r["outcome"] == "ok" and r["dropped"] == [1]
