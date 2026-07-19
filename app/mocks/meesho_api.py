"""Mock Meesho Seller API — the ONLY external boundary Karigar's code talks to (via services/meesho)."""

from __future__ import annotations

import asyncio
import random
import string

from app.mocks import gst_enrolment, gst_lookup

_listings: dict[str, dict] = {}

_COMPARABLES: dict[str, dict] = {
    "madhubani": {
        "price_band": {"low": 249, "high": 599},
        "sample_listings": [
            {"title": "Madhubani Painting Fish Motif Wall Decor 8x12", "price": 349},
            {"title": "Mithila Art Handmade Peacock Painting", "price": 449},
            {"title": "Madhubani Wall Art Unframed Paper", "price": 299},
        ],
    },
    "warli": {
        "price_band": {"low": 199, "high": 499},
        "sample_listings": [
            {"title": "Warli Art Tribal Painting Wall Decor", "price": 249},
            {"title": "Handmade Warli Painting Village Scene", "price": 399},
        ],
    },
    "default": {
        "price_band": {"low": 199, "high": 599},
        "sample_listings": [
            {"title": "Handmade Painting Wall Decor", "price": 299},
            {"title": "Hand Painted Canvas Art for Home", "price": 499},
        ],
    },
}


async def get_category_comparables(craft: str | None) -> dict:
    """Category price-check before listing — mimics the marketplace's category data."""
    key = (craft or "default").strip().lower()
    record = _COMPARABLES.get(key, _COMPARABLES["default"])
    return {"category": key, **record}


def _new_id() -> str:
    return "MSH" + "".join(random.choices(string.digits, k=9))


def _seller_id() -> str:
    return "MSHS" + "".join(random.choices(string.digits, k=8))


async def lookup_gstin(gstin: str) -> dict | None:
    """Meesho's backend verifies the GSTIN against the government registry."""
    await asyncio.sleep(1)
    return gst_lookup.lookup(gstin)


async def create_seller_account(payload: dict) -> dict:
    """Seller onboarding as Meesho does it: GSTIN sellers verify against the GST registry; non-GSTIN sellers are enrolled for an EID via the GST portal (both government steps happen inside Meesho's backend — nested mocks)."""
    for field in ("legal_name", "email", "bank_account_ref", "ifsc", "pickup_address"):
        if not payload.get(field):
            return {"verification_status": "rejected", "error": f"missing field: {field}"}

    if payload.get("gstin"):
        record = gst_lookup.lookup(payload["gstin"])
        if record is None:
            return {"verification_status": "rejected", "error": "GSTIN not found"}
        await asyncio.sleep(1)
        return {"seller_id": _seller_id(), "verification_status": "verified",
                "registration_type": "gstin", "business": record}

    enrolment = await gst_enrolment.submit_enrolment({
        "legal_name": payload["legal_name"], "pan_ref": payload.get("pan_ref"),
        "bank_account_ref": payload["bank_account_ref"], "ifsc": payload["ifsc"],
        "otp_phone": payload.get("otp_phone"), "pincode": payload.get("pincode"),
    })
    if enrolment.get("status") != "pending":
        return {"verification_status": "rejected", "error": enrolment.get("error")}
    return {"verification_status": "otp_required", "otp_required": True,
            "registration_type": "eid", "application_id": enrolment["application_id"]}


async def confirm_seller_otp(application_id: str, otp: str) -> dict:
    result = await gst_enrolment.confirm_otp(application_id, otp)
    if result.get("status") != "issued":
        return {"verification_status": "otp_invalid", "error": result.get("error")}
    return {"seller_id": _seller_id(), "verification_status": "verified",
            "registration_type": "eid", "enrolment_id": result["enrolment_id"]}


async def create_listing(payload: dict) -> dict:
    for field in ("title", "price", "photo_urls"):
        if not payload.get(field):
            return {"status": "rejected", "error": f"missing field: {field}"}
    await asyncio.sleep(1)
    listing_id = _new_id()
    _listings[listing_id] = {**payload, "status": "live"}
    return {"meesho_listing_id": listing_id, "status": "live"}


async def update_listing(meesho_listing_id: str, patch: dict) -> dict:
    if meesho_listing_id not in _listings:
        return {"status": "rejected", "error": "unknown listing id"}
    _listings[meesho_listing_id].update(patch)
    return {"meesho_listing_id": meesho_listing_id, "status": _listings[meesho_listing_id]["status"]}


async def cancel_pickup(order_id: str) -> dict:
    await asyncio.sleep(0.5)
    return {"order_id": order_id, "pickup_cancelled": True}
