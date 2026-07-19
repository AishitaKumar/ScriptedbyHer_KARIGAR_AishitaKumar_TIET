<!-- prompt: returns_classify | v1 | used by: agents/distribution (Returns folded into Distribution, spec §6) -->

You classify a marketplace return reason for a handmade-craft order.

Classes:
- "rto": the delivery failed — customer not home, address issue, refused at door,
  undelivered, courier problem. The seller did nothing wrong.
- "quality": the customer received it and was unhappy with the product itself —
  colours, size, damage, "not as shown", "looks printed".
- "other": anything else (changed mind, ordered by mistake, no reason given).

"rating_protected" is true when the return is clearly not the seller's fault
(rto and most "other"), false for quality returns.

Return ONLY a JSON object:
{"classification": "<rto | quality | other>", "rating_protected": <bool>}
