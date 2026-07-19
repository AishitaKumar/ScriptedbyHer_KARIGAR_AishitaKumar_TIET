"""Regression drive for the flow fixes:
1. 'Naya Karigar' restarts onboarding from any mid-flow state
2. Active seller adds a new listing → NO KYC re-ask, straight to preview
3. Custom price echo says 'आपकी बताई कीमत', not 'मशीन के हिसाब से'
4. Preview 'नहीं' → redo choice (price/photos/keep), not a full restart

Uses the existing verified artisan session 'happy-5db851' for the add-listing
test. Server must be running on :8000.
"""

import mimetypes
import sys
import time
import uuid
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
KYC = ROOT / "test_images" / "kyc"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

client = httpx.Client(base_url="http://127.0.0.1:8000", timeout=60)


class Session:
    def __init__(self, sid: str):
        self.id = sid
        self.since = client.get("/api/console/poll", params={"session": sid, "since": 0}).json()["next"]
        print(f"\n=== session {sid} ===")

    def send(self, type_: str, text=None, path: Path | None = None):
        data = {"session": self.id, "type": type_}
        if text:
            data["text"] = text
            print(f"   USER: {text}")
        files = None
        if path:
            mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
            files = {"file": (path.name, path.read_bytes(), mime)}
            print(f"   USER: [image {path.name}]")
        client.post("/api/console/send", data=data, files=files).raise_for_status()

    def wait_for(self, *subs, timeout=120, forbid=None):
        deadline = time.time() + timeout
        while time.time() < deadline:
            payload = client.get("/api/console/poll", params={"session": self.id, "since": self.since}).json()
            self.since = payload["next"]
            for m in payload["messages"]:
                print(f"   BOT : {m['text'][:100]}{'…' if len(m['text']) > 100 else ''}")
                if forbid and any(f in m["text"] for f in forbid):
                    raise AssertionError(f"FORBIDDEN message appeared: {m['text'][:80]}")
                if any(s in m["text"] for s in subs):
                    return m["text"]
            time.sleep(1.5)
        raise TimeoutError(f"never saw {subs!r}")


def test_1_keyword_restart():
    print("\n[1] Naya Karigar mid-flow → clean restart")
    s = Session("restart-" + uuid.uuid4().hex[:6])
    s.send("text", "Naya Karigar"); s.wait_for("आपकी भाषा")
    s.send("text", "1"); s.wait_for("नाम क्या है")
    s.send("text", "Naya Karigar")
    s.wait_for("आपकी भाषा", forbid=["मैंने सुना: Naya Karigar"])
    print("   ✅ keyword restarts, never captured as a name")


def test_2_add_listing_skips_kyc():
    print("\n[2] verified seller adds a product → no KYC, straight to preview")
    s = Session("happy-5db851")
    s.send("text", "मुझे एक नई पेंटिंग बेचनी है")
    s.wait_for("तस्वीरें भेजें")
    s.send("image", path=KYC / "painting_front.jpeg")
    s.wait_for("पीछे की तरफ", timeout=150)
    s.send("image", path=KYC / "painting_back.jpeg")
    s.wait_for("कीमत", timeout=90)

    print("\n[3] custom price wording")
    s.send("text", "2")
    s.wait_for("कितनी कीमत")
    s.send("text", "650")
    text = s.wait_for("आपकी बताई कीमत", forbid=["मशीन के हिसाब से"])
    assert "650" in text and "590" in text
    print("   ✅ artisan's price echoed as hers, in-hand correct")

    s.send("text", "1")
    s.wait_for("लिस्टिंग तैयार है", timeout=60, forbid=["पैन कार्ड", "पासबुक"])
    print("   ✅ KYC skipped for verified seller")

    print("\n[4] preview 'नहीं' → redo choice, change price only")
    s.send("text", "2")
    s.wait_for("क्या बदलना चाहेंगी")
    s.send("text", "1")
    s.wait_for("कितनी कीमत")
    s.send("text", "550")
    s.wait_for("आपकी बताई कीमत")
    s.send("text", "1")
    s.wait_for("लिस्टिंग तैयार है", timeout=60, forbid=["तस्वीरें भेजें", "पैन कार्ड"])
    s.send("text", "1")
    s.wait_for("बधाई हो", timeout=90)
    listings = client.get("/api/listings").json()["listings"]
    assert any(l["price"] == 550 for l in listings), "550 listing not live"
    print("   ✅ redo changed only the price; listing live at ₹550")


if __name__ == "__main__":
    assert client.get("/health").json()["ok"]
    test_1_keyword_restart()
    test_2_add_listing_skips_kyc()
    print("\nALL FLOW FIXES VERIFIED")
