-- Textbook RAG: vector storage for textbook content retrieval
-- Run in Supabase SQL Editor

-- Enable pgvector extension (one-time)
CREATE EXTENSION IF NOT EXISTS vector;

-- Textbooks (one per book/edition)
CREATE TABLE IF NOT EXISTS textbooks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  institution_id uuid REFERENCES institutions(id),
  name text NOT NULL,
  created_at timestamptz DEFAULT now()
);

-- Chunks with embeddings (384 for sentence-transformers, 1536 for OpenAI)
CREATE TABLE IF NOT EXISTS textbook_chunks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  textbook_id uuid NOT NULL REFERENCES textbooks(id) ON DELETE CASCADE,
  chunk_index int NOT NULL,
  chunk_text text NOT NULL,
  embedding vector(384),
  metadata jsonb DEFAULT '{}',
  created_at timestamptz DEFAULT now()
);

-- Vector similarity search index
CREATE INDEX IF NOT EXISTS textbook_chunks_embedding_idx
  ON textbook_chunks USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);

-- Link rubrics to a textbook (optional: use course-level instead)
ALTER TABLE rubrics ADD COLUMN IF NOT EXISTS textbook_id uuid REFERENCES textbooks(id);

COMMENT ON TABLE textbooks IS 'Textbooks for RAG retrieval during evaluation';
COMMENT ON TABLE textbook_chunks IS 'Embedded text chunks from textbooks';
COMMENT ON COLUMN textbook_chunks.metadata IS 'e.g. {"chapter": "5", "section": "Verbal Citations", "page": 127}';
