<!-- prompt: name_equivalence | v1 | used by: flows/common.names_match_smart -->

You are given two Indian names that are expected to belong to the SAME person —
one typically from a PAN card, the other from a bank passbook or spoken aloud by
the user. Decide whether they plausibly refer to the same person's name.

Treat as the SAME when the difference is only:
- Script: one in Latin, the other in Devanagari (e.g. "AISHTA KUMAR" ≈ "आइशिता कुमार").
- Transliteration/spelling variants ("Aishita" ≈ "Aishta" ≈ "Ayeshita").
- Minor OCR errors, missing/extra middle name, honorifics (Shri/Smt/जी), or word order.

Treat as DIFFERENT only when they are genuinely different people
("Suresh Kumar" vs "Ramesh Kumar", "Aishita" vs "Sunita").

Return ONLY a JSON object: {"same": <bool>}
