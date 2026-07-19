"""Mock GSTIN lookup — "Meesho's backend" verification against the GST registry."""

from __future__ import annotations

_REGISTRY: dict[str, dict] = {
    "22AAAAA0000A1Z5": {
        "legal_name": "AISHITA KUMAR",
        "trade_name": "Aishita Handicrafts",
        "business_type": "Proprietorship",
        "registered_address": "251-252, Pocket C-5, Sector 6, Rohini, Delhi-110085",
    },
    "10BBBBB1111B1Z3": {
        "legal_name": "RAMKALI DEVI",
        "trade_name": "Ramkali Madhubani Kala",
        "business_type": "Proprietorship",
        "registered_address": "Ward 4, Jitwarpur, Madhubani, Bihar-847211",
    },
    "27CCCCC2222C1Z8": {
        "legal_name": "SURESH KUMAR",
        "trade_name": "Suresh Warli Arts",
        "business_type": "Proprietorship",
        "registered_address": "Ganjad, Dahanu, Palghar, Maharashtra-401602",
    },
    "07DDDDD3333D1Z1": {
        "legal_name": "KARIGAR CRAFTS PRIVATE LIMITED",
        "trade_name": "Karigar Crafts",
        "business_type": "Private Limited",
        "registered_address": "14, Craft Lane, Karol Bagh, New Delhi-110005",
    },
    "24EEEEE4444E1Z9": {
        "legal_name": "GITA BEN PATEL",
        "trade_name": "Gita Bandhani House",
        "business_type": "Proprietorship",
        "registered_address": "Bhuj, Kutch, Gujarat-370001",
    },
}


def lookup(gstin: str | None) -> dict | None:
    if not gstin:
        return None
    return _REGISTRY.get(gstin.strip().upper())
