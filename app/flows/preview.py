"""Listing preview card + publish — shared by the KYC completion path, the skip-KYC path (already-verified sellers adding listings) and the redo flow."""

from __future__ import annotations

from app.agentlog import log_event
from app.db import queries
from app.flows.common import say
from app.flows.messages import t
from app.services import meesho
from app.transports.base import Button, Transport


def _store_suggestion(artisan: dict, listing: dict) -> str:
    craft = (listing.get("craft_type") or "Handmade").replace("_", " ").title()
    return f"{artisan.get('name') or 'Karigar'} {craft} Arts"


async def send_preview(artisan: dict, sender: str, transport: Transport) -> None:
    from app.flows.messages import current_lang

    listing = (await queries.listings_for_artisan(artisan["id"], ["pending_approval"]))[0]
    badge = ""
    if artisan.get("seller_identity_id"):
        identity = await queries.get_seller_identity(artisan["seller_identity_id"])
        store = identity.get("business_name") or _store_suggestion(artisan, listing)
        badge = t("store_line", store=store)
    display_title = (listing["title"] if current_lang() == "en"
                     else artisan["context"].get("title_hi") or listing["title"])
    await queries.set_state(artisan["id"], "awaiting_preview_approval",
                            {"listing_id": listing["id"]})
    await say(transport, sender,
              t("preview", title_hi=display_title,
                price=listing["price"], original_price=listing["original_price"], badge=badge),
              image_url=listing.get("enhanced_photo_url"),
              buttons=[Button("yes", t("btn_list_yes")), Button("no", t("btn_list_no"))],
              artisan_id=artisan["id"])


async def publish(artisan: dict, sender: str, transport: Transport) -> None:
    """The human-approved publish — the ONLY path to a live listing."""
    listing = (await queries.listings_for_artisan(artisan["id"], ["pending_approval"]))[0]
    api_result = await meesho.create_listing({
        "title": listing["title"], "price": listing["price"],
        "photo_urls": listing["photo_urls"],
    })
    log_event("distribution", "listing published via mock Meesho API", api_result)
    await queries.update_listing(listing["id"], {
        "status": "live", "meesho_listing_id": api_result["meesho_listing_id"],
    })
    if artisan.get("seller_identity_id"):
        identity = await queries.get_seller_identity(artisan["seller_identity_id"])
        if not identity.get("business_name"):
            await queries.update_seller_identity(
                identity["id"], {"business_name": _store_suggestion(artisan, listing)}
            )
    await queries.set_state(artisan["id"], "active")
    await say(transport, sender,
              t("launched", craft=artisan["context"].get("title_hi", "कला")),
              artisan_id=artisan["id"])


async def kyc_already_verified(artisan: dict) -> bool:
    """True when this artisan's seller identity has completed KYC — new listings then skip straight from pricing to the preview (KYC is per seller, not per listing)."""
    identity_id = artisan.get("seller_identity_id")
    if not identity_id:
        return False
    identity = await queries.get_seller_identity(identity_id)
    return identity.get("kyc_status") == "verified"
