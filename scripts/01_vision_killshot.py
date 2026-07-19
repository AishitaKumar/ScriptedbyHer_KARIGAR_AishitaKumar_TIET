"""Kill-shot test: can GPT-4o Vision separate real handmade Madhubani from factory prints?

Everything else in Karigar depends on the answer. Run this BEFORE building infrastructure.

Usage:
    1. Put real handmade craft photos in   test_images/real/
       (Wikimedia Commons has good Madhubani photos)
    2. Put factory-print counterexamples in test_images/print/
       (marketplace screenshots of printed "Madhubani" posters)
    3. Set OPENAI_API_KEY in .env
    4. python scripts/01_vision_killshot.py

Pass criterion: every real photo scores >= 60 with verdict handmade/likely_handmade,
every print scores <= 40 with verdict print/likely_print. Uncertain verdicts on
borderline images are acceptable (the product asks for more photos, it never guesses).
"""

import base64
import json
import mimetypes
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

ROOT = Path(__file__).resolve().parent.parent
PROMPT = (ROOT / "app" / "prompts" / "vision_authenticity.md").read_text(encoding="utf-8")
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}

load_dotenv(ROOT / ".env")
client = OpenAI()


def analyze(image_path: Path) -> dict:
    mime = mimetypes.guess_type(image_path.name)[0] or "image/jpeg"
    b64 = base64.b64encode(image_path.read_bytes()).decode()
    response = client.chat.completions.create(
        model="gpt-4o",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Analyse this product photo."},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{b64}", "detail": "high"},
                    },
                ],
            },
        ],
    )
    return json.loads(response.choices[0].message.content)


def run_folder(folder: Path, expected: str) -> list[dict]:
    results = []
    images = sorted(p for p in folder.iterdir() if p.suffix.lower() in IMAGE_EXTS)
    if not images:
        print(f"  (no images in {folder} — add some and rerun)")
        return results
    for path in images:
        try:
            r = analyze(path)
        except Exception as e:  # noqa: BLE001 — report and keep testing the rest
            print(f"  {path.name}: ERROR {e}")
            continue
        score = r.get("authenticity_score")
        verdict = r.get("authenticity_verdict")
        provenance = r.get("image_provenance")
        handmade_verdicts = {"handmade", "likely_handmade"}
        reject_verdicts = {"print", "likely_print", "suspect_downloaded_image"}
        if expected == "real":
            ok = verdict in handmade_verdicts
        else:
            ok = verdict in reject_verdicts
        mark = "PASS" if ok else ("?   " if verdict in {"uncertain", "insufficient_evidence"} else "FAIL")
        print(f"  [{mark}] {path.name}: craft={r.get('craft')} score={score} verdict={verdict} provenance={provenance}")
        for reason in r.get("reasons", []):
            print(f"          - {reason}")
        results.append({"file": path.name, "expected": expected, "ok": ok, **r})
    return results


def main() -> int:
    real_dir = ROOT / "test_images" / "real"
    print_dir = ROOT / "test_images" / "print"
    real_dir.mkdir(parents=True, exist_ok=True)
    print_dir.mkdir(parents=True, exist_ok=True)

    print("=== REAL handmade photos (expect handmade/likely_handmade) ===")
    real = run_folder(real_dir, "real")
    print("\n=== FACTORY-PRINT counterexamples (expect print/likely_print) ===")
    prints = run_folder(print_dir, "print")

    all_results = real + prints
    if not all_results:
        print("\nNo images tested. Add images to test_images/real and test_images/print.")
        return 1

    (ROOT / "scripts" / "killshot_results.json").write_text(
        json.dumps(all_results, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    correct = sum(1 for r in all_results if r["ok"])
    print(f"\n=== VERDICT: {correct}/{len(all_results)} correctly classified ===")
    print("Full JSON saved to scripts/killshot_results.json")
    if real and prints and correct == len(all_results):
        print("KILL-SHOT PASSED — the authenticity pitch stands. Build the pipeline.")
        return 0
    print("Review the misses above. If prints score as handmade, the prompt needs work")
    print("before ANY other code is written — or the authenticity pitch must pivot.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
