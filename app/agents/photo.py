"""Agent 2 — Photo enhancement (local, free: rembg + Pillow)."""

from __future__ import annotations

import io
import logging

from PIL import Image, ImageEnhance, ImageOps

logger = logging.getLogger("karigar.photo")

try:
    from rembg import remove as _rembg_remove  # type: ignore

    _REMBG_AVAILABLE = True
except Exception:  # noqa: BLE001 — any import failure means "no rembg on this host"
    _REMBG_AVAILABLE = False
    logger.warning("rembg unavailable — falling back to Pillow-only enhancement")

MAX_SIDE = 1600
BG_COLOR = (255, 255, 255)


def enhance(image_bytes: bytes, remove_background: bool = True) -> bytes:
    """Enhance a product photo. Synchronous & CPU-bound — call via asyncio.to_thread."""
    img = Image.open(io.BytesIO(image_bytes))
    img = ImageOps.exif_transpose(img)

    if remove_background and _REMBG_AVAILABLE:
        try:
            cutout = _rembg_remove(img)
            flat = Image.new("RGB", cutout.size, BG_COLOR)
            flat.paste(cutout, mask=cutout.split()[-1])
            img = flat
        except Exception:  # noqa: BLE001
            logger.exception("rembg failed; keeping original background")

    img = img.convert("RGB")
    img.thumbnail((MAX_SIDE, MAX_SIDE))
    img = ImageOps.autocontrast(img, cutoff=1)
    img = ImageEnhance.Brightness(img).enhance(1.05)
    img = ImageEnhance.Sharpness(img).enhance(1.1)

    out = io.BytesIO()
    img.save(out, format="JPEG", quality=88)
    return out.getvalue()
