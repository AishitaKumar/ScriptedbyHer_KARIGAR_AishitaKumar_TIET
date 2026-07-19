"""Edge-case coverage across every decision point: irrelevant/unclear/wrong/
incomplete inputs at each step. Calls the real agents/validators (live LLM) with
the builder's real documents plus programmatic degradations (blur, crop, wrong
doc, blank). Prints a PASS/FAIL table; exits non-zero on any failure.
"""
import asyncio, io, json, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace"); sys.path.insert(0, ".")
from dotenv import load_dotenv; load_dotenv()
from PIL import Image, ImageFilter

from app.flows.common import validate_answer, names_match_smart
from app.flows import kyc
from app.flows.messages import set_lang
from app.agents import vision
from app.agents.distribution import classify_return
from app.llm import chat_json, load_prompt, VISION_MODEL, image_content

ROOT = Path(".")
KYC = ROOT / "test_images" / "kyc"
set_lang("hi")
results = []
def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  · {detail}" if detail else ""))

def jpg(img):
    b = io.BytesIO(); img.convert("RGB").save(b, format="JPEG", quality=85); return b.getvalue()
def blur(path, r=10):   return jpg(Image.open(path).filter(ImageFilter.GaussianBlur(r)))
def top_strip(path, frac=0.35):
    im = Image.open(path); w, h = im.size; return jpg(im.crop((0, 0, w, int(h*frac))))
def blank():            return jpg(Image.new("RGB", (900, 600), (238, 236, 232)))

async def ocr(prompt_name, img_bytes):
    return await chat_json(load_prompt(prompt_name),
        [{"type": "text", "text": "Read this document photo."}, image_content(img_bytes, "image/jpeg")],
        model=VISION_MODEL, what="test", temperature=0)

async def main():
    print("\n=== NAME validation (irrelevant / gibberish / valid) ===")
    for txt, want in [("नहीं बताऊंगी", False), ("asdfgh", False), ("रामकली देवी", True), ("मुझे नहीं पता", False)]:
        r = await validate_answer("name", txt, "hi")
        check(f"name {txt!r}", r.get("valid") == want, f"valid={r.get('valid')}")

    print("\n=== VILLAGE validation ===")
    for txt, want in [("नहीं", False), ("जितवारपुर, मधुबनी", True), ("पता नहीं", False)]:
        r = await validate_answer("village", txt, "hi")
        check(f"village {txt!r}", r.get("valid") == want, f"valid={r.get('valid')}")

    print("\n=== DIMENSIONS parsing (clear / unit-assumed / irrelevant) ===")
    for txt, want in [("बारह गुणा अठारह इंच", True), ("12 by 18 inches", True),
                      ("तीस सेंटीमीटर", True), ("नहीं पता", False), ("मौसम अच्छा है", False)]:
        r = await chat_json(load_prompt("parse_dimensions"),
                            json.dumps({"answer": txt, "language": "hi"}, ensure_ascii=False), what="t")
        check(f"dim {txt!r}", bool(r.get("valid")) == want, f"canonical={r.get('canonical')}")

    print("\n=== PHOTO authenticity (real / print / blurry / no-craft) ===")
    r = await vision.analyze_photo(open(KYC/"painting_front.jpeg","rb").read())
    check("real handmade → accepted", r.get("authenticity_verdict") in {"handmade","likely_handmade"}, r.get("authenticity_verdict"))
    r = await vision.analyze_photo(jpg(Image.open(ROOT/"test_images"/"print"/"print_1.png")))
    check("factory print → rejected/suspect", r.get("authenticity_verdict") in {"print","likely_print","suspect_downloaded_image"}, r.get("authenticity_verdict"))
    r = await vision.analyze_photo(blur(KYC/"painting_front.jpeg", 12))
    check("blurry art → quality fail", r.get("quality_score")=="fail" or r.get("authenticity_verdict")=="insufficient_evidence", f"q={r.get('quality_score')} v={r.get('authenticity_verdict')}")
    r = await vision.analyze_photo(blank())
    check("blank/no-craft → not accepted", r.get("quality_score")=="fail" or r.get("craft")=="none", f"craft={r.get('craft')} q={r.get('quality_score')}")

    print("\n=== PAN OCR (valid / blurry / wrong doc / random) ===")
    pan_req = ["name", "pan_number"]
    r = await ocr("ocr_pan", open(KYC/"pan_1.jpeg","rb").read())
    check("PAN valid → complete", kyc._doc_issue_message(r,"पैन","is_pan_card",pan_req) is None, f"name={r.get('name')}")
    r = await ocr("ocr_pan", open(KYC/"pan_blur.jpeg","rb").read())
    check("PAN blurry → retry", kyc._doc_issue_message(r,"पैन","is_pan_card",pan_req) is not None, f"issue={r.get('image_issue')}")
    r = await ocr("ocr_pan", open(KYC/"passbook_1.jpeg","rb").read())
    check("passbook-as-PAN → wrong doc", kyc._doc_issue_message(r,"पैन","is_pan_card",pan_req) is not None, f"is_pan={r.get('is_pan_card')}")
    r = await ocr("ocr_pan", open(KYC/"random_1.jpeg","rb").read())
    check("random img as PAN → wrong doc", kyc._doc_issue_message(r,"पैन","is_pan_card",pan_req) is not None, f"is_pan={r.get('is_pan_card')}")

    print("\n=== PASSBOOK OCR (valid / real cut photo / missing-IFSC logic / wrong doc / random) ===")
    req = ["name","account_number","ifsc"]
    r = await ocr("ocr_passbook", open(KYC/"passbook_1.jpeg","rb").read())
    check("passbook_1 → complete?", kyc._doc_issue_message(r,"पासबुक","is_passbook",req) is None,
          f"name={bool(r.get('name'))} acct={bool(r.get('account_number'))} ifsc={bool(r.get('ifsc'))}")
    r = await ocr("ocr_passbook", open(KYC/"passbook_cut.jpeg","rb").read())
    check("passbook_cut (incomplete) → ask complete photo", kyc._doc_issue_message(r,"पासबुक","is_passbook",req) is not None,
          f"issue={r.get('image_issue')} acct={r.get('account_number')} ifsc={r.get('ifsc')}")
    fake = {"is_passbook":True,"name":"AISHITA KUMAR","account_number":"110103722273","ifsc":None,"image_issue":"ok","confidence":92}
    check("passbook missing IFSC (logic) → ask complete", kyc._doc_issue_message(fake,"पासबुक","is_passbook",req) is not None, "ifsc=None")
    r = await ocr("ocr_passbook", open(KYC/"pan_1.jpeg","rb").read())
    check("PAN-as-passbook → wrong doc", kyc._doc_issue_message(r,"पासबुक","is_passbook",req) is not None, f"is_pb={r.get('is_passbook')}")
    r = await ocr("ocr_passbook", open(KYC/"random_2.jpeg","rb").read())
    check("random img as passbook → wrong doc", kyc._doc_issue_message(r,"पासबुक","is_passbook",req) is not None, f"is_pb={r.get('is_passbook')}")

    print("\n=== NAME cross-script match / GSTIN parse / returns ===")
    check("AISHTA≈आइशिता", await names_match_smart("AISHTA KUMAR","आइशिता कुमार") is True)
    check("Suresh≠Ramesh", await names_match_smart("Suresh Kumar","Ramesh Kumar") is False)
    check("GSTIN valid 15", kyc._parse_gstin("22AAAAA0000A1Z5") == "22AAAAA0000A1Z5")
    check("GSTIN short → None", kyc._parse_gstin("22AAAA") is None)
    for reason, want in [("customer not home","rto"), ("colours faded, not as shown","quality")]:
        v = await classify_return(reason)
        check(f"return {reason!r}→{want}", v["classification"]==want, v["classification"])

    n_fail = sum(1 for _,ok,_ in results if not ok)
    print(f"\n=== {len(results)-n_fail}/{len(results)} passed, {n_fail} failed ===")
    return 1 if n_fail else 0

sys.exit(asyncio.run(main()))
