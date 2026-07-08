-- Optional helper for manual PostgreSQL setup after Alembic has created document_chunks.
-- Adjust vector(1536) to match EMBEDDING_DIMENSION if your hosted embedding model differs.
ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS embedding_vector vector(1536);
CREATE INDEX IF NOT EXISTS ix_document_chunks_embedding_vector
  ON document_chunks USING ivfflat (embedding_vector vector_cosine_ops);
