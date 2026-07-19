"""Web Demo Console transport — a second REAL client, not a mock."""

from __future__ import annotations

import time
from collections import defaultdict

from app.transports.base import OutboundMessage, Transport

_outbox: dict[str, list[dict]] = defaultdict(list)


class WebConsoleTransport(Transport):
    name = "web_console"

    async def send(self, message: OutboundMessage) -> None:
        _outbox[message.to].append({
            "ts": time.time(),
            "text": message.text,
            "audio_url": message.audio_url,
            "image_url": message.image_url,
            "buttons": [{"id": b.id, "label": b.label} for b in message.buttons],
            "meta": message.meta,
        })


def poll(session: str, since: int = 0) -> dict:
    messages = _outbox.get(session, [])
    return {"messages": messages[since:], "next": len(messages)}


def reset() -> None:
    _outbox.clear()
