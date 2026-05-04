-- JudgeAI Cursor upgrade additions (run in Supabase SQL editor)
-- pgvector semantic search + action_plan columns + nullable notification user_id

CREATE EXTENSION IF NOT EXISTS vector;

ALTER TABLE IF EXISTS extracted_actions
  ADD COLUMN IF NOT EXISTS action_plan JSONB DEFAULT NULL;

ALTER TABLE IF EXISTS extracted_actions
  ADD COLUMN IF NOT EXISTS action_plan_reasoning JSONB DEFAULT NULL;

ALTER TABLE IF EXISTS cases
  ADD COLUMN IF NOT EXISTS layout_blocks JSONB DEFAULT NULL;

ALTER TABLE IF EXISTS cases
  ADD COLUMN IF NOT EXISTS embedding vector(384);

-- After you have embeddings in production, add a cosine index in Supabase, e.g.:
-- CREATE INDEX idx_cases_embedding_hnsw ON cases USING hnsw (embedding vector_cosine_ops);

ALTER TABLE notifications ALTER COLUMN user_id DROP NOT NULL;

COMMENT ON COLUMN cases.embedding IS '384-d MiniLM normalized embedding for cosine search';

COMMENT ON COLUMN extracted_actions.action_plan IS 'Structured government decision output';

CREATE OR REPLACE FUNCTION match_cases_semantic(
  query_embedding vector(384),
  match_limit int DEFAULT 10
)
RETURNS TABLE (
  id uuid,
  case_number varchar,
  pdf_url text,
  similarity float
)
LANGUAGE sql
STABLE
AS $$
  SELECT
    c.id,
    c.case_number::varchar,
    c.pdf_url::text,
    (1 - (c.embedding <=> query_embedding))::float AS similarity
  FROM cases c
  WHERE c.embedding IS NOT NULL
  ORDER BY c.embedding <=> query_embedding
  LIMIT match_limit;
$$;
