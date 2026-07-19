"""Per-seller email auto-provisioning via plus-addressing on a real controlled inbox — computed derivation at runtime, never a stored constant."""

from __future__ import annotations

import os
import re

BASE_INBOX = os.environ.get("KARIGAR_EMAIL_BASE", "karigar.sellers@gmail.com")

_DEV2LAT = {
    "अ": "a", "आ": "aa", "इ": "i", "ई": "i", "उ": "u", "ऊ": "u", "ए": "e", "ऐ": "ai",
    "ओ": "o", "औ": "au", "क": "k", "ख": "kh", "ग": "g", "घ": "gh", "च": "ch", "छ": "chh",
    "ज": "j", "झ": "jh", "ट": "t", "ठ": "th", "ड": "d", "ढ": "dh", "ण": "n", "त": "t",
    "थ": "th", "द": "d", "ध": "dh", "न": "n", "प": "p", "फ": "ph", "ब": "b", "भ": "bh",
    "म": "m", "य": "y", "र": "r", "ल": "l", "व": "v", "श": "sh", "ष": "sh", "स": "s",
    "ह": "h", "ा": "a", "ि": "i", "ी": "i", "ु": "u", "ू": "u", "े": "e", "ै": "ai",
    "ो": "o", "ौ": "au", "ं": "n", "़": "", "्": "",
}


def _slugify(name: str) -> str:
    latin = "".join(_DEV2LAT.get(ch, ch) for ch in name.lower())
    slug = re.sub(r"[^a-z0-9]+", ".", latin).strip(".")
    return slug[:24] or "seller"


def derive(name: str, seller_identity_id: str) -> str:
    """karigar.sellers+<name-slug>.<short-id>@gmail.com — unique per seller."""
    local, domain = BASE_INBOX.split("@", 1)
    short = seller_identity_id.replace("-", "")[:4]
    return f"{local}+{_slugify(name)}.{short}@{domain}"
