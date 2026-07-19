"""Standalone pipeline test: run Vision → [Photo ∥ Story ∥ Pricing] on local images.

Usage: python scripts/02_pipeline_test.py [image1 image2 ...]
Defaults to the first 3 images in test_images/real/.
"""

import asyncio
import json
import mimetypes
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from app.pipeline import build_listing_package  # noqa: E402


async def main() -> int:
    if len(sys.argv) > 1:
        paths = [Path(p) for p in sys.argv[1:]]
    else:
        real = ROOT / "test_images" / "real"
        paths = sorted(p for p in real.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png"})[:3]
    images = [
        (p.read_bytes(), mimetypes.guess_type(p.name)[0] or "image/jpeg") for p in paths
    ]
    print(f"Running pipeline over {len(images)} images: {[p.name for p in paths]}")

    start = time.perf_counter()
    result = await build_listing_package(images)
    elapsed = time.perf_counter() - start

    print(f"\noutcome: {result['outcome']}  ({elapsed:.1f}s total)")
    if result["outcome"] != "ok":
        print("reasons:", result.get("reasons"))
        return 1

    out_dir = ROOT / "scripts" / "pipeline_out"
    out_dir.mkdir(exist_ok=True)
    (out_dir / "enhanced.jpg").write_bytes(result["enhanced_photo"])
    listing = result["listing"]
    print(json.dumps(listing, indent=2, ensure_ascii=False))
    print(f"\nGI: {result['gi_record']['display_name'] if result['gi_record'] else 'not GI-registered'}")
    print(f"In-hand for artisan: Rs.{listing['in_hand']} of Rs.{listing['price']}")
    print(f"Enhanced photo saved to {out_dir / 'enhanced.jpg'}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
