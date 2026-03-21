"""Supabase client helpers."""
from supabase import create_client, Client
from backend.config import SUPABASE_URL, SUPABASE_KEY

_client: Client | None = None


def get_client() -> Client:
    global _client
    if _client is None:
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client


def search_chunks(embedding: list[float], filters: dict | None = None,
                  top_k: int = 10) -> list[dict]:
    """Semantic search against document_chunks using pgvector."""
    client = get_client()
    params = {
        "query_embedding": embedding,
        "match_count": top_k,
        "filter_country": filters.get("country") if filters else None,
        "filter_theme": filters.get("theme") if filters else None,
        "filter_verified_only": filters.get("verified_only", False) if filters else False,
    }
    result = client.rpc("match_documents", params).execute()
    return result.data


def query_stats(stat_type: str, country: str | None = None) -> list[dict]:
    """Query pre-computed aggregated stats."""
    client = get_client()
    q = client.table("aggregated_stats").select("*").eq("stat_type", stat_type)
    if country:
        q = q.eq("country", country)
    return q.execute().data
