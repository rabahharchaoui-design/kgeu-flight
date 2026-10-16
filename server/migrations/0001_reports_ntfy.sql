-- ntfyfix (2026-10-15): the outcome of each report's phone push, kept on the row. Adds one
-- nullable column; every existing row stays as it is (ntfy null: from before this column).
-- Applied once to the live database with
--   npx wrangler d1 execute pfs-scores --remote -y --file=migrations/0001_reports_ntfy.sql
-- A fresh database built from schema.sql already has the column: do not run this on it.
ALTER TABLE reports ADD COLUMN ntfy TEXT;
