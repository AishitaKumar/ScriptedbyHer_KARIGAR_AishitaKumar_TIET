"""E2E drive of the onboarding flow through the Web Demo Console API —
exactly what a judge does, scripted. Covers §14 steps 1-3 plus the adversarial
challenge rejection (§14.10 variant: pristine white back → rejection).

Run the server first: .venv\\Scripts\\python -m uvicorn app.main:app --port 8000
"""

import io
import mimetypes
import sys
import time
import uuid
from pathlib import Path

import httpx
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = "http://127.0.0.1:8000"
SESSION = "e2e-" + uuid.uuid4().hex[:6]
client = httpx.Client(base_url=BASE, timeout=30)
since = 0


def send(type_: str, text: str | None = None, file: tuple | None = None):
    data = {"session": SESSION, "type": type_}
    if text:
        data["text"] = text
    files = {"file": file} if file else None
    r = client.post("/api/console/send", data=data, files=files)
    r.raise_for_status()


def wait_for(substring: str, timeout: float = 60) -> list[dict]:
    """Poll until a bot message containing substring arrives; return new messages."""
    global since
    deadline = time.time() + timeout
    collected = []
    while time.time() < deadline:
        r = client.get("/api/console/poll", params={"session": SESSION, "since": since})
        payload = r.json()
        since = payload["next"]
        for m in payload["messages"]:
            collected.append(m)
            print(f"   BOT: {m['text'][:120]}{'…' if len(m['text']) > 120 else ''}"
                  + (" [voice]" if m.get("audio_url") else "")
                  + (f" [buttons: {[b['label'] for b in m['buttons']]}]" if m.get("buttons") else ""))
            if substring in m["text"]:
                return collected
        time.sleep(1.5)
    raise TimeoutError(f"never saw: {substring!r}")


def img_file(path: Path) -> tuple:
    mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    return (path.name, path.read_bytes(), mime)


def white_back() -> tuple:
    """A pristine blank-white 'poster back' — the factory print's tell."""
    img = Image.new("RGB", (900, 1200), (252, 252, 250))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return ("back.jpg", buf.getvalue(), "image/jpeg")


def main() -> int:
    print(f"session {SESSION}")
    assert client.get("/health").json()["ok"]

    print("\n[1] initiation")
    send("text", "Naya Karigar")
    wait_for("आपकी भाषा")
    send("text", "1")
    wait_for("नाम क्या है")

    print("\n[2] name + village with confirmations")
    send("text", "मेरा नाम रामकली है")
    wait_for("मैंने सुना")
    send("text", "हाँ")
    wait_for("गाँव")
    send("text", "जितवारपुर, मधुबनी")
    wait_for("मैंने सुना")
    send("text", "1")
    wait_for("तस्वीरें भेजें")

    print("\n[3] photo batch → pipeline (Vision ∥ Photo ∥ Story ∥ Pricing)")
    real = sorted((ROOT / "test_images" / "real").glob("*.jpg"))[:3]
    for p in real:
        send("image", file=img_file(p))
        time.sleep(0.5)
    wait_for("पीछे की तरफ", timeout=120)

    print("\n[4] ADVERSARIAL: synthetic blank image at the challenge step")
    send("image", file=white_back())
    msgs = wait_for("फोटो", timeout=90)
    texts = " ".join(m["text"] for m in msgs)
    assert "समझ नहीं आई" in texts or "माफ़" in texts, texts

    print("\nE2E PASSED: onboarding → pipeline → challenge issue + safe handling of a non-photo.")
    print("(Happy path continuation — real back photo, PAN, passbook — needs real images.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
