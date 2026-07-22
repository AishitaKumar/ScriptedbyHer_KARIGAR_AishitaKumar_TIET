# Karigar — the artisan's only interface is their voice

**Meesho ScriptedByHer 2.0 · Build for Bharat with the power of Agentic AI**

Karigar turns a few WhatsApp photos and voice notes from a craftsperson — who may
not be able to read a form, type a description, or navigate an app — into a live,
authenticity-checked Meesho listing, and then runs their entire storefront by
voice: onboarding, KYC, orders, payouts, returns, and business coaching, all as
warm spoken messages in their own language.

---

## Live deployment

**Open the app → https://karigar-577066629459.asia-south1.run.app/v2**

That's the landing page. Click **Live Demo** to open the WhatsApp-style Demo
Console; the Meesho-styled shop is reachable from there too.

Hosted on **GCP Cloud Run** (`asia-south1`), always-on (`--min-instances 1
--no-cpu-throttling`) so background agent jobs finish after the webhook returns.
No login required.

### Demo walkthrough video (how to use)

**Watch → https://drive.google.com/file/d/1SYRpFxcxgZYc0oREhemL0XW4vM3DBdTx/view?usp=sharing**

Also available in-app: click **"How it works"** on the landing page.

### Test images for judges

**Folder → https://github.com/AishitaKumar/ScriptedbyHer_KARIGAR_AishitaKumar_TIET/tree/main/test_images**

A ready-made set for testing the pipeline and its safeguards: real handmade
artworks, fake/factory-print artworks, dummy PAN cards and bank passbooks
(including deliberately blurred and partially-cropped ones), and random
unrelated images — so you can try both the happy path and the adversarial cases.

> **Important — before entering a GSTIN in the prototype:** only specific
> seeded GSTINs verify (by design — random numbers will not work). Read
> **`https://drive.google.com/file/d/1rkprPwUa00EOZ7t-FwgEkVn46bGMHvMM/view?usp=sharing`** first for the valid GSTINs and
> why this is mocked this way.

---

## 01 · Project Core

### The problem
India has ~1.13 crore artisans, ~64% of them women, many earning around ₹270 a
day while middlemen take the majority of the retail value. Meesho's Project
Suraksha removed 52 lakh+ fake "handmade" listings — but the real artisans those
fakes imitate still aren't on the shelf. **The barrier is not willingness; it is
digital literacy.** Every seller platform assumes you can read a form, type a
product description, upload and crop photos, and manage an app. Many artisans can
do none of that — but every one of them has a phone with WhatsApp and can speak.

### The solution
Karigar removes the interface entirely. The artisan **speaks, in their language,
over WhatsApp** — a channel they already use. They send photos of their work and
a voice note; Karigar's agents do the rest and read everything back for spoken
confirmation before anything is saved or published. **Nothing is ever
auto-published — a human always approves.**

### AI model integration (single-vendor OpenAI stack)
| Capability | Model | Where |
|---|---|---|
| Craft ID, motif detection, authenticity forensics, document OCR | **GPT-4o Vision** | Vision agent, KYC |
| Voice-note transcription (every inbound audio) | **Whisper** | `app/voice/stt.py` |
| Intent routing, listing copy, pricing intricacy, returns, coaching | **GPT-4o** | orchestrator + agents |
| Every outbound message spoken back to the artisan | **gpt-4o-mini-tts** | `app/voice/tts.py` |
| Live category price comparables | **GPT-4o + `web_search` (Responses API)** | `app/services/market_prices.py` |

Everything AI is **real** — there are zero canned or hardcoded model outputs.

### The six agents
One orchestrator (GPT-4o function-calling) routes every message using the
sender's **database state** — a new number starts onboarding, a mid-KYC user
resumes at their exact step, an active seller gets natural-language intent
classification. No menus, ever.

| # | Agent | Input → Output | Tech |
|---|---|---|---|
| 1 | **Vision** | photo batch → craft, motifs, quality gate, authenticity score + provenance | GPT-4o Vision |
| 2 | **Photo** | raw photo → lighting cleaned up + sharpened (kept as shot) | Pillow (local, free) |
| 3 | **Story** | craft JSON + GI craft knowledge → Meesho-format title + Hindi/English description | GPT-4o |
| 4 | **Pricing** | craft JSON + live comparables → price, strike-through, **in-hand amount (computed in code, never by the LLM)** | GPT-4o |
| 5 | **Distribution** | listing package → live listing + the full order lifecycle: orders, payouts, returns, exchanges, reviews — voice-notifying on each | GPT-4o + mock Seller API |
| 6 | **Trend** | 7-day sales + returns/reviews from DB → bestseller/seasonal coaching voice note | GPT-4o + TTS |

_(Returns classification is one prompt folded inside Distribution, not a separate
service — hence six agents, not seven.)_

---

## 02 · Live deployment — how judges test it

From the landing page, click **Live Demo** to open the Demo Console. It is **not a
mock UI**: it is a real transport client speaking the exact same `InboundMessage`
contract, through the exact same orchestrator and agents, as the WhatsApp path.
Beside the chat, a **live agent-activity panel** shows every agent's raw JSON
output as it runs.

**Suggested run (end-to-end, all live):**
1. Click **Naya Karigar** → pick a language (हिंदी / English).
2. Give a name and village by voice or text — each is read back and confirmed.
3. **KYC first (seller account before cataloging):** send a PAN photo (name is
   OCR-anchored), then a passbook photo (name-matched to the PAN), a pickup
   pincode (parsed digit-by-digit), and an OTP → a mock GST **Enrolment ID** is
   issued. _Or_ type a GSTIN for the instant fast-path.
4. Send photos of a craft (e.g. a Madhubani painting) → watch Vision → Photo ∥
   Story ∥ Pricing run in the activity panel.
5. Give the size when asked → a price proposal card (e.g. **₹299**, ~~₹450~~,
   with the in-hand amount) → approve it.
6. Approve the preview → the listing appears live on **/v2/shop**.
7. Use the demo rail: **Order + Payment Received** → a Hindi voice note arrives;
   deliver → review → return/exchange, each voice-notified.
8. Ask **"कितना कमाया?"** by voice → earnings are computed from the DB and spoken.
9. **Adversarial:** onboard with a factory-print / downloaded image → rejected
   with the actual reason (provenance / not-a-craft), not a generic error.
10. **Agent activity** button → run **Trend** coaching → a spoken business tip.

Every confirmation card (PAN, passbook, GSTIN, pincode, OTP) is **read aloud with
each digit spoken individually** so numbers are never misheard.

> **Before entering a GSTIN:** only specific seeded GSTINs verify — see the
> **Test images for judges** note above for the valid list and the reasoning.

---

## 03 · Code & Setup

### Source code
Public repository: **https://github.com/AishitaKumar/ScriptedbyHer_KARIGAR_AishitaKumar_TIET**

### Run and verify locally
```bash
git clone <repo-url> && cd karigar
python -m venv .venv
.venv\Scripts\activate                 # Windows  (source .venv/bin/activate on macOS/Linux)
pip install -r requirements.txt

cp .env.example .env                    # fill OPENAI_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY
                                        # (WhatsApp/Twilio keys optional — Demo Console needs none)

# In the Supabase SQL editor, run in order:
#   app/db/schema.sql
#   app/db/migrations/002_artisan_context.sql  →  007_market_demand.sql
# In Supabase Storage, create a PUBLIC bucket named "media"

uvicorn app.main:app --port 8000
# open http://127.0.0.1:8000/v2/demo
```

### Test coverage
```bash
pytest                 # 60 unit tests
```
The suite covers the parts most likely to break under real, messy input:
orchestrator routing (state × message-type), the Hindi/English yes-no classifier,
Identity-Anchor name matching (incl. cross-script), spoken-digit parsing
(`"चार सात दो एक"` → `4721`, and the Whisper सात/साथ homophone), and every mock
contract. Standalone live-validation scripts:

| Script | What it proves |
|---|---|
| `scripts/01_vision_killshot.py` | authenticity: real Madhubani vs. factory print |
| `scripts/05_e2e_full.py` | full journeys: EID happy path, GSTIN fast-path, fraud rejection |
| `scripts/08_post_purchase_test.py` | order → delivery → review → return/exchange lifecycle |
| `scripts/13_edge_cases.py` | 31 adversarial inputs (blurry / irrelevant / half-cut / wrong docs) |

### Architecture
```
WhatsApp Cloud API ─┐
Twilio sandbox ─────┤→ Transport Adapter → 200 OK immediately → async Job Queue
Web Demo Console ───┘        (normalize)         │
                                                 ▼
                              ORCHESTRATOR (state-injected routing)
                               │                        │
                     Onboarding + KYC            Operations flows
                     state machines (DB)        (orders/earnings/returns)
                               │                        │
        Vision ──► [ Photo ∥ (GI lookup → Story) ∥ Pricing ] ──► preview
                               │                                    │
                        Supabase (Postgres + storage)      HUMAN APPROVAL GATE
                                                                    │
                                                        mock Meesho API → /shop
```
- **Vision is the only sequential gate** — Photo, Story, and Pricing fan out
  concurrently (`asyncio.gather`).
- **No conversation state in process memory** — every step lives in
  `artisans.onboarding_state` (+ a JSONB scratch context for unconfirmed values).
  Kill the server mid-KYC and the artisan resumes exactly where they left off.
  (The background job queue and console outbox are in-memory — see limitations.)
- **Every user-supplied fact is confirmed aloud before it is written** to a real
  column; typed values skip read-back, voice/OCR values never do.
- Every OpenAI call retries with exponential backoff (max 2), then degrades to a
  graceful spoken apology — never a stack trace, never a silent drop.
- Every LLM prompt is a **versioned file** in `app/prompts/` — no inline strings.
- Transports (WhatsApp, Twilio, Web Console) sit behind **one adapter interface**;
  the orchestrator is transport-agnostic.

### Repository map
```
app/
  agents/        vision, photo, story, pricing, distribution (returns inside), trend
  orchestrator/  state-injected GPT-4o router
  flows/         onboarding + KYC state machines, operations, messages (all copy)
  transports/    whatsapp_cloud, twilio_wa, web_console + shared adapter contract
  prompts/       every LLM prompt, versioned
  voice/         Whisper STT, TTS, confirm/deny + spoken-digit parsing
  services/      meesho (the ONLY seller-side surface Karigar calls), market_prices, email_alias
  mocks/         meesho_api, gst_lookup, gst_enrolment, gi_registry (swap-ready)
  db/            schema.sql, migrations 002–007, queries
  jobs/          async queue (Cloud-Tasks-swappable)
web_v2/          Demo Console, Meesho-styled shop, landing (static frontend)
tests/           60 unit tests
scripts/         01 kill-shot · 05 e2e · 08 post-purchase · 13 edge cases · …
deploy/          Cloud Run instructions
docs/            pitch document, architecture
```

---

## Real vs. Mocked, and why

**Everything AI is real** — GPT-4o Vision authenticity + OCR, Whisper on every
voice note, GPT-4o for intent/story/pricing/returns/trend, TTS on every reply.

| System | Status | Why |
|---|---|---|
| GPT-4o / Vision / Whisper / TTS | **REAL** | The core intelligence. Never mocked. |
| Photo enhancement (rembg + Pillow) | **REAL** (local) | Runs in-container, no API. |
| Supabase Postgres + storage | **REAL** | Live DB, live media URLs. |
| Live price comparables (web search) | **REAL** | OpenAI Responses `web_search`, cached. |
| WhatsApp Cloud API / Twilio | **BUILT** (adapter, not in live demo) | Real adapters behind the shared transport interface; they activate with a Meta test number + credentials. The **Web Demo Console** is the live transport for this demo. |
| Meesho Seller API | **MOCK** (`app/mocks/meesho_api.py`) | No public seller sandbox exists. Karigar's code talks **only** to `app/services/meesho.py`; the mock is the swap point. |
| GST lookup + enrolment | **MOCK** (`app/mocks/gst_*.py`) | The GST portal is captcha-protected with no public API. Called **inside** the Meesho mock ("Meesho's backend"), never by Karigar directly. Production path: Playwright form-filler pausing at OTP (documented). |


Each mock sits behind a swap-ready interface marked `TODO: replace with real
integration`.

---

## The Authenticity Engine (what stops fake sellers)

Two checks run live in the pipeline; the rest is a documented roadmap.

**Built and live:**
1. **Vision forensics + image provenance** — GPT-4o Vision looks for the tells of a
   hand (brush strokes, pigment pooling, ink-density variation, line wobble) and
   the machine's giveaway (flat ink, halftone/moiré, CMYK rosettes). It separately
   judges **provenance**: a watermarked, perfectly-cropped, studio-flat image is a
   downloaded scan, not a phone photo of a physical object, and is rejected
   regardless of how handmade the depicted art looks. A framing gate also rejects
   photos that don't clearly show the front of the finished piece. This is the
   primary gate.
2. **Same-artwork guard** — when a seller changes the photo on a listing, a second
   Vision pass checks the new photo is the **same physical piece**, so a different
   artwork can't be quietly substituted onto an existing listing.

**Honest caveat:** this raises the cost of faking; it does not make it impossible.
A fraudster who owns one real painting can still pass onboarding. Validation:
`scripts/01_vision_killshot.py` separates real Madhubani photos from print-seller
images; tuned primarily for **Madhubani** (with Warli), while the pipeline itself
handles whatever craft the Vision agent identifies.

**Designed, not built (see Future work):** cross-seller duplicate detection
(pgvector embeddings) and behavioral-signal checks. A back-of-piece challenge was
prototyped earlier but is not wired into the current flow.

---

## The Identity Anchor (KYC that survives messy family credentials)

Each seller gets their own GST-portal **Enrolment ID** (the mechanism Meesho uses
for non-GST sellers) — no shared GSTIN. One rule, enforced in code: **PAN + bank
account + OTP phone must belong to the same one person.** PAN OCR anchors the
name; the passbook is name-checked against it; a mismatch triggers diagnosis and
re-anchoring, never a dead end. No payout path exists unless
`seller_identities.consistency_verified = true`. The onboarding partner never
touches money — when the artisan owns their full document set, payouts land
directly with them.

---

## Known limitations (deliberate scope)

- Only **Hindi (full pipeline) + English (listing output)** are live today; other
  languages are a translation effort, not new architecture, since `language_code`
  threads through the whole pipeline (STT → agents → TTS → copy). The voice loop
  is single-vendor OpenAI — a deliberate choice for one auth/latency and a
  tone-steerable voice over mixing in Google TTS; OpenAI's weaker Hindi number
  pronunciation is handled in code by spelling identifiers
  (account/IFSC/pincode/OTP) digit-by-digit before they are spoken.
- The in-process job queue and console outbox mean a single Cloud Run instance
  (`--max-instances 1`); the production swap is Cloud Tasks + Redis.

---

## Future work

The architecture was built so each of these is an extension, not a rewrite.

**1. More languages.** `language_code` is already threaded through the entire
pipeline (STT → agents → TTS → copy), so adding **Bengali and Tamil** — then the
other major Indian languages — is prompts + message copy, not engineering. A graceful coming-soon already handles requests for other languages.

**2. Real GI authentication.** Today the GI craft knowledge is a curated table
and authenticity is Vision forensics. Next is a genuine **GI verification
process**: integrating with GI registry / cooperative data to confirm a seller
belongs to a recognised GI cluster, and completing Authenticity Engine Layers
4–5 — **duplicate detection** (pgvector embedding match across sellers, since
handmade pieces are never pixel-identical) and **behavioral signals** (volume
anomaly caps, geo consistency, return-reason feedback, SHG/NGO attestation).

**3. Production hardening — swap the mocks for real APIs.** Every external
boundary already sits behind a swap-ready interface:
- **Meesho Seller API** in place of the mock, once a registered seller account is
  provisioned (Karigar's code only ever calls `app/services/meesho.py`).
- **GST portal** enrolment via the documented Playwright form-filler that pauses
  at the real OTP step, replacing the mock enrolment.
- **Cloud Tasks + Redis** for the job queue and outbox, lifting the single-instance
  limit to horizontal scale.
- **WhatsApp Cloud API at scale** (beyond the test number's whitelist), plus
  observability, rate-limit handling, and cost monitoring for the OpenAI calls.

---

## 04 · Open-source attribution

Every third-party dependency, its license, how it is used, and where it comes
from. All are used as **direct, unmodified** library integrations.

| Library | Version | License | Role in the build | Source |
|---|---|---|---|---|
| FastAPI | ≥0.115 | MIT | HTTP framework (webhooks, console API, static hosting) | https://github.com/fastapi/fastapi |
| Uvicorn | ≥0.32 | BSD-3-Clause | ASGI server | https://github.com/encode/uvicorn |
| OpenAI Python SDK | ≥1.60 | Apache-2.0 | GPT-4o / Vision / Whisper / TTS client | https://github.com/openai/openai-python |
| supabase-py | ≥2.10 | MIT | Postgres + storage client | https://github.com/supabase/supabase-py |
| Pillow | ≥11.0 | MIT-CMU (HPND) | Image enhancement (Photo agent) | https://github.com/python-pillow/Pillow |
| rembg | ≥2.0.60 | MIT | Background removal (Photo agent) | https://github.com/danielgatis/rembg |
| onnxruntime | ≥1.20 | MIT | rembg model runtime | https://github.com/microsoft/onnxruntime |
| httpx | ≥0.27 | BSD-3-Clause | Async HTTP (Graph/Twilio APIs, tests) | https://github.com/encode/httpx |
| python-dotenv | ≥1.0.1 | BSD-3-Clause | Environment loading | https://github.com/theskumar/python-dotenv |
| python-multipart | ≥0.0.12 | Apache-2.0 | Console file uploads | https://github.com/Kludex/python-multipart |
| pytest | ≥8.3 | MIT | Test runner | https://github.com/pytest-dev/pytest |
| pytest-asyncio | ≥0.24 | Apache-2.0 | Async test support | https://github.com/pytest-dev/pytest-asyncio |
| ffmpeg (system, in Docker) | 7.x | LGPL-2.1+ | Audio container safety net (OGG/Opus) | https://ffmpeg.org |
| Tailwind CSS (CDN, frontends) | 3.x | MIT | Demo Console / shop / landing styling | https://github.com/tailwindlabs/tailwindcss |

**Models & platforms:** OpenAI GPT-4o, GPT-4o Vision, Whisper, gpt-4o-mini-tts
(commercial API) · Supabase (Postgres + storage) · Google Cloud Run (hosting). The `u2net` background-removal model shipped via rembg is
MIT-licensed.
