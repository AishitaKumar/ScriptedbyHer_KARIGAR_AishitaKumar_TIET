"""In-memory agent activity log for the Demo Console's live view."""

from __future__ import annotations

import time
from collections import deque

_events: deque[dict] = deque(maxlen=200)


def log_event(agent: str, summary: str, payload: dict | list | str | None = None) -> None:
    _events.append(
        {"ts": time.time(), "agent": agent, "summary": summary, "payload": payload}
    )


def recent(limit: int = 50) -> list[dict]:
    return list(_events)[-limit:]


def clear() -> None:
    _events.clear()
