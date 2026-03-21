"""FastAPI application with all endpoints, auth middleware, CORS, and rate limiting."""

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime, timezone
import json
import uuid
from pathlib import Path

from backend.config import API_KEY
from backend.agents.chat_agent import create_chat_agent

app = FastAPI(title="BRACE4PEACE Chat API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://ksvend.github.io"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting (in-memory, resets on restart)
_rate_limits: dict[str, dict] = {}  # key -> {"count": int, "date": str}
DAILY_LIMIT = 50

_chat_agent = None
_supabase = None
_hs_posts = None


def _get_chat_agent():
    global _chat_agent
    if _chat_agent is None:
        _chat_agent = create_chat_agent()
    return _chat_agent


def _get_supabase():
    global _supabase
    if _supabase is None:
        from backend.db import get_client

        _supabase = get_client()
    return _supabase


def _get_hs_posts():
    global _hs_posts
    if _hs_posts is None:
        path = (
            Path(__file__).resolve().parent.parent
            / "docs"
            / "data"
            / "hate_speech_posts.json"
        )
        if path.exists():
            _hs_posts = json.loads(path.read_text())
        else:
            _hs_posts = []
    return _hs_posts


async def verify_api_key(request: Request):
    """Validate X-API-Key header and enforce daily rate limit."""
    key = request.headers.get("X-API-Key")
    if key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    # Rate limiting
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if key not in _rate_limits or _rate_limits[key]["date"] != today:
        _rate_limits[key] = {"count": 0, "date": today}
    _rate_limits[key]["count"] += 1
    if _rate_limits[key]["count"] > DAILY_LIMIT:
        raise HTTPException(status_code=429, detail="Daily query limit exceeded")
    return key


# ---------------------------------------------------------------------------
# Pydantic request models
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    query: str
    session_id: str | None = None
    filters: dict | None = None


class FeedbackRequest(BaseModel):
    session_id: str
    feedback_type: str  # "helpful" or "not_helpful"


class VerificationRequest(BaseModel):
    finding_id: str
    action: str
    reviewer_name: str
    note: str | None = None
    corrections: dict | None = None


class AnnotationRequest(BaseModel):
    post_id: str
    action: str
    reviewer_name: str
    corrections: dict | None = None
    note: str | None = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/health")
async def health():
    """System status check -- no auth required."""
    return {"status": "healthy"}


@app.post("/chat")
async def chat(req: ChatRequest, _=Depends(verify_api_key)):
    """Main chat endpoint. Invokes the LangGraph chat agent."""
    agent = _get_chat_agent()
    session_id = req.session_id or str(uuid.uuid4())
    result = agent.invoke(
        {
            "query": req.query,
            "filters": req.filters or {},
            "session_id": session_id,
            "messages": [],
        }
    )
    # Log to chat_sessions
    try:
        client = _get_supabase()
        client.table("chat_sessions").insert(
            {
                "session_id": session_id,
                "query_text": req.query,
                "filters": req.filters,
                "response_text": result.get("response", ""),
                "sources_cited": result.get("sources", []),
                "confidence": result.get("confidence", "LOW"),
            }
        ).execute()
    except Exception:
        pass
    return {
        "response": result.get("response", ""),
        "sources": result.get("sources", []),
        "confidence": result.get("confidence", "LOW"),
        "session_id": session_id,
    }


@app.get("/chat/history/{session_id}")
async def chat_history(session_id: str, _=Depends(verify_api_key)):
    """Return conversation history for the given session."""
    client = _get_supabase()
    result = (
        client.table("chat_sessions")
        .select("*")
        .eq("session_id", session_id)
        .order("created_at")
        .execute()
    )
    return {"messages": result.data or []}


@app.post("/chat/feedback")
async def chat_feedback(req: FeedbackRequest, _=Depends(verify_api_key)):
    """Record lightweight feedback on a chat session."""
    try:
        client = _get_supabase()
        latest = (
            client.table("chat_sessions")
            .select("id")
            .eq("session_id", req.session_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if latest.data:
            client.table("chat_sessions").update(
                {"feedback": req.feedback_type}
            ).eq("id", latest.data[0]["id"]).execute()
    except Exception:
        pass
    return {"status": "recorded"}


@app.get("/knowledge/stats")
async def knowledge_stats(_=Depends(verify_api_key)):
    """Return high-level knowledge base statistics."""
    client = _get_supabase()
    chunks = client.table("document_chunks").select("id", count="exact").execute()
    findings = client.table("findings").select("id", count="exact").execute()
    pending = (
        client.table("findings")
        .select("id", count="exact")
        .eq("status", "UNVERIFIED")
        .execute()
    )
    meta = (
        client.table("system_metadata")
        .select("*")
        .eq("key", "last_research_run")
        .execute()
    )
    return {
        "total_chunks": chunks.count or 0,
        "total_findings": findings.count or 0,
        "pending_verification": pending.count or 0,
        "last_research_run": meta.data[0]["value"] if meta.data else None,
    }


@app.get("/knowledge/search")
async def knowledge_search(
    country: str | None = None,
    theme: str | None = None,
    classification: str | None = None,
    status: str | None = None,
    limit: int = 20,
    offset: int = 0,
    _=Depends(verify_api_key),
):
    """Filtered search over findings."""
    client = _get_supabase()
    q = client.table("findings").select("*", count="exact")
    if country:
        q = q.contains("country", [country])
    if theme:
        q = q.contains("theme", [theme])
    if classification:
        q = q.eq("classification", classification)
    if status:
        q = q.eq("status", status)
    result = (
        q.range(offset, offset + limit - 1)
        .order("created_at", desc=True)
        .execute()
    )
    return {"results": result.data or [], "total": result.count or 0}


@app.get("/verification/pending")
async def verification_pending(limit: int = 50, _=Depends(verify_api_key)):
    """Return unverified findings for human review."""
    client = _get_supabase()
    result = (
        client.table("findings")
        .select("*")
        .eq("status", "UNVERIFIED")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return {"findings": result.data or []}


@app.post("/verification/decide")
async def verification_decide(req: VerificationRequest, _=Depends(verify_api_key)):
    """Record a verification decision (VERIFY / FLAG / REJECT) on a finding."""
    client = _get_supabase()
    current = client.table("findings").select("*").eq("id", req.finding_id).execute()
    if not current.data:
        raise HTTPException(status_code=404, detail="Finding not found")
    old_status = current.data[0]["status"]
    new_status = {"VERIFY": "VERIFIED", "FLAG": "FLAGGED", "REJECT": "REJECTED"}[
        req.action
    ]
    update_data = {
        "status": new_status,
        "verified_by": req.reviewer_name,
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "verification_note": req.note,
    }
    if req.corrections:
        update_data.update(req.corrections)
    client.table("findings").update(update_data).eq("id", req.finding_id).execute()
    client.table("verification_log").insert(
        {
            "finding_id": req.finding_id,
            "reviewer_id": req.reviewer_name,
            "action": req.action,
            "note": req.note,
            "previous_status": old_status,
            "new_status": new_status,
        }
    ).execute()
    return {
        "finding_id": req.finding_id,
        "previous_status": old_status,
        "new_status": new_status,
    }


@app.get("/posts/review-queue")
async def posts_review_queue(
    country: str | None = None,
    subtype: str | None = None,
    limit: int = 20,
    offset: int = 0,
    _=Depends(verify_api_key),
):
    """Return hate-speech posts for human annotation, sorted by lowest confidence."""
    posts = _get_hs_posts()
    filtered = posts
    if country:
        filtered = [p for p in filtered if p.get("country") == country]
    if subtype:
        filtered = [p for p in filtered if subtype in (p.get("subtopics") or [])]
    filtered.sort(key=lambda p: p.get("eaHsConf", 1.0))
    page = filtered[offset : offset + limit]
    return {"posts": page, "total": len(filtered)}


@app.post("/posts/annotate")
async def posts_annotate(req: AnnotationRequest, _=Depends(verify_api_key)):
    """Save a human annotation for a hate-speech post."""
    client = _get_supabase()
    client.table("post_annotations").insert(
        {
            "post_id": req.post_id,
            "reviewer": req.reviewer_name,
            "action": req.action,
            "corrections": req.corrections,
            "note": req.note,
        }
    ).execute()
    return {"post_id": req.post_id, "action": req.action, "status": "saved"}
