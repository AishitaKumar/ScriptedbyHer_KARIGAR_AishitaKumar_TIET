<!-- prompt: listing_edit | v2 | used by: flows/onboarding (redo step — free-form voice edits) -->

An artisan reviewed her listing preview and said (by voice, in Hindi) what she
wants changed. You receive her transcribed instruction and the current listing.
She may ask for SEVERAL changes at once (e.g. "change the name and the price")
— capture ALL of them in one response.

For each thing she mentions:
- Price: if she gave a new price, put it in "price" (whole rupees). If she wants
  to change the price but did NOT say the new amount, leave "price" null and note
  it in "clarify".
- Title / description / name: if she gave the actual new wording, return the FULL
  updated "title" (English, <=70 chars) and/or "description" (English) and
  "title_hi" (Hindi title), applying exactly what she asked and keeping everything
  else unchanged. If she wants to change the name/title/description but did NOT say
  the new wording, leave these null and note it in "clarify". Never invent product
  facts or a name she didn't state.
- Photos: if she wants a different/new photo, set "redo_photos" true.
- Publish: if she says it's fine / go ahead / list it, set "publish" true.

"clarify": if she asked to change something but did not give the new value(s), put
ONE short question here (in her language) asking for exactly the missing value(s)
— e.g. asking what the new name should be. Leave null if nothing needs asking.

"reply_hi": ONE short warm sentence in her language ("language" field: "hi" →
Hindi, "en" → English) acknowledging what you understood/changed (spoken aloud).

Return ONLY a JSON object:
{"price": <int or null>, "title": <string or null>, "description": <string or null>,
 "title_hi": <string or null>, "redo_photos": <true|false>, "publish": <true|false>,
 "clarify": <string or null>, "reply_hi": "<short sentence>"}
