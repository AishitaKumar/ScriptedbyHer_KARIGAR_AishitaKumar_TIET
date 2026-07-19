-- Migration 005: store the Hindi listing title so artisan-facing voice notes
-- (orders, payouts, returns, exchange, reviews, trend) speak the craft name in
-- her language instead of the English Meesho title.
alter table listings add column if not exists title_hi text;
