"""Orchestrator entry point: every inbound message from every transport lands here."""

from __future__ import annotations

import logging

from app.agentlog import log_event
from app.db import queries
from app.flows import onboarding, operations
from app.transports.base import InboundMessage, Transport

logger = logging.getLogger("karigar.orchestrator")


async def handle_inbound(msg: InboundMessage, transport: Transport) -> None:
    from app.flows import messages

    artisan = await queries.get_or_create_artisan(msg.sender)
    artisan.setdefault("context", {})
    if artisan["context"] is None:
        artisan["context"] = {}
    messages.set_lang(artisan.get("language_code"))
    log_event("orchestrator",
              f"inbound {msg.type} from {msg.sender[-6:]} (state={artisan['onboarding_state']})",
              {"text": msg.text})

    if msg.type == "button" and msg.text in {"order_ok", "order_oos"}:
        await operations.handle_order_ack(artisan, msg.sender, transport,
                                          ack_ok=(msg.text == "order_ok"))
        return

    text = (msg.text or "").strip().lower().replace("🙏", "").strip()
    if msg.type in {"text", "button"} and text in {"naya karigar", "नया कारीगर", "naya karigar shuru"}:
        if artisan["onboarding_state"] == "active":
            from app.flows.common import say
            from app.flows.messages import t

            await say(transport, msg.sender, t("already_active"), artisan_id=artisan["id"])
            return
        artisan = await queries.update_artisan(
            artisan["id"], {"onboarding_state": "new", "context": {}}
        )
        artisan.setdefault("context", {})

    if artisan["onboarding_state"] == "active":
        await operations.handle(artisan, msg, transport)
    else:
        await onboarding.handle(artisan, msg, transport)
