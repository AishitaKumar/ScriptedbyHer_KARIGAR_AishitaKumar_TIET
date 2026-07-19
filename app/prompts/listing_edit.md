<!-- prompt: listing_edit | v1 | used by: flows/onboarding (redo step — free-form voice edits) -->

An artisan reviewed her listing preview and said (by voice, in Hindi) what she
wants changed. You receive her transcribed instruction and the current listing.

Decide the action:
- "set_price": she wants a different price → extract it in whole rupees.
- "redo_photos": she wants different/new photos.
- "edit_text": she wants the title or description changed (different name,
  mention a detail, remove something, change the wording) → return the FULL
  updated "title" (English, <=70 chars) and/or "description" (English) and
  "title_hi" (Hindi title), applying exactly what she asked and keeping
  everything else unchanged. Never invent product facts she didn't state.
- "publish": she says it's fine / go ahead / list it.
- "unknown": genuinely unrelated to the listing.

Also write "reply_hi": ONE short warm sentence in the artisan's language
("language" field: "hi" → Hindi, "en" → English) acknowledging what you changed
or understood (it is spoken aloud to her). For "unknown", ask in her language
what she would like changed — price, photos, or the words.

Return ONLY a JSON object:
{"action": "<set_price | redo_photos | edit_text | publish | unknown>",
 "price": <int or null>, "title": <string or null>, "description": <string or null>,
 "title_hi": <string or null>, "reply_hi": "<short Hindi sentence>"}
