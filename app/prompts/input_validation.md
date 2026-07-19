<!-- prompt: input_validation | v1 | used by: flows/onboarding — reject irrelevant answers -->

An artisan is being onboarded to a Meesho seller assistant. We asked her a
specific question and she replied (by voice or text, Hindi/English). Decide
whether her reply is a genuine, usable answer to THAT question — or something
irrelevant (a refusal like "नहीं बताऊँगी", gibberish, an unrelated sentence, a
question back, an emoji, etc.).

You are told the "field" being collected:
- "name": expects a person's name (the artisan's or shopkeeper's). A refusal,
  a random word, or a non-name is NOT valid.
- "village": expects a village/town/city/place name. Not valid if it's a refusal
  or clearly not a place.

If valid, echo the cleaned value. If not valid, write a SHORT, warm nudge in her
language ("hi" → Hindi Devanagari, "en" → English) that names the problem and
asks again — e.g. for a refused name: "दुकान शुरू करने के लिए हमें कारीगर का नाम
चाहिए। कृपया नाम बताइए।" Tailor the nudge to what she actually said.

Return ONLY a JSON object:
{"valid": <bool>, "cleaned": "<string|null>", "message": "<nudge if invalid, else null>"}
