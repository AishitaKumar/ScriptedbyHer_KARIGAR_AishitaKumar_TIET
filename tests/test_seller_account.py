"""Nested-mock seller account creation (spec: Meesho's backend does government
verification; Karigar only sees the Meesho boundary) + email alias derivation."""

import pytest

from app.mocks import gst_lookup
from app.services import email_alias, meesho

BASE_PAYLOAD = {
    "legal_name": "AISHITA KUMAR", "email": "x@y.com",
    "bank_account_ref": "1234567890", "ifsc": "SBIN0001234",
    "registered_address": "Rohini, Delhi-110085", "pickup_address": "Rohini, Delhi-110085",
    "otp_phone": "web:test", "pincode": "110085",
}


@pytest.mark.asyncio
async def test_gstin_seller_verified_instantly():
    r = await meesho.create_seller_account({**BASE_PAYLOAD, "gstin": "22AAAAA0000A1Z5"})
    assert r["verification_status"] == "verified"
    assert r["registration_type"] == "gstin"
    assert r["seller_id"].startswith("MSHS")
    assert r["business"]["trade_name"] == "Aishita Handicrafts"


@pytest.mark.asyncio
async def test_unknown_gstin_rejected():
    r = await meesho.create_seller_account({**BASE_PAYLOAD, "gstin": "99ZZZZZ9999Z9Z9"})
    assert r["verification_status"] == "rejected"


@pytest.mark.asyncio
async def test_eid_seller_needs_otp_then_verifies():
    r = await meesho.create_seller_account({**BASE_PAYLOAD, "pan_ref": "ABCDE1234F"})
    assert r["verification_status"] == "otp_required" and r["otp_required"]
    r2 = await meesho.confirm_seller_otp(r["application_id"], "472172")
    assert r2["verification_status"] == "verified"
    assert len(r2["enrolment_id"]) == 15


@pytest.mark.asyncio
async def test_missing_fields_rejected():
    r = await meesho.create_seller_account({"legal_name": "X"})
    assert r["verification_status"] == "rejected"


def test_gst_lookup_contract():
    r = gst_lookup.lookup("10BBBBB1111B1Z3")
    assert r["legal_name"] == "RAMKALI DEVI" and r["business_type"] == "Proprietorship"
    assert gst_lookup.lookup("nope") is None
    assert gst_lookup.lookup(None) is None
    assert gst_lookup.lookup("22aaaaa0000a1z5") is not None


def test_email_alias_derivation():
    e = email_alias.derive("Aishita Kumar", "7f3k9d2a-0000-0000-0000-000000000000")
    local, domain = e.split("@")
    assert "+" in local and local.startswith("karigar.sellers+")
    assert "aishita.kumar" in local and "7f3k" in local
    assert domain == "gmail.com"


def test_email_alias_devanagari_name():
    e = email_alias.derive("रामकली देवी", "abcd1234-0000-0000-0000-000000000000")
    assert "@" in e and "+" in e
    local = e.split("@")[0]
    assert all(c.isascii() for c in local)


def test_email_alias_unique_per_seller():
    a = email_alias.derive("Ramkali Devi", "aaaa1111-0000-0000-0000-000000000000")
    b = email_alias.derive("Ramkali Devi", "bbbb2222-0000-0000-0000-000000000000")
    assert a != b
