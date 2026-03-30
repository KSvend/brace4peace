"""Tests for blind annotation endpoints."""

import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import MagicMock

os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-key")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "test-key")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("API_KEY", "test-api-key")

from backend.app import app


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ---------------------------------------------------------------------------
# POST /posts/blind-annotate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_blind_annotate_success(client, mocker):
    mock_table = MagicMock()
    mock_table.insert.return_value.execute.return_value = MagicMock(data=[{"id": "abc"}])
    mock_client = MagicMock()
    mock_client.table.return_value = mock_table
    mocker.patch("backend.app._get_supabase", return_value=mock_client)

    resp = await client.post(
        "/posts/blind-annotate",
        json={
            "post_id": "post-123",
            "reviewer_name": "annotator_kenya",
            "pass_number": 1,
            "classification": "Hate",
            "subtype": "Incitement",
            "confidence": "High",
            "note": "Clear hate speech",
        },
        headers={"X-API-Key": "test-api-key"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["post_id"] == "post-123"
    assert data["pass"] == 1
    assert data["status"] == "saved"


@pytest.mark.asyncio
async def test_blind_annotate_minimal_fields(client, mocker):
    """Only required fields — optional ones default to None."""
    mock_table = MagicMock()
    mock_table.insert.return_value.execute.return_value = MagicMock(data=[])
    mock_client = MagicMock()
    mock_client.table.return_value = mock_table
    mocker.patch("backend.app._get_supabase", return_value=mock_client)

    resp = await client.post(
        "/posts/blind-annotate",
        json={
            "post_id": "post-456",
            "reviewer_name": "annotator_sudan",
            "pass_number": 2,
            "classification": "Normal",
        },
        headers={"X-API-Key": "test-api-key"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "saved"


@pytest.mark.asyncio
async def test_blind_annotate_inserts_correct_payload(client, mocker):
    """Verify the exact payload sent to Supabase."""
    mock_table = MagicMock()
    mock_table.insert.return_value.execute.return_value = MagicMock(data=[])
    mock_client = MagicMock()
    mock_client.table.return_value = mock_table
    mocker.patch("backend.app._get_supabase", return_value=mock_client)

    await client.post(
        "/posts/blind-annotate",
        json={
            "post_id": "post-789",
            "reviewer_name": "annotator_ethiopia",
            "pass_number": 1,
            "classification": "Abusive",
            "confidence": "Medium",
        },
        headers={"X-API-Key": "test-api-key"},
    )

    mock_client.table.assert_called_with("blind_annotations")
    inserted = mock_table.insert.call_args[0][0]
    assert inserted["post_id"] == "post-789"
    assert inserted["reviewer"] == "annotator_ethiopia"
    assert inserted["pass"] == 1
    assert inserted["classification"] == "Abusive"
    assert inserted["confidence"] == "Medium"
    assert inserted["subtype"] is None
    assert inserted["note"] is None


# ---------------------------------------------------------------------------
# GET /posts/blind-review-queue
# ---------------------------------------------------------------------------

SAMPLE_POSTS = [
    {"i": "post-aaa", "t": "text A", "c": "Kenya"},
    {"i": "post-bbb", "t": "text B", "c": "Sudan"},
    {"i": "post-ccc", "t": "text C", "c": "Kenya"},
]

SAMPLE_MANIFEST = {
    "post-aaa": {"post_id": "post-aaa", "primary_annotator": "annotator_kenya", "cross_annotator": ""},
    "post-bbb": {"post_id": "post-bbb", "primary_annotator": "annotator_sudan", "cross_annotator": "annotator_kenya"},
    "post-ccc": {"post_id": "post-ccc", "primary_annotator": "annotator_kenya", "cross_annotator": ""},
}


@pytest.mark.asyncio
async def test_blind_review_queue_primary_annotator(client, mocker):
    mocker.patch("backend.app._get_blind_posts", return_value=SAMPLE_POSTS)
    mocker.patch("backend.app._get_blind_manifest", return_value=SAMPLE_MANIFEST)

    resp = await client.get(
        "/posts/blind-review-queue?reviewer=annotator_kenya",
        headers={"X-API-Key": "test-api-key"},
    )
    assert resp.status_code == 200
    data = resp.json()
    # annotator_kenya is primary for post-aaa, post-ccc and cross for post-bbb
    assert data["total"] == 3
    ids = {p["i"] for p in data["posts"]}
    assert ids == {"post-aaa", "post-bbb", "post-ccc"}


@pytest.mark.asyncio
async def test_blind_review_queue_different_reviewer(client, mocker):
    mocker.patch("backend.app._get_blind_posts", return_value=SAMPLE_POSTS)
    mocker.patch("backend.app._get_blind_manifest", return_value=SAMPLE_MANIFEST)

    resp = await client.get(
        "/posts/blind-review-queue?reviewer=annotator_sudan",
        headers={"X-API-Key": "test-api-key"},
    )
    assert resp.status_code == 200
    data = resp.json()
    # annotator_sudan is primary only for post-bbb
    assert data["total"] == 1
    assert data["posts"][0]["i"] == "post-bbb"


@pytest.mark.asyncio
async def test_blind_review_queue_unknown_reviewer(client, mocker):
    mocker.patch("backend.app._get_blind_posts", return_value=SAMPLE_POSTS)
    mocker.patch("backend.app._get_blind_manifest", return_value=SAMPLE_MANIFEST)

    resp = await client.get(
        "/posts/blind-review-queue?reviewer=nobody",
        headers={"X-API-Key": "test-api-key"},
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


@pytest.mark.asyncio
async def test_blind_review_queue_pagination(client, mocker):
    mocker.patch("backend.app._get_blind_posts", return_value=SAMPLE_POSTS)
    mocker.patch("backend.app._get_blind_manifest", return_value=SAMPLE_MANIFEST)

    resp = await client.get(
        "/posts/blind-review-queue?reviewer=annotator_kenya&limit=2&offset=0",
        headers={"X-API-Key": "test-api-key"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["posts"]) == 2
    assert data["total"] == 3
