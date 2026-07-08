-- Optional helper for manual PostgreSQL setup after Alembic has created document_chunks.
-- Docker also mounts this file during database bootstrap, before Alembic creates tables,
-- so it must be safe to run when document_chunks does not exist yet.
-- Default vector(64) matches local deterministic embeddings. Adjust it to match
-- EMBEDDING_DIMENSION before running manually with a real embedding provider.
CREATE EXTENSION IF NOT EXISTS vector;

DO $$
BEGIN
  IF to_regclass('public.document_chunks') IS NOT NULL THEN
    ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS embedding_vector vector(64);
    CREATE INDEX IF NOT EXISTS ix_document_chunks_embedding_vector
      ON document_chunks USING ivfflat (embedding_vector vector_cosine_ops);
  END IF;
END $$;
