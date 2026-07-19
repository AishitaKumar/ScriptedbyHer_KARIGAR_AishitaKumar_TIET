<!-- prompt: parse_dimensions | v1 | used by: flows/onboarding._awaiting_dimensions -->

An artisan was asked the size (dimensions) of her handmade piece and answered by
voice or text, in Hindi or English. Understand EXACTLY what she said and
normalise it — do not invent numbers she didn't say.

Extract width, height (and depth if given) with their unit. Handle spoken forms:
- "बारह गुणा अठारह इंच" / "12 by 18 inches" → 12 × 18 inch
- "डेढ़ फुट लंबा एक फुट चौड़ा" → 1.5 × 1 foot
- "तीस सेंटीमीटर" (one number only) → 30 cm (single dimension)
- units: इंच/inch, फुट/feet, सेंटीमीटर/cm. If she gives no unit, default to inch
  and set unit_assumed true.

If the answer is NOT about size at all (a refusal, gibberish, a different topic),
set "valid" false.

"normalized": a short human-readable size string in the artisan's language for
read-back, e.g. "12 x 18 इंच" (hi) or "12 x 18 inch" (en).
"canonical": a stable English string for the listing, e.g. "12 x 18 inch".

Return ONLY a JSON object:
{"valid": <bool>, "normalized": "<string|null>", "canonical": "<string|null>",
 "unit_assumed": <bool>}
