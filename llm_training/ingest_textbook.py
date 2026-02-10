#!/usr/bin/env python3
"""
Ingest a textbook PDF for RAG: chunk, embed, store in Supabase.

Usage:
  python ingest_textbook.py path/to/textbook.pdf "Public Speaking Handbook"
  python ingest_textbook.py path/to/textbook.pdf "Speech 101" --institution-id <uuid>

  With institution (optional): --institution-id <uuid> from institutions.id

Requires:
  pip install pymupdf sentence-transformers psycopg2-binary python-dotenv

Environment:
  SUPABASE_DB_URL  - Postgres connection string (Supabase → Settings → Database → Connection string)
                     e.g. postgresql://postgres.[ref]:[password]@aws-0-us-east-1.pooler.supabase.com:6543/postgres
  Or: DATABASE_URL - Same format (alternative name)
"""

import argparse
import os
import sys
from pathlib import Path

# Load .env from repo root
try:
    from dotenv import load_dotenv
    _repo_root = Path(__file__).resolve().parent.parent
    load_dotenv(_repo_root / ".env")
except ImportError:
    pass


def extract_text_from_pdf(pdf_path: str) -> list[tuple[str, dict]]:
    """Extract text from PDF. Returns list of (chunk_text, metadata)."""
    import fitz  # pymupdf

    doc = fitz.open(pdf_path)
    chunks = []
    chunk_tokens_target = 400  # ~300 words
    overlap = 50

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()
        if not text.strip():
            continue

        # Simple chunking: split by paragraphs, then merge to ~target size
        paras = [p.strip() for p in text.split("\n\n") if p.strip()]
        current = []
        current_len = 0

        for p in paras:
            tokens_approx = len(p.split())  # rough token estimate
            if current_len + tokens_approx > chunk_tokens_target and current:
                chunk_text = "\n\n".join(current)
                chunks.append((chunk_text, {"page": page_num + 1}))
                # overlap: keep last few paras
                overlap_paras = []
                overlap_len = 0
                for x in reversed(current):
                    if overlap_len + len(x.split()) <= overlap:
                        overlap_paras.insert(0, x)
                        overlap_len += len(x.split())
                    else:
                        break
                current = overlap_paras
                current_len = overlap_len

            current.append(p)
            current_len += tokens_approx

        if current:
            chunk_text = "\n\n".join(current)
            chunks.append((chunk_text, {"page": page_num + 1}))

    doc.close()
    return chunks


def embed_chunks(chunks: list[tuple[str, dict]], model_name: str = "all-MiniLM-L6-v2") -> list[list[float]]:
    """Embed chunks using sentence-transformers."""
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(model_name)
    texts = [c[0] for c in chunks]
    embeddings = model.encode(texts, show_progress_bar=True)
    return embeddings.tolist()


def store_chunks(
    textbook_id: str,
    chunks: list[tuple[str, dict]],
    embeddings: list[list[float]],
    db_url: str,
) -> None:
    """Insert chunks into textbook_chunks via Postgres."""
    import json
    import psycopg2
    from psycopg2.extras import execute_values

    conn = psycopg2.connect(db_url)
    try:
        with conn.cursor() as cur:
            rows = [
                (textbook_id, i, chunk_text, str(embedding), json.dumps(metadata or {}))
                for i, ((chunk_text, metadata), embedding) in enumerate(zip(chunks, embeddings))
            ]
            execute_values(
                cur,
                """
                INSERT INTO textbook_chunks (textbook_id, chunk_index, chunk_text, embedding, metadata)
                VALUES %s
                """,
                rows,
                template="(%s, %s, %s, %s::vector, %s::jsonb)",
            )
        conn.commit()
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Ingest textbook PDF for RAG")
    parser.add_argument("pdf_path", help="Path to textbook PDF")
    parser.add_argument("name", help="Textbook name (e.g. 'Public Speaking Handbook')")
    parser.add_argument("--institution-id", default=None, help="Optional institution UUID")
    parser.add_argument("--embedding-model", default="all-MiniLM-L6-v2", help="Sentence-transformers model")
    args = parser.parse_args()

    pdf_path = Path(args.pdf_path)
    if not pdf_path.exists():
        print(f"Error: {pdf_path} not found")
        sys.exit(1)

    db_url = os.environ.get("SUPABASE_DB_URL") or os.environ.get("DATABASE_URL")
    if not db_url:
        print("Error: Set SUPABASE_DB_URL or DATABASE_URL in .env")
        print("Supabase → Settings → Database → Connection string (URI, Transaction mode)")
        sys.exit(1)

    # 1. Create textbook row
    import psycopg2
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO textbooks (name, institution_id) VALUES (%s, %s) RETURNING id",
        (args.name, args.institution_id),
    )
    textbook_id = str(cur.fetchone()[0])
    conn.commit()
    cur.close()
    conn.close()
    print(f"Created textbook: {args.name} (id={textbook_id})")

    # 2. Extract chunks
    print("Extracting text from PDF...")
    chunks = extract_text_from_pdf(str(pdf_path))
    print(f"  Extracted {len(chunks)} chunks")

    # 3. Embed
    print(f"Embedding with {args.embedding_model}...")
    embeddings = embed_chunks(chunks, args.embedding_model)

    # 4. Store
    print("Storing in textbook_chunks...")
    store_chunks(textbook_id, chunks, embeddings, db_url)
    print(f"Done. Textbook id: {textbook_id}")
    print("Link this textbook_id to rubrics (textbook_id column) to enable RAG during evaluation.")


if __name__ == "__main__":
    main()
