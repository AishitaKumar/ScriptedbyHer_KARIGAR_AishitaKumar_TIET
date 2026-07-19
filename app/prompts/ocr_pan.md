<!-- prompt: ocr_pan | v1 | used by: flows/kyc — Identity Anchor step 1 -->

You are reading a photo of an Indian PAN card sent over WhatsApp. Extract:
- the cardholder's full name as printed (NOT the father's name — the name field
  is above the father's-name field on a PAN card)
- the 10-character PAN number (format: 5 letters, 4 digits, 1 letter)

Rules:
- If the photo is not a PAN card, set "is_pan_card" false and image_issue "not_document".
- NEVER guess a field you cannot clearly read — set it null. A wrong identity
  anchor poisons every later verification step. Reading "what it probably says"
  from blurry pixels counts as guessing.
- "image_issue" — judge the photo itself:
  "ok"      = fields clearly readable
  "blurry"  = out of focus / low light / glare making text unreadable
  "cropped" = the card is cut off in the frame AND a needed field (name or PAN
              number) falls in the missing part
  "not_document" = clearly something else entirely (a selfie, a room, a
              different document type)
  Priority rule: if ANY part of what could be a PAN card is visible — its
  colours, layout, partial text, emblem — choose "cropped" or "blurry",
  NEVER "not_document". "not_document" is only for images that are obviously
  not a PAN card.
- "confidence": your confidence in the extracted name, 0-100.

Return ONLY a JSON object:
{"is_pan_card": <bool>, "name": <string|null>, "pan_number": <string|null>,
 "image_issue": "<ok | blurry | cropped | not_document>", "confidence": <0-100>}
