"""
Textbook RAG retrieval: fetch relevant textbook chunks for evaluation prompts.

Usage:
  chunks = get_relevant_chunks(textbook_id, ["verbal citation", "eye contact"], top_k=5)

Requires: sentence-transformers, psycopg2-binary
Environment: SUPABASE_DB_URL or DATABASE_URL
"""

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    _repo_root = Path(__file__).resolve().parent.parent
    load_dotenv(_repo_root / ".env")
except ImportError:
    pass

_embedding_model = None
_embedding_model_name = "all-MiniLM-L6-v2"


def _get_embedding_model():
    """Lazy-load sentence-transformers model."""
    global _embedding_model
    if _embedding_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _embedding_model = SentenceTransformer(_embedding_model_name)
        except ImportError:
            return None
    return _embedding_model


def get_relevant_chunks(
    textbook_id: str,
    queries: list[str],
    top_k: int = 5,
    db_url: str | None = None,
) -> list[str]:
    """
    Retrieve top_k most relevant textbook chunks for the given queries.

    Args:
        textbook_id: UUID of the textbook
        queries: List of search strings (e.g. rubric category names)
        top_k: Number of chunks to return
        db_url: Postgres URL (default: SUPABASE_DB_URL or DATABASE_URL)

    Returns:
        List of chunk text strings (may be empty if retrieval fails)
    """
    if not textbook_id or not queries:
        return []

    db_url = db_url or os.environ.get("SUPABASE_DB_URL") or os.environ.get("DATABASE_URL")
    if not db_url:
        return []

    model = _get_embedding_model()
    if model is None:
        return []

    # Combine queries into one search string and embed
    combined = " ".join(q.strip() for q in queries if q and q.strip())
    if not combined:
        return []
    query_embedding = model.encode([combined], show_progress_bar=False)[0].tolist()

    try:
        import psycopg2
        conn = psycopg2.connect(db_url)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT chunk_text
                    FROM textbook_chunks
                    WHERE textbook_id = %s
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                    """,
                    (textbook_id, str(query_embedding), top_k),
                )
                rows = cur.fetchall()
                return [r[0] for r in rows if r[0]]
        finally:
            conn.close()
    except Exception:
        return []
