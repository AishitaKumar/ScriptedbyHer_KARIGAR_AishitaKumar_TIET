"""Meta WhatsApp Cloud API transport (primary, spec §5)."""

from __future__ import annotations

import logging
import os

import httpx
from fastapi import APIRouter, Query, Request, Response

from app.jobs.queue import enqueue
from app.transports.base import InboundMessage, OutboundMessage, Transport

logger = logging.getLogger("karigar.whatsapp")

GRAPH = "https://graph.facebook.com/v21.0"

router = APIRouter()


def _token() -> str:
    return os.environ["WHATSAPP_TOKEN"]


def _phone_id() -> str:
    return os.environ["WHATSAPP_PHONE_NUMBER_ID"]


class WhatsAppCloudTransport(Transport):
    name = "whatsapp_cloud"

    async def send(self, message: OutboundMessage) -> None:
        async with httpx.AsyncClient(timeout=30) as client:
            headers = {"Authorization": f"Bearer {_token()}"}
            url = f"{GRAPH}/{_phone_id()}/messages"

            async def post(payload: dict) -> None:
                r = await client.post(url, json={
                    "messaging_product": "whatsapp", "to": message.to, **payload,
                })
                if r.status_code >= 400:
                    logger.error("whatsapp send failed %s: %s", r.status_code, r.text)

            if message.image_url:
                await post({"type": "image", "image": {"link": message.image_url}})
            if message.buttons:
                await post({
                    "type": "interactive",
                    "interactive": {
                        "type": "button",
                        "body": {"text": message.text},
                        "action": {"buttons": [
                            {"type": "reply", "reply": {"id": b.id, "title": b.label[:20]}}
                            for b in message.buttons[:3]
                        ]},
                    },
                })
            else:
                await post({"type": "text", "text": {"body": message.text}})
            if message.audio_url:
                await post({"type": "audio", "audio": {"link": message.audio_url}})


transport = WhatsAppCloudTransport()


async def _fetch_media(media_id: str) -> tuple[bytes, str]:
    async with httpx.AsyncClient(timeout=60) as client:
        headers = {"Authorization": f"Bearer {_token()}"}
        meta = (await client.get(f"{GRAPH}/{media_id}", headers=headers)).json()
        blob = await client.get(meta["url"], headers=headers)
        return blob.content, meta.get("mime_type", "application/octet-stream")


@router.get("/webhook/whatsapp")
async def verify(
    mode: str = Query(None, alias="hub.mode"),
    token: str = Query(None, alias="hub.verify_token"),
    challenge: str = Query(None, alias="hub.challenge"),
):
    if mode == "subscribe" and token == os.environ.get("WHATSAPP_VERIFY_TOKEN"):
        return Response(content=challenge, media_type="text/plain")
    return Response(status_code=403)


@router.post("/webhook/whatsapp")
async def receive(request: Request):
    """Async webhook pattern (spec §12): parse, enqueue, return 200 immediately."""
    from app.orchestrator.router import handle_inbound

    body = await request.json()
    try:
        for entry in body.get("entry", []):
            for change in entry.get("changes", []):
                for m in change.get("value", {}).get("messages", []):
                    msg = await _parse(m)
                    if msg:
                        enqueue(handle_inbound(msg, transport), name="wa-inbound")
    except Exception:  # noqa: BLE001 — never 500 a webhook; Meta retries aggressively
        logger.exception("failed to parse whatsapp webhook")
    return {"ok": True}


async def _parse(m: dict) -> InboundMessage | None:
    sender = m.get("from", "")
    mtype = m.get("type")
    if mtype == "text":
        return InboundMessage(sender=sender, type="text", text=m["text"]["body"],
                              transport="whatsapp_cloud")
    if mtype == "interactive":
        reply = m["interactive"].get("button_reply", {})
        return InboundMessage(sender=sender, type="button", text=reply.get("id"),
                              transport="whatsapp_cloud")
    if mtype == "button":
        return InboundMessage(sender=sender, type="button", text=m["button"].get("payload"),
                              transport="whatsapp_cloud")
    if mtype in {"audio", "voice"}:
        data, mime = await _fetch_media(m[mtype]["id"])
        return InboundMessage(sender=sender, type="audio", media=data, media_mime=mime,
                              transport="whatsapp_cloud")
    if mtype == "image":
        data, mime = await _fetch_media(m["image"]["id"])
        return InboundMessage(sender=sender, type="image", media=data, media_mime=mime,
                              transport="whatsapp_cloud")
    logger.info("ignoring unsupported message type %s", mtype)
    return None
