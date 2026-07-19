"""Karigar FastAPI app: console API, demo triggers, listing page API, health."""

from __future__ import annotations

import logging
import os
import random

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app import agentlog
from app.agents.pricing import in_hand_amount
from app.db import queries
from app.flows import operations
from app.jobs.queue import enqueue
from app.orchestrator.router import handle_inbound
from app.transports import web_console
from app.transports.base import InboundMessage

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Karigar")
console_transport = web_console.WebConsoleTransport()

if os.environ.get("WHATSAPP_TOKEN"):
    from app.transports import whatsapp_cloud

    app.include_router(whatsapp_cloud.router)
if os.environ.get("TWILIO_ACCOUNT_SID"):
    from app.transports import twilio_wa

    app.include_router(twilio_wa.router)

WEB_DIR = Path(__file__).resolve().parent.parent / "web"
WEB_V2_DIR = Path(__file__).resolve().parent.parent / "web_v2"
app.mount("/assets", StaticFiles(directory=WEB_DIR / "assets"), name="assets")
app.mount("/assets2", StaticFiles(directory=WEB_V2_DIR / "assets2"), name="assets2")


@app.post("/api/console/send")
async def console_send(
    session: str = Form(...),
    type: str = Form(...),
    text: str | None = Form(None),
    file: UploadFile | None = File(None),
):
    media = await file.read() if file else None
    msg = InboundMessage(
        sender=f"web:{session}", type=type, text=text,
        media=media, media_mime=file.content_type if file else None,
        transport="web_console",
    )
    enqueue(handle_inbound(msg, console_transport), name="inbound")
    return {"ok": True}


@app.get("/api/console/poll")
async def console_poll(session: str, since: int = 0):
    return web_console.poll(f"web:{session}", since)


@app.get("/api/agent-log")
async def agent_log():
    return {"events": agentlog.recent()}


@app.get("/api/listings")
async def listings():
    rows = await queries.live_listings()
    return {"listings": rows}


@app.post("/demo/buy")
async def buy_listing(listing_id: str = Form(...)):
    """Judge clicks 'Buy Now' on the shop → real order row → Distribution agent notifies the artisan's WhatsApp/console chat with a Hindi voice note."""
    listing = await queries.get_listing(listing_id)
    if listing["status"] != "live":
        return JSONResponse({"error": "listing is not live"}, status_code=400)
    order = await queries.create_order(
        {"listing_id": listing["id"], "buyer_ref": f"buyer_{random.randint(1000, 9999)}",
         "amount": listing["price"], "status": "placed"}
    )
    agentlog.log_event("distribution", "order placed from shop", {"order_id": order["id"]})
    artisan = await queries.get_artisan(listing["artisan_id"])
    artisan.setdefault("context", {})
    enqueue(operations.notify_new_order(artisan, order, listing, console_transport), name="order-notify")
    return {"ok": True, "order_id": order["id"], "title": listing["title"]}


@app.post("/demo/return-order")
async def return_order(order_id: str = Form(...), reason: str = Form("ग्राहक घर पर नहीं था")):
    """Judge returns an order from the shop → GPT-4o classifies the reason → de-escalation voice note to the artisan."""
    from app.agents.distribution import classify_return

    order = await queries.get_order(order_id)
    if order["status"] not in {"placed", "shipped", "delivered"}:
        return JSONResponse({"error": f"order is {order['status']}, cannot return"}, status_code=400)
    verdict = await classify_return(reason)
    row = await queries.create_return({"order_id": order["id"], "reason_text": reason, **verdict})
    listing = order["listings"]
    artisan = await queries.get_artisan(listing["artisan_id"])
    artisan.setdefault("context", {})
    enqueue(operations.notify_return(artisan, listing, row, console_transport), name="return-notify")
    return {"ok": True, **verdict}


@app.post("/demo/market-buy")
async def market_buy(craft: str = Form(...)):
    """A base (non-artisan) catalogue item was bought → record craft demand so the Trend agent can surface 'similar <craft> is selling well'."""
    await queries.record_market_demand(craft.strip().lower())
    agentlog.log_event("distribution", f"market demand recorded: {craft}", {"craft": craft})
    return {"ok": True}


@app.post("/demo/exchange-order")
async def exchange_order(order_id: str = Form(...), reason: str = Form(...)):
    """Buyer requests an exchange → Distribution notifies the artisan (voice note)."""
    order = await queries.get_order(order_id)
    await queries.create_return(
        {"order_id": order["id"], "reason_text": reason,
         "classification": "exchange", "rating_protected": True}
    )
    listing = order["listings"]
    artisan = await queries.get_artisan(listing["artisan_id"])
    artisan.setdefault("context", {})
    enqueue(operations.notify_exchange(artisan, listing, reason, console_transport), name="exchange-notify")
    return {"ok": True}


@app.post("/demo/deliver-order")
async def deliver_order(order_id: str = Form(...)):
    """The Meesho phone delivered a specific order → mark it delivered and pay the artisan for THAT order."""
    order = await queries.get_order(order_id)
    if order["status"] == "delivered":
        return {"ok": True, "already": True}
    await queries.update_order(order["id"], {"status": "delivered"})
    listing = order["listings"]
    artisan = await queries.get_artisan(listing["artisan_id"])
    artisan.setdefault("context", {})
    enqueue(
        operations.notify_payout(artisan, listing, in_hand_amount(order["amount"]), console_transport),
        name="payout-notify",
    )
    return {"ok": True, "order_id": order["id"]}


@app.post("/demo/submit-review")
async def submit_review(order_id: str = Form(...), rating: int = Form(...), comment: str = Form("")):
    """Buyer submits a rating + review → Distribution sends the artisan a warm appreciation voice note; the review is stored for Trend aggregation."""
    if not 1 <= rating <= 5:
        return JSONResponse({"error": "rating must be 1-5"}, status_code=400)
    order = await queries.get_order(order_id)
    await queries.create_review({"order_id": order["id"], "rating": rating, "comment": comment or None})
    listing = order["listings"]
    artisan = await queries.get_artisan(listing["artisan_id"])
    artisan.setdefault("context", {})
    enqueue(operations.notify_review(artisan, listing, rating, comment, console_transport), name="review-notify")
    return {"ok": True}


async def _artisan_for_session(session: str | None) -> dict | None:
    if session:
        return await queries.get_or_create_artisan(f"web:{session}")
    return None


@app.post("/demo/trigger-order")
async def trigger_order(session: str = Form(...)):
    artisan = await _artisan_for_session(session)
    live = await queries.listings_for_artisan(artisan["id"], ["live"])
    if not live:
        return JSONResponse({"error": "no live listing for this session"}, status_code=400)
    listing = live[0]
    order = await queries.create_order(
        {"listing_id": listing["id"], "buyer_ref": f"buyer_{random.randint(1000, 9999)}",
         "amount": listing["price"], "status": "placed"}
    )
    agentlog.log_event("distribution", "mock order webhook received", {"order_id": order["id"]})
    artisan.setdefault("context", {})
    enqueue(operations.notify_new_order(artisan, order, listing, console_transport), name="order-notify")
    return {"ok": True, "order_id": order["id"]}


@app.post("/demo/trigger-return")
async def trigger_return(session: str = Form(...), reason: str = Form("ग्राहक घर पर नहीं था")):
    from app.agents.distribution import classify_return

    artisan = await _artisan_for_session(session)
    orders = await queries.orders_for_artisan(artisan["id"])
    placed = [o for o in orders if o["status"] in {"placed", "shipped", "delivered"}]
    if not placed:
        return JSONResponse({"error": "no order to return — trigger an order first"}, status_code=400)
    order = placed[0]
    verdict = await classify_return(reason)
    row = await queries.create_return({"order_id": order["id"], "reason_text": reason, **verdict})
    listing = {"id": order["listing_id"], "title": order["listings"]["title"],
               "title_hi": order["listings"].get("title_hi")}
    enqueue(operations.notify_return(artisan, listing, row, console_transport), name="return-notify")
    return {"ok": True, **verdict}


@app.post("/demo/trigger-trend")
async def trigger_trend(session: str = Form(...)):
    from app.agents import trend

    artisan = await _artisan_for_session(session)
    artisan.setdefault("context", {})
    identity = None
    if artisan.get("seller_identity_id"):
        identity = await queries.get_seller_identity(artisan["seller_identity_id"])
    if not identity or identity.get("kyc_status") != "verified":
        enqueue(operations.notify_account_needed(artisan, console_transport), name="trend-blocked")
        return {"ok": True, "blocked": True}
    enqueue(trend.run_for_artisan(artisan, console_transport), name="trend")
    return {"ok": True}


@app.post("/demo/trigger-payout")
async def trigger_payout(session: str = Form(...)):
    artisan = await _artisan_for_session(session)
    orders = await queries.orders_for_artisan(artisan["id"])
    undelivered = [o for o in orders if o["status"] in {"placed", "shipped"}]
    if not undelivered:
        return JSONResponse({"error": "no undelivered order — place an order first"}, status_code=400)
    order = undelivered[-1]
    await queries.update_order(order["id"], {"status": "delivered"})
    listing = {"title": order["listings"]["title"], "title_hi": order["listings"].get("title_hi")}
    enqueue(
        operations.notify_payout(artisan, listing, in_hand_amount(order["amount"]), console_transport),
        name="payout-notify",
    )
    return {"ok": True, "order_id": order["id"]}


@app.post("/demo/advance-week")
async def advance_week(session: str = Form(...)):
    """Seed a week of sales + one return so the Trend agent has data (spec §12)."""
    artisan = await _artisan_for_session(session)
    live = await queries.listings_for_artisan(artisan["id"], ["live"])
    if not live:
        return JSONResponse({"error": "no live listing for this session"}, status_code=400)
    created = []
    for _ in range(3):
        listing = random.choice(live)
        order = await queries.create_order(
            {"listing_id": listing["id"], "buyer_ref": f"buyer_{random.randint(1000, 9999)}",
             "amount": listing["price"], "status": "delivered"}
        )
        created.append(order["id"])
    await queries.create_return(
        {"order_id": created[0], "reason_text": "रंग थोड़े हल्के थे",
         "classification": "quality", "rating_protected": False}
    )
    agentlog.log_event("distribution", "seeded a week of sales", {"orders": len(created), "returns": 1})
    return {"ok": True, "orders_created": len(created)}


@app.post("/demo/reset")
async def demo_reset():
    """Wipe all demo data for a clean run: DB rows, console outboxes, agent log."""
    counts = await queries.wipe_demo_data()
    web_console.reset()
    agentlog.clear()
    agentlog.log_event("system", "demo data reset", counts)
    return {"ok": True, "deleted": counts}


@app.on_event("startup")
async def _prewarm_pricing():
    """Warm the web-search price cache for the demo's common crafts so the first listing is fast."""
    import asyncio

    from app.services import market_prices

    asyncio.create_task(market_prices.prewarm("madhubani", "warli", "pattachitra"))


@app.get("/health")
async def health():
    return {"ok": True}


@app.get("/")
async def landing_page():
    return FileResponse(WEB_DIR / "landing.html")


@app.get("/demo")
async def demo_page():
    return FileResponse(WEB_DIR / "demo.html")


@app.get("/console")
async def console_page():
    return FileResponse(WEB_DIR / "console.html")


@app.get("/shop")
async def shop_page():
    return FileResponse(WEB_DIR / "shop.html")


@app.get("/v2")
async def v2_landing():
    return FileResponse(WEB_V2_DIR / "landing.html")


@app.get("/v2/demo")
async def v2_demo():
    return FileResponse(WEB_V2_DIR / "demo.html")


@app.get("/v2/console")
async def v2_console():
    return FileResponse(WEB_V2_DIR / "console.html")


@app.get("/v2/shop")
async def v2_shop():
    return FileResponse(WEB_V2_DIR / "shop.html")
