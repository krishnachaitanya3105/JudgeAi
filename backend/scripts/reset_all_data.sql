-- =============================================================================
-- JudgeAI — reset application data for end-to-end retesting
-- Run in Supabase SQL editor (or psql against your project DB).
--
-- Clears: cases (+ layout_blocks/embeddings via row delete), extracted_actions,
--         verification_queue rows that reference extracted_actions, notifications,
--         audit_logs.
-- Keeps:  public.users (officer/admin profiles).
--
-- NOT cleared here:
--   • auth.users — use Supabase Dashboard → Authentication if you must wipe logins.
--   • Storage bucket PDFs — delete objects in Storage UI if you need a cold start.
-- =============================================================================

BEGIN;

TRUNCATE TABLE notifications RESTART IDENTITY;

TRUNCATE TABLE audit_logs RESTART IDENTITY;

-- FK chain: extracted_actions → cases ; verification_queue → extracted_actions
TRUNCATE TABLE cases CASCADE;

COMMIT;

-- Optional: wipe user profiles registered in app table (still does not remove auth.users):
-- BEGIN;
-- TRUNCATE TABLE users RESTART IDENTITY CASCADE;
-- COMMIT;
