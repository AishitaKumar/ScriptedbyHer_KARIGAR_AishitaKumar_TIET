-- Migration 006: the artisan states the size of the piece (asked after the
-- photos pass), stored on the listing and shown to buyers.
alter table listings add column if not exists dimensions text;
