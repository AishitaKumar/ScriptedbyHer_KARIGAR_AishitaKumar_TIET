-- Migration 007: record buyer demand for the base (non-artisan) catalogue so the
-- Trend agent can say "similar <craft> is selling well right now" even before the
-- artisan's own pieces sell. Only relevant crafts are tagged/recorded.
create table if not exists market_demand (
  id uuid primary key default gen_random_uuid(),
  craft_type text not null,
  created_at timestamptz not null default now()
);
create index if not exists idx_market_demand_created on market_demand(created_at);
