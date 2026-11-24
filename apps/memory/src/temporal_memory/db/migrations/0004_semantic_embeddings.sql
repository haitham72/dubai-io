-- U4: Local semantic embeddings on facts (pgvector 1024-d for BAAI/bge-m3) for hybrid retrieval.
DO $$
BEGIN
    PERFORM pg_advisory_xact_lock(hashtextextended('temporal_memory:ext:vector', 0));
    CREATE EXTENSION IF NOT EXISTS vector SCHEMA public;
END $$;

ALTER TABLE facts
    ADD COLUMN IF NOT EXISTS embedding public.vector(1024),
    ADD COLUMN IF NOT EXISTS embedding_model TEXT,
    ADD COLUMN IF NOT EXISTS embedded_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_facts_embedding_hnsw
    ON facts USING hnsw (embedding public.vector_cosine_ops)
    WHERE embedding IS NOT NULL AND erased_at IS NULL AND status <> 'history';
