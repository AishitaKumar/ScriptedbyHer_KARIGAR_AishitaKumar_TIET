<!-- prompt: review_appreciation | v1 | used by: agents/distribution — per-review artisan notification -->

A customer just reviewed an artisan's handmade piece on Meesho. Write a short,
warm voice-note message telling the artisan her work was appreciated. This is
spoken aloud to a rural artisan, so keep it simple and genuinely happy for her.

You receive: the artisan's name, the product title, the star rating (1-5), and
the customer's comment (may be empty), and the language ("hi" → Hindi in
Devanagari, "en" → simple English).

Rules:
- Address her by name with जी (Hindi) / warmly (English).
- Mention the rating naturally (e.g. "5 में से 5 स्टार").
- If there's a comment, paraphrase the nice part of it warmly — never quote it
  raw if it's in another language; convey the sentiment in her language.
- 2-3 sentences. Encouraging, never salesy. End with light encouragement to
  keep making more.
- If the rating is low (1-2), be gentle and supportive instead of celebratory,
  and frame the feedback as something to learn from — never blame her.

Return ONLY a JSON object: {"message": "<the full message in her language>"}
