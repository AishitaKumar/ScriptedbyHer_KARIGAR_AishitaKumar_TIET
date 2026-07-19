<!-- prompt: vision_clustering | v1 | used by: agents/vision (Tier-2 Mechanic A) -->

You are looking at a batch of product photos sent by a craft artisan. The batch
may contain several photos of the SAME piece (different angles/distances) and/or
photos of DIFFERENT pieces (distinct designs).

Group the photos by physical piece. Two photos belong to the same group only if
they plausibly show the same physical object (same composition, motifs, colours).

Images are provided in order; refer to them by 0-based index.

Return ONLY a JSON object:
{
  "groups": [
    {"image_indices": [<int>, ...], "label": "<short English description of the piece>"}
  ]
}
