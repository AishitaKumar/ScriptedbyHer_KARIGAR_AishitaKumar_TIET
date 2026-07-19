"""All database reads/writes."""

from __future__ import annotations

import asyncio
from typing import Any

from app.db.client import db


async def _run(fn):
    return await asyncio.to_thread(fn)


async def get_or_create_artisan(phone: str) -> dict:
    def op():
        found = db().table("artisans").select("*").eq("whatsapp_phone", phone).execute().data
        if found:
            return found[0]
        return (
            db().table("artisans")
            .insert({"whatsapp_phone": phone, "onboarding_state": "new"})
            .execute()
            .data[0]
        )

    return await _run(op)


async def update_artisan(artisan_id: str, patch: dict[str, Any]) -> dict:
    return await _run(
        lambda: db().table("artisans").update(patch).eq("id", artisan_id).execute().data[0]
    )


async def set_state(artisan_id: str, state: str | None, context_patch: dict | None = None) -> dict:
    """Move the state machine; optionally merge scratch context in the same write."""

    def op():
        patch: dict[str, Any] = {}
        if state is not None:
            patch["onboarding_state"] = state
        if context_patch is not None:
            current = (
                db().table("artisans").select("context").eq("id", artisan_id).execute().data[0]
            )["context"] or {}
            current.update(context_patch)
            patch["context"] = current
        return db().table("artisans").update(patch).eq("id", artisan_id).execute().data[0]

    return await _run(op)


async def merge_context(artisan_id: str, context_patch: dict) -> dict:
    """Merge scratch context WITHOUT touching onboarding_state — proactive notifications must never clobber a conversation mid-step."""
    return await set_state(artisan_id, None, context_patch)


async def get_artisan(artisan_id: str) -> dict:
    return await _run(
        lambda: db().table("artisans").select("*").eq("id", artisan_id).execute().data[0]
    )


async def get_listing(listing_id: str) -> dict:
    return await _run(
        lambda: db().table("listings").select("*").eq("id", listing_id).execute().data[0]
    )


async def get_order(order_id: str) -> dict:
    return await _run(
        lambda: db().table("orders").select("*, listings(id, title, title_hi, artisan_id)")
        .eq("id", order_id).execute().data[0]
    )


async def get_seller_identity(identity_id: str) -> dict:
    return await _run(
        lambda: db().table("seller_identities").select("*").eq("id", identity_id).execute().data[0]
    )


async def create_seller_identity(fields: dict) -> dict:
    return await _run(lambda: db().table("seller_identities").insert(fields).execute().data[0])


async def update_seller_identity(identity_id: str, patch: dict) -> dict:
    return await _run(
        lambda: db().table("seller_identities").update(patch).eq("id", identity_id).execute().data[0]
    )


async def create_listing(fields: dict) -> dict:
    return await _run(lambda: db().table("listings").insert(fields).execute().data[0])


async def update_listing(listing_id: str, patch: dict) -> dict:
    return await _run(
        lambda: db().table("listings").update(patch).eq("id", listing_id).execute().data[0]
    )


async def live_listings() -> list[dict]:
    return await _run(
        lambda: db().table("listings").select("*, artisans(name, village)")
        .eq("status", "live").order("created_at", desc=True).execute().data
    )


async def listings_for_artisan(artisan_id: str, statuses: list[str] | None = None) -> list[dict]:
    def op():
        q = db().table("listings").select("*").eq("artisan_id", artisan_id)
        if statuses:
            q = q.in_("status", statuses)
        return q.order("created_at", desc=True).execute().data

    return await _run(op)


async def create_order(fields: dict) -> dict:
    return await _run(lambda: db().table("orders").insert(fields).execute().data[0])


async def update_order(order_id: str, patch: dict) -> dict:
    return await _run(
        lambda: db().table("orders").update(patch).eq("id", order_id).execute().data[0]
    )


async def orders_for_artisan(artisan_id: str, days: int | None = None) -> list[dict]:
    def op():
        listing_ids = [
            l["id"] for l in db().table("listings").select("id").eq("artisan_id", artisan_id).execute().data
        ]
        if not listing_ids:
            return []
        q = db().table("orders").select("*, listings(title, title_hi, price)").in_("listing_id", listing_ids)
        if days is not None:
            from datetime import datetime, timedelta, timezone

            cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
            q = q.gte("created_at", cutoff)
        return q.order("created_at", desc=True).execute().data

    return await _run(op)


async def create_return(fields: dict) -> dict:
    return await _run(lambda: db().table("returns").insert(fields).execute().data[0])


async def returns_for_artisan(artisan_id: str) -> list[dict]:
    def op():
        listing_ids = [
            l["id"] for l in db().table("listings").select("id").eq("artisan_id", artisan_id).execute().data
        ]
        if not listing_ids:
            return []
        order_ids = [
            o["id"] for o in db().table("orders").select("id").in_("listing_id", listing_ids).execute().data
        ]
        if not order_ids:
            return []
        return db().table("returns").select("*").in_("order_id", order_ids).execute().data

    return await _run(op)


async def create_review(fields: dict) -> dict:
    return await _run(lambda: db().table("reviews").insert(fields).execute().data[0])


async def record_market_demand(craft_type: str) -> None:
    await _run(lambda: db().table("market_demand").insert({"craft_type": craft_type}).execute())


async def reviews_for_artisan(artisan_id: str) -> list[dict]:
    def op():
        listing_ids = [
            l["id"] for l in db().table("listings").select("id").eq("artisan_id", artisan_id).execute().data
        ]
        if not listing_ids:
            return []
        order_ids = [
            o["id"] for o in db().table("orders").select("id").in_("listing_id", listing_ids).execute().data
        ]
        if not order_ids:
            return []
        return db().table("reviews").select("*").in_("order_id", order_ids).execute().data

    return await _run(op)


async def platform_demand(days: int = 7) -> list[dict]:
    """Order counts by craft across ALL sellers — the marketplace demand signal the Trend agent uses ('similar items are selling well right now')."""

    def op():
        from collections import Counter
        from datetime import datetime, timedelta, timezone

        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        rows = (
            db().table("orders").select("id, created_at, listings(craft_type)")
            .gte("created_at", cutoff).execute().data
        )
        counts = Counter(
            (r.get("listings") or {}).get("craft_type") or "unknown" for r in rows
        )
        try:
            for r in db().table("market_demand").select("craft_type").gte("created_at", cutoff).execute().data:
                counts[r["craft_type"]] += 1
        except Exception:  # noqa: BLE001 — table may not exist until migration 007 runs
            pass
        return [{"craft": c, "units_ordered": n} for c, n in counts.most_common(8)]

    return await _run(op)


async def wipe_demo_data() -> dict:
    """Delete all demo data (FK order matters)."""

    def op():
        counts = {}
        for table in ("reviews", "returns", "orders", "market_demand", "voice_messages", "listings", "artisans", "seller_identities"):
            rows = db().table(table).delete().neq("id", "00000000-0000-0000-0000-000000000000").execute().data
            counts[table] = len(rows)
        return counts

    return await _run(op)


async def log_voice_message(fields: dict) -> None:
    await _run(lambda: db().table("voice_messages").insert(fields).execute())
