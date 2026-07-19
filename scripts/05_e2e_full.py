"""FULL acceptance-test drive (spec §14) with real images in test_images/kyc/:

Phase A (happy path): onboarding → real painting photos → back challenge passes
→ pricing → PAN/passbook KYC → pincode/address → OTP → EID → preview → approve
→ live on /shop → mock order → earnings voice round trip.

Phase B (adversarial): fresh session → poster print front → if it survives
Layer 1, the blank print back must be rejected at the challenge.

Run the server first: .venv\\Scripts\\python -m uvicorn app.main:app --port 8000
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

BASE = "http://127.0.0.1:8000"
client = httpx.Client(base_url=BASE, timeout=60)


class Session:
    def __init__(self, label: str):
        self.id = f"{label}-{uuid.uuid4().hex[:6]}"
        self.since = 0
        print(f"\n=== session {self.id} ===")

    def send(self, type_: str, text: str | None = None, path: Path | None = None):
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

    def wait_for(self, *substrings: str, timeout: float = 120) -> str:
        """Wait until any of the substrings appears in a bot message; return it."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            r = client.get("/api/console/poll", params={"session": self.id, "since": self.since})
            payload = r.json()
            self.since = payload["next"]
            for m in payload["messages"]:
                print(f"   BOT : {m['text'][:110]}{'…' if len(m['text']) > 110 else ''}")
                for s in substrings:
                    if s in m["text"]:
                        return m["text"]
            time.sleep(1.5)
        raise TimeoutError(f"never saw any of {substrings!r}")

    def trigger(self, name: str) -> dict:
        r = client.post(f"/demo/{name}", data={"session": self.id})
        print(f"   TRIGGER {name}: {r.status_code}")
        return r.json()


def phase_a() -> None:
    s = Session("happy")
    print("\n[A1] onboarding (KYC comes FIRST — seller account before photos)")
    s.send("text", "Naya Karigar"); s.wait_for("आपकी भाषा")
    s.send("text", "1"); s.wait_for("नाम क्या है")
    s.send("text", "आइशिता कुमार"); s.wait_for("गाँव")
    s.send("text", "पटना, बिहार"); s.wait_for("GSTIN")

    print("\n[A2] EID route: no GSTIN → PAN anchor")
    s.send("text", "2")
    s.wait_for("पैन कार्ड")
    s.send("image", path=KYC / "pan_Aishita.jpeg")
    s.wait_for("पैन कार्ड से मैंने पढ़ा", timeout=90)
    s.send("text", "1")

    print("\n[A3] passbook BEFORE enrolment (grouped 4-field confirm)")
    s.wait_for("पासबुक")
    s.send("image", path=KYC / "passbook_Aishita.jpeg")
    s.wait_for("पासबुक से मैंने पढ़ा", timeout=90)
    s.send("text", "1")

    print("\n[A4] pickup address (different from registered)")
    s.wait_for("पिकअप का पता भी है")
    s.send("text", "2")
    s.wait_for("पिकअप का पूरा पता")
    s.send("text", "मकान 12, गांधी मैदान रोड, पटना")
    s.wait_for("पिन कोड")
    s.send("text", "800001")

    print("\n[A5] OTP device pre-check → Meesho createSellerAccount → OTP → EID")
    s.wait_for("फोन अभी पास में है")
    s.send("text", "1")
    s.wait_for("OTP लिख कर भेजें", timeout=60)
    s.send("text", "472172")
    s.wait_for("पंजीकरण", timeout=60)

    print("\n[A6] summary card → then cataloging begins")
    text = s.wait_for("दुकान का खाता तैयार", timeout=60)
    assert "तस्वीरें" in text

    print("\n[A7] painting photos → pipeline → challenge")
    s.send("image", path=KYC / "painting_front.jpeg")
    time.sleep(0.5)
    s.send("image", path=KYC / "painting_side.jpeg")
    s.wait_for("पीछे की तरफ", timeout=150)
    s.send("image", path=KYC / "painting_back.jpeg")
    s.wait_for("पक्का हो गया", timeout=90)
    s.wait_for("कीमत")
    s.send("text", "1")

    print("\n[A8] preview (store name suggested from her art) → approval → live")
    s.wait_for("लिस्टिंग तैयार है", timeout=60)
    s.send("text", "1")
    s.wait_for("बधाई हो", timeout=90)
    listings = client.get("/api/listings").json()["listings"]
    assert listings, "no live listing on /shop!"
    print(f"   /shop now shows: {listings[0]['title']} @ ₹{listings[0]['price']}"
          f" (gi_status={listings[0]['gi_status']})")

    print("\n[A9] mock order → voice notification → earnings round trip")
    s.trigger("trigger-order")
    s.wait_for("खुशखबरी", timeout=60)
    s.send("text", "1")
    time.sleep(3)
    s.send("text", "मैंने कितना कमाया?")
    s.wait_for("बिकी", "बिक्री", timeout=60)

    print("\n[A10] trend coaching over seeded sales")
    s.trigger("advance-week")
    time.sleep(2)
    s.trigger("trigger-trend")
    s.wait_for("जी", timeout=90)
    print("\nPHASE A COMPLETE ✅")


def phase_gstin() -> None:
    """GSTIN fast-path: registry lookup, business confirm, passbook, NO OTP."""
    s = Session("gstin")
    print("\n[G1] onboarding → GSTIN route")
    s.send("text", "Naya Karigar"); s.wait_for("आपकी भाषा")
    s.send("text", "1"); s.wait_for("नाम क्या है")
    s.send("text", "आइशिता कुमार"); s.wait_for("गाँव")
    s.send("text", "रोहिणी, दिल्ली"); s.wait_for("GSTIN")
    s.send("text", "1")
    s.wait_for("15 अंकों")
    s.send("text", "22AAAAA0000A1Z5")
    s.wait_for("सही है")
    s.send("text", "1")
    s.wait_for("GSTIN मिल गया", timeout=60)
    s.send("text", "1")

    print("\n[G2] passbook name vs GSTIN legal/trade name")
    s.wait_for("पासबुक")
    s.send("image", path=KYC / "passbook_Aishita.jpeg")
    s.wait_for("पासबुक से मैंने पढ़ा", timeout=90)
    s.send("text", "1")

    print("\n[G3] pickup = registered address → instant verification, NO OTP")
    s.wait_for("पिकअप का पता भी है")
    s.send("text", "1")
    text = s.wait_for("दुकान का खाता तैयार", timeout=60)
    assert "GSTIN" in text and "OTP" not in text
    assert "Aishita Handicrafts" in text
    print("\nPHASE GSTIN COMPLETE ✅ (no OTP asked)")


def phase_b() -> None:
    s = Session("fraud")
    print("\n[B1] fraudster passes KYC (owns real documents) — authenticity is the gate")
    s.send("text", "Naya Karigar"); s.wait_for("आपकी भाषा")
    s.send("text", "1"); s.wait_for("नाम क्या है")
    s.send("text", "नकली विक्रेता"); s.wait_for("गाँव")
    s.send("text", "कहीं और"); s.wait_for("GSTIN")
    s.send("text", "2")
    s.wait_for("पैन कार्ड")
    s.send("image", path=KYC / "pan_Aishita.jpeg")
    s.wait_for("पैन कार्ड से मैंने पढ़ा", timeout=90); s.send("text", "1")
    s.wait_for("पासबुक")
    s.send("image", path=KYC / "passbook_Aishita.jpeg")
    s.wait_for("पासबुक से मैंने पढ़ा", timeout=90); s.send("text", "1")
    s.wait_for("पिकअप का पता भी है"); s.send("text", "1")
    s.wait_for("फोन अभी पास में है"); s.send("text", "1")
    s.wait_for("OTP लिख कर भेजें", timeout=60); s.send("text", "123456")
    s.wait_for("दुकान का खाता तैयार", timeout=90)

    print("\n[B2] print front → Layer 1 or Layer 2 must catch it")
    s.send("image", path=KYC / "print_front.jpeg")
    text = s.wait_for("पीछे की तरफ", "हाथ से बनी", "धुंधली", timeout=150)
    if "पीछे की तरफ" in text:
        print("\n[B3] print passed Layer 1 → sending the print's blank back")
        s.send("image", path=KYC / "print_back.jpeg")
        s.wait_for("हाथ से बनी", timeout=90)
        print("   → REJECTED at the challenge (Layer 2) ✅")
    else:
        print("   → REJECTED at Layer 1 (vision forensics) ✅")
    print("\nPHASE B COMPLETE ✅")


if __name__ == "__main__":
    assert client.get("/health").json()["ok"]
    which = sys.argv[1] if len(sys.argv) > 1 else "agb"
    if "a" in which:
        phase_a()
    if "g" in which:
        phase_gstin()
    if "b" in which:
        phase_b()
    print("\nACCEPTANCE DRIVE PASSED")
