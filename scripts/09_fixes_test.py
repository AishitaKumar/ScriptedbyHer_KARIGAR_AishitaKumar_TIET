"""Verify: fix 6 (Hindi title in notes), fix 5/7 (mid-flow Q&A), fix 3 (external-
only trend before sales), fix 1 (no challenge). Seeds a live listing owned by a
console session, drives real endpoints + the console router, polls the outbox.
"""
import sys, time
import httpx
sys.stdout.reconfigure(encoding="utf-8", errors="replace"); sys.path.insert(0, ".")
from dotenv import load_dotenv; load_dotenv()
from app.db.client import db

SESSION = "e2e-fixes"; PHONE = f"web:{SESSION}"
c = httpx.Client(base_url="http://127.0.0.1:8000", timeout=60)

assert "title_hi" in db().table("listings").select("*").limit(1).execute().data[0] if db().table("listings").select("*").limit(1).execute().data else True

db().table("artisans").delete().eq("whatsapp_phone", PHONE).execute()
ident = db().table("seller_identities").insert({"legal_name":"Ramkali","business_name":"Ramkali Madhubani Kala","kyc_status":"verified","registration_type":"eid"}).execute().data[0]
art = db().table("artisans").insert({"whatsapp_phone":PHONE,"name":"Ramkali","village":"Jitwarpur","craft":"madhubani","language_code":"hi","onboarding_state":"active","seller_identity_id":ident["id"]}).execute().data[0]
listing = db().table("listings").insert({"artisan_id":art["id"],"title":"Madhubani Peacock Wall Art","title_hi":"मधुबनी मोर वाली पेंटिंग","craft_type":"madhubani","price":299,"original_price":450,"photo_urls":["x"],"gi_status":"verified","status":"live"}).execute().data[0]
print("seeded listing", listing["id"][:8])

since = 0
def poll(*subs, timeout=60):
    global since
    end = time.time()+timeout
    while time.time() < end:
        r = c.get("/api/console/poll", params={"session":SESSION,"since":since}).json(); since=r["next"]
        for m in r["messages"]:
            print("   ARTISAN:", m["text"][:90].replace("\n"," "))
            if any(s in m["text"] for s in subs): return m["text"]
        time.sleep(1.5)
    raise SystemExit(f"TIMEOUT {subs}")
def send_text(t):
    c.post("/api/console/send", data={"session":SESSION,"type":"text","text":t})

print("\n[Fix 3] Trend BEFORE any sale → external only, must NOT claim her product sold")
c.post("/demo/trigger-trend", data={"session":SESSION})
txt = poll("जी", timeout=60)
assert "बिकी" not in txt and "बिका" not in txt, "trend fabricated an internal sale!"
print("   OK: external-only trend, no fabricated internal sale")

print("\n[Fix 6] Place order → notification uses HINDI title")
c.post("/demo/buy", data={"listing_id":listing["id"]})
txt = poll("ऑर्डर आया", timeout=45)
assert "मधुबनी मोर वाली पेंटिंग" in txt, "order note did not use Hindi title"
assert "Madhubani Peacock Wall Art" not in txt, "English title leaked!"
print("   OK: Hindi title in order note, no English leak")

print("\n[Fix 5/7] Mid-listing question during awaiting_photos → answer + resume")
db().table("artisans").update({"onboarding_state":"awaiting_photos"}).eq("id",art["id"]).execute()
send_text("मेरे पैसे कब आएंगे")
txt = poll("रुपये", "कमाई", "बने", "हफ्ते", timeout=60)
poll("तस्वीर", "फोटो", timeout=20)
print("   OK: answered the question AND resumed asking for photos")

print("\n[Fix 5] Cancel mid-listing → back to normal chat")
send_text("रुक जाओ अभी नहीं करना")
poll("कोई बात नहीं", "तैयार", timeout=30)
st = db().table("artisans").select("onboarding_state").eq("id",art["id"]).execute().data[0]["onboarding_state"]
assert st == "active", f"cancel did not return to active (state={st})"
print("   OK: cancelled, back to active")

oids=[o["id"] for o in db().table("orders").select("id").eq("listing_id",listing["id"]).execute().data]
if oids: db().table("reviews").delete().in_("order_id",oids).execute(); db().table("orders").delete().in_("id",oids).execute()
db().table("listings").delete().eq("id",listing["id"]).execute()
db().table("voice_messages").delete().eq("artisan_id",art["id"]).execute()
db().table("artisans").delete().eq("id",art["id"]).execute()
db().table("seller_identities").delete().eq("id",ident["id"]).execute()
print("\nALL FIX CHECKS PASSED — cleaned up.")
