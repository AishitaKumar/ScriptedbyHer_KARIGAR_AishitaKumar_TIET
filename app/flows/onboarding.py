"""Onboarding state machine."""

from __future__ import annotations

import asyncio
import logging

from app.agentlog import log_event
from app.agents import photo, vision
from app.db import queries
from app.db.client import upload_media
from app.flows import kyc
from app.flows.common import incoming_text, say, validate_answer, yes_no_buttons
from app.flows.messages import t
from app.jobs.queue import enqueue
from app.llm import LLMError
from app.pipeline import build_listing_package, triage_batch
from app.transports.base import Button, InboundMessage, Transport
from app.voice.classify import classify_yes_no

logger = logging.getLogger("karigar.onboarding")

BATCH_DEBOUNCE_SECONDS = 8
_batches: dict[str, dict] = {}


async def handle(artisan: dict, msg: InboundMessage, transport: Transport) -> None:
    state = artisan["onboarding_state"]
    if state.startswith("kyc_"):
        await kyc.handle(artisan, msg, transport)
        return
    handler = _HANDLERS.get(state)
    if handler is None:
        logger.error("no handler for state %s", state)
        await say(transport, msg.sender, t("error"), artisan_id=artisan["id"])
        return
    try:
        await handler(artisan, msg, transport)
    except LLMError:
        await say(transport, msg.sender, t("error"), artisan_id=artisan["id"])


def _lang_buttons() -> list[Button]:
    return [Button("lang_hi", "हिंदी"), Button("lang_en", "English")]


async def _new(artisan: dict, msg: InboundMessage, transport: Transport) -> None:
    await queries.set_state(artisan["id"], "awaiting_language")
    await say(transport, msg.sender, t("welcome"), buttons=_lang_buttons(), artisan_id=artisan["id"])


async def _awaiting_language(artisan: dict, msg: InboundMessage, transport: Transport) -> None:
    from app.flows import messages

    choice = (await incoming_text(msg, artisan) or "").strip().lower()
    if choice in {"1", "lang_hi", "हिंदी", "hindi"}:
        lang = "hi"
    elif choice in {"2", "lang_en", "english", "अंग्रेजी", "इंग्लिश"}:
        lang = "en"
    elif choice in {"3", "4", "lang_bn", "lang_ta", "বাংলা", "தமிழ்", "bangla", "bengali", "tamil"}:
        await say(transport, msg.sender, t("language_coming_soon"), artisan_id=artisan["id"])
        lang = "hi"
    else:
        await say(transport, msg.sender, t("welcome"), buttons=_lang_buttons(), artisan_id=artisan["id"])
        return
    await queries.update_artisan(artisan["id"], {"language_code": lang})
    messages.set_lang(lang)
    await queries.set_state(artisan["id"], "awaiting_name")
    await say(transport, msg.sender, t("ask_name"), artisan_id=artisan["id"], language_code=lang)


async def _awaiting_name(artisan: dict, msg: InboundMessage, transport: Transport) -> None:
    heard = await incoming_text(msg, artisan)
    if not heard:
        await say(transport, msg.sender, t("expect_voice_or_text"), artisan_id=artisan["id"])
        return
    name = heard.strip().strip("।.").removeprefix("मेरा नाम ").removesuffix(" है").strip()
    check = await validate_answer("name", name, artisan.get("language_code", "hi"))
    if not check.get("valid"):
        await say(transport, msg.sender, check.get("message") or t("re_ask"), artisan_id=artisan["id"])
        return
    name = check.get("cleaned") or name
    if msg.type == "text":
        await queries.update_artisan(artisan["id"], {"name": name})
        await queries.set_state(artisan["id"], "awaiting_village")
        await say(transport, msg.sender, t("ask_village", name=name), artisan_id=artisan["id"])
        return
    await queries.set_state(artisan["id"], "confirm_name", {"pending_name": name})
    await say(transport, msg.sender, t("confirm_heard", value=name),
              buttons=yes_no_buttons(), artisan_id=artisan["id"])


async def _confirm_name(artisan: dict, msg: InboundMessage, transport: Transport) -> None:
    reply = await incoming_text(msg, artisan) or ""
    verdict = await classify_yes_no(reply)
    if verdict == "yes":
        name = artisan["context"].get("pending_name", "")
        await queries.update_artisan(artisan["id"], {"name": name})
        await queries.set_state(artisan["id"], "awaiting_village")
        await say(transport, msg.sender, t("ask_village", name=name), artisan_id=artisan["id"])
    else:
        await queries.set_state(artisan["id"], "awaiting_name")
        await say(transport, msg.sender, t("re_ask"), artisan_id=artisan["id"])


async def _awaiting_village(artisan: dict, msg: InboundMessage, transport: Transport) -> None:
    heard = await incoming_text(msg, artisan)
    if not heard:
        await say(transport, msg.sender, t("expect_voice_or_text"), artisan_id=artisan["id"])
        return
    village = heard.strip().strip("।.")
    check = await validate_answer("village", village, artisan.get("language_code", "hi"))
    if not check.get("valid"):
        await say(transport, msg.sender, check.get("message") or t("re_ask"), artisan_id=artisan["id"])
        return
    village = check.get("cleaned") or village
    if msg.type == "text":
        await queries.update_artisan(artisan["id"], {"village": village})
        await kyc.entry(artisan, msg.sender, transport)
        return
    await queries.set_state(artisan["id"], "confirm_village", {"pending_village": village})
    await say(transport, msg.sender, t("confirm_heard", value=village),
              buttons=yes_no_buttons(), artisan_id=artisan["id"])


async def _confirm_village(artisan: dict, msg: InboundMessage, transport: Transport) -> None:
    reply = await incoming_text(msg, artisan) or ""
    if await classify_yes_no(reply) == "yes":
        await queries.update_artisan(artisan["id"], {"village": artisan["context"].get("pending_village", "")})
        await kyc.entry(artisan, msg.sender, transport)
    else:
        await queries.set_state(artisan["id"], "awaiting_village")
        await say(transport, msg.sender, t("re_ask"), artisan_id=artisan["id"])


async def _awaiting_photos(artisan: dict, msg: InboundMessage, transport: Transport) -> None:
    if msg.type != "image" or not msg.media:
        from app.flows import operations

        text = (await incoming_text(msg, artisan) or "").strip()
        if text:
            intent = await operations.classify_intent(artisan, text)
            if intent == "cancel":
                await queries.set_state(artisan["id"], "active")
                await say(transport, msg.sender, t("cancelled_listing"), artisan_id=artisan["id"])
                return
            if await operations._dispatch_query(artisan, text, msg.sender, transport, intent):
                await say(transport, msg.sender, t("resume_photos"), artisan_id=artisan["id"])
                return
        await say(transport, msg.sender, t("expect_photo"), artisan_id=artisan["id"])
        return
    # photos often arrive a few seconds apart, so debounce them into one batch
    batch = _batches.setdefault(artisan["id"], {"images": [], "timer": None})
    batch["images"].append((msg.media, msg.media_mime or "image/jpeg"))
    if batch["timer"]:
        batch["timer"].cancel()
    if len(batch["images"]) == 1:
        await say(transport, msg.sender, t("processing"), voice=False, artisan_id=artisan["id"])

    async def fire():
        await asyncio.sleep(BATCH_DEBOUNCE_SECONDS)
        images = _batches.pop(artisan["id"], {}).get("images", [])
        if images:
            enqueue(_process_batch(artisan, msg.sender, images, transport), name="photo-batch")

    batch["timer"] = asyncio.create_task(fire())


async def _process_batch(
    artisan: dict, sender: str, images: list[tuple[bytes, str]], transport: Transport
) -> None:
    if len(images) > 2:  # only worth clustering when there could be multiple designs
        cluster = await vision.cluster_batch(images)
        log_event("vision", f"clustering → {len(cluster['groups'])} design(s)", cluster)
        if len(cluster["groups"]) > 1:
            await say(transport, sender,
                      t("multiple_designs", n=len(cluster["groups"])), artisan_id=artisan["id"])
            return

    result = await build_listing_package(images, artisan.get("language_code", "hi"))
    log_event("pipeline", f"batch of {len(images)} → {result['outcome']}",
              {"analyses": result.get("analyses"), "listing": result.get("listing")})

    if result["outcome"] == "rejected":
        reason = (result.get("reasons") or ["साफ़ नहीं दिख रहा"])[0]
        await say(transport, sender, t("auth_reject", reason=reason), artisan_id=artisan["id"])
        return
    if result["outcome"] == "all_suspect":
        await say(transport, sender, t("photo_suspect"), artisan_id=artisan["id"])
        return
    if result["outcome"] == "all_failed":
        # "not a craft at all" needs a different nudge than "a craft, but blurry"
        analyses = result.get("analyses") or []
        no_craft = analyses and all((a.get("craft") in (None, "", "none")) for a in analyses)
        await say(transport, sender, t("photo_not_craft") if no_craft else t("photo_fail"),
                  artisan_id=artisan["id"])
        return

    if result["dropped_indices"]:
        await say(transport, sender,
                  t("partial_success", kept=len(result["usable_indices"]), dropped=len(result["dropped_indices"])),
                  artisan_id=artisan["id"])

    photo_urls = [
        upload_media(images[i][0], ".jpg", images[i][1], folder="photos")
        for i in result["usable_indices"]
    ]
    enhanced_url = upload_media(result["enhanced_photo"], ".jpg", "image/jpeg", folder="enhanced")
    listing = result["listing"]
    title_hi = listing.get("title_hi") or listing["title"]
    row = await queries.create_listing({
        "artisan_id": artisan["id"], "craft_type": listing["craft_type"], "style": listing["style"],
        "motifs": listing["motifs"], "title": listing["title"], "title_hi": title_hi,
        "description": listing["description"],
        "price": listing["price"], "original_price": listing["original_price"],
        "photo_urls": photo_urls, "enhanced_photo_url": enhanced_url,
        "gi_status": listing["gi_status"], "quality_score": listing["quality_score"],
        "authenticity_score": listing["authenticity_score"],
        "authenticity_reasons": listing["authenticity_reasons"], "status": "pending_approval",
    })
    await queries.update_artisan(artisan["id"], {"craft": listing["craft_type"]})
    await queries.set_state(artisan["id"], "awaiting_dimensions",
                            {"listing_id": row["id"], "in_hand": listing["in_hand"],
                             "title_hi": title_hi})
    await say(transport, sender, t("ask_dimensions"), artisan_id=artisan["id"])


async def _send_price_proposal(artisan: dict, sender: str, transport: Transport) -> None:
    listing = await queries.get_listing(artisan["context"]["listing_id"])
    await queries.set_state(artisan["id"], "awaiting_price_confirm")
    await say(transport, sender,
              t("price_proposal", price=listing["price"],
                in_hand=artisan["context"].get("in_hand", listing["price"] - 60)),
              buttons=[Button("yes", t("btn_proceed")), Button("no", t("btn_change_price"))],
              artisan_id=artisan["id"])


async def _awaiting_dimensions(artisan: dict, msg: InboundMessage, transport: Transport) -> None:
    import json

    from app.llm import chat_json, load_prompt

    heard = (await incoming_text(msg, artisan) or "").strip()
    if not heard:
        await say(transport, msg.sender, t("dimensions_unclear"), artisan_id=artisan["id"])
        return
    parsed = await chat_json(
        load_prompt("parse_dimensions"),
        json.dumps({"answer": heard, "language": artisan.get("language_code", "hi")}, ensure_ascii=False),
        what="onboarding.parse_dimensions",
    )
    if not parsed.get("valid") or not parsed.get("canonical"):
        await say(transport, msg.sender, t("dimensions_unclear"), artisan_id=artisan["id"])
        return
    await queries.set_state(artisan["id"], "confirm_dimensions",
                            {"pending_dimensions": parsed["canonical"]})
    await say(transport, msg.sender,
              t("confirm_dimensions", size=parsed.get("normalized") or parsed["canonical"]),
              buttons=yes_no_buttons(), artisan_id=artisan["id"])


async def _confirm_dimensions(artisan: dict, msg: InboundMessage, transport: Transport) -> None:
    reply = await incoming_text(msg, artisan) or ""
    if await classify_yes_no(reply) == "yes":
        await queries.update_listing(artisan["context"]["listing_id"],
                                     {"dimensions": artisan["context"].get("pending_dimensions")})
        await _send_price_proposal(artisan, msg.sender, transport)
    else:
        await queries.set_state(artisan["id"], "awaiting_dimensions")
        await say(transport, msg.sender, t("ask_dimensions"), artisan_id=artisan["id"])


async def _awaiting_challenge(artisan: dict, msg: InboundMessage, transport: Transport) -> None:
    if msg.type != "image" or not msg.media:
        await say(transport, msg.sender, t("expect_photo"), artisan_id=artisan["id"])
        return
    result = await vision.evaluate_back_challenge(
        msg.media, msg.media_mime or "image/jpeg", artisan.get("language_code", "hi")
    )
    log_event("vision", f"back-of-piece challenge → {result.get('verdict')}", result)
    listing_id = artisan["context"].get("listing_id")

    if result.get("verdict") == "pass":
        listing = await queries.update_listing(listing_id, {"status": "pending_approval"})
        await queries.set_state(artisan["id"], "awaiting_price_confirm", {"challenge_attempts": 0})
        await say(transport, msg.sender, t("challenge_pass"), artisan_id=artisan["id"])
        await say(transport, msg.sender,
                  t("price_proposal", price=listing["price"], in_hand=artisan["context"].get("in_hand", listing["price"] - 60)),
                  buttons=[Button("yes", t("btn_proceed")), Button("no", t("btn_change_price"))],
                  artisan_id=artisan["id"])
        return

    attempts = (artisan["context"].get("challenge_attempts") or 0) + 1
    if result.get("verdict") == "fail" or attempts >= 3:
        await queries.update_listing(listing_id, {"status": "rejected"})
        reason = (result.get("reasons") or ["पीछे की तरफ हाथ की बनी कला के निशान नहीं मिले"])[0]
        await queries.set_state(artisan["id"], "awaiting_photos",
                                {"listing_id": None, "challenge_attempts": 0})
        await say(transport, msg.sender, t("auth_reject", reason=reason), artisan_id=artisan["id"])
    else:
        await queries.set_state(artisan["id"], "awaiting_challenge", {"challenge_attempts": attempts})
        if result.get("verdict") == "wrong_photo":
            reason = (result.get("reasons") or ["यह पेंटिंग के पीछे की तरफ नहीं दिख रही।"])[0]
            await say(transport, msg.sender,
                      t("challenge_wrong_photo", reason=reason), artisan_id=artisan["id"])
        else:
            await say(transport, msg.sender, t("challenge_unclear"), artisan_id=artisan["id"])


async def _awaiting_price_confirm(artisan: dict, msg: InboundMessage, transport: Transport) -> None:
    from app.flows import preview

    reply = await incoming_text(msg, artisan) or ""
    if await classify_yes_no(reply) == "yes":
        if await preview.kyc_already_verified(artisan):
            await preview.send_preview(artisan, msg.sender, transport)
        else:
            await kyc.entry(artisan, msg.sender, transport)
    else:
        await queries.set_state(artisan["id"], "awaiting_custom_price")
        await say(transport, msg.sender, t("price_ask_new"), artisan_id=artisan["id"])


async def _awaiting_custom_price(artisan: dict, msg: InboundMessage, transport: Transport) -> None:
    from app.agents.pricing import PRICE_CAP, in_hand_amount
    from app.voice.classify import parse_spoken_digits

    heard = await incoming_text(msg, artisan) or ""
    digits = parse_spoken_digits(heard)
    if not digits or not (50 <= int(digits) <= PRICE_CAP):
        await say(transport, msg.sender, t("price_ask_new"), artisan_id=artisan["id"])
        return
    price = int(digits)
    listing_id = artisan["context"]["listing_id"]
    await queries.update_listing(listing_id, {"price": price, "original_price": int(price * 1.4)})
    await queries.set_state(artisan["id"], "awaiting_price_confirm", {"in_hand": in_hand_amount(price)})
    await say(transport, msg.sender,
              t("price_custom_confirm", price=price, in_hand=in_hand_amount(price)),
              buttons=[Button("yes", t("btn_proceed")), Button("no", t("btn_change_price"))],
              artisan_id=artisan["id"])


async def _awaiting_preview_approval(artisan: dict, msg: InboundMessage, transport: Transport) -> None:
    from app.flows import preview

    reply = await incoming_text(msg, artisan) or ""
    if await classify_yes_no(reply) == "yes":
        await preview.publish(artisan, msg.sender, transport)
    else:
        await queries.set_state(artisan["id"], "awaiting_redo_choice")
        await say(transport, msg.sender, t("redo_choice"),
                  buttons=[Button("redo_price", t("btn_redo_price")),
                           Button("redo_photos", t("btn_redo_photos")),
                           Button("redo_keep", t("btn_redo_keep"))],
                  artisan_id=artisan["id"])


async def _awaiting_redo_choice(artisan: dict, msg: InboundMessage, transport: Transport) -> None:
    from app.flows import preview

    reply = (await incoming_text(msg, artisan) or "").strip().lower()
    listing_id = artisan["context"].get("listing_id")
    if reply in {"1", "redo_price"} or "कीमत" in reply or "दाम" in reply:
        await queries.set_state(artisan["id"], "awaiting_custom_price")
        await say(transport, msg.sender, t("price_ask_new"), artisan_id=artisan["id"])
    elif reply in {"2", "redo_photos"} or "फोटो" in reply or "तस्वीर" in reply:
        await queries.set_state(artisan["id"], "awaiting_replacement_photo")
        await say(transport, msg.sender, t("redo_photos"), artisan_id=artisan["id"])
    elif reply in {"3", "redo_keep"}:
        await preview.publish(artisan, msg.sender, transport)
    else:
        await _apply_freeform_edit(artisan, msg, transport, reply)


async def _apply_freeform_edit(
    artisan: dict, msg: InboundMessage, transport: Transport, instruction: str
) -> None:
    import json

    from app.agents.pricing import PRICE_CAP, in_hand_amount
    from app.flows import preview
    from app.llm import chat_json, load_prompt

    listing_id = artisan["context"].get("listing_id")
    listing = await queries.get_listing(listing_id)
    result = await chat_json(
        load_prompt("listing_edit"),
        json.dumps({"instruction": instruction,
                    "language": artisan.get("language_code", "hi"),
                    "listing": {"title": listing["title"], "description": listing["description"],
                                "price": listing["price"]}}, ensure_ascii=False),
        what="listing.edit",
    )
    log_event("orchestrator", f"listing edit → {result.get('action')}",
              {"instruction": instruction, **result})
    action = result.get("action")

    if action == "set_price" and result.get("price"):
        price = min(int(result["price"]), PRICE_CAP)
        await queries.update_listing(listing_id, {"price": price, "original_price": int(price * 1.4)})
        await queries.set_state(artisan["id"], "awaiting_redo_choice", {"in_hand": in_hand_amount(price)})
    elif action == "redo_photos":
        await queries.set_state(artisan["id"], "awaiting_replacement_photo")
        await say(transport, msg.sender, t("redo_photos"), artisan_id=artisan["id"])
        return
    elif action == "edit_text":
        patch = {k: result[k] for k in ("title", "description") if result.get(k)}
        if patch:
            await queries.update_listing(listing_id, patch)
        if result.get("title_hi"):
            await queries.set_state(artisan["id"], artisan["onboarding_state"],
                                    {"title_hi": result["title_hi"]})
            artisan["context"]["title_hi"] = result["title_hi"]
    elif action == "publish":
        await preview.publish(artisan, msg.sender, transport)
        return
    else:
        await say(transport, msg.sender,
                  result.get("reply_hi") or t("redo_choice"), artisan_id=artisan["id"])
        return

    if result.get("reply_hi"):
        await say(transport, msg.sender, result["reply_hi"], artisan_id=artisan["id"])
    await preview.send_preview(artisan, msg.sender, transport)


async def _awaiting_replacement_photo(artisan: dict, msg: InboundMessage, transport: Transport) -> None:
    """Change-photo: take ONE new photo, check it's real, swap it into the existing
    listing — title, price and size stay exactly as they were."""
    if msg.type != "image" or not msg.media:
        await say(transport, msg.sender, t("expect_photo"), artisan_id=artisan["id"])
        return
    await say(transport, msg.sender, t("processing"), voice=False, artisan_id=artisan["id"])
    enqueue(_process_replacement_photo(
        artisan, msg.sender, (msg.media, msg.media_mime or "image/jpeg"), transport),
        name="photo-swap")


async def _process_replacement_photo(
    artisan: dict, sender: str, image: tuple[bytes, str], transport: Transport
) -> None:
    listing_id = artisan["context"].get("listing_id")
    if not listing_id:  # safety: nothing to swap into
        await say(transport, sender, t("error"), artisan_id=artisan["id"])
        return
    analyses = await vision.analyze_batch([image], artisan.get("language_code", "hi"))
    triage = triage_batch(analyses)
    log_event("pipeline", f"replacement photo → {triage['outcome']}", {"analyses": analyses})

    if triage["outcome"] != "ok":  # same honest rejection reasons as the first upload
        if triage["outcome"] == "rejected":
            reason = (triage.get("reasons") or ["साफ़ नहीं दिख रहा"])[0]
            await say(transport, sender, t("auth_reject", reason=reason), artisan_id=artisan["id"])
        elif triage["outcome"] == "all_suspect":
            await say(transport, sender, t("photo_suspect"), artisan_id=artisan["id"])
        else:
            no_craft = analyses and all((a.get("craft") in (None, "", "none")) for a in analyses)
            await say(transport, sender, t("photo_not_craft") if no_craft else t("photo_fail"),
                      artisan_id=artisan["id"])
        return  # state stays awaiting_replacement_photo — she can try another photo

    enhanced = await asyncio.to_thread(photo.enhance, image[0])
    photo_url = upload_media(image[0], ".jpg", image[1], folder="photos")
    enhanced_url = upload_media(enhanced, ".jpg", "image/jpeg", folder="enhanced")
    await queries.update_listing(listing_id, {"photo_urls": [photo_url], "enhanced_photo_url": enhanced_url})
    from app.flows import preview
    await preview.send_preview(artisan, sender, transport)


_HANDLERS = {
    "new": _new,
    "awaiting_language": _awaiting_language,
    "awaiting_name": _awaiting_name,
    "confirm_name": _confirm_name,
    "awaiting_village": _awaiting_village,
    "confirm_village": _confirm_village,
    "awaiting_photos": _awaiting_photos,
    "awaiting_dimensions": _awaiting_dimensions,
    "confirm_dimensions": _confirm_dimensions,
    "awaiting_price_confirm": _awaiting_price_confirm,
    "awaiting_custom_price": _awaiting_custom_price,
    "awaiting_preview_approval": _awaiting_preview_approval,
    "awaiting_redo_choice": _awaiting_redo_choice,
    "awaiting_replacement_photo": _awaiting_replacement_photo,
}

