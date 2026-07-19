# Karigar — the pitch

**ScriptedByHer 2.0 · Build for Bharat with the power of Agentic AI**

## The problem: the shelf Project Suraksha cleared is still empty

Meesho removed 52 lakh+ fake craft listings — factory prints pretending to be
handmade. The real artisans those fakes copied are still not on Meesho: India's
~1.13 crore artisans (64% women) earn ~₹270/day, selling to passing tourists
for ₹50 while middlemen take ~60% of retail value. The barrier is not skill.
Many artisans cannot read or write in any language on a phone; many use keypad
phones or a family member's smartphone. Every seller platform assumes literacy
they don't have.

## The insight

> The artisan must never have to read, type, or learn an app. Her only
> interface is her **voice**, in **her own language**, over **WhatsApp — on a
> phone she already has.**

## The product

Karigar is an agentic AI system that turns a few WhatsApp photos and voice
notes into a live, GI-verified Meesho listing — zero literacy required — and
then runs her storefront by voice: orders, payouts, returns handled with a
mandatory de-escalation tone, and weekly business coaching.

Two-sided model: an **onboarding partner** (NGO/SHG worker or family member)
operates WhatsApp during onboarding while the artisan speaks; from then on the
**artisan owns the relationship** — no menus, no numbered options; she asks
"कितना कमाया मैंने?" and the orchestrator infers the intent from her words and
her database state.

## Why agentic AI (seven agents, one orchestrator)

Vision (authenticity + craft identification) → Photo (enhancement) → Story
(listing copy grounded in GI tradition) → Pricing (Meesho-realistic bands, with
the artisan's in-hand amount computed deterministically and spoken plainly) →
Distribution (publishing, order lifecycle, returns classification) → Trend
(weekly coaching from real sales data). The orchestrator routes every message
by the sender's live database state — the same photo means "onboarding" from a
new number and "new listing" from an active seller.

## The moat: an Authenticity Engine judges can attack live

The exact fraud Suraksha cleaned up will try to re-enter through any artisan
door. Karigar's defense is layered and demoable in 30 seconds:

1. **Vision forensics** — machine prints are *too perfect*; the model scores
   brush strokes, pigment pooling, line wobble, halftone/moiré tells. Tested:
   15/16 on real Madhubani vs. print-seller images.
2. **Provenance detection** (discovered through adversarial testing) — a
   watermarked, perfectly-cropped, studio-flat image is a *downloaded scan*,
   not a phone photo of a physical piece. Rejected even when the depicted
   artwork is genuinely handmade — because it proves nothing about the sender.
3. **Challenge-response** — "अब पेंटिंग के पीछे की तरफ की फोटो भेजिए।" A real
   painting's back shows pigment bleed-through; a print's back is blank poster
   paper. Defeats the one attack forensics cannot see.
4. **Duplicate detection & behavioral signals** — production roadmap
   (pgvector similarity across sellers; volume anomaly caps — a hand-painter
   cannot fulfil 300 orders/week; NGO/SHG attestation).

Honestly stated: this raises the cost of faking; Layers 4–5 catch over time
what a determined fraudster with one real painting can slip past onboarding.

## Inclusive compliance: the Identity Anchor

Rural documents are messy: the PAN may be the husband's, the bank account the
mother-in-law's. Karigar enforces exactly one rule — **PAN + bank + OTP phone
must belong to the same one person** — and *diagnoses* mismatches instead of
rejecting ("किसके पास पैन और बैंक खाता, दोनों अपने नाम के हैं?"). The artisan
always remains the user the system coaches and notifies, whoever the seller of
record is. When she has her own complete document set, payouts land directly
with her — women's financial agency as an emergent property of good
engineering, not a special-case gate. Wrong-account risk is engineered away:
account digits are read back aloud and nothing unconfirmed is ever saved.

## Business model

Karigar is the artisan-side onboarding + operations layer Meesho doesn't have
(no rural field network). Meesho gets what Project Suraksha could not create by
deletion alone: **verified, authentic handmade supply** for the shelf it
cleared, from sellers who could never have onboarded themselves. Unit
economics: one GPT-4o onboarding costs a few rupees; a single ₹299 sale repays
it many times over. Partner channel: NGO/SHG networks already embedded in
craft clusters.

## Production roadmap

Real Meesho Seller API integration (interface is swap-ready) · GST enrolment
via Playwright with a human-in-the-loop OTP step · Layers 4–5 of the
Authenticity Engine · Bengali + Tamil (the pipeline is language-parameterized
end-to-end) · more GI crafts with deep authenticity tuning · payout
reconciliation.

## The team

Solo builder. Everything AI in the prototype is a real model call — the demo
console shows every agent's raw JSON output live, and every flow in this pitch
can be exercised by the judges themselves.
