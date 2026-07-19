"""Voice-layer validation: TTS Hindi → Whisper → digit parsing round trips.

1. Synthesize a Hindi order notification (the spec's exact copy) → save OGG →
   transcribe it back with Whisper → eyeball fidelity.
2. Synthesize a spoken OTP "चार सात दो एक सात दो" → Whisper → parse_spoken_digits
   → must equal 472172 (spec: Hindi spoken-digit transcription must be
   specifically tested).
3. Run the yes/no classifier over a table of utterances.
"""

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from app.voice.classify import classify_yes_no, parse_spoken_digits  # noqa: E402
from app.voice.stt import transcribe  # noqa: E402
from app.voice.tts import speak  # noqa: E402

OUT = ROOT / "scripts" / "voice_out"

ORDER_MSG = (
    "खुशखबरी! आपकी मधुबनी पेंटिंग का ऑर्डर आया है। "
    "डिलीवरी वाले भैया कल इसे लेने आएंगे। कृपया इसे पैक करके रखें।"
)
OTP_SPOKEN = "ओ टी पी है चार सात दो एक सात दो"
OTP_EXPECTED = "472172"

YES_NO_TABLE = [
    ("हाँ ठीक है", "yes"), ("जी बिल्कुल कर दीजिए", "yes"), ("1", "yes"),
    ("अरे हाँ हाँ सही है", "yes"), ("theek hai haan", "yes"),
    ("नहीं रहने दो", "no"), ("ना ना मत करो", "no"), ("2", "no"), ("nahi", "no"),
    ("कीमत कितनी रखी है?", "unclear"), ("वो डिलीवरी वाला कब आएगा", "unclear"),
]


async def main() -> int:
    OUT.mkdir(exist_ok=True)
    failures = 0

    print("1) TTS order notification -> Whisper round trip")
    audio = await speak(ORDER_MSG)
    (OUT / "order_notification.ogg").write_bytes(audio)
    print(f"   voice note saved: {OUT / 'order_notification.ogg'} ({len(audio)//1024} KB) — LISTEN to judge Hindi quality")
    heard = await transcribe(audio)
    print(f"   sent : {ORDER_MSG}")
    print(f"   heard: {heard}")

    print("\n2) Spoken-OTP round trip")
    otp_audio = await speak(OTP_SPOKEN)
    (OUT / "otp.ogg").write_bytes(otp_audio)
    otp_heard = await transcribe(otp_audio)
    parsed = parse_spoken_digits(otp_heard, expected_length=6)
    ok = parsed == OTP_EXPECTED
    failures += 0 if ok else 1
    print(f"   spoken: {OTP_SPOKEN}")
    print(f"   heard : {otp_heard}")
    print(f"   parsed: {parsed}  [{'PASS' if ok else 'FAIL'} — expected {OTP_EXPECTED}]")

    print("\n3) Yes/No classifier table")
    for text, expected in YES_NO_TABLE:
        got = await classify_yes_no(text)
        ok = got == expected
        failures += 0 if ok else 1
        print(f"   [{'PASS' if ok else 'FAIL'}] '{text}' -> {got} (expected {expected})")

    print(f"\n{'ALL PASS' if failures == 0 else f'{failures} FAILURES'}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
