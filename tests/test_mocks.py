"""Mock contracts (spec §11) — these shapes are what real integrations must match."""

import pytest

from app.mocks import gi_registry, gst_enrolment, meesho_api


def test_gi_lookup_known_craft():
    r = gi_registry.lookup("madhubani")
    assert r["gi_status"] == "verified"
    assert r["region"].endswith("Bihar")
    assert len(r["process_facts"]) >= 2


def test_gi_lookup_alias():
    assert gi_registry.lookup("Mithila painting")["craft_key"] == "madhubani"


def test_gi_lookup_unknown_returns_none():
    assert gi_registry.lookup("crochet") is None
    assert gi_registry.lookup(None) is None


def test_gi_has_ten_crafts():
    assert len(gi_registry._GI_CRAFTS) == 10


@pytest.mark.asyncio
async def test_enrolment_happy_path():
    payload = {"legal_name": "Suresh Kumar", "pan_ref": "ABCDE1234F",
               "bank_account_ref": "1234", "ifsc": "SBIN0001234",
               "otp_phone": "919999999999", "pincode": "847214"}
    r = await gst_enrolment.submit_enrolment(payload)
    assert r["status"] == "pending" and r["otp_required"]
    r2 = await gst_enrolment.confirm_otp(r["application_id"], "472172")
    assert r2["status"] == "issued"
    assert len(r2["enrolment_id"]) == 15


@pytest.mark.asyncio
async def test_enrolment_missing_fields_rejected():
    r = await gst_enrolment.submit_enrolment({"legal_name": "X"})
    assert r["status"] == "rejected"


@pytest.mark.asyncio
async def test_bad_otp_rejected():
    payload = {"legal_name": "S", "pan_ref": "P", "bank_account_ref": "B",
               "ifsc": "I", "otp_phone": "9", "pincode": "847214"}
    r = await gst_enrolment.submit_enrolment(payload)
    assert (await gst_enrolment.confirm_otp(r["application_id"], "12ab"))["status"] == "otp_invalid"


@pytest.mark.asyncio
async def test_create_listing_contract():
    r = await meesho_api.create_listing({"title": "T", "price": 299, "photo_urls": ["u"]})
    assert r["status"] == "live" and r["meesho_listing_id"].startswith("MSH")


@pytest.mark.asyncio
async def test_create_listing_missing_field():
    r = await meesho_api.create_listing({"title": "T"})
    assert r["status"] == "rejected"


@pytest.mark.asyncio
async def test_category_comparables_contract():
    r = await meesho_api.get_category_comparables("madhubani")
    assert r["price_band"]["low"] >= 199 and r["price_band"]["high"] <= 599
    assert all(l["price"] <= 1700 for l in r["sample_listings"])
    assert (await meesho_api.get_category_comparables("crochet"))["category"] == "crochet"
    assert (await meesho_api.get_category_comparables(None))["price_band"]


@pytest.mark.asyncio
async def test_cancel_pickup():
    r = await meesho_api.cancel_pickup("order-1")
    assert r["pickup_cancelled"] is True
