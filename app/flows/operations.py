"""Post-onboarding operations: orders, earnings, inventory — the artisan's own voice-only chat."""

from __future__ import annotations

import json
import logging

from app.agentlog import log_event
from app.agents.pricing import in_hand_amount
from app.db import queries
from app.flows.common import incoming_text, say
from app.flows.messages import t
from app.llm import LLMError, chat_json, load_prompt
from app.services import meesho
from app.transports.base import InboundMessage, Transport
from app.voice.classify import classify_yes_no

logger = logging.getLogger("karigar.operations")


_CRAFT_HI = {
    "madhubani": "मधुबनी पेंटिंग", "warli": "वारली पेंटिंग", "channapatna": "चन्नापटना खिलौने",
    "kutch_embroidery": "कच्छ कढ़ाई", "bidriware": "बिदरी कलाकृति", "pashmina": "पश्मीना शॉल",
    "blue_pottery": "ब्लू पॉटरी", "pochampally_ikat": "पोचमपल्ली इकत", "kanjeevaram": "कांजीवरम साड़ी",
    "bandhani": "बांधनी", "acrylic painting": "पेंटिंग",
}
_CRAFT_EN = {
    "madhubani": "Madhubani paintings", "warli": "Warli paintings",
    "channapatna": "Channapatna toys", "acrylic painting": "paintings",
}


def _craft_label(craft: str | None, lang: str | None) -> str:
    key = (craft or "").strip().lower().replace("-", "_").replace(" ", "_")
    plain = (craft or "").strip().lower()
    if (lang or "hi") == "hi":
        return _CRAFT_HI.get(key) or _CRAFT_HI.get(plain) or "कलाकृतियाँ"
    return _CRAFT_EN.get(key) or _CRAFT_EN.get(plain) or "artworks"


def _title(listing: dict, lang: str | None) -> str:
    """The craft name in the artisan's language — her Hindi title for Hindi voice notes, the English Meesho title otherwise."""
    if (lang or "hi") == "hi" and listing.get("title_hi"):
        return listing["title_hi"]
    return listing.get("title") or ""


async def handle(artisan: dict, msg: InboundMessage, transport: Transport) -> None:
    try:
        await _handle(artisan, msg, transport)
    except LLMError:
        await say(transport, msg.sender, t("error"), artisan_id=artisan["id"])


async def _handle(artisan: dict, msg: InboundMessage, transport: Transport) -> None:
    if msg.type == "image":
        paused = await queries.listings_for_artisan(artisan["id"], ["out_of_stock"])
        if paused:
            await queries.update_listing(paused[0]["id"], {"status": "live"})
            log_event("distribution", "listing reactivated by new photo", {"listing_id": paused[0]["id"]})
            await say(transport, msg.sender, t("relisted"), artisan_id=artisan["id"])
        else:
            await say(transport, msg.sender, t("unknown_intent"), artisan_id=artisan["id"])
        return

    text = await incoming_text(msg, artisan) or ""

    if artisan["context"].get("awaiting_order_ack"):
        verdict = await classify_yes_no(text)
        if verdict in {"yes", "no"}:
            await handle_order_ack(artisan, msg.sender, transport, ack_ok=(verdict == "yes"))
            return

    intent = await classify_intent(artisan, text)
    log_event("orchestrator", f"intent → {intent}", {"transcript": text})

    if intent == "add_new_listing":
        await say(transport, msg.sender, t("ask_photos"), artisan_id=artisan["id"])
        await queries.set_state(artisan["id"], "awaiting_photos")
    elif intent == "manage_inventory":
        listings = await queries.listings_for_artisan(artisan["id"], ["live"])
        if listings:
            await queries.update_listing(listings[0]["id"], {"status": "out_of_stock"})
            await say(transport, msg.sender, t("order_paused", craft=artisan.get("craft") or "कला"),
                      artisan_id=artisan["id"])
        else:
            await say(transport, msg.sender, t("unknown_intent"), artisan_id=artisan["id"])
    elif not await _dispatch_query(artisan, text, msg.sender, transport, intent):
        await say(transport, msg.sender, t("unknown_intent"), artisan_id=artisan["id"])


async def classify_intent(artisan: dict, text: str) -> str:
    state = {
        "name": artisan.get("name"), "craft": artisan.get("craft"),
        "live_listings": len(await queries.listings_for_artisan(artisan["id"], ["live"])),
    }
    result = await chat_json(
        load_prompt("orchestrator_intent"),
        json.dumps({"CURRENT_DATABASE_STATE": state, "transcript": text}, ensure_ascii=False),
        what="orchestrator.intent",
    )
    return result.get("intent", "unknown")


async def answer_seller_question(artisan: dict, text: str, sender: str, transport: Transport) -> bool:
    """Classify + answer a seller question."""
    intent = await classify_intent(artisan, text)
    return await _dispatch_query(artisan, text, sender, transport, intent)


async def _dispatch_query(artisan: dict, text: str, sender: str, transport: Transport, intent: str) -> bool:
    if intent == "query_revenue":
        await _earnings(artisan, sender, transport)
    elif intent == "query_orders":
        await _orders_summary(artisan, sender, transport)
    elif intent == "query_trend":
        from app.agents import trend
        await trend.run_for_artisan(artisan, transport)
    elif intent == "general":
        await _general_answer(artisan, text, sender, transport)
    else:
        return False
    return True


async def _orders_summary(artisan: dict, sender: str, transport: Transport) -> None:
    """Assembled from the real order/return picture — includes deliveries, returns and exchanges, only mentioning what actually happened."""
    orders = await queries.orders_for_artisan(artisan["id"], days=7)
    returns = await queries.returns_for_artisan(artisan["id"])
    came = [o for o in orders if o["status"] != "cancelled"]
    if not came:
        await say(transport, sender, t("orders_none"), artisan_id=artisan["id"])
        return
    delivered = sum(1 for o in orders if o["status"] == "delivered")
    undelivered = sum(1 for o in orders if o["status"] in {"placed", "shipped"})
    returned = sum(1 for o in orders if o["status"] == "returned")
    exchanges = sum(1 for r in returns if r.get("classification") == "exchange")

    lines = [t("orders_total", count=len(came))]
    if delivered:
        lines.append(t("orders_delivered", count=delivered))
    if undelivered:
        lines.append(t("orders_undelivered", count=undelivered))
    if returned:
        lines.append(t("orders_returned", count=returned))
    if exchanges:
        lines.append(t("orders_exchange", count=exchanges))
    lines.append(t("orders_ok"))
    await say(transport, sender, " ".join(lines), artisan_id=artisan["id"])


async def _general_answer(artisan: dict, text: str, sender: str, transport: Transport) -> None:
    """Grounded free-form answer to any other seller question (spec §9.7)."""
    orders = await queries.orders_for_artisan(artisan["id"], days=7)
    sold = [o for o in orders if o["status"] in {"placed", "shipped", "delivered"}]
    identity = None
    if artisan.get("seller_identity_id"):
        identity = await queries.get_seller_identity(artisan["seller_identity_id"])
    facts = {
        "language": artisan.get("language_code", "hi"),
        "name": artisan.get("name"), "craft": artisan.get("craft"),
        "store_name": (identity or {}).get("business_name"),
        "shop_is_live": len(await queries.listings_for_artisan(artisan["id"], ["live"])) > 0,
        "live_listings": len(await queries.listings_for_artisan(artisan["id"], ["live"])),
        "orders_this_week": len(sold),
        "earned_in_hand": sum(in_hand_amount(o["amount"]) for o in sold),
        "question": text,
    }
    result = await chat_json(
        load_prompt("seller_qa"), json.dumps(facts, ensure_ascii=False), what="operations.general_qa"
    )
    answer = result.get("answer") or t("unknown_intent")
    await say(transport, sender, answer, artisan_id=artisan["id"])


async def _earnings(artisan: dict, sender: str, transport: Transport) -> None:
    """Situation-aware earnings: distinguish money already paid (delivered orders) from money still pending (sold but not yet delivered/paid)."""
    orders = await queries.orders_for_artisan(artisan["id"], days=7)
    paid = [o for o in orders if o["status"] == "delivered"]
    pending = [o for o in orders if o["status"] in {"placed", "shipped"}]
    sold = paid + pending
    if not sold:
        await say(transport, sender, t("earnings_none"), artisan_id=artisan["id"])
        return
    craft = _craft_label(artisan.get("craft"), artisan.get("language_code"))
    paid_amt = sum(in_hand_amount(o["amount"]) for o in paid)
    pend_amt = sum(in_hand_amount(o["amount"]) for o in pending)
    if paid and not pending:
        msg = t("earnings_paid", count=len(sold), craft=craft, paid=paid_amt)
    elif pending and not paid:
        msg = t("earnings_pending", count=len(sold), craft=craft, pending=pend_amt)
    else:
        msg = t("earnings_mixed", count=len(sold), craft=craft, paid=paid_amt, pending=pend_amt)
    await say(transport, sender, msg, artisan_id=artisan["id"])


async def handle_order_ack(artisan: dict, sender: str, transport: Transport, ack_ok: bool) -> None:
    order = artisan["context"].get("awaiting_order_ack")
    await queries.merge_context(artisan["id"], {"awaiting_order_ack": None})
    if not order:
        return
    if not ack_ok:
        await meesho.cancel_pickup(order["order_id"])
        await queries.update_order(order["order_id"], {"status": "cancelled"})
        await queries.update_listing(order["listing_id"], {"status": "out_of_stock"})
        log_event("distribution", "order paused: out of stock", order)
        await say(transport, sender, t("order_paused", craft=artisan.get("craft") or "कला"),
                  artisan_id=artisan["id"])


async def notify_new_order(artisan: dict, order: dict, listing: dict, transport: Transport) -> None:
    from app.flows.messages import set_lang

    lang = artisan.get("language_code")
    set_lang(lang)
    await queries.update_order(order["id"], {"artisan_notified_at": "now()"})
    await say(transport, artisan["whatsapp_phone"],
              t("new_order", title=_title(listing, lang)),
              artisan_id=artisan["id"])


async def notify_payout(artisan: dict, listing: dict, amount: int, transport: Transport) -> None:
    from app.flows.messages import set_lang

    lang = artisan.get("language_code")
    set_lang(lang)
    await say(transport, artisan["whatsapp_phone"],
              t("payout", title=_title(listing, lang), amount=amount), artisan_id=artisan["id"])


async def notify_return(artisan: dict, listing: dict, return_row: dict, transport: Transport) -> None:
    """De-escalation tone is mandatory (spec §9.7)."""
    from app.flows.messages import set_lang

    lang = artisan.get("language_code")
    set_lang(lang)
    await queries.update_order(return_row["order_id"], {"status": "returned"})
    key = "return_rto" if return_row.get("classification") == "rto" else "return_quality"
    await say(transport, artisan["whatsapp_phone"],
              t(key, title=_title(listing, lang)), artisan_id=artisan["id"])


async def notify_exchange(artisan: dict, listing: dict, reason: str, transport: Transport) -> None:
    from app.flows.messages import set_lang

    lang = artisan.get("language_code")
    set_lang(lang)
    await say(transport, artisan["whatsapp_phone"],
              t("exchange", title=_title(listing, lang), reason=reason), artisan_id=artisan["id"])


async def notify_account_needed(artisan: dict, transport: Transport) -> None:
    """Trend/coaching asked before the seller account exists — nudge to onboard."""
    from app.flows.messages import set_lang

    set_lang(artisan.get("language_code"))
    await say(transport, artisan["whatsapp_phone"], t("account_needed_first"),
              artisan_id=artisan["id"])


async def notify_review(artisan: dict, listing: dict, rating: int, comment: str,
                        transport: Transport) -> None:
    """Distribution turns a customer review into a warm appreciation voice note."""
    from app.agents.distribution import appreciation_message
    from app.flows.messages import set_lang

    lang = artisan.get("language_code", "hi")
    set_lang(lang)
    message = await appreciation_message(
        artisan.get("name") or "", _title(listing, lang), rating, comment, lang
    )
    if message:
        await say(transport, artisan["whatsapp_phone"], message, artisan_id=artisan["id"])
