"""Transport adapter interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class Button:
    id: str
    label: str


@dataclass
class InboundMessage:
    sender: str
    type: str
    text: str | None = None
    media: bytes | None = None
    media_mime: str | None = None
    transport: str = "unknown"


@dataclass
class OutboundMessage:
    to: str
    text: str
    audio_url: str | None = None
    image_url: str | None = None
    buttons: list[Button] = field(default_factory=list)
    meta: dict = field(default_factory=dict)


class Transport(ABC):
    """One instance per transport; registered with the router."""

    name: str = "base"

    @abstractmethod
    async def send(self, message: OutboundMessage) -> None: ...

    def supports_buttons(self) -> bool:
        return True
