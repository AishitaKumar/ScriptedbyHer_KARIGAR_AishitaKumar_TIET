"""Supabase client + storage helpers. All DB access goes through this module."""

from __future__ import annotations

import os
import uuid

from supabase import Client, create_client

MEDIA_BUCKET = "media"

_client: Client | None = None


def db() -> Client:
    global _client
    if _client is None:
        url = os.environ["SUPABASE_URL"]
        key = os.environ["SUPABASE_SERVICE_KEY"]
        _client = create_client(url, key)
    return _client


def upload_media(data: bytes, suffix: str, content_type: str, folder: str = "photos") -> str:
    """Upload bytes to the media bucket, return the public URL."""
    path = f"{folder}/{uuid.uuid4().hex}{suffix}"
    db().storage.from_(MEDIA_BUCKET).upload(
        path, data, file_options={"content-type": content_type}
    )
    return db().storage.from_(MEDIA_BUCKET).get_public_url(path)


def download_media(url: str) -> bytes:
    """Fetch bytes back from a public media URL (sync — call via asyncio.to_thread)."""
    import httpx

    r = httpx.get(url, timeout=30)
    r.raise_for_status()
    return r.content
