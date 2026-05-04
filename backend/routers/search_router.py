"""Semantic search over case embeddings."""

from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Query

from backend.config import get_supabase
from backend.services.embedding_service import generate_embedding

router = APIRouter()


@router.get("/search-semantic")
async def search_semantic(q: str = Query(..., min_length=2), limit: int = Query(10, ge=1, le=50)) -> Dict[str, Any]:
    vec = generate_embedding(q)
    supabase = get_supabase()

    try:
        resp = supabase.rpc(
            "match_cases_semantic",
            {"query_embedding": vec, "match_limit": limit},
        ).execute()
        rows = resp.data or []
        return {"query": q, "limit": limit, "results": rows}
    except Exception:
        fallback = _fallback_text_search(q, limit, supabase)
        return {
            "query": q,
            "limit": limit,
            "results": fallback,
            "note": "RPC match_cases_semantic unavailable—using text fallback.",
        }


def _fallback_text_search(q: str, limit: int, supabase) -> List[Dict[str, Any]]:
    try:
        resp = (
            supabase.table("cases")
            .select("case_number,pdf_url,created_at,id")
            .ilike("case_number", f"%{q}%")
            .limit(limit)
            .execute()
        )
        return [
            {"id": row.get("id"), "case_number": row.get("case_number"), "pdf_url": row.get("pdf_url"), "similarity": 0.5}
            for row in (resp.data or [])
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {e}")
