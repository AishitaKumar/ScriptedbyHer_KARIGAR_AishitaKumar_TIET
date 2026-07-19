-- Migration 002: scratch context for the state machine (unconfirmed values live
-- here until the user confirms them — spec §10 invariant: confirmed data only
-- in real columns).
alter table artisans add column if not exists context jsonb not null default '{}'::jsonb;
