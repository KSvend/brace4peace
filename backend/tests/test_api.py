"""Tests for the FastAPI application endpoints."""

import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, MagicMock

# Set env vars before importing app
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-key")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "test-key")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("API_KEY", "test-api-key")

from backend.app import app, _rate_limits, DAILY_LIMIT


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture(autouse=True)
def reset_rate_limits():
    """Clear rate-limit state between tests."""
    _rate_limits.clear()
    yield
    _rate_limits.clear()


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_no_auth(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


# ---------------------------------------------------------------------------
# Auth & rate limiting
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_chat_requires_auth(client):
    resp = await client.post("/chat", json={"query": "test"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_invalid_api_key_rejected(client):
    resp = await client.post(
        "/chat",
        json={"query": "test"},
        headers={"X-API-Key": "wrong-key"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_rate_limit_enforced(client, mocker):
    mocker.patch("backend.app._get_chat_agent")
    mocker.patch("backend.app._get_supabase")
    # Exhaust the daily limit
    _rate_limits["test-api-key"] = {
        "count": DAILY_LIMIT,
        "date": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ).strftime("%Y-%m-%d"),
    }
    resp = await client.post(
        "/chat",
        json={"query": "one more"},
        headers={"X-API-Key": "test-api-key"},
    )
    assert resp.status_code == 429


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_chat_with_valid_key(client, mocker):
    mock_agent = mocker.patch("backend.app._get_chat_agent")
    mock_agent.return_value.invoke.return_value = {
        "response": "Test response [Source](https://example.com)",
        "sources": [{"title": "Source", "source_url": "https://example.com"}],
        "confidence": "HIGH",
        "session_id": "s1",
    }
    mocker.patch("backend.app._get_supabase")
    resp = await client.post(
        "/chat",
        json={"query": "test question"},
        headers={"X-API-Key": "test-api-key"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "response" in data
    assert data["confidence"] == "HIGH"
    assert "session_id" in data


# ---------------------------------------------------------------------------
# Feedback
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_feedback_endpoint(client, mocker):
    mocker.patch("backend.app._get_supabase")
    resp = await client.post(
        "/chat/feedback",
        json={"session_id": "s1", "feedback_type": "helpful"},
        headers={"X-API-Key": "test-api-key"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "recorded"


# ---------------------------------------------------------------------------
# Posts review queue (uses local JSON, no Supabase)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_posts_review_queue(client, mocker):
    mocker.patch(
        "backend.app._get_hs_posts",
        return_value=[
            {"id": "p1", "country": "Kenya", "eaHsConf": 0.5, "subtopics": ["hate"]},
            {"id": "p2", "country": "Sudan", "eaHsConf": 0.3, "subtopics": ["threat"]},
        ],
    )
    resp = await client.get(
        "/posts/review-queue",
        headers={"X-API-Key": "test-api-key"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    # Sorted by eaHsConf ascending
    assert data["posts"][0]["id"] == "p2"


@pytest.mark.asyncio
async def test_posts_review_queue_filter_country(client, mocker):
    mocker.patch(
        "backend.app._get_hs_posts",
        return_value=[
            {"id": "p1", "country": "Kenya", "eaHsConf": 0.5},
            {"id": "p2", "country": "Sudan", "eaHsConf": 0.3},
        ],
    )
    resp = await client.get(
        "/posts/review-queue?country=Kenya",
        headers={"X-API-Key": "test-api-key"},
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 1
