# CLAUDE.md — Karigar (Meesho ScriptedByHer 2.0 hackathon)

Single source of truth: `KARIGAR_PROJECT_SPEC.md` — read it before any nontrivial work.
Solo builder. Deadline: **July 19, 2026**. Judges test the live deployment in real time.

## Decisions made (2026-07-15, with the builder)

- **Stack: Python 3.13 + FastAPI**, single container. rembg + Pillow for the Photo
  agent, ffmpeg (in Docker) for audio transcode, `asyncio.gather` for the parallel
  agent fan-out. Supabase (Postgres + storage). Frontends (Demo Console + listing
  page) served as static files from the same FastAPI app.
- **Deploy: GCP Cloud Run**, `--min-instances=1 --cpu-always-allocated` — required
  so background agent jobs survive after the webhook returns 200. Job queue is
  in-process asyncio behind an interface (Cloud Tasks is a swap, not a rewrite).
- **Pipeline parallelism:** Vision is the only sequential gate. After it, Photo
  enhancement ∥ (GI lookup → Story) ∥ Pricing run concurrently.

## HARD CONSTRAINTS (spec §5 — never violate, never propose alternatives)

- **OpenAI APIs only**: GPT-4o (text), GPT-4o Vision, Whisper STT, OpenAI TTS.
  No Google AI, Anthropic API, Azure, ElevenLabs. (GCP for *hosting* is fine.)
- OpenAI TTS Hindi is weaker than Google TTS — accepted tradeoff, document it,
  never switch providers.
- Languages: Hindi full pipeline + English listing output. বাংলা/தமிழ் buttons →
  graceful coming-soon. `language_code` threaded through the ENTIRE pipeline.
- Transports: Meta WhatsApp Cloud API (primary), Twilio sandbox (fallback, no
  buttons → every button needs a text/voice fallback), Web Demo Console — all
  behind one adapter interface, same orchestrator.
- Meesho price band ₹199–₹599 (max ~₹1700). Canonical listing: Madhubani ₹299
  (was ₹450). Not a luxury marketplace.
- Identity Anchor: PAN + bank + OTP phone must belong to ONE person. The
  onboarding partner never touches money. No payout unless
  `seller_identities.consistency_verified = true`.
- **Human approval gate: nothing auto-publishes. Ever.**
- Audio is async voice-note files (OGG/Opus) only — no live streaming.
- Authenticity claims: tuned for Madhubani (deep) + Warli (shallow). Claim
  exactly that. Terminology: GST **Enrolment ID (EID)** — never "UIN".
- Every DB write of user-provided data happens only AFTER explicit user
  confirmation. Every OpenAI call: retry (exp backoff, max 2) + graceful Hindi
  failure message, never a stack trace or silent drop.

## What is real vs. mocked (NESTED architecture — decided 2026-07-17)

Everything AI is REAL (Vision, Whisper, GPT-4o, TTS) — zero canned outputs.
**Karigar's code talks ONLY to `app/services/meesho.py`** (implemented by
`mocks/meesho_api`). Government verification is Meesho's backend: the Meesho
mock internally calls `mocks/gst_lookup` + `mocks/gst_enrolment`. Karigar never
imports GST mocks directly — grep before adding any such import.

1. `meesho_api` — `create_seller_account(payload) -> {seller_id,
   verification_status, enrolment_id?}` (GSTIN sellers verify instantly; EID
   sellers get otp_required → `confirm_seller_otp`), `lookup_gstin`,
   `createListing`, `updateListing`, `cancelPickup`, `get_category_comparables`,
   order-webhook simulator (`POST /demo/trigger-order`), payout simulator.
2. `gst_lookup` — 5 seeded GSTINs -> {legal_name, trade_name, business_type,
   registered_address}; no free official GST API exists (captcha-protected).
3. `gst_enrolment` — `submitEnrolment` / `confirmOtp -> {enrolment_id}`
   (15-char, ~2s delay, any 6-digit OTP ok).
4. `gi_registry` — hardcoded 10 GI crafts (Karigar-owned data, imported directly).

`services/email_alias.py` derives a REAL deliverable per-seller plus-address
(karigar.sellers+<slug>.<id4>@gmail.com) at runtime — never a stored constant.

**KYC runs BEFORE cataloging** (seller account first): GSTIN branch (instant,
no OTP) or EID branch (PAN → passbook → pickup address → OTP → EID). Typed
answers skip read-back confirmation; voice and OCR values are always confirmed.

README must contain the "Real vs. Mocked, and why" table.

## Build tiers (spec §13 — the clock cuts from the bottom)

**Tier 1 (demo dies without these, in order):** 1. Vision kill-shot script
(`scripts/01_vision_killshot.py`) — real Madhubani vs. factory print; if Vision
can't separate them the pitch pivots. 2. Pipeline Vision→Photo→Story→Pricing +
Supabase + all mocks. 3. Transport adapter + Whisper + confirmations + language
selector + onboarding state machine. 4. KYC / Identity Anchor + mock EID.
5. Preview → approval → Meesho-styled listing page. 6. Mock order → Hindi TTS
notification; "कितना कमाया?" round trip. 7. Back-of-painting challenge +
fake-print rejection. 8. Web Demo Console (with live agent-activity view).

**Tier 2:** 9. Trend agent (committed — must exist). 10. Returns classification
inside Distribution. 11. Photo clustering (ONE Vision call → JSON groups).

**Tier 3 (spare time only):** negotiation dialogue, Layer-3 process questions,
implicit photo-drop expansion, randomized challenge variants.

**Structural rule:** Tier 2/3 features live in their own modules behind flags,
independently removable WITHOUT touching Tier 1 paths. Out of time mid-feature →
abandon uncommitted, never half-wire into the demo path.

**Freeze rule:** final ~24h = rehearsal of the §14 acceptance test, backup demo
video, deployment checks, README polish. No new features.

## DO NOT BUILD (document only)

Bengali/Tamil working pipelines; real GST portal automation (Playwright roadmap
in README); duplicate-detection embeddings (Layer 4, pgvector design in docs);
behavioral signals (Layer 5); authenticity tuning beyond Madhubani + Warli.

## Repo layout

```
app/            FastAPI backend
  transports/   whatsapp_cloud, twilio, web_console + base adapter
  orchestrator/ GPT-4o function-calling router + DB-state injection
  flows/        onboarding state machine, kyc, operations
  agents/       vision, photo, story, pricing, distribution (returns inside), trend
  prompts/      every LLM prompt in its own versioned file — never inline strings
  voice/        whisper STT, TTS, transcode
  mocks/        meesho_api, gst_enrolment, gi_registry
  db/           supabase client, queries
  jobs/         asyncio queue (Cloud-Tasks-swappable)
web/            Demo Console + Meesho-styled listing page (static)
tests/          routing matrix, yes/no classifier, name-match, digit parsing, mocks
scripts/        standalone validation scripts (01_vision_killshot.py first)
docs/           pitch document, architecture diagram
```

## Testing focus (criterion 02)

Orchestrator routing (state × message-type matrix), confirm/deny classifier
(Hindi/English utterance table), Identity Anchor name-matching, pincode/OTP
spoken-digit parsing ("चार सात दो एक" → 4721), mock contracts. Integration test
with recorded fixtures. Don't chase coverage numbers.
