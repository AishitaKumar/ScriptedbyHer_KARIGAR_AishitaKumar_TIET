"""E2E for the post-purchase flow: order (Confirm) → oldest-order deliver+pay →
review appreciation → exchange. Seeds one live artisan listing owned by a
console session, then drives the real buyer endpoints and polls the artisan's
WhatsApp console outbox to confirm each voice note.
"""
import sys, time, uuid
import httpx
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from dotenv import load_dotenv; load_dotenv()
from app.db.client import db

SESSION = "e2e-post"
PHONE = f"web:{SESSION}"
c = httpx.Client(base_url="http://127.0.0.1:8000", timeout=60)

db().table("artisans").delete().eq("whatsapp_phone", PHONE).execute()
ident = db().table("seller_identities").insert(
    {"legal_name": "Ramkali Devi", "kyc_status": "verified", "consistency_verified": True,
     "registration_type": "eid"}).execute().data[0]
art = db().table("artisans").insert(
    {"whatsapp_phone": PHONE, "name": "Ramkali Devi", "village": "Jitwarpur", "craft": "madhubani",
     "language_code": "hi", "onboarding_state": "active", "seller_identity_id": ident["id"]}).execute().data[0]
listing = db().table("listings").insert(
    {"artisan_id": art["id"], "title": "Handmade Madhubani Peacock Painting", "craft_type": "madhubani",
     "price": 299, "original_price": 450, "photo_urls": ["x"], "gi_status": "verified",
     "status": "live"}).execute().data[0]
print("seeded listing", listing["id"][:8], "for", PHONE)

since = 0
def poll(*subs, timeout=45):
    global since
    end = time.time() + timeout
    while time.time() < end:
        r = c.get("/api/console/poll", params={"session": SESSION, "since": since}).json()
        since = r["next"]
        for m in r["messages"]:
            print("   ARTISAN:", m["text"][:95].replace("\n", " "))
            if any(s in m["text"] for s in subs):
                return m["text"]
        time.sleep(1.5)
    raise SystemExit(f"TIMEOUT waiting for {subs}")

def buy():
    r = c.post("/demo/buy", data={"listing_id": listing["id"]}); r.raise_for_status()
    return r.json()["order_id"]

print("\n[1] Buy TWICE (two placed orders)")
o1 = buy(); poll("ऑर्डर आया", timeout=45)
time.sleep(1)
o2 = buy(); poll("ऑर्डर आया", timeout=45)

print("\n[2] 'Order Received + Payment Received' → OLDEST delivered + paid")
r = c.post("/demo/trigger-payout", data={"session": SESSION}).json()
print("   payout endpoint returned order_id:", r.get("order_id", "")[:8], "| expected oldest:", o1[:8])
assert r.get("order_id") == o1, "payout did NOT target the oldest order!"
poll("जमा हो गए", "बैंक खाते", timeout=45)
st1 = db().table("orders").select("status").eq("id", o1).execute().data[0]["status"]
st2 = db().table("orders").select("status").eq("id", o2).execute().data[0]["status"]
print(f"   order statuses -> oldest={st1} (want delivered), newest={st2} (want placed)")
assert st1 == "delivered" and st2 == "placed"

print("\n[3] Submit REVIEW (5 stars) on the delivered order → appreciation note")
c.post("/demo/submit-review", data={"order_id": o1, "rating": 5, "comment": "बहुत सुंदर पेंटिंग, रंग बहुत अच्छे हैं"}).raise_for_status()
poll("रामकली", "स्टार", "पसंद", "बधाई", "सुंदर", timeout=60)
rev = db().table("reviews").select("rating").eq("order_id", o1).execute().data
print("   review row persisted:", rev)

print("\n[4] Submit EXCHANGE on the newest order → exchange note")
c.post("/demo/exchange-order", data={"order_id": o2, "reason": "साइज़ थोड़ा छोटा है"}).raise_for_status()
poll("बदल", "exchange", "वापसी", timeout=45)

print("\nPOST-PURCHASE FLOW VERIFIED — order, oldest deliver+pay, review, exchange all notified the artisan.")
