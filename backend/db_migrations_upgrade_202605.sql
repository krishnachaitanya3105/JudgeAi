-- JudgeAI Migration 2026-05: Durable async job identity + heartbeat recovery
-- Safe, non-destructive schema alignment for the async upload pipeline.

CREATE EXTENSION IF NOT EXISTS vector;

ALTER TABLE IF EXISTS cases
  ADD COLUMN IF NOT EXISTS processing_status TEXT DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS processing_stage TEXT DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS processing_error TEXT DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS processing_job_id TEXT DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS processing_started_at TIMESTAMPTZ DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS processing_finished_at TIMESTAMPTZ DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS processing_heartbeat_at TIMESTAMPTZ DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS layout_blocks JSONB DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS embedding vector(384);

ALTER TABLE IF EXISTS extracted_actions
  ADD COLUMN IF NOT EXISTS action_plan JSONB DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS action_plan_reasoning JSONB DEFAULT NULL;

CREATE INDEX IF NOT EXISTS idx_cases_processing_status ON cases(processing_status);
CREATE INDEX IF NOT EXISTS idx_cases_processing_job_id ON cases(processing_job_id);
CREATE INDEX IF NOT EXISTS idx_cases_processing_stage ON cases(processing_stage);
CREATE INDEX IF NOT EXISTS idx_cases_pdf_url ON cases(pdf_url);
