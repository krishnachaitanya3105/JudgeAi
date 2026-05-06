-- ══════════════════════════════════════════════════════════════════
-- JudgeAI Migration 2026-03: Durable Processing Status
-- Run in Supabase SQL editor ONCE.
-- ══════════════════════════════════════════════════════════════════

-- Add granular processing-status tracking to cases table.
-- This lets the backend survive restarts without losing job progress.

ALTER TABLE cases
  ADD COLUMN IF NOT EXISTS processing_status  TEXT    DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS processing_stage   TEXT    DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS processing_error   TEXT    DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS processing_started_at   TIMESTAMPTZ DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS processing_finished_at  TIMESTAMPTZ DEFAULT NULL;

-- Index for frontend polling by case pdf_url
CREATE INDEX IF NOT EXISTS idx_cases_processing_status ON cases(processing_status);
CREATE INDEX IF NOT EXISTS idx_cases_pdf_url           ON cases(pdf_url);

-- ══════════════════════════════════════════════════════════════════
