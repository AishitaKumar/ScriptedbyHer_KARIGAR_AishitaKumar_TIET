<!-- prompt: vision_same_artwork | v1 | used by: agents/vision (change-photo guard) -->

You are given two product photos of handmade craft.
- Image A is the photo currently on the seller's listing.
- Image B is a new photo the seller wants to swap in.

Decide whether both photos show the **same single physical artwork** — the same
painting/object — allowing for a different angle, distance, lighting, crop, or
background. It is still the same artwork if it is clearly the same piece shot
again.

It is a DIFFERENT artwork if the subject, composition, motifs, colours, or craft
type differ in a way that means it is simply another piece — not the same object
re-photographed.

Return ONLY a JSON object:
{"same_artwork": <true|false>, "confidence": <0-100>, "reason": "<short reason>"}
