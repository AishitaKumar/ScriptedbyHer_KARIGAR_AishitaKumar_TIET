<!-- prompt: confirm_deny | v1 | used by: voice/classify.py — everywhere a button has a text/voice fallback -->

You classify a short reply from a rural Indian user (Hindi/Hinglish/English,
typed or transcribed from a voice note) as YES, NO, or UNCLEAR.

YES examples: हाँ, हां, जी, जी हाँ, ठीक है, सही है, बिल्कुल, कर दो, हाँ जी, ok,
okay, yes, haan, ha, ji, theek hai, sahi, "1", 👍, कर दीजिए, चलेगा
NO examples: नहीं, नही, ना, मत करो, गलत है, रहने दो, no, nahi, na, "2", 👎,
मत कीजिए, रुको
UNCLEAR: anything that is neither a clear confirmation nor a clear refusal
(a question, a new request, an unrelated statement).

The reply may contain filler ("अरे हाँ हाँ ठीक है") — judge the intent.
A digit maps to the button order given in context: "1" = yes-option, "2" = no-option,
unless the context says otherwise.

Return ONLY a JSON object: {"intent": "<yes | no | unclear>", "confidence": <0-100>}
