-- Migration 003: KYC-first seller accounts — GSTIN route, email alias,
-- registered vs pickup address, registration type.
alter table seller_identities add column if not exists gstin text;
alter table seller_identities add column if not exists business_name text;
alter table seller_identities add column if not exists email text;
alter table seller_identities add column if not exists registered_address text;
alter table seller_identities add column if not exists pickup_address text;
alter table seller_identities add column if not exists registration_type text
  check (registration_type in ('gstin', 'eid'));
