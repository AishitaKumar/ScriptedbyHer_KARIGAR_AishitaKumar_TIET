-- Migration 004: customer reviews (rating + comment) for aggregation by the
-- Trend agent and per-review appreciation notifications by Distribution.
create table if not exists reviews (
  id uuid primary key default gen_random_uuid(),
  order_id uuid not null references orders(id),
  rating int not null check (rating between 1 and 5),
  comment text,
  artisan_notified_at timestamptz,
  created_at timestamptz not null default now()
);
create index if not exists idx_reviews_order on reviews(order_id);

-- Exchange requests reuse the returns table via classification 'exchange'.
alter table returns drop constraint if exists returns_classification_check;
alter table returns add constraint returns_classification_check
  check (classification in ('rto', 'quality', 'other', 'exchange'));
