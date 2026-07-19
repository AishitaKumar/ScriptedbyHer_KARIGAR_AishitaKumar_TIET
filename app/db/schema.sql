-- Karigar schema (Supabase / Postgres). Run in the Supabase SQL editor.
-- Spec §10: shared memory — the orchestrator holds NO state in process memory.

create table if not exists seller_identities (
  id uuid primary key default gen_random_uuid(),
  legal_name text,
  pan_ref text,                -- masked/reference, never full PAN in logs
  bank_account_ref text,
  ifsc text,
  otp_phone text,
  enrolment_id text,
  kyc_status text not null default 'collecting'
    check (kyc_status in ('collecting', 'awaiting_otp_device', 'verified')),
  -- name-match across PAN, passbook, OTP phone, confirmed by OCR + user confirmation
  consistency_verified boolean not null default false,
  created_at timestamptz not null default now()
);

create table if not exists artisans (
  id uuid primary key default gen_random_uuid(),
  name text,
  village text,
  pincode text,
  craft text,
  language_code text not null default 'hi',
  photo_url text,
  onboarding_partner_phone text,
  whatsapp_phone text unique,
  -- may be her own or a family member's (Identity Anchor model, spec §8)
  seller_identity_id uuid references seller_identities(id),
  -- explicit state machine step; drives orchestrator routing
  onboarding_state text not null default 'new',
  created_at timestamptz not null default now()
);

create table if not exists listings (
  id uuid primary key default gen_random_uuid(),
  artisan_id uuid not null references artisans(id),
  craft_type text,
  style text,
  motifs text[],
  title text,
  description text,
  price int,
  original_price int,
  photo_urls text[],
  enhanced_photo_url text,
  gi_status text not null default 'unverified'
    check (gi_status in ('verified', 'unverified', 'rejected')),
  quality_score text,
  authenticity_score int,
  authenticity_reasons text[],
  status text not null default 'draft'
    check (status in ('draft', 'pending_approval', 'live', 'out_of_stock', 'rejected')),
  meesho_listing_id text,
  created_at timestamptz not null default now()
);

create table if not exists orders (
  id uuid primary key default gen_random_uuid(),
  listing_id uuid not null references listings(id),
  buyer_ref text,
  amount int,
  status text not null default 'placed'
    check (status in ('placed', 'shipped', 'delivered', 'returned', 'cancelled')),
  artisan_notified_at timestamptz,
  created_at timestamptz not null default now()
);

create table if not exists returns (
  id uuid primary key default gen_random_uuid(),
  order_id uuid not null references orders(id),
  reason_text text,
  classification text check (classification in ('rto', 'quality', 'other')),
  rating_protected boolean,
  artisan_notified_at timestamptz,
  created_at timestamptz not null default now()
);

create table if not exists voice_messages (
  id uuid primary key default gen_random_uuid(),
  artisan_id uuid references artisans(id),
  direction text not null check (direction in ('inbound', 'outbound')),
  transcript text,
  audio_url text,
  intent text,
  language_code text not null default 'hi',
  created_at timestamptz not null default now()
);

create index if not exists idx_artisans_whatsapp on artisans(whatsapp_phone);
create index if not exists idx_listings_artisan on listings(artisan_id);
create index if not exists idx_orders_listing on orders(listing_id);
