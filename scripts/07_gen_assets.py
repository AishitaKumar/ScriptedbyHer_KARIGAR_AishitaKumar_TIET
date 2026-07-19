"""One-time generation of frontend image assets (OpenAI image API → web/assets/).

Static marketplace dressing for the Meesho-replica screen + landing hero.
Falls back from gpt-image-1 to dall-e-3 if the org lacks access.
"""

import base64
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "web" / "assets"
ASSETS.mkdir(exist_ok=True)
load_dotenv(ROOT / ".env")
client = OpenAI()

PRODUCT_STYLE = ("Realistic e-commerce product photograph, soft natural light, "
                 "clean neutral home setting, shot on phone, no text, no watermark, no people.")

JOBS = [
    ("hero_artisan", "1536x1024",
     "Documentary photograph of an elderly Indian woman artisan in a rustic mud-walled village "
     "home, sitting cross-legged on a jute mat, painting an intricate Madhubani artwork on paper "
     "with a fine bamboo brush, clay pots of natural pigment colours beside her, warm golden "
     "window light, maroon and orange saree, deeply focused expression. Warm, dignified, "
     "photorealistic. No text, no watermark."),
    ("p_toys", "1024x1024",
     f"Set of 3 colourful Channapatna lacquered wooden toys (stacking rings and spinning tops) on a beige cloth. {PRODUCT_STYLE}"),
    ("p_pattachitra", "1024x1024",
     f"Pattachitra hand-painted cloth scroll artwork of a peacock with ornate borders, laid flat. {PRODUCT_STYLE}"),
    ("p_madhubani", "1024x1024",
     f"Madhubani painting of a decorated elephant with fish and floral motifs, bright natural colours on handmade paper, hung on a wall. {PRODUCT_STYLE}"),
    ("p_bluepottery", "1024x1024",
     f"Jaipur blue pottery ceramic vase with cobalt floral patterns on a wooden table. {PRODUCT_STYLE}"),
    ("p_bandhani", "1024x1024",
     f"Colourful bandhani tie-dye cotton dupatta fabric, folded and draped on a plain surface. {PRODUCT_STYLE}"),
    ("p_cleaner", "1024x1024",
     f"Generic multipurpose kitchen cleaner spray bottle, green trigger, plain label without readable text, on a kitchen counter. {PRODUCT_STYLE}"),
    ("p_moneyplant", "1024x1024",
     f"Artificial money plant vine with green leaves hanging on a white wall near a shelf, home decor. {PRODUCT_STYLE}"),
    ("p_clock", "1024x1024",
     f"Vintage round wooden wall clock on an exposed brick wall. {PRODUCT_STYLE}"),
    ("p_bottle", "1024x1024",
     f"Plain stainless steel water bottle 1 litre on a kitchen table. {PRODUCT_STYLE}"),
    ("p_cushions", "1024x1024",
     f"Set of printed decorative cushion covers in warm colours arranged on a sofa. {PRODUCT_STYLE}"),
]


def generate(name: str, size: str, prompt: str) -> None:
    out = ASSETS / f"{name}.jpg"
    if out.exists():
        print(f"skip {name} (exists)")
        return
    try:
        r = client.images.generate(model="gpt-image-1", prompt=prompt, size=size, quality="medium")
        data = base64.b64decode(r.data[0].b64_json)
    except Exception as e:  # noqa: BLE001 — fall back if gpt-image-1 unavailable
        print(f"gpt-image-1 failed for {name} ({str(e)[:80]}), trying dall-e-3")
        de_size = "1792x1024" if size == "1536x1024" else "1024x1024"
        r = client.images.generate(model="dall-e-3", prompt=prompt, size=de_size,
                                   quality="standard", response_format="b64_json")
        data = base64.b64decode(r.data[0].b64_json)
    import io

    from PIL import Image

    img = Image.open(io.BytesIO(data)).convert("RGB")
    img.save(out, "JPEG", quality=88)
    print(f"done {name} ({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    for name, size, prompt in JOBS:
        generate(name, size, prompt)
    print("ALL ASSETS READY")
