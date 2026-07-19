"""KYC / seller-account creation — runs BEFORE cataloging (the store account must exist before listings do)."""

from __future__ import annotations

import logging
import random
import re

from app.agentlog import log_event
from app.db import queries
from app.flows.common import incoming_text, names_match_smart, say, voice_of, yes_no_buttons
from app.flows.messages import t
from app.llm import LLMError, VISION_MODEL, chat_json, image_content, load_prompt
from app.services import email_alias, meesho
from app.transports.base import Button, InboundMessage, Transport
from app.voice.classify import classify_yes_no, parse_spoken_digits

logger = logging.getLogger("karigar.kyc")


async def entry(artisan: dict, sender: str, transport: Transport) -> None:
    """Called by onboarding right after name+village — before any photos."""
    await queries.set_state(artisan["id"], "kyc_gstin_question")
    await say(transport, sender, t("kyc_intro"), artisan_id=artisan["id"])
    await say(transport, sender, t("gstin_question"),
              buttons=yes_no_buttons(), artisan_id=artisan["id"])


async def handle(artisan: dict, msg: InboundMessage, transport: Transport) -> None:
    if msg.type == "button" and msg.text in _MISMATCH_ACTIONS:
        await _MISMATCH_ACTIONS[msg.text](artisan, msg.sender, transport)
        return
    handler = _HANDLERS.get(artisan["onboarding_state"])
    if handler is None:
        await say(transport, msg.sender, t("error"), artisan_id=artisan["id"])
        return
    try:
        await handler(artisan, msg, transport)
    except LLMError:
        await say(transport, msg.sender, t("error"), artisan_id=artisan["id"])


def _anchor_name(artisan: dict) -> str:
    ctx = artisan["context"]
    return ctx.get("pan_name") or (ctx.get("gstin_record") or {}).get("legal_name") or ""


async def _park_jandhan(artisan: dict, sender: str, transport: Transport) -> None:
    """Nobody in the family has a matching PAN+bank pair."""
    pan_name = _anchor_name(artisan)
    log_event("kyc", "parked: no matching PAN+bank pair → Jan Dhan guidance; partner notified",
              {"anchor": pan_name, "partner_phone": artisan.get("onboarding_partner_phone")})
    await queries.set_state(artisan["id"], "kyc_parked_bank", {"parked_anchor": pan_name})
    await say(transport, sender, t("jandhan_parked", pan_name=pan_name),
              buttons=[Button("kyc_have_docs", t("have_docs_label"))], artisan_id=artisan["id"])


async def _parked_bank(artisan: dict, msg: InboundMessage, transport: Transport) -> None:
    if msg.type == "image" and msg.media:
        await _awaiting_passbook(artisan, msg, transport)
        return
    await say(transport, msg.sender,
              t("parked_reminder", pan_name=artisan["context"].get("parked_anchor") or _anchor_name(artisan)),
              artisan_id=artisan["id"])


async def _redo_pan(artisan: dict, sender: str, transport: Transport) -> None:
    await queries.set_state(artisan["id"], "kyc_awaiting_pan")
    await say(transport, sender, t("ask_pan"), artisan_id=artisan["id"])


async def _redo_passbook(artisan: dict, sender: str, transport: Transport) -> None:
    await queries.set_state(artisan["id"], "kyc_awaiting_passbook")
    await say(transport, sender, t("ask_passbook"), artisan_id=artisan["id"])


async def _switch_eid(artisan: dict, sender: str, transport: Transport) -> None:
    """GSTIN passbook doesn't match → drop the GSTIN and continue on the PAN/EID path."""
    ctx = {k: v for k, v in artisan["context"].items() if k != "gstin_record"}
    ctx["gstin_record"] = None
    if artisan.get("seller_identity_id"):
        await queries.update_seller_identity(artisan["seller_identity_id"],
                                             {"registration_type": "eid", "gstin": None,
                                              "business_name": None})
    await queries.set_state(artisan["id"], "kyc_awaiting_pan", {"gstin_record": None})
    await say(transport, sender, t("ask_pan"), artisan_id=artisan["id"])


def _mismatch_buttons() -> list[Button]:
    return [Button("kyc_redo_pan", t("redo_pan_label")),
            Button("kyc_redo_passbook", t("redo_passbook_label")),
            Button("kyc_redo_both", t("redo_both_label")),
            Button("kyc_no_match", t("no_match_label"))]


def _gstin_mismatch_buttons() -> list[Button]:
    return [Button("kyc_redo_passbook", t("redo_passbook_label")),
            Button("kyc_switch_eid", t("switch_eid_label"))]


_MISMATCH_ACTIONS = {
    "kyc_redo_pan": _redo_pan,
    "kyc_redo_passbook": _redo_passbook,
    "kyc_redo_both": _redo_pan,
    "kyc_no_match": _park_jandhan,
    "kyc_have_docs": _redo_pan,
    "kyc_switch_eid": _switch_eid,
}


def _spaced(digits: str) -> str:
    return " ".join(digits)


def _pincode_in(address: str | None) -> str | None:
    m = re.search(r"\b(\d{6})\b", address or "")
    return m.group(1) if m else None


def _doc_issue_message(ocr: dict, doc: str, doc_flag: str, required: list[str]) -> str | None:
    """Return a specific retry message if the photo is unusable, else None."""
    if not ocr.get(doc_flag):
        return t("doc_wrong", doc=doc)
    issue = ocr.get("image_issue")
    if issue == "blurry":
        return t("doc_blurry", doc=doc)
    if issue == "not_document":
        return t("doc_wrong", doc=doc)
    if issue == "cropped":
        return t("doc_cropped", doc=doc)
    if any(not ocr.get(f) for f in required) or ocr.get("confidence", 0) < 60:
        return t("doc_cropped", doc=doc)
    return None


async def _gstin_question(artisan: dict, msg: InboundMessage, transport: Transport) -> None:
    reply = await incoming_text(msg, artisan) or ""
    if await classify_yes_no(reply) == "yes":
        await queries.set_state(artisan["id"], "kyc_awaiting_gstin")
        await say(transport, msg.sender, t("ask_gstin"), artisan_id=artisan["id"])
    else:
        await queries.set_state(artisan["id"], "kyc_awaiting_pan")
        await say(transport, msg.sender, t("ask_pan"), artisan_id=artisan["id"])


def _parse_gstin(text: str) -> str | None:
    cleaned = re.sub(r"[^0-9A-Za-z]", "", text).upper()
    return cleaned if len(cleaned) == 15 else None


async def _awaiting_gstin(artisan: dict, msg: InboundMessage, transport: Transport) -> None:
    heard = await incoming_text(msg, artisan) or ""
    if await classify_yes_no(heard) == "no":
        await queries.set_state(artisan["id"], "kyc_awaiting_pan")
        await say(transport, msg.sender, t("ask_pan"), artisan_id=artisan["id"])
        return
    gstin = _parse_gstin(heard)
    if not gstin:
        await say(transport, msg.sender, t("gstin_invalid"), artisan_id=artisan["id"])
        return
    await queries.set_state(artisan["id"], "kyc_confirm_gstin", {"pending_gstin": gstin})
    lang = artisan.get("language_code", "hi")
    card = t("confirm_gstin", spaced=_spaced(gstin))
    await say(transport, msg.sender, card,
              voice_text=voice_of(card, lang), buttons=yes_no_buttons(), artisan_id=artisan["id"])


async def _confirm_gstin(artisan: dict, msg: InboundMessage, transport: Transport) -> None:
    reply = await incoming_text(msg, artisan) or ""
    if await classify_yes_no(reply) != "yes":
        await queries.set_state(artisan["id"], "kyc_awaiting_gstin")
        await say(transport, msg.sender, t("ask_gstin"), artisan_id=artisan["id"])
        return
    gstin = artisan["context"]["pending_gstin"]
    record = await meesho.lookup_gstin(gstin)
    log_event("meesho-mock", f"GSTIN lookup → {'found' if record else 'not found'}",
              {"gstin": gstin, **(record or {})})
    if record is None:
        await queries.set_state(artisan["id"], "kyc_awaiting_gstin")
        await say(transport, msg.sender, t("gstin_not_found"), artisan_id=artisan["id"])
        return
    await queries.set_state(artisan["id"], "kyc_confirm_business",
                            {"gstin_record": record})
    lang = artisan.get("language_code", "hi")
    card = t("confirm_business", legal_name=record["legal_name"],
             trade_name=record["trade_name"], address=record["registered_address"])
    await say(transport, msg.sender, card,
              voice_text=voice_of(card, lang), buttons=yes_no_buttons(), artisan_id=artisan["id"])


async def _confirm_business(artisan: dict, msg: InboundMessage, transport: Transport) -> None:
    reply = await incoming_text(msg, artisan) or ""
    if await classify_yes_no(reply) != "yes":
        await queries.set_state(artisan["id"], "kyc_awaiting_gstin")
        await say(transport, msg.sender, t("ask_gstin"), artisan_id=artisan["id"])
        return
    ctx = artisan["context"]
    record = ctx["gstin_record"]
    identity = await queries.create_seller_identity({
        "legal_name": record["legal_name"], "gstin": ctx["pending_gstin"],
        "business_name": record["trade_name"], "registered_address": record["registered_address"],
        "registration_type": "gstin", "kyc_status": "collecting",
    })
    await queries.update_artisan(artisan["id"], {"seller_identity_id": identity["id"]})
    artisan["seller_identity_id"] = identity["id"]
    await queries.set_state(artisan["id"], "kyc_awaiting_passbook")
    await say(transport, msg.sender, t("ask_passbook"), artisan_id=artisan["id"])


async def _awaiting_pan(artisan: dict, msg: InboundMessage, transport: Transport) -> None:
    if msg.type != "image" or not msg.media:
        heard = (await incoming_text(msg, artisan) or "").lower()
        if "gstin" in heard or "gst" in heard or "जीएसटी" in heard:
            await queries.set_state(artisan["id"], "kyc_awaiting_gstin")
            await say(transport, msg.sender, t("ask_gstin"), artisan_id=artisan["id"])
            return
        await say(transport, msg.sender, t("ask_pan"), artisan_id=artisan["id"])
        return
    ocr = await chat_json(
        load_prompt("ocr_pan"),
        [{"type": "text", "text": "Read this document photo."},
         image_content(msg.media, msg.media_mime or "image/jpeg")],
        model=VISION_MODEL, what="kyc.ocr_pan", temperature=0,
    )
    log_event("vision-ocr", "PAN card OCR",
              {**ocr, "pan_number": "******" + (ocr.get("pan_number") or "")[-4:]})
    retry = _doc_issue_message(ocr, t("doc_pan"), "is_pan_card", ["name", "pan_number"])
    if retry:
        await say(transport, msg.sender, retry, artisan_id=artisan["id"])
        return
    await queries.set_state(artisan["id"], "kyc_confirm_pan_fields",
                            {"pan_name": ocr["name"], "pan_number": ocr.get("pan_number")})
    await _show_pan_fields(artisan, msg.sender, transport,
                           ocr["name"], ocr.get("pan_number"))


async def _show_pan_fields(artisan: dict, sender: str, transport: Transport,
                           name: str, number: str | None) -> None:
    lang = artisan.get("language_code", "hi")
    card = t("confirm_pan_fields", name=name, number=number or "—")
    await say(transport, sender, card,
              voice_text=voice_of(card, lang), buttons=yes_no_buttons(), artisan_id=artisan["id"])


async def _confirm_pan_fields(artisan: dict, msg: InboundMessage, transport: Transport) -> None:
    reply = await incoming_text(msg, artisan) or ""
    ctx = artisan["context"]
    if await classify_yes_no(reply) != "yes":
        await queries.set_state(artisan["id"], "kyc_pan_fix_choice")
        await say(transport, msg.sender, t("pan_fix_choice"),
                  buttons=[Button("fix_name", t("field_name")),
                           Button("fix_number", t("field_number"))],
                  artisan_id=artisan["id"])
        return
    identity = await queries.create_seller_identity({
        "legal_name": ctx["pan_name"],
        "pan_ref": (ctx.get("pan_number") or "")[-4:],
        "registration_type": "eid", "kyc_status": "collecting",
    })
    await queries.update_artisan(artisan["id"], {"seller_identity_id": identity["id"]})
    artisan["seller_identity_id"] = identity["id"]
    await queries.set_state(artisan["id"], "kyc_awaiting_passbook")
    await say(transport, msg.sender, t("ask_passbook"), artisan_id=artisan["id"])


async def _pan_fix_choice(artisan: dict, msg: InboundMessage, transport: Transport) -> None:
    reply = (await incoming_text(msg, artisan) or "").strip().lower()
    if reply in {"1", "fix_name"} or "नाम" in reply or "name" in reply:
        field = "pan_name"
    elif reply in {"2", "fix_number"} or "नंबर" in reply or "number" in reply:
        field = "pan_number"
    else:
        await say(transport, msg.sender, t("pan_fix_choice"),
                  buttons=[Button("fix_name", t("field_name")),
                           Button("fix_number", t("field_number"))],
                  artisan_id=artisan["id"])
        return
    label = t("field_name") if field == "pan_name" else t("field_number")
    await queries.set_state(artisan["id"], "kyc_pan_fix_value", {"fix_field": field})
    await say(transport, msg.sender, t("fix_prompt", field=label), artisan_id=artisan["id"])


async def _pan_fix_value(artisan: dict, msg: InboundMessage, transport: Transport) -> None:
    heard = (await incoming_text(msg, artisan) or "").strip()
    if not heard:
        await say(transport, msg.sender, t("expect_voice_or_text"), artisan_id=artisan["id"])
        return
    field = artisan["context"].get("fix_field", "pan_name")
    value = re.sub(r"[^0-9A-Za-z]", "", heard).upper() if field == "pan_number" else heard
    await queries.set_state(artisan["id"], "kyc_confirm_pan_fields", {field: value})
    artisan["context"][field] = value
    await _show_pan_fields(artisan, msg.sender, transport,
                           artisan["context"]["pan_name"], artisan["context"].get("pan_number"))


def _route(artisan: dict) -> str:
    return "gstin" if artisan["context"].get("gstin_record") else "eid"


async def _awaiting_passbook(artisan: dict, msg: InboundMessage, transport: Transport) -> None:
    if msg.type != "image" or not msg.media:
        await say(transport, msg.sender, t("ask_passbook"), artisan_id=artisan["id"])
        return
    ocr = await chat_json(
        load_prompt("ocr_passbook"),
        [{"type": "text", "text": "Read this document photo."},
         image_content(msg.media, msg.media_mime or "image/jpeg")],
        model=VISION_MODEL, what="kyc.ocr_passbook", temperature=0,
    )
    log_event("vision-ocr", "passbook OCR",
              {**ocr, "account_number": "******" + (ocr.get("account_number") or "")[-4:]})
    retry = _doc_issue_message(ocr, t("doc_passbook"), "is_passbook",
                               ["name", "account_number", "ifsc"])
    if retry:
        await say(transport, msg.sender, retry, artisan_id=artisan["id"])
        return

    await queries.set_state(artisan["id"], "kyc_confirm_pb_fields",
                            {"pb_name": ocr.get("name"),
                             "account_number": ocr["account_number"], "ifsc": ocr.get("ifsc"),
                             "passbook_address": ocr.get("address")})
    for k, v in (("pb_name", ocr.get("name")), ("account_number", ocr["account_number"]),
                 ("ifsc", ocr.get("ifsc")), ("passbook_address", ocr.get("address"))):
        artisan["context"][k] = v
    await _show_pb_fields(artisan, msg.sender, transport)


def _pb_fix_buttons() -> list[Button]:
    return [Button("fix_name", t("field_name")), Button("fix_account", t("field_account")),
            Button("fix_ifsc", t("field_ifsc")), Button("fix_address", t("field_address"))]


async def _show_pb_fields(artisan: dict, sender: str, transport: Transport) -> None:
    ctx = artisan["context"]
    account = ctx.get("account_number") or ""
    lang = artisan.get("language_code", "hi")
    card = t("confirm_pb_fields", name=ctx.get("pb_name") or "—",
             account=" ".join(account[i:i + 4] for i in range(0, len(account), 4)),
             ifsc=ctx.get("ifsc") or "—", address=ctx.get("passbook_address") or "—")
    await say(transport, sender, card,
              voice_text=voice_of(card, lang), buttons=yes_no_buttons(), artisan_id=artisan["id"])


async def _confirm_pb_fields(artisan: dict, msg: InboundMessage, transport: Transport) -> None:
    reply = await incoming_text(msg, artisan) or ""
    ctx = artisan["context"]
    if await classify_yes_no(reply) != "yes":
        await queries.set_state(artisan["id"], "kyc_pb_fix_choice")
        await say(transport, msg.sender, t("pb_fix_choice"),
                  buttons=_pb_fix_buttons(), artisan_id=artisan["id"])
        return

    pb_name = ctx.get("pb_name")
    if _route(artisan) == "gstin":
        record = ctx["gstin_record"]
        if not (await names_match_smart(record["legal_name"], pb_name)
                or await names_match_smart(record["trade_name"], pb_name)):
            await queries.set_state(artisan["id"], "kyc_awaiting_passbook")
            await say(transport, msg.sender,
                      t("name_mismatch_gstin", business_name=record["legal_name"],
                        bank_name=pb_name or "—"),
                      buttons=_gstin_mismatch_buttons(), artisan_id=artisan["id"])
            return
        base_address = record["registered_address"]
    else:
        anchor = ctx.get("pan_name", "")
        if not await names_match_smart(anchor, pb_name):
            await queries.set_state(artisan["id"], "kyc_awaiting_pan")
            await say(transport, msg.sender,
                      t("name_mismatch", pan_name=anchor, bank_name=pb_name or "—"),
                      buttons=_mismatch_buttons(), artisan_id=artisan["id"])
            return
        base_address = ctx.get("passbook_address") or ""

    await queries.update_seller_identity(artisan["seller_identity_id"], {
        "bank_account_ref": (ctx.get("account_number") or "")[-4:], "ifsc": ctx.get("ifsc"),
        "registered_address": base_address,
    })
    await _ask_pickup(artisan, msg.sender, transport, base_address)


_PB_FIX_FIELDS = {
    "1": ("pb_name", "field_name"), "fix_name": ("pb_name", "field_name"),
    "2": ("account_number", "field_account"), "fix_account": ("account_number", "field_account"),
    "3": ("ifsc", "field_ifsc"), "fix_ifsc": ("ifsc", "field_ifsc"),
    "4": ("passbook_address", "field_address"), "fix_address": ("passbook_address", "field_address"),
}


async def _pb_fix_choice(artisan: dict, msg: InboundMessage, transport: Transport) -> None:
    reply = (await incoming_text(msg, artisan) or "").strip().lower()
    choice = _PB_FIX_FIELDS.get(reply)
    if choice is None:
        for token, key in (("नाम", "1"), ("name", "1"), ("खाता", "2"), ("account", "2"),
                           ("ifsc", "3"), ("पता", "4"), ("address", "4")):
            if token in reply:
                choice = _PB_FIX_FIELDS[key]
                break
    if choice is None:
        await say(transport, msg.sender, t("pb_fix_choice"),
                  buttons=_pb_fix_buttons(), artisan_id=artisan["id"])
        return
    field, label_key = choice
    await queries.set_state(artisan["id"], "kyc_pb_fix_value", {"fix_field": field})
    await say(transport, msg.sender, t("fix_prompt", field=t(label_key)), artisan_id=artisan["id"])


async def _pb_fix_value(artisan: dict, msg: InboundMessage, transport: Transport) -> None:
    heard = (await incoming_text(msg, artisan) or "").strip()
    if not heard:
        await say(transport, msg.sender, t("expect_voice_or_text"), artisan_id=artisan["id"])
        return
    field = artisan["context"].get("fix_field", "pb_name")
    if field == "account_number":
        value = parse_spoken_digits(heard) or re.sub(r"\D", "", heard)
        if not value:
            await say(transport, msg.sender, t("expect_voice_or_text"), artisan_id=artisan["id"])
            return
    elif field == "ifsc":
        value = re.sub(r"[^0-9A-Za-z]", "", heard).upper()
    else:
        value = heard
    await queries.set_state(artisan["id"], "kyc_confirm_pb_fields", {field: value})
    artisan["context"][field] = value
    await _show_pb_fields(artisan, msg.sender, transport)


async def _ask_pickup(artisan: dict, sender: str, transport: Transport, base_address: str) -> None:
    await queries.set_state(artisan["id"], "kyc_pickup_question", {"base_address": base_address})
    await say(transport, sender, t("pickup_question", address=base_address),
              buttons=yes_no_buttons(), artisan_id=artisan["id"])


async def _pickup_question(artisan: dict, msg: InboundMessage, transport: Transport) -> None:
    reply = await incoming_text(msg, artisan) or ""
    if await classify_yes_no(reply) == "yes":
        await _pickup_done(artisan, msg.sender, transport, artisan["context"]["base_address"])
    else:
        await queries.set_state(artisan["id"], "kyc_awaiting_pickup_address")
        await say(transport, msg.sender, t("ask_pickup_address"), artisan_id=artisan["id"])


async def _awaiting_pickup_address(artisan: dict, msg: InboundMessage, transport: Transport) -> None:
    heard = (await incoming_text(msg, artisan) or "").strip()
    if not heard:
        await say(transport, msg.sender, t("expect_voice_or_text"), artisan_id=artisan["id"])
        return
    if msg.type == "text":
        await _pickup_address_captured(artisan, msg.sender, transport, heard)
        return
    await queries.set_state(artisan["id"], "kyc_confirm_pickup_address", {"pending_pickup": heard})
    await say(transport, msg.sender, t("confirm_address", address=heard),
              buttons=yes_no_buttons(), artisan_id=artisan["id"])


async def _confirm_pickup_address(artisan: dict, msg: InboundMessage, transport: Transport) -> None:
    reply = await incoming_text(msg, artisan) or ""
    if await classify_yes_no(reply) != "yes":
        await queries.set_state(artisan["id"], "kyc_awaiting_pickup_address")
        await say(transport, msg.sender, t("ask_pickup_address"), artisan_id=artisan["id"])
        return
    await _pickup_address_captured(artisan, msg.sender, transport,
                                   artisan["context"]["pending_pickup"])


async def _pickup_address_captured(artisan: dict, sender: str, transport: Transport, address: str) -> None:
    if _pincode_in(address):
        await _pickup_done(artisan, sender, transport, address)
        return
    await queries.set_state(artisan["id"], "kyc_awaiting_pickup_pincode", {"pending_pickup": address})
    await say(transport, sender, t("ask_pickup_pincode"), artisan_id=artisan["id"])


async def _awaiting_pickup_pincode(artisan: dict, msg: InboundMessage, transport: Transport) -> None:
    heard = await incoming_text(msg, artisan) or ""
    pincode = parse_spoken_digits(heard, expected_length=6)
    if not pincode:
        await say(transport, msg.sender, t("pincode_retry"), artisan_id=artisan["id"])
        return
    if msg.type != "text":
        await queries.set_state(artisan["id"], "kyc_confirm_pickup_pincode",
                                {"pending_pincode": pincode})
        card = t("confirm_pincode", spaced=_spaced(pincode))
        await say(transport, msg.sender, card,
                  voice_text=voice_of(card, artisan.get("language_code", "hi")),
                  buttons=yes_no_buttons(), artisan_id=artisan["id"])
        return
    address = f"{artisan['context']['pending_pickup']}, पिन {pincode}"
    await _pickup_done(artisan, msg.sender, transport, address)


async def _confirm_pickup_pincode(artisan: dict, msg: InboundMessage, transport: Transport) -> None:
    reply = await incoming_text(msg, artisan) or ""
    if await classify_yes_no(reply) != "yes":
        await queries.set_state(artisan["id"], "kyc_awaiting_pickup_pincode")
        await say(transport, msg.sender, t("ask_pickup_pincode"), artisan_id=artisan["id"])
        return
    ctx = artisan["context"]
    address = f"{ctx['pending_pickup']}, पिन {ctx['pending_pincode']}"
    await _pickup_done(artisan, msg.sender, transport, address)


async def _pickup_done(artisan: dict, sender: str, transport: Transport, pickup_address: str) -> None:
    await queries.update_seller_identity(artisan["seller_identity_id"],
                                         {"pickup_address": pickup_address})
    pincode = _pincode_in(pickup_address)
    if pincode:
        await queries.update_artisan(artisan["id"], {"pincode": pincode})
    await _create_account_and_finish(artisan, sender, transport)


async def _account_payload(artisan: dict) -> dict:
    identity = await queries.get_seller_identity(artisan["seller_identity_id"])
    email = email_alias.derive(identity["legal_name"] or "seller", identity["id"])
    await queries.update_seller_identity(identity["id"], {"email": email})
    ctx = artisan["context"]
    return {
        "gstin": identity.get("gstin"),
        "pan_ref": ctx.get("pan_number"),
        "legal_name": identity["legal_name"],
        "email": email,
        "bank_account_ref": ctx.get("account_number"),
        "ifsc": identity.get("ifsc"),
        "registered_address": identity.get("registered_address"),
        "pickup_address": identity.get("pickup_address"),
        "otp_phone": artisan.get("whatsapp_phone"),
        "pincode": artisan.get("pincode") or _pincode_in(identity.get("pickup_address")),
    }


async def _create_account_and_finish(artisan: dict, sender: str, transport: Transport) -> None:
    payload = await _account_payload(artisan)
    result = await meesho.create_seller_account(payload)
    log_event("meesho-mock", f"createSellerAccount → {result.get('verification_status')}", result)
    if result.get("verification_status") == "verified":
        await _finalize(artisan, sender, transport)
    elif result.get("otp_required"):
        await queries.set_state(artisan["id"], "kyc_awaiting_otp",
                                {"application_id": result.get("application_id")})
        await _send_otp(artisan, sender, transport)
    else:
        await say(transport, sender, t("error"), artisan_id=artisan["id"])


async def _send_otp(artisan: dict, sender: str, transport: Transport) -> None:
    """Generate a real 6-digit OTP, deliver it as a dismissible popup with a voice note, and wait for the artisan to enter it back."""
    code = f"{random.randint(0, 999999):06d}"
    await queries.set_state(artisan["id"], "kyc_awaiting_otp", {"otp_code": code})
    log_event("otp", "OTP generated + sent to seller's phone (demo popup)", {"otp": code})
    otp_card = t("otp_popup_text", spaced=_spaced(code))
    await say(transport, sender, otp_card,
              voice_text=voice_of(otp_card, artisan.get("language_code", "hi")),
              meta={"otp_popup": code}, artisan_id=artisan["id"])
    await say(transport, sender, t("ask_otp"), voice=False, artisan_id=artisan["id"])


async def _awaiting_otp(artisan: dict, msg: InboundMessage, transport: Transport) -> None:
    heard = await incoming_text(msg, artisan) or ""
    entered = parse_spoken_digits(heard, expected_length=6)
    if not entered:
        await say(transport, msg.sender, t("otp_retry"), artisan_id=artisan["id"])
        return
    if entered == artisan["context"].get("otp_code"):
        await _submit_otp(artisan, msg.sender, transport, entered)
    else:
        await say(transport, msg.sender, t("otp_wrong"), artisan_id=artisan["id"])
        await _send_otp(artisan, msg.sender, transport)


async def _submit_otp(artisan: dict, sender: str, transport: Transport, otp: str) -> None:
    result = await meesho.confirm_seller_otp(artisan["context"].get("application_id", ""), otp)
    log_event("meesho-mock", f"OTP → {result.get('verification_status')}", result)
    if result.get("verification_status") != "verified":
        await queries.set_state(artisan["id"], "kyc_awaiting_otp")
        await say(transport, sender, t("otp_retry"), artisan_id=artisan["id"])
        return
    await queries.update_seller_identity(artisan["seller_identity_id"],
                                         {"enrolment_id": result.get("enrolment_id")})
    await say(transport, sender, t("eid_issued"), artisan_id=artisan["id"])
    await _finalize(artisan, sender, transport)


async def _finalize(artisan: dict, sender: str, transport: Transport) -> None:
    identity = await queries.update_seller_identity(artisan["seller_identity_id"], {
        "kyc_status": "verified", "consistency_verified": True,
        "otp_phone": artisan.get("whatsapp_phone"),
    })
    if identity.get("registration_type") == "gstin":
        reg_line = f"🧾 GSTIN: {identity.get('gstin')}"
        store = identity.get("business_name") or t("store_tbd")
    else:
        reg_line = f"🧾 Enrolment ID: {identity.get('enrolment_id')}"
        store = t("store_tbd")
    await queries.set_state(artisan["id"], "awaiting_photos")
    await say(transport, sender,
              t("kyc_summary", legal_name=identity.get("legal_name"),
                store=store, last4=identity.get("bank_account_ref") or "----",
                pickup=identity.get("pickup_address") or "-", reg_line=reg_line),
              artisan_id=artisan["id"])
    await say(transport, sender, t("ask_photos"), artisan_id=artisan["id"])


_HANDLERS = {
    "kyc_gstin_question": _gstin_question,
    "kyc_awaiting_gstin": _awaiting_gstin,
    "kyc_confirm_gstin": _confirm_gstin,
    "kyc_confirm_business": _confirm_business,
    "kyc_awaiting_pan": _awaiting_pan,
    "kyc_confirm_pan_fields": _confirm_pan_fields,
    "kyc_pan_fix_choice": _pan_fix_choice,
    "kyc_pan_fix_value": _pan_fix_value,
    "kyc_awaiting_passbook": _awaiting_passbook,
    "kyc_confirm_pb_fields": _confirm_pb_fields,
    "kyc_pb_fix_choice": _pb_fix_choice,
    "kyc_pb_fix_value": _pb_fix_value,
    "kyc_pickup_question": _pickup_question,
    "kyc_awaiting_pickup_address": _awaiting_pickup_address,
    "kyc_confirm_pickup_address": _confirm_pickup_address,
    "kyc_awaiting_pickup_pincode": _awaiting_pickup_pincode,
    "kyc_confirm_pickup_pincode": _confirm_pickup_pincode,
    "kyc_parked_bank": _parked_bank,
    "kyc_awaiting_otp": _awaiting_otp,
}
