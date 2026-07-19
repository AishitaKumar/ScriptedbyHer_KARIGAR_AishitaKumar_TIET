"""Mock GI (Geographical Indication) registry."""

from __future__ import annotations

_GI_CRAFTS: dict[str, dict] = {
    "madhubani": {
        "display_name": "Madhubani (Mithila) Painting",
        "region": "Mithila region, Bihar",
        "tradition": (
            "Practised for centuries by women of the Mithila region, painted on "
            "walls and floors for weddings and festivals, now on handmade paper "
            "and canvas. Styles include bharni (filled colour), kachni (fine-line "
            "hatching) and godna (tattoo-motif)."
        ),
        "process_facts": [
            "Black colour is traditionally made from soot/kajal (lamp black) mixed with cow dung or gum",
            "Twigs, matchsticks and nib-pens are used instead of brushes for fine lines",
            "A double outline with hatching between the lines is characteristic of kachni style",
        ],
    },
    "warli": {
        "display_name": "Warli Painting",
        "region": "Palghar district, Maharashtra",
        "tradition": (
            "Tribal art of the Warli community: white geometric figures — circles, "
            "triangles, squares — depicting daily life and the tarpa dance, painted "
            "on austere mud-brown backgrounds."
        ),
        "process_facts": [
            "White pigment is made from rice paste with gum as a binder",
            "The background is traditionally a mud/cow-dung coated wall, giving the brown base",
            "A bamboo stick chewed at the end serves as the brush",
        ],
    },
    "channapatna": {
        "display_name": "Channapatna Toys",
        "region": "Channapatna, Karnataka",
        "tradition": (
            "Lacquered wooden toys turned on a lathe, a 200+ year tradition "
            "traced to Tipu Sultan's era; known as gombegala ooru (toy town)."
        ),
        "process_facts": [
            "Made from ivory wood (Wrightia tinctoria), locally called aale mara",
            "Coloured with natural vegetable dyes applied as lac while the piece spins on the lathe",
        ],
    },
    "kutch_embroidery": {
        "display_name": "Kutch Embroidery",
        "region": "Kutch district, Gujarat",
        "tradition": (
            "Intricate thread work with mirrors (abhla) by communities of Kutch — "
            "each community (Rabari, Ahir, Mutwa) has a distinct stitch vocabulary."
        ),
        "process_facts": [
            "Small mirrors (abhla) are anchored with a buttonhole-style stitch ring",
            "Patterns are stitched from memory, not printed templates",
        ],
    },
    "bidriware": {
        "display_name": "Bidriware",
        "region": "Bidar, Karnataka",
        "tradition": (
            "Blackened zinc-copper alloy metalware inlaid with silver, a 14th-century "
            "Persian-influenced craft of Bidar."
        ),
        "process_facts": [
            "The black finish comes from a paste containing soil from Bidar fort, which oxidises the alloy",
            "Pure silver wire or sheet is hammered into engraved grooves before blackening",
        ],
    },
    "pashmina": {
        "display_name": "Kashmir Pashmina",
        "region": "Kashmir",
        "tradition": (
            "Hand-spun, hand-woven shawls from the undercoat of the Changthangi goat "
            "of Ladakh; spinning on the yinder (spinning wheel) is done by women."
        ),
        "process_facts": [
            "Genuine pashmina fibre is 12-16 microns thick and cannot be machine-spun without blending",
            "The raw fleece is combed, not sheared, from the goat each spring",
        ],
    },
    "blue_pottery": {
        "display_name": "Jaipur Blue Pottery",
        "region": "Jaipur, Rajasthan",
        "tradition": (
            "Turko-Persian glazed pottery made WITHOUT clay — a quartz-based dough — "
            "famous for cobalt blue and turquoise floral patterns."
        ),
        "process_facts": [
            "The body is quartz stone powder, glass, and multani mitti — no clay at all",
            "Fired only once, at low temperature; the blue comes from cobalt oxide",
        ],
    },
    "pochampally_ikat": {
        "display_name": "Pochampally Ikat",
        "region": "Bhoodan Pochampally, Telangana",
        "tradition": (
            "Double-ikat weaving where the pattern is dyed into the threads BEFORE "
            "weaving — the design emerges as warp and weft meet on the loom."
        ),
        "process_facts": [
            "Threads are tie-dyed to the pattern before weaving; the blur at motif edges is the ikat signature",
            "Both warp and weft are patterned in double ikat, requiring exact loom alignment",
        ],
    },
    "kanjeevaram": {
        "display_name": "Kanjeevaram (Kanchipuram) Silk",
        "region": "Kanchipuram, Tamil Nadu",
        "tradition": (
            "Heavy mulberry-silk saris with contrasting borders; body and border are "
            "woven separately and interlocked — the korvai technique."
        ),
        "process_facts": [
            "The border and body are joined by the korvai interlocking weave, visible as a fine zigzag",
            "Zari thread is silk wound with silver wire, gilded with gold",
        ],
    },
    "bandhani": {
        "display_name": "Bandhani (Bandhej)",
        "region": "Gujarat and Rajasthan",
        "tradition": (
            "Tie-dye where thousands of tiny points are pinch-tied with thread before "
            "dyeing; the dots' slight irregularity is the mark of the hand."
        ),
        "process_facts": [
            "Each dot is pinched and bound by hand with cotton thread before dye immersion",
            "A genuine bandhani shows a tiny raised peak at each dot centre where the cloth was tied",
        ],
    },
}

_ALIASES = {
    "mithila": "madhubani",
    "madhubani painting": "madhubani",
    "mithila painting": "madhubani",
    "warli painting": "warli",
    "channapatna toys": "channapatna",
    "kutch": "kutch_embroidery",
    "kutch embroidery": "kutch_embroidery",
    "bidri": "bidriware",
    "kanchipuram": "kanjeevaram",
    "bandhej": "bandhani",
    "ikat": "pochampally_ikat",
}


def lookup(craft_name: str | None) -> dict | None:
    """Return GI record for a craft, or None if not a GI-registered craft."""
    if not craft_name:
        return None
    key = craft_name.strip().lower().replace("-", "_").replace(" ", "_")
    if key not in _GI_CRAFTS:
        key = _ALIASES.get(craft_name.strip().lower())
    record = _GI_CRAFTS.get(key)
    if record is None:
        return None
    return {"gi_status": "verified", "craft_key": key, **record}
