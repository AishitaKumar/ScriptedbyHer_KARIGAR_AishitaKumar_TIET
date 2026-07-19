"""Shared OpenAI client: every call goes through here."""

from __future__ import annotations

import asyncio
import base64
import json
import logging
from pathlib import Path

from openai import AsyncOpenAI, APIError, APITimeoutError, RateLimitError

logger = logging.getLogger("karigar.llm")

TEXT_MODEL = "gpt-4o"
VISION_MODEL = "gpt-4o"

PROMPTS_DIR = Path(__file__).parent / "prompts"

_client: AsyncOpenAI | None = None


class LLMError(Exception):
    """Raised after retries are exhausted; flows translate this to a Hindi apology."""


def client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI()
    return _client


def load_prompt(name: str) -> str:
    """Load a versioned prompt file from app/prompts/ (never inline strings)."""
    return (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")


def image_content(image_bytes: bytes, mime: str = "image/jpeg", detail: str = "high") -> dict:
    b64 = base64.b64encode(image_bytes).decode()
    return {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}", "detail": detail}}


async def _with_retry(coro_factory, what: str):
    delay = 1.0
    for attempt in range(3):
        try:
            return await coro_factory()
        except (APIError, APITimeoutError, RateLimitError, json.JSONDecodeError) as e:
            logger.warning("%s failed (attempt %d/3): %s", what, attempt + 1, e)
            if attempt == 2:
                raise LLMError(f"{what} failed after retries") from e
            await asyncio.sleep(delay)
            delay *= 2


async def chat_json(system_prompt: str, user_content, *, model: str = TEXT_MODEL,
                    what: str = "llm-call", temperature: float | None = None) -> dict:
    """One chat completion returning a parsed JSON object."""

    async def call():
        kwargs = {"temperature": temperature} if temperature is not None else {}
        response = await client().chat.completions.create(
            model=model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            **kwargs,
        )
        return json.loads(response.choices[0].message.content)

    return await _with_retry(call, what)


async def chat_text(system_prompt: str, user_content, *, model: str = TEXT_MODEL, what: str = "llm-call") -> str:
    async def call():
        response = await client().chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
        )
        return response.choices[0].message.content

    return await _with_retry(call, what)
