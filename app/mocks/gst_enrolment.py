"""Mock GST-portal Enrolment ID (EID) issuance."""

from __future__ import annotations

import asyncio
import random
import string
import uuid

_pending: dict[str, dict] = {}

REQUIRED_FIELDS = ("legal_name", "pan_ref", "bank_account_ref", "ifsc", "otp_phone", "pincode")


async def submit_enrolment(payload: dict) -> dict:
    missing = [f for f in REQUIRED_FIELDS if not payload.get(f)]
    if missing:
        return {"status": "rejected", "error": f"missing fields: {', '.join(missing)}"}
    await asyncio.sleep(2)
    application_id = str(uuid.uuid4())
    _pending[application_id] = payload
    return {"status": "pending", "otp_required": True, "application_id": application_id}


async def confirm_otp(application_id: str, otp: str) -> dict:
    if application_id not in _pending:
        return {"status": "rejected", "error": "unknown application_id"}
    if not (otp.isdigit() and len(otp) == 6):
        return {"status": "otp_invalid", "error": "OTP must be 6 digits"}
    await asyncio.sleep(2)
    _pending.pop(application_id)
    eid = "10" + "".join(random.choices(string.ascii_uppercase + string.digits, k=10)) + "".join(
        random.choices(string.digits, k=3)
    )
    return {"status": "issued", "enrolment_id": eid}
