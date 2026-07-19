"""Twilio WhatsApp Sandbox transport (fallback, spec §5)."""

from __future__ import annotations

import logging
import os

import httpx
from fastapi import APIRouter, Form

from app.jobs.queue import enqueue
from app.transports.base import InboundMessage, OutboundMessage, Transport

logger = logging.getLogger("karigar.twilio")

router = APIRouter()


def _auth() -> tuple[str, str]:
    return os.environ["TWILIO_ACCOUNT_SID"], os.environ["TWILIO_AUTH_TOKEN"]


class TwilioTransport(Transport):
    name = "twilio"

    def supports_buttons(self) -> bool:
        return False

    async def send(self, message: OutboundMessage) -> None:
        sid, token = _auth()
        url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
        async with httpx.AsyncClient(timeout=30, auth=(sid, token)) as client:
            data = {
                "From": "whatsapp:+14155238886",
                "To": f"whatsapp:{message.to}",
                "Body": message.text,
            }
            media = message.audio_url or message.image_url
            if media:
                data["MediaUrl"] = media
            r = await client.post(url, data=data)
            if r.status_code >= 400:
                logger.error("twilio send failed %s: %s", r.status_code, r.text)


transport = TwilioTransport()


@router.post("/webhook/twilio")
async def receive(
    From: str = Form(""),
    Body: str = Form(""),
    NumMedia: int = Form(0),
    MediaUrl0: str = Form(None),
    MediaContentType0: str = Form(None),
):
    from app.orchestrator.router import handle_inbound

    sender = From.removeprefix("whatsapp:")
    if NumMedia and MediaUrl0:
        async with httpx.AsyncClient(timeout=60, auth=_auth()) as client:
            blob = await client.get(MediaUrl0, follow_redirects=True)
        mime = MediaContentType0 or ""
        mtype = "audio" if mime.startswith("audio") else "image"
        msg = InboundMessage(sender=sender, type=mtype, media=blob.content,
                             media_mime=mime, transport="twilio")
    else:
        msg = InboundMessage(sender=sender, type="text", text=Body, transport="twilio")
    enqueue(handle_inbound(msg, transport), name="twilio-inbound")
    return {"ok": True}
