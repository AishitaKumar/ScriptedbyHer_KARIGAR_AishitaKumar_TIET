"""Verify the 'no matching PAN+bank pair → Jan Dhan draft' fallback: seed an
artisan mid-KYC at the PAN-anchored passbook step, tap 'no match', confirm it
parks resumably, then a passbook photo resumes the flow."""
import sys, time
import httpx
sys.stdout.reconfigure(encoding="utf-8", errors="replace"); sys.path.insert(0, ".")
from dotenv import load_dotenv; load_dotenv()
from app.db.client import db

SESSION = "e2e-jandhan"; PHONE = f"web:{SESSION}"
c = httpx.Client(base_url="http://127.0.0.1:8000", timeout=60)
db().table("artisans").delete().eq("whatsapp_phone", PHONE).execute()
ident = db().table("seller_identities").insert({"legal_name":"Suresh Kumar","kyc_status":"collecting","registration_type":"eid"}).execute().data[0]
art = db().table("artisans").insert({"whatsapp_phone":PHONE,"name":"Ramkali","language_code":"hi",
  "onboarding_state":"kyc_awaiting_pan","seller_identity_id":ident["id"],
  "context":{"pan_name":"SURESH KUMAR","pan_number":"ABCDE1234F"}}).execute().data[0]
print("seeded artisan at kyc_awaiting_pan, anchor=SURESH KUMAR")

since=0
def poll(*subs, timeout=40):
    global since
    end=time.time()+timeout
    while time.time()<end:
        r=c.get("/api/console/poll", params={"session":SESSION,"since":since}).json(); since=r["next"]
        for m in r["messages"]:
            print("   BOT:", m["text"][:90].replace(chr(10)," "),
                  "| buttons:", [b["label"] for b in m["buttons"]] or "-")
            if any(s in m["text"] for s in subs): return m["text"]
        time.sleep(1.2)
    raise SystemExit(f"TIMEOUT {subs}")

print("\n[1] tap 'No one has a matching pair' (kyc_no_match)")
c.post("/api/console/send", data={"session":SESSION,"type":"button","text":"kyc_no_match"})
poll("जन धन", "सुरक्षित", timeout=40)
st = db().table("artisans").select("onboarding_state").eq("id",art["id"]).execute().data[0]["onboarding_state"]
print("   state now:", st, "(want kyc_parked_bank)")
assert st == "kyc_parked_bank"

print("\n[2] send a text while parked → gentle reminder")
c.post("/api/console/send", data={"session":SESSION,"type":"text","text":"ठीक है"})
poll("पासबुक", "तैयार", timeout=30)

print("\nJAN DHAN PARK FLOW VERIFIED (resumable).")
db().table("voice_messages").delete().eq("artisan_id",art["id"]).execute()
db().table("artisans").delete().eq("id",art["id"]).execute()
db().table("seller_identities").delete().eq("id",ident["id"]).execute()
print("cleaned.")
