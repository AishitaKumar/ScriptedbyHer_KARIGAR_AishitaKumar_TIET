# KARIGAR — Complete Project Specification for Claude Code

> **How to use this file:** This is the single source of truth for the Karigar prototype, built for the Meesho **ScriptedByHer 2.0** hackathon. Read it fully before writing any code. Help the builder plan first, then build. If anything in here is ambiguous, contradictory, or technically wrong, say so explicitly before proceeding — do not silently choose an interpretation. The builder is **solo**, the deadline is **July 19, 2026**, and the only paid API available is **OpenAI**.

---

## 1. THE PROBLEM

India has ~1.13 crore artisans — Madhubani painters, Kutch embroiderers, Channapatna toy makers. 64% are women. Most earn around ₹270/day, below minimum wage in every Indian state.

Meesho removed 52 lakh+ fake craft listings under Project Suraksha — factory prints pretending to be handmade. But the real artisans those fakes copied are still not on Meesho. The shelf was cleared and never refilled with the genuine article.

The barrier is not skill; it is digital:
- Many artisans cannot read or write, in any language, on a phone.
- Many use keypad phones, or a smartphone belonging to a family member.
- Every seller platform assumes you can read a form, type a product description, research competitor pricing, and manage orders. They can do none of that. So they sell to passing tourists for ₹50 while a middleman takes ~60% of retail value.

**The single insight the whole product rests on:**
> The artisan must never have to read, type, or learn an app. Her only interface is her **voice**, in **her own language**, over **WhatsApp — on a phone she already has.**

## 2. THE SOLUTION

Karigar is an **agentic AI system** that turns a few WhatsApp photos and voice notes into a live, GI-verified Meesho listing, with **zero literacy required from the artisan**, and then runs her storefront (orders, payouts, returns, coaching) entirely through voice.

Two-sided interaction model:
- **Onboarding partner** (NGO/SHG worker or family member — NOT a Meesho employee; Meesho has no rural field network) operates WhatsApp during onboarding while the artisan speaks.
- **The artisan herself** owns the ongoing relationship: she receives voice notes in Hindi and replies by voice only. There is NO numbered 1/2/3 menu for her — she speaks naturally ("कितना कमाया मैंने?") and the orchestrator infers intent.

---

## 3. HACKATHON SUBMISSION REQUIREMENTS (verbatim from organizers — these are hard requirements)

**01 Project Core**
- Description: clear overview of the problem, proposed solution, and AI model integration details.
- Presentation: pitch deck or document outlining the overall business concept and technology.

**02 Live Deployment**
- Live Demo: accessible URL of the deployed application or a hosted running instance.
- Interactivity: ensure judges can test core interactions, workflows, and view model responses directly.

**03 Code & Setup**
- Source Code: link to public repository (GitHub/GitLab) with complete project code.
- README Guide: detailed setup file with clear instructions on how to run and verify the codebase locally.

**04 Open-Source Attribution**
- For every library, framework, or tool used, declare: Name & version, License type (MIT, Apache 2.0, GPL v3, etc.), Role in your build (direct integration, modified code), Source link to the original project.

## 4. EVALUATION CRITERIA (verbatim from organizers — optimize for these)

**01 Working Prototype** — Functional & bug-free MVP. Core features implemented, **not mocked or hardcoded**. Judges should be able to run and test the prototype.

**02 Code Quality & Architecture** — Clean & modular code. Well-structured architecture, proper readme.md documentation. Test coverage and coding best practices.

**03 Usability & User Experience** — Intuitive & user-friendly. Well-designed for the target user. Smooth navigation and interaction flows.

**04 Completeness** — End-to-end coverage. All key features built, complete user flows. Not just a partial demo or a single screen.

### 4a. CRITICAL INTERPRETATION — "not mocked or hardcoded" vs. our necessary mocks

This tension must be handled deliberately, in code and in the README:

- **Everything AI is real.** GPT-4o Vision authenticity analysis, Whisper transcription, GPT-4o intent classification, story/pricing generation, TTS voice notes — all real API calls, zero canned responses, zero hardcoded outputs. This is the "core" the criteria refer to, and none of it may be faked.
- **Only externally-inaccessible systems are mocked**, and each mock exists because real access is impossible for anyone outside those organizations:
  1. **Meesho Seller API** — requires a registered seller account; no public sandbox exists.
  2. **GST portal enrolment** — a web form with no API; requires real PAN + real OTP.
  3. **GI registry** — no API exists anywhere; replaced by a curated lookup table.
- Each mock: lives in a `mocks/` directory, mimics the real request/response shape, sits behind a clean interface (swap-ready), and carries a `TODO: replace with real integration` comment plus a README section explaining exactly why it is mocked. The README must contain a table: "Real vs. Mocked, and why."
- **Judges must be able to test everything themselves** (requirement 02). Since WhatsApp Cloud API test mode limits recipients to ~5 whitelisted numbers, judges cannot easily message the bot. Therefore build a **web-based Demo Console** (see §12) that exercises the identical backend through the identical orchestrator — same code path, different transport. The console is not a mock; it is a second real client.

---

## 5. HARD CONSTRAINTS — never violate, never propose alternatives

- **OpenAI APIs only.** GPT-4o (text), GPT-4o Vision, Whisper (STT), OpenAI TTS. The builder has an OpenAI API key and nothing else paid. Do not propose Google Cloud, Anthropic API, Azure, ElevenLabs, or any other paid service.
- **Known accepted limitation:** OpenAI TTS Hindi is passable but weaker than Google TTS; Bengali/Tamil TTS is rough. This is a deliberate tradeoff — acknowledge it in docs, do not switch providers.
- **Languages:** Hindi (artisan-facing, full pipeline) + English (listing output; Meesho auto-translates for buyers in production). The onboarding language selector shows हिंदी | বাংলা | தமிழ் buttons; tapping বাংলা or தமிழ் returns a graceful "यह भाषा जल्द आ रही है" style message. `language_code` must be a parameter threaded through the ENTIRE pipeline so adding a language later is config, not engineering. Do NOT claim "listings written natively in 20 regional languages."
- **WhatsApp transport:** Primary = **Meta WhatsApp Cloud API free developer/test mode** (test phone number, up to 5 whitelisted recipients, interactive reply buttons work inside the 24-hour session window). Fallback = **Twilio WhatsApp Sandbox** (free; NO buttons/cards/menus render, so every button interaction needs a text fallback: bot phrases prompts as "हाँ बोलें या 1 भेजें" and accepts a typed digit/word or a voice yes/no). Build the transport as an adapter interface so both (plus the web Demo Console) plug into the same orchestrator.
- **Pricing reality:** Meesho is price-sensitive — most products ₹199–₹599, max ~₹1700. The villain is the middleman's ~60% cut, not a platform price ceiling. Canonical example listing: Madhubani painting, ₹299 (was ₹450, 33% off). Do NOT model this as a luxury marketplace.
- **Payments/compliance:** see the Identity Anchor model (§8). The onboarding partner NEVER touches money. No payout path may exist to anyone outside the verified seller identity.
- **Human approval gate:** nothing auto-publishes. A human taps/says yes on the listing preview before anything goes live. Hard requirement.
- **Audio is strictly asynchronous:** all voice interaction is recorded WhatsApp voice-note files (OGG/Opus) processed by Whisper. There is no live microphone streaming anywhere in this architecture.
- **Craft scope:** the system is **craft-agnostic by construction** (Vision prompt + GI table cover ~10 GI crafts), but authenticity detection is **tuned and validated for Madhubani painting** (primary) and **Warli painting** (secondary, shallow validation). Claim exactly that — no more.

---

## 6. THE AGENTS

Seven specialized agents coordinated by an **Orchestrator**. The Orchestrator is NOT one of the seven.

| # | Agent | Input | Output | Tech |
|---|-------|-------|--------|------|
| 1 | **Vision** | Photo batch | `{craft, style, motifs[], quality_score, authenticity_score, authenticity_verdict, reasons[]}` per image + clustering groups | GPT-4o Vision |
| 2 | **Photo** | Raw photo + craft JSON | Enhanced image (background cleanup, brightness) + pass/fail quality gate | rembg + sharp (local, free) |
| 3 | **Story** | Craft JSON + GI lookup result | Meesho-format title + description (English/Hindi base) | GPT-4o text |
| 4 | **Pricing** | Craft JSON + category comparables | Recommended price, strike-through original price, artisan's in-hand amount after deductions | GPT-4o text |
| 5 | **Distribution** | Full listing package | (Mock) live listing ID + order webhook; notifies artisan by voice on every order; **includes returns classification** (see below) | Mock Meesho API |
| 6 | **Returns** (folded INTO Distribution — not a separate module boundary, one classification prompt inside Distribution) | Return reason text | `{classification: rto|quality|other, rating_protected: bool}` + gentle reassuring Hindi voice note | GPT-4o text |
| 7 | **Trend** | 7-day sales + returns data from DB | Bestseller identification, seasonal advice (e.g., Diwali prep), constructive returns feedback — as Hindi voice note + text | GPT-4o text + OpenAI TTS |

- **Orchestrator:** GPT-4o function calling. Routes every inbound message (text/audio/image/button-reply) to the right flow. Its prompt is injected with `CURRENT_DATABASE_STATE` for the sender (new user vs. mid-onboarding step vs. active seller) to guarantee mutually exclusive intent routing — e.g., an active seller sending 3 photos out of nowhere routes to `add_new_listing`, while a brand-new number sending a photo routes to onboarding.
- **Voice intake:** Whisper transcribes all voice notes. Confirm/deny intent classification (हाँ / नहीं / 1 / ठीक है / सही है …) is one small GPT-4o call used everywhere a button has a fallback.
- Only Agent #1 uses GPT-4o Vision. Agents 3, 4, 6, 7 use plain GPT-4o text. Never route text-only calls through the Vision model.

---

## 7. THE AUTHENTICITY ENGINE (anti-fake-seller defense)

**Threat model:** middlemen or factory-print traders onboarding "as artisans" through this exact flow — the same fraud Project Suraksha cleaned up. Defense is layered; each layer is cheap for a real artisan, expensive for a faker. Authenticity is a **continuous score, not a one-time gate**.

**Layer 1 — Vision forensics (BUILD, core).** The Vision agent's prompt scores authenticity signals: visible brush strokes and pigment pooling vs. flat uniform ink; natural asymmetry and hand-drawn line wobble vs. pixel-perfect repetition; canvas/paper texture; halftone dots or moiré patterns (dead giveaway of a print); edge bleed. Factory prints are *too perfect* — the machine's tell is the absence of human variance. Output: `authenticity_score` 0–100 + `reasons[]` in plain language. The agent is explicitly prompted to NEVER guess when uncertain; low confidence → ask for more photos, not a verdict.

**Layer 2 — Challenge-response photo (BUILD, core).** Defeats pre-prepared stock images (liveness-check principle). During onboarding, after the initial batch passes Layer 1, the bot issues ONE randomized physical challenge:
- "अब पेंटिंग के **पीछे की तरफ** की फोटो भेजिए" — a hand-painted piece's back shows pigment bleed-through and raw canvas; a print's back is blank poster paper. (Primary challenge; build this one.)
- Variants for randomization (stretch): macro shot of a randomly named corner (checked for motif continuity with the wide shot + close-range brushwork); piece held in hand in the artisan's environment.
The Vision agent evaluates the challenge photo specifically against the expected physical evidence. Fail → polite rejection with reason, no listing.

**Layer 3 — Process interrogation by voice (STRETCH, one prompt).** 2–3 craft-specific questions pulled from the GI table's tradition metadata (e.g., Madhubani: "काला रंग किस चीज़ से बनाती हैं?" — soot/kajal; "यह भरनी शैली है या कचनी?"). Whisper transcribes; GPT-4o scores answers against known process knowledge. Soft signal, combined with Layer 2.

**Layer 4 — Duplicate detection (DO NOT BUILD — document only).** Embed every incoming photo; near-exact matches across sellers flag factory prints (handmade pieces are never pixel-identical). pgvector design documented in README/deck as production roadmap.

**Layer 5 — Behavioral signals (DO NOT BUILD — document only).** Geo-consistency (craft vs. pincode — soft flag only, artisans migrate), volume anomaly caps (a hand-painter cannot fulfill 300 orders/week), return-reason feedback ("printed/not handmade" lowers seller authenticity score), NGO/SHG partner attestation as the human trust layer.

**Demo money-shot (must work):** onboard with real Madhubani photos → passes → then attempt with a factory-print image → bot issues the back-of-painting challenge → blank white back sent → **rejection with a stated reason**. This 30-second sequence is the answer to "what stops fake sellers?"

**Honest caveat (state in docs):** this raises the cost of faking; it does not make it impossible. A fraudster owning one real painting can pass onboarding — Layers 4–5 catch that pattern over time.

---

## 8. THE IDENTITY ANCHOR MODEL (KYC that survives messy family credentials)

**Design decision:** Karigar does NOT hold a shared seller GSTIN (misuse risk; single legal point of failure). Each seller gets their own GST-portal **Enrolment ID (EID)** — the mechanism Meesho actually uses since October 2023 to onboard non-GST-registered sellers for intra-state sales. Terminology: it is an **Enrolment ID**, NOT a "UIN" (UIN is a different GST instrument for embassies/UN bodies — never use that term).

**The goal is that the artisan earns.** Whose account the family routes money through is their decision, not the system's. The system enforces exactly ONE rule:

> **PAN + bank account + OTP phone must all belong to the same one person** — the "seller of record." May be the artisan herself, her husband, or another family member.

**Flow (documents come AFTER cataloging — product first establishes value before high-friction KYC):**
1. **PAN first — it becomes the anchor.** "सबसे पहले पैन कार्ड की फोटो भेजें — जिसके नाम से दुकान चलेगी, उसका पैन।" → GPT-4o Vision OCR → name + PAN number → **micro-confirmation**: "पैन कार्ड पर नाम सुरेश कुमार है, सही है?" Confirmed name = anchor. Every later document is name-checked against it.
2. **Passbook.** "अब उसी नाम की बैंक पासबुक के पहले पन्ने की फोटो भेजें।" → OCR holder name (checked vs. anchor), account number, IFSC → **micro-confirmation on account number, last 4 digits read back**: "खाता नंबर के आखिरी 4 अंक 4 7 2 1 हैं, सही है?" A wrong bank account is the single most damaging OCR error possible — never save unconfirmed.
   - **Mismatch → diagnose, don't reject:** "पैन सुरेश जी का है, पर पासबुक रामकली जी की है। मीशो के नियम से दोनों एक ही इंसान के होने चाहिए। किसके पास पैन और बैंक खाता, दोनों अपने नाम के हैं?" → re-anchor on whoever has the complete set.
   - **No complete set in the family:** listing parks as `status = draft`; bot guides toward a zero-balance Jan Dhan account in the PAN-holder's name (opens in ~a day with Aadhaar) and notifies the NGO/SHG partner. Work saved, nothing lost.
3. **Address + pincode.** Pincode captured digit-by-digit by voice, read back digit-by-digit ("आठ-चार-सात-दो-एक-चार। सही है?"), stored as a separate structured field. Then the rest of the address by voice note, transcribed, read back once, confirmed.
4. **OTP-device pre-check (BEFORE submission, not after):** the enrolment OTP goes to the anchor's PAN-linked phone, which may not be the WhatsApp device. Bot asks: "OTP सुरेश जी के पैन से जुड़े फोन नंबर पर आएगा। क्या वह फोन अभी पास में है?"
   - Yes → submit (mock); OTP arrives; partner sends it via Gboard SMS-autofill tap OR reads it aloud as a **voice note** (Whisper transcribes the Hindi digits; bot reads back for confirmation before submitting). Hindi spoken-digit transcription ("चार सात दो एक" → 4721) must be specifically tested.
   - No → do NOT submit. Save the complete validated application as `kyc_status = awaiting_otp_device`. "कोई बात नहीं। जब वह फोन पास हो, बस 'OTP' लिख कर भेज दीजिएगा — हम वहीं से शुरू करेंगे।" Resumable state; in a village the PAN-holder's phone may be away at work all day.
5. **EID issued (mock):** `mocks/gst_enrolment` receives payload + OTP, waits ~2s, returns a realistic 15-character Enrolment ID → saved to `seller_identities.enrolment_id`, `kyc_status = verified`.

**Production path (document in README, do not build):** the GST enrolment form has no API. Real integration = a Playwright browser-automation worker that fills the form and pauses at the human OTP step, OR an early-operations back-office human submitting the pre-validated application (~2 minutes because the agent already collected, OCR'd, and confirmed everything). The agent's real job — turning a voice conversation and two photos into a portal-ready, error-free application — is fully built.

**Relationship design:** regardless of whose documents anchor the account, the **artisan remains the user** — all voice notifications, order alerts, earnings summaries, and Trend coaching address HER, in her language, on her chat. The seller-of-record is a payments/compliance detail. When the artisan is a woman with her own complete document set, payouts land directly with her — an emergent property of the same rule, not a separate gate. (This framing matters: the hackathon is ScriptedByHer; keep the women-empowerment narrative as the emergent outcome, and the inclusive engineering as the mechanism.)

---

## 9. COMPLETE CONVERSATION FLOWS (exact copy — implement these strings)

Every bot message is sent as **voice note (OpenAI TTS) + matching Devanagari text**. Every button has a sandbox/text fallback ("…के लिए 1 भेजें, या 'हाँ' बोलें").

### 9.1 Onboarding — initiation & identity
1. Partner sends keyword **"Naya Karigar"** (or taps quick-reply where supported).
2. Bot: "स्वागत है कारीगर में! 🙏 आपकी भाषा क्या है?" → buttons हिंदी | বাংলা | தமிழ் (fallback: "हिंदी के लिए 1 भेजें…"). বাংলা/தமிழ் → graceful coming-soon message, stay on Hindi.
3. Bot: "कारीगर का नाम क्या है? कृपया बोल कर बताएं।"
4. Voice note: "मेरा नाम रामकली है।" → Whisper → Bot: "मैंने सुना: रामकली। सही है?" → 👍 हाँ | 👎 नहीं (fallback text/voice). नहीं → re-ask.
5. Same pattern for village.

### 9.2 Cataloging & the Vision quality gate
6. Bot: "कृपया अपनी कला की 5-6 साफ तस्वीरें भेजें।" → partner sends batch.
7. Bot instantly (async pattern): "फोटो मिल गई ✓ प्रोसेसिंग हो रहा है..."
8. **Mechanic A — clustering (Tier 2):** 15 photos, 3 distinct products → Vision groups them → Bot: "बहुत सुंदर! आपकी तस्वीरों में मुझे 3 अलग-अलग डिज़ाइन मिले हैं। चलिए, एक-एक करके इनकी कीमत तय करते हैं।" → sequential pricing loop per design. Implementation: ONE GPT-4o Vision call over all images returning JSON groups of image indices — not embedding clustering.
9. **Mechanic B — partial success:** 1 of 5 blurry → scores [pass,pass,pass,fail,pass] → drop the failure → Bot: "बहुत बढ़िया! 4 तस्वीरें बहुत साफ़ आई हैं, मैंने उन्हें चुन लिया है। एक तस्वीर धुंधली थी, इसलिए मैंने उसे हटा दिया है।"
10. **Mechanic C — total failure / no craft (anti-hallucination):** all blurry, or a selfie/courtyard → `{"quality_score":"fail"}`, NEVER guess → Bot: "माफ़ कीजिये, यह फोटो थोड़ी धुंधली आई है / मुझे इसमें आपकी कोई कला नहीं दिख रही है। कृपया डिज़ाइन को अच्छी रौशनी में रखकर एक और साफ़ फोटो खींच कर भेजें।"
11. **Authenticity challenge (Layer 2):** after batch passes → Bot: "बहुत सुंदर! अब एक आखिरी फोटो — पेंटिंग के पीछे की तरफ की फोटो भेजिए।" → Vision evaluates back-of-piece evidence → pass: continue; fail: "माफ़ कीजिये, यह हाथ से बनी कला नहीं लग रही है। कारीगर सिर्फ़ हाथ की बनी चीज़ों के लिए है।" + reason.

### 9.3 GI verification
- Story agent matches Vision's craft ID against the hardcoded GI table (~10 crafts: Madhubani, Warli, Channapatna toys, Kutch embroidery, Bidriware, Pashmina, Blue Pottery, Pochampally Ikat, Kanjeevaram, Bandhani — each with region + tradition metadata + 2-3 process facts for Layer 3).
- Match → `gi_status = verified` → "Verified Artisan" badge + "GI Certified" tag on preview and listing page. No match → `unverified`, still listable, no badge.

### 9.4 Pricing & negotiation
- Bot: "मशीन के हिसाब से मीशो पर इसकी कीमत ₹350 होनी चाहिए। डिलीवरी का खर्च हटाकर, आपके बैंक खाते में सीधे ₹290 आएंगे। क्या हम इसे लिस्ट कर दें?" → हाँ, लिस्ट कर दो | नहीं, कीमत बदलें. (The "in-hand" translation of deductions is the point — never say "commission structure.")
- **Negotiation (Tier 3):** user demands ₹1500 (above demographic threshold) → "रामकली जी, आपकी मेहनत बिल्कुल सही है। लेकिन मीशो पर ग्राहक ऐसी पेंटिंग ₹400 से ₹500 के बीच खरीदते हैं। शुरुआत में ज़्यादा ऑर्डर पाने के लिए, क्या हम अभी इसे ₹499 में लगा सकते हैं?" → हाँ, ₹499 कर दें | नहीं, ₹1500 ही रखें. **Final override always exists — the artisan retains absolute agency.**

### 9.5 KYC → EID (full detail in §8)
### 9.6 Approval & launch
- Backend generates mock EID, pushes payload to mock Meesho API → Bot sends **Listing Preview Card**: photo thumbnail, title, price, badge if verified → हाँ, लिस्ट कर दो | नहीं, दोबारा करो (fallback 1/2). **Nothing auto-publishes.**
- On approval: "🎉 बधाई हो! आपकी मधुबनी पेंटिंग मीशो पे तैयार है!" + voice note. Listing goes live on the Meesho-styled page.

### 9.7 Post-onboarding operations (artisan's own chat, voice-only)
- **New order (proactive):** "खुशखबरी! आपकी मधुबनी पेंटिंग का ऑर्डर आया है। डिलीवरी वाले भैया कल इसे लेने आएंगे। कृपया इसे पैक करके रखें।" → 👍 समझ गई | ❌ सामान नहीं है.
  - **❌ downstream flow:** Distribution marks listing `out_of_stock` (paused, not deleted), cancels pickup via mock API before dispatch (avoids failed-pickup penalty) → "कोई बात नहीं, मैंने ऑर्डर रोक दिया है। जब पेंटिंग तैयार हो जाए, बस उसकी फोटो भेज दीजिएगा, लिस्टिंग फिर चालू हो जाएगी।" A new photo of the finished piece re-activates the listing.
- **Payout:** "पिछले हफ्ते जो पेंटिंग बिकी थी, उसके ₹290 आज आपके बैंक खाते में जमा हो गए हैं।"
- **Return/RTO (de-escalation tone is mandatory):** "एक पेंटिंग वापस आ रही है क्योंकि ग्राहक घर पर नहीं था। आप चिंता बिल्कुल ना करें, इसमें आपकी कोई गलती नहीं है और आपके पैसों पर कोई असर नहीं पड़ेगा।"
- **Reactive voice intent:** artisan asks anything by voice; orchestrator classifies (`query_revenue`, `manage_inventory`, `unknown`).
  - Earnings: "मैंने कितना पैसा कमाया?" → "इस हफ्ते आपकी 3 पेंटिंग बिकी हैं। कट-पीट कर आपके 870 रुपये बने हैं, जो मंगलवार तक आपके खाते में आ जाएंगे।" (computed from DB, spoken via TTS — never hardcoded numbers)
  - Unknown (honest refusal): "वो डिलीवरी वाला अभी तक क्यों नहीं आया?" → "माफ़ कीजिये, मैं डिलीवरी का समय नहीं देख पा रहा हूँ। आप मुझसे अपनी कमाई, नए ऑर्डर, या छुट्टियों के बारे में पूछ सकती हैं।"

### 9.8 Catalog expansion (Tier 3)
- **Explicit:** "नया सामान" keyword/menu → "क्या आपने कोई नई डिज़ाइन बनाई है? कृपया उस नई कला की 3-4 साफ़ तस्वीरें यहाँ भेजें।" → Vision & Pricing loop (KYC NOT re-asked).
- **Implicit:** active seller drops 3 photos out of nowhere → orchestrator (state-injected) routes to `add_new_listing` → "क्या आप इस नई डिज़ाइन को भी मीशो दुकान पर बेचना चाहती हैं? मशीन के हिसाब से इसकी कीमत ₹350 होनी चाहिए।" → हाँ, लिस्ट कर दो | नहीं, बस ऐसे ही भेजी है.

### 9.9 Trend agent (Tier 2 — committed in the submitted idea, must exist)
Runs over the orders/returns tables (mock-populated), one GPT-4o call + TTS:
- Bestseller: "रामकली जी, इस हफ्ते आपकी कृष्ण भगवान वाली पेंटिंग बहुत बिकी है! अगर आप अगले हफ्ते के लिए 2-3 और बना लें, तो वो जल्दी बिक जाएंगी।"
- Seasonal: "अगले महीने दिवाली है। आप अभी से कुछ और पेंटिंग बनाकर रख लें, ताकि अचानक से ज़्यादा ऑर्डर आएं तो हम तैयार रहें।"
- Returns feedback: "आपकी एक पेंटिंग वापस आई है। ग्राहक ने बताया कि रंग थोड़े हल्के थे। अगली बार थोड़ा गहरा रंग इस्तेमाल करके देखिएगा।"

---

## 10. DATA MODEL (Supabase / Postgres — shared memory; the orchestrator holds NO state in process memory)

```
seller_identities
  id uuid pk, legal_name, pan_ref, bank_account_ref, ifsc,
  otp_phone, enrolment_id,
  kyc_status (collecting | awaiting_otp_device | verified),
  consistency_verified bool,   -- name-match across PAN, passbook, OTP phone,
                               -- confirmed by OCR + user confirmation
  created_at

artisans
  id uuid pk, name, village, pincode, craft, language_code,
  photo_url, onboarding_partner_phone, whatsapp_phone,
  seller_identity_id fk -> seller_identities,  -- may be her own or a family member's
  onboarding_state,   -- explicit state machine step, drives orchestrator routing
  created_at

listings
  id uuid pk, artisan_id fk, craft_type, style, motifs text[],
  title, description, price int, original_price int,
  photo_urls text[], enhanced_photo_url,
  gi_status (verified | unverified | rejected),
  quality_score, authenticity_score int, authenticity_reasons text[],
  status (draft | pending_approval | live | out_of_stock | rejected),
  meesho_listing_id, created_at

orders
  id uuid pk, listing_id fk, buyer_ref, amount int,
  status (placed | shipped | delivered | returned | cancelled),
  artisan_notified_at, created_at

returns
  id uuid pk, order_id fk, reason_text,
  classification (rto | quality | other),
  rating_protected bool, artisan_notified_at, created_at

voice_messages
  id uuid pk, artisan_id fk, direction (inbound | outbound),
  transcript, audio_url, intent, language_code, created_at
```

Invariants enforced in code:
- No payout logic fires unless `seller_identities.consistency_verified = true`.
- All conversational agents key off `artisans` (she is the user); all payout/compliance logic keys off `seller_identities`. One seller_identity may back multiple artisans in a household.
- Every DB write of user-provided data (name, village, pincode, account digits) happens only AFTER an explicit user confirmation.

---

## 11. MOCKS — exact contracts

All in `mocks/`, each behind an interface, each with `TODO: replace with real integration`, each explained in README.

1. **`mocks/meesho_api`** — mimics a plausible Seller API: `createListing(payload) -> {meesho_listing_id, status}`, `updateListing`, `cancelPickup(order_id)`, plus an order-webhook simulator: a `POST /demo/trigger-order` (and a Demo Console button) creates an order row and fires the artisan's voice notification. Payout simulator similarly triggerable.
2. **`mocks/gst_enrolment`** — `submitEnrolment(payload) -> {pending, otp_required}`, `confirmOtp(otp) -> {enrolment_id}` (realistic 15-char format, ~2s delay). Any 6-digit OTP accepted in the prototype.
3. **`mocks/gi_registry`** — hardcoded table of the 10 GI crafts with region, tradition metadata, and 2-3 process facts each. `lookup(craft_name) -> {gi_status, region, tradition, process_facts[]} | null`.

---

## 12. SURFACES / CLIENTS

1. **WhatsApp (Meta Cloud API primary, Twilio fallback)** — the real product surface, used in the demo video and live where whitelisting allows.
2. **Web Demo Console** — REQUIRED for the judges-can-test criterion. A WhatsApp-styled web chat (send text, upload images, record/upload audio, tap the same buttons) that hits the SAME backend through the SAME orchestrator via the transport adapter. Also includes demo controls: "Trigger mock order", "Trigger return", "Advance a week of sales" (for the Trend agent), and a live view of agent activity (which agent ran, its JSON output) so judges can "view model responses directly" (their words). This is a second real client, not a mock — same code path.
3. **Meesho-styled listing page** — public page rendering live listings: enhanced photo, title, description, ₹price with strike-through original, "Verified Artisan" badge + "GI Certified" tag when applicable, artisan name + village. Visual language close to Meesho's (clean product card, price-forward) without copying assets.

**Async webhook pattern (mandatory):** vision processing takes 10–12s; Meta/Twilio webhooks time out. On any inbound needing slow work: return 200 immediately, send buffer message ("फोटो मिल गई ✓ प्रोसेसिंग हो रहा है..."), run the agent chain in a background job, push results via a fresh outbound API call. WhatsApp voice notes arrive as OGG/Opus — confirm Whisper ingestion of that container (transcode via ffmpeg if needed).

---

## 13. BUILD TIERS (priority order — the clock cuts from the bottom; NO day-by-day plan here, plan it together with the builder)

**Tier 1 — the demo dies without these. Build first, in roughly this order:**
1. Vision agent + authenticity scoring, validated on real Madhubani photos (Wikimedia Commons) vs. factory-print counterexamples (marketplace screenshots). **This is the kill-shot test — if GPT-4o Vision cannot reliably separate real from print, the authenticity pitch must pivot, and the builder needs to know before anything else is built.** Test as a standalone script first.
2. Pipeline: Vision → Photo → Story → Pricing as sequential calls persisting to Supabase; all three mocks.
3. Transport adapter + WhatsApp intake + Whisper + confirmation loops + language selector (Hindi live, other buttons graceful) + onboarding state machine.
4. KYC flow with Identity Anchor + OCR confirmations + mock EID.
5. Preview → approval → Meesho-styled listing page with badge.
6. Mock order trigger → Hindi TTS voice note; "कितना कमाया?" voice round trip.
7. Back-of-painting challenge + fake-print rejection sequence.
8. Web Demo Console.

**Tier 2 — committed features, build next, in order:**
9. Trend agent (committed in the submitted idea — must exist).
10. Returns classification inside Distribution + de-escalation voice note.
11. Photo clustering (single Vision call over the batch, JSON groups).

**Tier 3 — only with spare time:**
12. Price negotiation dialogue. 13. Layer-3 process questions. 14. Phase-3 implicit photo drop / catalog expansion. 15. Randomized challenge variants.

**Deleted / documented-only (do NOT build):** Bengali/Tamil working pipelines; real GST portal automation; duplicate-detection embeddings (Layer 4); behavioral signals (Layer 5); crafts beyond Madhubani (deep) + Warli (shallow) for authenticity tuning.

**Structural rule:** Tier 2/3 features live in their own modules behind flags, callable from the orchestrator, and must be independently removable WITHOUT touching Tier 1 code paths. If the builder runs out of time mid-feature, the feature is abandoned uncommitted — never half-wired into the demo path.

**Freeze rule:** the final ~24 hours before submission are for end-to-end rehearsal, a recorded backup demo video, deployment checks, and README polish — not new features.

---

## 14. THE ACCEPTANCE TEST (build backwards from this — all steps must run live)

1. Send 5 photos of a Madhubani painting over WhatsApp.
2. Bot asks name + village → replied by voice notes, each confirmed.
3. Bot issues the back-of-painting challenge → real back sent → passes.
4. Bot collects PAN + passbook + address/pincode with confirmations → OTP exchange → mock EID issued.
5. Bot returns a listing preview card: title, description, ₹299 price (strike-through ₹450), Verified Artisan badge.
6. Approve via "हाँ, लिस्ट कर दो" (button or text/voice fallback).
7. Listing appears on the Meesho-styled page with badge + GI Certified tag.
8. Trigger a mock order → artisan's WhatsApp receives the Hindi voice note about the order.
9. Send a voice note "कितना कमाया?" → spoken earnings summary computed from the DB.
10. **Adversarial pass:** attempt onboarding with a factory-print image → challenge issued → blank back sent → rejection with reason.
11. Trigger the Trend agent over seeded sales data → bestseller voice note arrives.
12. Every step above must also be reproducible by a judge in the Web Demo Console.

---

## 15. ENGINEERING & QUALITY REQUIREMENTS (evaluation criterion 02 explicitly scores these)

- **Stack suggestion (challenge if you disagree):** Node.js/TypeScript backend (Express or Fastify), Supabase (Postgres + storage for images/audio), a minimal job queue for the async pattern (even an in-process queue is fine at this scale), React or plain-HTML frontends for the Demo Console and listing page. Deployment: any free tier with a public URL (Railway/Render/Fly.io + Vercel for frontends) — a live URL is a hard submission requirement.
- **Architecture:** clean module boundaries — `agents/`, `orchestrator/`, `transports/` (whatsapp-cloud, twilio, web-console), `mocks/`, `db/`, `flows/` (onboarding state machine), `prompts/` (every LLM prompt in its own versioned file, not inline strings).
- **Tests (criterion 02 mentions test coverage):** unit tests for the orchestrator's routing logic (state × message-type matrix), the confirm/deny classifier (table of Hindi/English yes-no utterances), the Identity Anchor name-matching, pincode/OTP digit parsing, and mock contracts. Integration test for the pipeline with recorded fixture responses. Do not chase coverage numbers; test the routing and parsing logic where regressions are silent.
- **Error handling:** every OpenAI call wrapped with retry (exponential backoff, max 2 retries) and a graceful Hindi failure message ("थोड़ी दिक्कत आ गई है, एक बार फिर भेजिए") — never a stack trace to the user, never a silent drop.
- **Secrets:** `.env` + `.env.example`; never committed.
- **README must contain:** problem/solution overview; architecture diagram; agent table; **"Real vs. Mocked and why" table**; setup + run instructions (judges must be able to run locally — criterion 01/03); deployed URLs; the acceptance-test script as a verification checklist; the **open-source attribution table** (name, version, license, role, source link — for EVERY dependency including rembg, sharp, ffmpeg, Express/Fastify, React, Supabase client, OpenAI SDK, etc. — submission requirement 04 is explicit and easy to lose points on); known limitations (OpenAI TTS Hindi quality; authenticity validated for Madhubani deep/Warli shallow; language-agnostic pipeline with Hindi live).
- **Pitch material (submission requirement 01):** a `docs/` folder with the pitch document — problem, solution, the seven agents, the Authenticity Engine, the Identity Anchor, business model (Karigar as the artisan-side onboarding + operations layer; Meesho gets verified authentic supply for the shelf Project Suraksha cleared), and the production roadmap (Layers 4-5, real integrations, more languages/crafts).

## 16. WHAT CLAUDE CODE SHOULD DO FIRST

1. Read this entire file. Flag any contradiction, ambiguity, or technical error you find — do not silently resolve them.
2. Challenge the stack suggestion and the tier ordering if you believe they are wrong for a solo builder on this deadline; say why.
3. Create a `CLAUDE.md` in the repo root distilling: hard constraints (§5), tier order + structural rule + freeze rule (§13), the mock contracts (§11), and "DO NOT BUILD" list — so every future session inherits them.
4. Propose the repo structure and a concrete plan WITH the builder (they will plan the schedule interactively — do not impose a day-by-day plan from this file).
5. Build item 1 of Tier 1 first — the standalone Vision authenticity test — before any infrastructure. Everything else depends on its result.
