"""Meesho service interface — the ONLY boundary Karigar's code uses for marketplace operations."""

from __future__ import annotations

from app.mocks import meesho_api as _impl

create_seller_account = _impl.create_seller_account
confirm_seller_otp = _impl.confirm_seller_otp
lookup_gstin = _impl.lookup_gstin
create_listing = _impl.create_listing
update_listing = _impl.update_listing
cancel_pickup = _impl.cancel_pickup
get_category_comparables = _impl.get_category_comparables
