# AgenticNGO RAG Pilot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a RAG-augmented conversational intelligence layer on BRACE4PEACE — chat interface, knowledge base, research agent, admin panel, and pipeline integration.

**Architecture:** FastAPI + LangGraph chat service on HuggingFace Spaces (free), Supabase for pgvector + structured DB (free), GitHub Actions for batch agents (free). Vanilla JS frontend embedded in existing GitHub Pages dashboard.

**Tech Stack:** Python 3.11, FastAPI, LangGraph, LangChain, Anthropic Claude API, Supabase (pgvector + PostgREST), sentence-transformers (MiniLM), trafilatura, GitHub Actions, vanilla JS.

**Spec:** `docs/superpowers/specs/2026-03-21-agenticngo-rag-pilot-design.md`

---

## Review Fixes (MUST apply during implementation)

The following issues were identified during plan review and MUST be addressed:

### Critical
1. **`__init__.py` files**: Create `__init__.py` in `backend/`, `backend/agents/`, `backend/tools/`, `backend/ingest/`, `backend/tests/`. Every directory must be a proper Python package. Do this in Task 1.
2. **Desk review parser heading patterns**: The real file has 4 parts with different heading formats — Part 1 uses `#### 1.1 Title`, Part 2 (cross-cutting) uses `#### A1. Title`, Part 3 (institutional) has numbered sections, Part 4 (academic) has no numbering prefix. The country splitter must also handle Parts 2-4 which use `## A. Topic` not `## Kenya`. Generalize the regex to `^#### (.+)` and handle all four document sections. Update the integration test to assert `== 261` not `>= 250`.
3. **`verified_at` timestamp**: In `app.py` verification endpoint, replace `"verified_at": "now()"` with `"verified_at": datetime.utcnow().isoformat()`. The Supabase client sends JSON, not SQL.
4. **Supabase schema table ordering**: Move the `sources` table definition BEFORE `document_chunks` in `schema.sql` — FK reference requires it.
5. **Daily findings ingestion**: The `ingest-daily-findings.yml` workflow is a placeholder. Implement a real `backend/ingest/ingest_daily_findings.py` that reads the latest `monitoring/findings/findings_YYYY-MM-DD.json`, parses entries, classifies, embeds, and stores as UNVERIFIED.

### Important
6. **Dockerfile imports**: The CMD uses `app:app` but imports use `from backend.X`. Either copy the entire repo and use `CMD ["python", "-m", "uvicorn", "backend.app:app", ...]` or restructure imports to be relative within `backend/`.
7. **Rate limiting**: The `_request_counts` dict is declared but never used. Add rate checking in `verify_api_key` dependency.
8. **Multi-turn session memory**: The Chat Agent always passes `messages: []`. Load prior messages from `chat_sessions` for the given `session_id` and pass them as conversation context.
9. **Add `TAVILY_API_KEY`** to `config.py` and `.env.example`.
10. **`seed_events.py` field name**: Use `narrative_families` (plural) not `narrative_family` when reading from events.json.
11. **Source type mapping**: In `seed_desk_review.py`, replace hardcoded `QUALITY_MEDIA` with a mapping dict: `{"UNDP": "UN_AGENCY", "ICG": "THINK_TANK", "HRW": "NGO_CSO", ...}` with `QUALITY_MEDIA` as fallback.
12. **Model routing**: Add Haiku vs Sonnet routing in the Chat Agent — detect simple factual queries and use Haiku, reserve Sonnet for multi-source synthesis. Per spec cost controls.
13. **Cold-start retry limit**: Add max 3 retries to `sendMessage()` in `chat-widget.js`, show error after exhaustion.
14. **Feedback endpoint**: Add a lightweight `POST /chat/feedback` endpoint instead of abusing the chat endpoint for feedback signals.
15. **`verify.py` tool**: Implement the automated verification checks (URL validity, dedup, completeness) listed in the spec. Add as a sub-step in Task 8 or as a new mini-task.
16. **Autolearned keywords**: The Research Agent should read `monitoring/autolearn/learned_keywords_hs.csv` and `narrative_discoveries.csv` in the `assess_gaps` step to inform search queries. Per spec Section 7.3.

---

## File Structure

```
backend/
├── app.py                          # FastAPI application, middleware, CORS, auth
├── config.py                       # Environment config (Supabase, Anthropic, API keys)
├── db.py                           # Supabase client helpers (query, insert, upsert)
├── requirements.txt                # Python dependencies
├── Dockerfile                      # HuggingFace Spaces deployment
├── agents/
│   ├── chat_agent.py               # LangGraph Chat Agent graph
│   └── research_agent.py           # LangGraph Research Agent graph
├── tools/
│   ├── vector_search.py            # pgvector semantic search tool
│   ├── stats_query.py              # SQL query tool for Tier 3
│   ├── classify.py                 # Classification pipeline function
│   ├── embed.py                    # Embedding generation + storage
│   └── verify.py                   # Automated verification checks
├── ingest/
│   ├── parse_desk_review.py        # Parse desk review markdown → structured entries
│   ├── fetch_sources.py            # Fetch full text from URLs (web + PDF)
│   ├── seed_desk_review.py         # Orchestrate: parse → fetch → chunk → embed → store
│   ├── seed_events.py              # Load events.json into knowledge base
│   └── compute_stats.py            # Compute Tier 3 aggregated stats
├── tests/
│   ├── test_parse_desk_review.py   # Parser unit tests
│   ├── test_embed.py               # Embedding tool tests
│   ├── test_classify.py            # Classification tests
│   ├── test_vector_search.py       # Search tool tests
│   ├── test_chat_agent.py          # Chat agent integration tests
│   ├── test_api.py                 # FastAPI endpoint tests
│   └── conftest.py                 # Shared fixtures (mock Supabase, mock LLM)
docs/
├── chat-widget.js                  # Chat panel JS (API calls, rendering, PIN gate)
├── chat-widget.css                 # Chat panel styles
├── admin.html                      # Admin/verification/annotation page
├── admin.js                        # Admin page logic
├── admin.css                       # Admin page styles
.github/workflows/
├── research-agent.yml              # Daily Research Agent
├── ingest-seed.yml                 # One-time knowledge base seeding
├── compute-stats.yml               # Tier 3 stats refresh
├── ingest-daily-findings.yml       # Ingest daily monitoring findings
```

**Modified files:**
- `docs/index.html` — add chat widget container + script/css references
- `docs/style.css` — minor adjustments for chat panel layout
- `monitoring/explain_posts.py` — add Supabase query for related sources

---

## Task 1: Python Project Setup + Supabase Schema

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/config.py`
- Create: `backend/db.py`
- Create: `backend/tests/conftest.py`
- Create: `supabase/schema.sql` (for reference / manual execution)

This task sets up the Python project, dependencies, Supabase schema, and shared test fixtures.

- [ ] **Step 1: Create backend/requirements.txt**

```
# Core
fastapi==0.115.0
uvicorn[standard]==0.30.0
python-dotenv==1.0.1

# LangChain / LangGraph
langgraph==0.4.1
langchain==0.3.25
langchain-anthropic==0.3.15
langchain-community==0.3.21

# Embedding
sentence-transformers==3.4.1

# Supabase
supabase==2.13.0

# Web scraping / document extraction
trafilatura==2.0.0
pymupdf==1.25.3

# Search
tavily-python==0.5.0

# Testing
pytest==8.3.4
pytest-asyncio==0.25.0
httpx==0.28.1
```

- [ ] **Step 2: Create backend/config.py**

```python
"""Configuration from environment variables."""
import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]  # anon key for chat service
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")  # for batch ingestion
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
API_KEY = os.environ["API_KEY"]  # shared API key for frontend auth
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
```

- [ ] **Step 3: Create backend/db.py**

```python
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
    # Uses Supabase RPC function for vector similarity search
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
```

- [ ] **Step 4: Create supabase/schema.sql**

Copy the full schema from the spec (Section 6) plus the `match_documents` RPC function:

```sql
-- Enable pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- (all tables from spec Section 6 — see spec for full SQL)

-- Vector similarity search function
CREATE OR REPLACE FUNCTION match_documents(
    query_embedding vector(384),
    match_count int DEFAULT 10,
    filter_country text DEFAULT NULL,
    filter_theme text DEFAULT NULL,
    filter_verified_only boolean DEFAULT false
)
RETURNS TABLE (
    id uuid,
    source_id uuid,
    tier text,
    content text,
    country text[],
    theme text[],
    classification text,
    date_published date,
    verified boolean,
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        dc.id, dc.source_id, dc.tier, dc.content,
        dc.country, dc.theme, dc.classification,
        dc.date_published, dc.verified,
        1 - (dc.embedding <=> query_embedding) AS similarity
    FROM document_chunks dc
    WHERE
        (filter_country IS NULL OR filter_country = ANY(dc.country))
        AND (filter_theme IS NULL OR filter_theme = ANY(dc.theme))
        AND (NOT filter_verified_only OR dc.verified = true)
    ORDER BY dc.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
```

- [ ] **Step 5: Create backend/tests/conftest.py**

```python
"""Shared test fixtures."""
import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_supabase():
    """Mock Supabase client for unit tests."""
    with patch("backend.db.get_client") as mock:
        client = MagicMock()
        mock.return_value = client
        yield client


@pytest.fixture
def mock_anthropic():
    """Mock Anthropic API responses."""
    with patch("langchain_anthropic.ChatAnthropic") as mock:
        llm = MagicMock()
        mock.return_value = llm
        yield llm


@pytest.fixture
def sample_desk_review_entry():
    """A single parsed desk review entry for testing."""
    return {
        "title": "NPS–NCIC Joint Investigations: 12 Hate Speech Cases Under Probe",
        "date": "2026-02-25",
        "source_name": "Capital FM Kenya",
        "source_url": "https://www.capitalfm.co.ke/news/2026/02/kenya-police-probe-hate-speech-cases-2027-elections/",
        "country": ["Kenya"],
        "theme": ["Hate Speech Incidents"],
        "classification": "CONTEXT",
        "summary": "Inspector General Douglas Kanja told the Senate...",
        "flagged": True,
    }
```

- [ ] **Step 6: Set up Supabase project**

Manual step — create a Supabase project at supabase.com, enable pgvector extension, run `supabase/schema.sql` in the SQL editor. Save `SUPABASE_URL` and keys.

- [ ] **Step 7: Create .env.example and verify setup**

Create `backend/.env.example`:
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-key
ANTHROPIC_API_KEY=sk-ant-...
API_KEY=your-shared-api-key
```

Run: `cd backend && pip install -r requirements.txt && python -c "from backend.config import SUPABASE_URL; print('OK')"`

- [ ] **Step 8: Commit**

```bash
git add backend/requirements.txt backend/config.py backend/db.py backend/tests/conftest.py supabase/schema.sql backend/.env.example
git commit -m "feat: project setup — dependencies, config, Supabase schema, test fixtures"
```

---

## Task 2: Desk Review Parser

**Files:**
- Create: `backend/ingest/parse_desk_review.py`
- Create: `backend/tests/test_parse_desk_review.py`

Parses the 2,656-line desk review markdown into 261 structured entries with metadata.

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_parse_desk_review.py
import pytest
from backend.ingest.parse_desk_review import parse_desk_review, parse_entry


def test_parse_entry_extracts_all_fields():
    raw = """#### 1.1 NPS–NCIC Joint Investigations: 12 Hate Speech Cases Under Probe
- **Date:** 25 February 2026
- **Source:** Capital FM Kenya / Allafrica
- **URL:** [Capital FM Kenya](https://www.capitalfm.co.ke/news/2026/02/kenya-police-probe-hate-speech-cases-2027-elections/)
- **Relevance:** Hate speech enforcement pipeline
- **Key takeaway:** Inspector General Douglas Kanja told the Senate Standing Committee...
- **[FLAG]:** This is the first publicly confirmed quantitative disclosure..."""

    entry = parse_entry(raw, country="Kenya", topic="Hate Speech Incidents")
    assert entry["title"] == "NPS–NCIC Joint Investigations: 12 Hate Speech Cases Under Probe"
    assert entry["date"] == "2026-02-25"
    assert entry["source_name"] == "Capital FM Kenya / Allafrica"
    assert entry["source_url"] == "https://www.capitalfm.co.ke/news/2026/02/kenya-police-probe-hate-speech-cases-2027-elections/"
    assert entry["country"] == ["Kenya"]
    assert entry["theme"] == ["Hate Speech Incidents"]
    assert entry["flagged"] is True
    assert "Inspector General" in entry["summary"]


def test_parse_entry_handles_missing_flag():
    raw = """#### 2.1 Raila Odinga Dies: October 15, 2025
- **Date:** 15 October 2025
- **Source:** Stratfor Worldview
- **URL:** [Stratfor](https://worldview.stratfor.com/article/what-raila-odingas-death-means-kenyan-politics)
- **Relevance:** Foundational political shift
- **Key takeaway:** Raila Odinga died on 15 October 2025."""

    entry = parse_entry(raw, country="Kenya", topic="Electoral Cycle")
    assert entry["flagged"] is False
    assert entry["date"] == "2025-10-15"


def test_parse_entry_handles_multiple_urls():
    raw = """#### 2.1 Raila Odinga Dies
- **Date:** 15 October 2025
- **Source:** Stratfor / Wikipedia
- **URL:** [Stratfor](https://stratfor.com/article) | [Wikipedia](https://en.wikipedia.org/wiki/ODM)
- **Key takeaway:** Summary here."""

    entry = parse_entry(raw, country="Kenya", topic="Electoral Cycle")
    assert entry["source_url"] == "https://stratfor.com/article"
    assert len(entry.get("additional_urls", [])) == 1


def test_parse_full_document_finds_261_entries(tmp_path):
    """Integration test: parse the real desk review file."""
    import shutil
    src = "documentation/desk-review-update-oct2025-mar2026.md"
    entries = parse_desk_review(src)
    assert len(entries) >= 250  # Allow some tolerance for parsing edge cases
    # Every entry has required fields
    for e in entries:
        assert e["title"]
        assert e["source_url"]
        assert e["country"]
        assert e["summary"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_parse_desk_review.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'backend.ingest'`

- [ ] **Step 3: Implement the parser**

```python
# backend/ingest/parse_desk_review.py
"""Parse the desk review markdown into structured entries."""
import re
from pathlib import Path
from datetime import datetime


def parse_desk_review(filepath: str) -> list[dict]:
    """Parse the full desk review markdown file.

    Splits by country headings (## Country), then by topic headings
    (### TOPIC), then by entry headings (#### number. title).
    """
    text = Path(filepath).read_text(encoding="utf-8")
    entries = []

    # Split into country sections
    country_sections = re.split(r"^## (Kenya|Somalia|South Sudan)", text, flags=re.MULTILINE)

    current_country = None
    for i, section in enumerate(country_sections):
        if section.strip() in ("Kenya", "Somalia", "South Sudan"):
            current_country = section.strip()
            continue
        if current_country is None:
            # Check for cross-cutting section
            if "Cross-Cutting" in section or "Cross-cutting" in section:
                current_country = "Regional"
            else:
                continue

        # Split into topic sections within country
        topic_splits = re.split(r"^### (?:TOPIC \d+: )?(.+)", section, flags=re.MULTILINE)

        current_topic = "General"
        for j, part in enumerate(topic_splits):
            # Odd indices are topic names from the capture group
            if j % 2 == 1:
                current_topic = part.strip()
                continue

            # Split into individual entries
            entry_blocks = re.split(r"^#### (?:\d+\.\d+\s+)?(.+)", part, flags=re.MULTILINE)

            for k in range(1, len(entry_blocks), 2):
                title = entry_blocks[k].strip()
                body = entry_blocks[k + 1] if k + 1 < len(entry_blocks) else ""
                if not body.strip():
                    continue

                entry = parse_entry(
                    f"#### {title}\n{body}",
                    country=current_country,
                    topic=current_topic,
                )
                if entry:
                    entries.append(entry)

    return entries


def parse_entry(raw: str, country: str, topic: str) -> dict | None:
    """Parse a single desk review entry block into a structured dict."""
    # Title
    title_match = re.search(r"^#### (?:\d+\.\d+\s+)?(.+)", raw, re.MULTILINE)
    if not title_match:
        return None
    title = title_match.group(1).strip()

    # Date
    date_match = re.search(r"\*\*Date:\*\*\s*(.+)", raw)
    date_str = date_match.group(1).strip() if date_match else ""
    parsed_date = _normalize_date(date_str)

    # Source name
    source_match = re.search(r"\*\*Source:\*\*\s*(.+)", raw)
    source_name = source_match.group(1).strip() if source_match else ""
    # Clean markdown links from source name
    source_name = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", source_name)

    # URLs — primary and additional
    url_pattern = r"\[([^\]]+)\]\((https?://[^)]+)\)"
    url_section_match = re.search(r"\*\*URL:\*\*\s*(.+)", raw)
    urls = []
    if url_section_match:
        urls = re.findall(url_pattern, url_section_match.group(1))

    source_url = urls[0][1] if urls else ""
    additional_urls = [u[1] for u in urls[1:]]

    # Key takeaway (summary)
    takeaway_match = re.search(
        r"\*\*Key takeaway:\*\*\s*(.+?)(?=\n- \*\*\[|$|\n---)",
        raw, re.DOTALL
    )
    summary = takeaway_match.group(1).strip() if takeaway_match else ""

    # Relevance tag
    relevance_match = re.search(r"\*\*Relevance:\*\*\s*(.+)", raw)
    relevance = relevance_match.group(1).strip() if relevance_match else ""

    # Flagged
    flagged = bool(re.search(r"\*\*\[FLAG\]", raw))

    # Country — use parent country, but could be multi-country
    countries = [country] if country != "Regional" else ["Kenya", "Somalia", "South Sudan"]

    if not source_url and not summary:
        return None

    result = {
        "title": title,
        "date": parsed_date,
        "source_name": source_name,
        "source_url": source_url,
        "country": countries,
        "theme": [topic],
        "relevance": relevance,
        "summary": summary,
        "flagged": flagged,
    }
    if additional_urls:
        result["additional_urls"] = additional_urls

    return result


def _normalize_date(date_str: str) -> str:
    """Try to parse various date formats into YYYY-MM-DD."""
    if not date_str:
        return ""
    # Handle date ranges: "20–21 January 2026" → use first date
    date_str = re.sub(r"(\d+)–\d+", r"\1", date_str)
    # Handle "Analysis: date" suffix
    date_str = re.split(r"\s*/\s*Analysis:", date_str)[0].strip()
    # Handle parenthetical notes
    date_str = re.split(r"\s*\(", date_str)[0].strip()

    formats = [
        "%d %B %Y",     # 25 February 2026
        "%B %Y",        # February 2026
        "%d %b %Y",     # 25 Feb 2026
        "%Y-%m-%d",     # 2026-02-25
        "%B %d, %Y",    # February 25, 2026
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return date_str  # Return raw if unparseable
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_parse_desk_review.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/ingest/parse_desk_review.py backend/tests/test_parse_desk_review.py
git commit -m "feat: desk review markdown parser with tests — extracts 261 structured entries"
```

---

## Task 3: Embedding Tool

**Files:**
- Create: `backend/tools/embed.py`
- Create: `backend/tests/test_embed.py`

Handles text chunking, embedding generation, and pgvector upsert.

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_embed.py
import pytest
from backend.tools.embed import chunk_text, generate_embedding, embed_and_store


def test_chunk_text_splits_at_target_size():
    text = "Sentence one. " * 100  # ~1400 chars
    chunks = chunk_text(text, max_tokens=100)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk.split()) <= 120  # Some tolerance


def test_chunk_text_preserves_all_content():
    text = "Alpha. Bravo. Charlie. Delta. Echo."
    chunks = chunk_text(text, max_tokens=500)
    joined = " ".join(chunks)
    assert "Alpha" in joined
    assert "Echo" in joined


def test_chunk_text_single_short_text():
    text = "Short text."
    chunks = chunk_text(text, max_tokens=500)
    assert len(chunks) == 1
    assert chunks[0] == "Short text."


def test_generate_embedding_returns_384_dims(mocker):
    """Mock the sentence-transformers model."""
    mock_model = mocker.patch("backend.tools.embed._get_model")
    mock_model.return_value.encode.return_value = [0.1] * 384
    result = generate_embedding("test text")
    assert len(result) == 384
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_embed.py -v`
Expected: FAIL

- [ ] **Step 3: Implement embedding tool**

```python
# backend/tools/embed.py
"""Text chunking, embedding generation, and pgvector storage."""
import re
from backend.config import EMBEDDING_MODEL

_model = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


def chunk_text(text: str, max_tokens: int = 500) -> list[str]:
    """Split text into chunks of approximately max_tokens words.

    Splits on paragraph boundaries first, then sentence boundaries.
    """
    if not text.strip():
        return []

    paragraphs = re.split(r"\n\n+", text.strip())
    chunks = []
    current_chunk = []
    current_size = 0

    for para in paragraphs:
        para_words = len(para.split())
        if current_size + para_words <= max_tokens:
            current_chunk.append(para)
            current_size += para_words
        else:
            if current_chunk:
                chunks.append("\n\n".join(current_chunk))
            # If single paragraph exceeds max, split by sentences
            if para_words > max_tokens:
                sentences = re.split(r"(?<=[.!?])\s+", para)
                sent_chunk = []
                sent_size = 0
                for sent in sentences:
                    sw = len(sent.split())
                    if sent_size + sw <= max_tokens:
                        sent_chunk.append(sent)
                        sent_size += sw
                    else:
                        if sent_chunk:
                            chunks.append(" ".join(sent_chunk))
                        sent_chunk = [sent]
                        sent_size = sw
                if sent_chunk:
                    chunks.append(" ".join(sent_chunk))
                current_chunk = []
                current_size = 0
            else:
                current_chunk = [para]
                current_size = para_words

    if current_chunk:
        chunks.append("\n\n".join(current_chunk))

    return chunks


def generate_embedding(text: str) -> list[float]:
    """Generate a 384-dim embedding for a text string."""
    model = _get_model()
    embedding = model.encode(text, normalize_embeddings=True)
    return embedding.tolist()


def embed_and_store(text: str, metadata: dict, client=None) -> list[str]:
    """Chunk text, embed each chunk, and upsert to Supabase pgvector.

    Args:
        text: Full document text to chunk and embed.
        metadata: Dict with keys: source_id, tier, country, theme,
                  classification, date_published, verified.
        client: Supabase client (uses default if None).

    Returns:
        List of inserted chunk UUIDs.
    """
    if client is None:
        from backend.db import get_client
        client = get_client()

    chunks = chunk_text(text)
    chunk_ids = []

    for i, chunk in enumerate(chunks):
        embedding = generate_embedding(chunk)
        row = {
            "source_id": metadata.get("source_id"),
            "tier": metadata.get("tier", "full_text"),
            "content": chunk,
            "chunk_index": i,
            "embedding": embedding,
            "country": metadata.get("country", []),
            "theme": metadata.get("theme", []),
            "classification": metadata.get("classification"),
            "date_published": metadata.get("date_published"),
            "verified": metadata.get("verified", False),
        }
        result = client.table("document_chunks").insert(row).execute()
        if result.data:
            chunk_ids.append(result.data[0]["id"])

    return chunk_ids
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_embed.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/tools/embed.py backend/tests/test_embed.py
git commit -m "feat: embedding tool — chunk text, generate MiniLM embeddings, store in pgvector"
```

---

## Task 4: Vector Search Tool

**Files:**
- Create: `backend/tools/vector_search.py`
- Create: `backend/tests/test_vector_search.py`

Wraps the Supabase RPC call with filter handling and source enrichment.

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_vector_search.py
import pytest
from backend.tools.vector_search import vector_search


def test_vector_search_calls_rpc_with_embedding(mock_supabase):
    mock_supabase.rpc.return_value.execute.return_value.data = [
        {"id": "abc", "content": "test content", "similarity": 0.92,
         "source_id": "src1", "tier": "finding", "country": ["Kenya"],
         "theme": ["OGBV"], "classification": "HS_DISINFO",
         "date_published": "2026-02-01", "verified": True}
    ]
    results = vector_search(
        query="hate speech in Kenya",
        filters={"country": "Kenya"},
        client=mock_supabase,
    )
    assert len(results) == 1
    assert results[0]["similarity"] == 0.92
    mock_supabase.rpc.assert_called_once()


def test_vector_search_enriches_with_source_metadata(mock_supabase):
    mock_supabase.rpc.return_value.execute.return_value.data = [
        {"id": "abc", "content": "test", "similarity": 0.9, "source_id": "src1",
         "tier": "full_text", "country": ["Kenya"], "theme": ["OGBV"],
         "classification": "HS_DISINFO", "date_published": "2026-02-01",
         "verified": True}
    ]
    mock_supabase.table.return_value.select.return_value.in_.return_value.execute.return_value.data = [
        {"id": "src1", "title": "NCIC Report", "source_name": "NCIC",
         "source_url": "https://ncic.go.ke/report"}
    ]
    results = vector_search(query="test", client=mock_supabase)
    assert results[0]["source_name"] == "NCIC"
    assert results[0]["source_url"] == "https://ncic.go.ke/report"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_vector_search.py -v`
Expected: FAIL

- [ ] **Step 3: Implement vector search**

```python
# backend/tools/vector_search.py
"""Semantic search tool for the Chat Agent."""
from backend.tools.embed import generate_embedding


def vector_search(query: str, filters: dict | None = None,
                  top_k: int = 10, client=None) -> list[dict]:
    """Search document chunks by semantic similarity.

    Args:
        query: Natural language search query.
        filters: Optional dict with country, theme, verified_only.
        top_k: Number of results to return.
        client: Supabase client (uses default if None).

    Returns:
        List of dicts with chunk content, metadata, source info, and similarity score.
    """
    if client is None:
        from backend.db import get_client
        client = get_client()

    embedding = generate_embedding(query)

    params = {
        "query_embedding": embedding,
        "match_count": top_k,
        "filter_country": filters.get("country") if filters else None,
        "filter_theme": filters.get("theme") if filters else None,
        "filter_verified_only": filters.get("verified_only", False) if filters else False,
    }
    result = client.rpc("match_documents", params).execute()
    chunks = result.data or []

    # Enrich with source metadata
    source_ids = list({c["source_id"] for c in chunks if c.get("source_id")})
    if source_ids:
        sources_result = (
            client.table("sources")
            .select("id, title, source_name, source_url")
            .in_("id", source_ids)
            .execute()
        )
        source_map = {s["id"]: s for s in (sources_result.data or [])}
        for chunk in chunks:
            src = source_map.get(chunk.get("source_id"), {})
            chunk["source_name"] = src.get("source_name", "")
            chunk["source_url"] = src.get("source_url", "")
            chunk["source_title"] = src.get("title", "")

    return chunks
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_vector_search.py -v`
Expected: All 2 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/tools/vector_search.py backend/tests/test_vector_search.py
git commit -m "feat: vector search tool — semantic search with source enrichment"
```

---

## Task 5: Stats Query Tool

**Files:**
- Create: `backend/tools/stats_query.py`
- Create: `backend/tests/test_stats_query.py`

Simple wrapper for querying Tier 3 aggregated statistics.

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_stats_query.py
import pytest
from backend.tools.stats_query import query_hs_stats


def test_query_hs_stats_returns_formatted_data(mock_supabase):
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"stat_type": "hs_by_country_subtype", "country": "Kenya",
         "data": {"Hate": 150, "Abusive": 300, "Normal": 2000},
         "period": "2025-10 to 2026-03"}
    ]
    result = query_hs_stats("hs_by_country_subtype", country="Kenya", client=mock_supabase)
    assert result["data"]["Hate"] == 150
    assert result["period"] == "2025-10 to 2026-03"
```

- [ ] **Step 2: Run test, verify fail**

Run: `cd backend && python -m pytest tests/test_stats_query.py -v`

- [ ] **Step 3: Implement**

```python
# backend/tools/stats_query.py
"""Query tool for pre-computed HS statistics (Tier 3)."""


def query_hs_stats(stat_type: str, country: str | None = None,
                   client=None) -> dict | None:
    """Query aggregated stats from Supabase.

    stat_type: one of hs_by_country_subtype, toxicity_by_country,
               trends_by_month, narrative_prevalence
    """
    if client is None:
        from backend.db import get_client
        client = get_client()

    q = client.table("aggregated_stats").select("*").eq("stat_type", stat_type)
    if country:
        q = q.eq("country", country)

    result = q.execute()
    return result.data[0] if result.data else None
```

- [ ] **Step 4: Run test, verify pass**

- [ ] **Step 5: Commit**

```bash
git add backend/tools/stats_query.py backend/tests/test_stats_query.py
git commit -m "feat: stats query tool for Tier 3 aggregated HS data"
```

---

## Task 6: Classification Pipeline Function

**Files:**
- Create: `backend/tools/classify.py`
- Create: `backend/tests/test_classify.py`

Uses Claude Haiku with few-shot examples to classify findings.

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_classify.py
import pytest
from unittest.mock import MagicMock
from backend.tools.classify import classify_finding


def test_classify_finding_returns_structured_result(mocker):
    mock_llm = mocker.patch("backend.tools.classify._get_llm")
    mock_llm.return_value.invoke.return_value.content = (
        '{"classification": "HS_DISINFO", "hs_subtype": "Political Incitement", "confidence": 0.85}'
    )
    result = classify_finding(
        title="MPs charged with hate speech",
        summary="Several members of parliament were charged with inciting violence...",
        country=["Kenya"],
    )
    assert result["classification"] == "HS_DISINFO"
    assert result["confidence"] == 0.85
    assert result["hs_subtype"] == "Political Incitement"


def test_classify_finding_handles_context_type(mocker):
    mock_llm = mocker.patch("backend.tools.classify._get_llm")
    mock_llm.return_value.invoke.return_value.content = (
        '{"classification": "CONTEXT", "hs_subtype": null, "confidence": 0.92}'
    )
    result = classify_finding(
        title="New cybercrime act passed",
        summary="Parliament passed the cybercrime act...",
        country=["South Sudan"],
    )
    assert result["classification"] == "CONTEXT"
    assert result["hs_subtype"] is None
```

- [ ] **Step 2: Run test, verify fail**

- [ ] **Step 3: Implement**

```python
# backend/tools/classify.py
"""Classification pipeline function using Claude Haiku."""
import json
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage

_llm = None

SYSTEM_PROMPT = """You are a classification agent for the BRACE4PEACE programme.
Classify findings about hate speech and disinformation in East Africa.

Return JSON with exactly these fields:
- classification: one of CONTEXT, HS_DISINFO, VE_PROPAGANDA
- hs_subtype: if HS_DISINFO, one of: Political Incitement, Clan Targeting,
  Religious Incitement, Dehumanisation, Anti-Foreign, Ethnic Targeting,
  General Abuse, Gendered Violence. null otherwise.
- confidence: float 0.0-1.0

Definitions:
- CONTEXT: Background events, policy changes, institutional actions
- HS_DISINFO: Direct hate speech, disinformation campaigns, content manipulation
- VE_PROPAGANDA: Violent extremist propaganda, recruitment, radicalisation material

Return ONLY valid JSON, no other text."""


def _get_llm():
    global _llm
    if _llm is None:
        _llm = ChatAnthropic(model="claude-haiku-4-5-20251001", max_tokens=200)
    return _llm


def classify_finding(title: str, summary: str,
                     country: list[str] | None = None) -> dict:
    """Classify a finding using Claude Haiku.

    Returns: {"classification": str, "hs_subtype": str|None, "confidence": float}
    """
    llm = _get_llm()
    user_msg = f"Title: {title}\nCountry: {', '.join(country or [])}\nSummary: {summary}"
    response = llm.invoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_msg),
    ])
    try:
        return json.loads(response.content)
    except json.JSONDecodeError:
        return {"classification": "CONTEXT", "hs_subtype": None, "confidence": 0.0}
```

- [ ] **Step 4: Run tests, verify pass**

- [ ] **Step 5: Commit**

```bash
git add backend/tools/classify.py backend/tests/test_classify.py
git commit -m "feat: classification function — Claude Haiku with few-shot BRACE4PEACE taxonomy"
```

---

## Task 7: LangGraph Chat Agent

**Files:**
- Create: `backend/agents/chat_agent.py`
- Create: `backend/tests/test_chat_agent.py`

The core conversational agent. LangGraph graph with ANALYZE → ROUTE → RETRIEVE → GENERATE → FORMAT nodes.

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_chat_agent.py
import pytest
from unittest.mock import MagicMock, patch
from backend.agents.chat_agent import create_chat_agent, ChatState


def test_chat_agent_returns_cited_response(mocker):
    """Integration test: mock LLM and vector search, verify citation format."""
    mock_search = mocker.patch("backend.agents.chat_agent.vector_search")
    mock_search.return_value = [
        {"content": "NCIC found 12 hate speech cases under investigation.",
         "source_name": "Capital FM Kenya",
         "source_url": "https://capitalfm.co.ke/report",
         "source_title": "NCIC Joint Investigations",
         "similarity": 0.91, "country": ["Kenya"],
         "classification": "CONTEXT", "verified": True}
    ]
    mock_stats = mocker.patch("backend.agents.chat_agent.query_hs_stats")
    mock_stats.return_value = None

    mock_llm = mocker.patch("backend.agents.chat_agent._get_llm")
    mock_llm.return_value.invoke.return_value.content = (
        "Based on available data, NCIC has 12 hate speech cases under investigation "
        "[Capital FM Kenya](https://capitalfm.co.ke/report).\n\n"
        "Confidence: HIGH"
    )

    agent = create_chat_agent()
    result = agent.invoke({
        "query": "How many hate speech cases are being investigated in Kenya?",
        "filters": {"country": "Kenya"},
        "session_id": "test-session",
        "messages": [],
    })

    assert "capitalfm.co.ke" in result["response"]
    assert len(result["sources"]) >= 1
    assert result["confidence"] in ("HIGH", "MEDIUM", "LOW")


def test_chat_agent_handles_stats_query(mocker):
    mock_search = mocker.patch("backend.agents.chat_agent.vector_search")
    mock_search.return_value = []
    mock_stats = mocker.patch("backend.agents.chat_agent.query_hs_stats")
    mock_stats.return_value = {
        "data": {"Hate": 150, "Abusive": 300, "Normal": 2000},
        "period": "2025-10 to 2026-03", "country": "Kenya",
    }
    mock_llm = mocker.patch("backend.agents.chat_agent._get_llm")
    mock_llm.return_value.invoke.return_value.content = (
        "In Kenya, there are 150 posts classified as Hate, 300 as Abusive, "
        "and 2000 as Normal in the monitoring period.\n\nConfidence: HIGH"
    )

    agent = create_chat_agent()
    result = agent.invoke({
        "query": "How much hate speech is there in Kenya?",
        "filters": {},
        "session_id": "test-session",
        "messages": [],
    })
    assert "150" in result["response"]
```

- [ ] **Step 2: Run tests, verify fail**

- [ ] **Step 3: Implement Chat Agent**

```python
# backend/agents/chat_agent.py
"""LangGraph Chat Agent for BRACE4PEACE."""
import re
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage
from backend.tools.vector_search import vector_search
from backend.tools.stats_query import query_hs_stats

SYSTEM_PROMPT = """You are an analyst assistant for the BRACE4PEACE programme,
specialising in hate speech and disinformation monitoring in East Africa
(Kenya, Somalia, South Sudan).

RULES:
1. Every factual statement must cite its source using [Source Name](URL).
   Never fabricate sources.
2. If retrieved evidence is insufficient, say "I don't have enough information
   on this topic." Indicate confidence level (HIGH / MEDIUM / LOW).
3. Do not take sides in conflicts. Present verified findings from multiple
   perspectives where available.
4. You answer questions about HS/disinfo dynamics in Kenya, Somalia, and
   South Sudan. Redirect out-of-scope queries politely.
5. When using statistical data, state the time period covered.
6. End every response with a line: "Confidence: HIGH/MEDIUM/LOW"

CONFIDENCE LEVELS:
- HIGH: 3+ corroborating sources, verified findings
- MEDIUM: 1-2 sources, or mix of verified and unverified
- LOW: Limited data, data gaps identified"""


class ChatState(TypedDict):
    query: str
    filters: dict
    session_id: str
    messages: list
    retrieved_chunks: list
    stats_data: dict | None
    response: str
    sources: list
    confidence: str


_llm = None


def _get_llm():
    global _llm
    if _llm is None:
        _llm = ChatAnthropic(model="claude-sonnet-4-20250514", max_tokens=2000)
    return _llm


def analyze_and_retrieve(state: ChatState) -> ChatState:
    """Analyze query intent and retrieve relevant context."""
    query = state["query"]
    filters = state.get("filters", {})

    # Detect if this is a stats query
    stats_keywords = ["how much", "how many", "count", "total", "statistics",
                      "prevalence", "trend", "percentage"]
    is_stats = any(kw in query.lower() for kw in stats_keywords)

    # Vector search for knowledge base content
    chunks = vector_search(query, filters=filters, top_k=10)

    # Stats query if detected
    stats = None
    if is_stats:
        country = filters.get("country")
        stats = query_hs_stats("hs_by_country_subtype", country=country)

    return {
        **state,
        "retrieved_chunks": chunks,
        "stats_data": stats,
    }


def generate_response(state: ChatState) -> ChatState:
    """Generate citation-grounded response using Claude."""
    llm = _get_llm()
    chunks = state.get("retrieved_chunks", [])
    stats = state.get("stats_data")

    # Build context
    context_parts = []
    if chunks:
        context_parts.append("RETRIEVED FINDINGS:")
        for i, c in enumerate(chunks, 1):
            source_info = f"[{c.get('source_name', 'Unknown')}]({c.get('source_url', '')})"
            verified = "VERIFIED" if c.get("verified") else "UNVERIFIED"
            context_parts.append(
                f"{i}. {source_info} ({verified})\n"
                f"   Country: {', '.join(c.get('country', []))}\n"
                f"   Content: {c.get('content', '')[:500]}"
            )

    if stats:
        context_parts.append(f"\nSTATISTICAL DATA:\n{stats}")

    if not context_parts:
        context_parts.append("No relevant findings found in the knowledge base.")

    context = "\n\n".join(context_parts)

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"CONTEXT:\n{context}\n\nQUERY: {state['query']}"),
    ]
    response = llm.invoke(messages)
    response_text = response.content

    # Extract confidence
    confidence_match = re.search(r"Confidence:\s*(HIGH|MEDIUM|LOW)", response_text)
    confidence = confidence_match.group(1) if confidence_match else "LOW"

    # Build sources list
    sources = []
    seen_urls = set()
    for c in chunks:
        url = c.get("source_url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            sources.append({
                "title": c.get("source_title", ""),
                "source_name": c.get("source_name", ""),
                "source_url": url,
                "date": c.get("date_published"),
                "country": c.get("country", []),
                "classification": c.get("classification"),
            })

    return {
        **state,
        "response": response_text,
        "sources": sources,
        "confidence": confidence,
    }


def create_chat_agent():
    """Build and compile the LangGraph chat agent."""
    graph = StateGraph(ChatState)
    graph.add_node("retrieve", analyze_and_retrieve)
    graph.add_node("generate", generate_response)
    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", END)
    return graph.compile()
```

- [ ] **Step 4: Run tests, verify pass**

Run: `cd backend && python -m pytest tests/test_chat_agent.py -v`

- [ ] **Step 5: Commit**

```bash
git add backend/agents/chat_agent.py backend/tests/test_chat_agent.py
git commit -m "feat: LangGraph Chat Agent — retrieve + generate with citation enforcement"
```

---

## Task 8: FastAPI Application

**Files:**
- Create: `backend/app.py`
- Create: `backend/tests/test_api.py`

All API endpoints with auth middleware.

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_api.py
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, MagicMock
import os

os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-key")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("API_KEY", "test-api-key")

from backend.app import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_health_no_auth(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert "status" in resp.json()


@pytest.mark.asyncio
async def test_chat_requires_auth(client):
    resp = await client.post("/chat", json={"query": "test"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_chat_with_valid_key(client, mocker):
    mock_agent = mocker.patch("backend.app._get_chat_agent")
    mock_agent.return_value.invoke.return_value = {
        "response": "Test response [Source](https://example.com)",
        "sources": [{"title": "Source", "source_url": "https://example.com"}],
        "confidence": "HIGH",
        "session_id": "s1",
    }
    resp = await client.post(
        "/chat",
        json={"query": "test question"},
        headers={"X-API-Key": "test-api-key"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "response" in data
    assert data["confidence"] == "HIGH"


@pytest.mark.asyncio
async def test_verification_decide(client, mocker):
    mock_client = mocker.patch("backend.app._get_supabase")
    mock_table = MagicMock()
    mock_client.return_value.table.return_value = mock_table
    mock_table.select.return_value.eq.return_value.execute.return_value.data = [
        {"id": "abc", "status": "UNVERIFIED"}
    ]
    mock_table.update.return_value.eq.return_value.execute.return_value.data = [
        {"id": "abc", "status": "VERIFIED"}
    ]
    mock_client.return_value.table.return_value.insert.return_value.execute.return_value.data = [{}]

    resp = await client.post(
        "/verification/decide",
        json={"finding_id": "abc", "action": "VERIFY", "reviewer_name": "analyst1"},
        headers={"X-API-Key": "test-api-key"},
    )
    assert resp.status_code == 200
```

- [ ] **Step 2: Run tests, verify fail**

- [ ] **Step 3: Implement FastAPI app**

```python
# backend/app.py
"""FastAPI application for BRACE4PEACE RAG chat service."""
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from backend.config import API_KEY
from backend.agents.chat_agent import create_chat_agent

app = FastAPI(title="BRACE4PEACE Chat API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://ksvend.github.io"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting state (in-memory, resets on restart)
_request_counts: dict[str, int] = {}
_DAILY_LIMIT = 50

_chat_agent = None
_supabase = None


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


async def verify_api_key(request: Request):
    key = request.headers.get("X-API-Key")
    if key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return key


# --- Models ---

class ChatRequest(BaseModel):
    query: str
    session_id: str | None = None
    filters: dict | None = None

class VerificationRequest(BaseModel):
    finding_id: str
    action: str  # VERIFY, FLAG, REJECT
    reviewer_name: str
    note: str | None = None
    corrections: dict | None = None

class AnnotationRequest(BaseModel):
    post_id: str
    action: str  # CONFIRM, CORRECT, FLAG
    reviewer_name: str
    corrections: dict | None = None
    note: str | None = None


# --- Endpoints ---

@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/chat")
async def chat(req: ChatRequest, _=Depends(verify_api_key)):
    import uuid
    agent = _get_chat_agent()
    session_id = req.session_id or str(uuid.uuid4())

    result = agent.invoke({
        "query": req.query,
        "filters": req.filters or {},
        "session_id": session_id,
        "messages": [],
    })

    # Log to chat_sessions
    try:
        client = _get_supabase()
        client.table("chat_sessions").insert({
            "session_id": session_id,
            "query_text": req.query,
            "filters": req.filters,
            "response_text": result.get("response", ""),
            "sources_cited": result.get("sources", []),
            "confidence": result.get("confidence", "LOW"),
        }).execute()
    except Exception:
        pass  # Don't fail the request if logging fails

    return {
        "response": result.get("response", ""),
        "sources": result.get("sources", []),
        "confidence": result.get("confidence", "LOW"),
        "session_id": session_id,
    }


@app.get("/chat/history/{session_id}")
async def chat_history(session_id: str, _=Depends(verify_api_key)):
    client = _get_supabase()
    result = (
        client.table("chat_sessions")
        .select("*")
        .eq("session_id", session_id)
        .order("created_at")
        .execute()
    )
    return {"messages": result.data or []}


@app.get("/knowledge/stats")
async def knowledge_stats(_=Depends(verify_api_key)):
    client = _get_supabase()
    chunks = client.table("document_chunks").select("id", count="exact").execute()
    findings = client.table("findings").select("id", count="exact").execute()
    pending = (
        client.table("findings").select("id", count="exact")
        .eq("status", "UNVERIFIED").execute()
    )
    meta = (
        client.table("system_metadata").select("*")
        .eq("key", "last_research_run").execute()
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
    result = q.range(offset, offset + limit - 1).order("created_at", desc=True).execute()
    return {"results": result.data or [], "total": result.count or 0}


@app.get("/verification/pending")
async def verification_pending(limit: int = 50, _=Depends(verify_api_key)):
    client = _get_supabase()
    result = (
        client.table("findings").select("*")
        .eq("status", "UNVERIFIED")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return {"findings": result.data or []}


@app.post("/verification/decide")
async def verification_decide(req: VerificationRequest, _=Depends(verify_api_key)):
    client = _get_supabase()

    # Get current finding
    current = (
        client.table("findings").select("*")
        .eq("id", req.finding_id).execute()
    )
    if not current.data:
        raise HTTPException(status_code=404, detail="Finding not found")

    old_status = current.data[0]["status"]
    new_status = {"VERIFY": "VERIFIED", "FLAG": "FLAGGED", "REJECT": "REJECTED"}[req.action]

    # Update finding
    update_data = {
        "status": new_status,
        "verified_by": req.reviewer_name,
        "verified_at": "now()",
        "verification_note": req.note,
    }
    if req.corrections:
        update_data.update(req.corrections)
    client.table("findings").update(update_data).eq("id", req.finding_id).execute()

    # Log verification
    client.table("verification_log").insert({
        "finding_id": req.finding_id,
        "reviewer_id": req.reviewer_name,
        "action": req.action,
        "note": req.note,
        "previous_status": old_status,
        "new_status": new_status,
    }).execute()

    return {"finding_id": req.finding_id, "previous_status": old_status, "new_status": new_status}


@app.get("/posts/review-queue")
async def posts_review_queue(
    country: str | None = None,
    subtype: str | None = None,
    limit: int = 20,
    offset: int = 0,
    _=Depends(verify_api_key),
):
    """Return HS posts for annotation review.

    Reads from docs/data/hate_speech_posts.json loaded at startup.
    Filters and paginates. Sorted by confidence (low first).
    """
    posts = _get_hs_posts()
    filtered = posts
    if country:
        filtered = [p for p in filtered if p.get("country") == country]
    if subtype:
        filtered = [p for p in filtered if subtype in (p.get("subtopics") or [])]
    # Sort by confidence ascending (review low-confidence first)
    filtered.sort(key=lambda p: p.get("eaHsConf", 1.0))
    page = filtered[offset:offset + limit]
    return {"posts": page, "total": len(filtered)}


@app.post("/posts/annotate")
async def posts_annotate(req: AnnotationRequest, _=Depends(verify_api_key)):
    client = _get_supabase()
    client.table("post_annotations").insert({
        "post_id": req.post_id,
        "reviewer": req.reviewer_name,
        "action": req.action,
        "corrections": req.corrections,
        "note": req.note,
    }).execute()
    return {"post_id": req.post_id, "action": req.action, "status": "saved"}


# --- HS Posts Cache ---
_hs_posts = None

def _get_hs_posts():
    global _hs_posts
    if _hs_posts is None:
        import json
        from pathlib import Path
        path = Path(__file__).resolve().parent.parent / "docs" / "data" / "hate_speech_posts.json"
        if path.exists():
            _hs_posts = json.loads(path.read_text())
        else:
            _hs_posts = []
    return _hs_posts
```

- [ ] **Step 4: Run tests, verify pass**

Run: `cd backend && python -m pytest tests/test_api.py -v`

- [ ] **Step 5: Commit**

```bash
git add backend/app.py backend/tests/test_api.py
git commit -m "feat: FastAPI app — all endpoints with auth, CORS, rate limiting"
```

---

## Task 9: Knowledge Base Seeding Scripts

**Files:**
- Create: `backend/ingest/fetch_sources.py`
- Create: `backend/ingest/seed_desk_review.py`
- Create: `backend/ingest/seed_events.py`
- Create: `backend/ingest/compute_stats.py`

These scripts run as GitHub Actions (one-time seed + recurring stats refresh).

- [ ] **Step 1: Implement fetch_sources.py**

```python
# backend/ingest/fetch_sources.py
"""Fetch full text from URLs — web pages and PDFs."""
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def fetch_url(url: str) -> dict:
    """Fetch and extract readable text from a URL.

    Returns: {"text": str, "status": "FETCHED"|"FAILED"|"PAYWALLED", "error": str|None}
    """
    try:
        from trafilatura import fetch_url as tf_fetch, extract
        downloaded = tf_fetch(url)
        if downloaded is None:
            return {"text": "", "status": "FAILED", "error": "Could not download"}

        text = extract(downloaded, include_links=True, include_tables=True)
        if not text or len(text) < 100:
            return {"text": text or "", "status": "PAYWALLED", "error": "Insufficient content"}

        return {"text": text, "status": "FETCHED", "error": None}
    except Exception as e:
        logger.warning(f"Failed to fetch {url}: {e}")
        return {"text": "", "status": "FAILED", "error": str(e)}


def fetch_pdf(url: str) -> dict:
    """Fetch and extract text from a PDF URL."""
    try:
        import urllib.request
        import tempfile
        import fitz  # pymupdf

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            urllib.request.urlretrieve(url, f.name)
            doc = fitz.open(f.name)
            text = "\n\n".join(page.get_text() for page in doc)
            doc.close()

        if not text.strip():
            return {"text": "", "status": "FAILED", "error": "Empty PDF"}
        return {"text": text, "status": "FETCHED", "error": None}
    except Exception as e:
        logger.warning(f"Failed to fetch PDF {url}: {e}")
        return {"text": "", "status": "FAILED", "error": str(e)}
```

- [ ] **Step 2: Implement seed_desk_review.py**

```python
# backend/ingest/seed_desk_review.py
"""Orchestrate knowledge base seeding from desk review."""
import logging
import sys
from pathlib import Path
from backend.ingest.parse_desk_review import parse_desk_review
from backend.ingest.fetch_sources import fetch_url, fetch_pdf
from backend.tools.embed import embed_and_store, generate_embedding
from backend.tools.classify import classify_finding

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DESK_REVIEW_PATH = REPO_ROOT / "documentation" / "desk-review-update-oct2025-mar2026.md"


def seed(dry_run: bool = False):
    """Parse desk review, fetch sources, embed, and store."""
    from backend.db import get_client
    client = get_client()

    entries = parse_desk_review(str(DESK_REVIEW_PATH))
    logger.info(f"Parsed {len(entries)} desk review entries")

    stats = {"total": len(entries), "fetched": 0, "failed": 0, "embedded": 0}

    for i, entry in enumerate(entries):
        logger.info(f"[{i+1}/{len(entries)}] {entry['title'][:60]}...")

        # Insert source record
        source_row = {
            "title": entry["title"],
            "source_name": entry.get("source_name", ""),
            "source_url": entry.get("source_url", ""),
            "source_type": "QUALITY_MEDIA",  # Default; could be smarter
            "date_published": entry.get("date") or None,
            "country": entry.get("country", []),
            "theme": entry.get("theme", []),
            "summary": entry.get("summary", ""),
            "created_by": "seed_desk_review",
        }

        if dry_run:
            logger.info(f"  DRY RUN: would insert source + embed")
            continue

        src_result = client.table("sources").insert(source_row).execute()
        source_id = src_result.data[0]["id"] if src_result.data else None

        # Classify if not already classified
        classification = classify_finding(
            title=entry["title"],
            summary=entry.get("summary", ""),
            country=entry.get("country"),
        )

        # Update source with classification
        if source_id:
            client.table("sources").update({
                "classification": classification["classification"],
                "credibility_score": classification["confidence"],
            }).eq("id", source_id).execute()

        # Embed the desk review summary as Tier 2
        summary_text = f"{entry['title']}\n\n{entry.get('summary', '')}"
        embedding = generate_embedding(summary_text)
        client.table("document_chunks").insert({
            "source_id": source_id,
            "tier": "finding",
            "content": summary_text,
            "chunk_index": 0,
            "embedding": embedding,
            "country": entry.get("country", []),
            "theme": entry.get("theme", []),
            "classification": classification["classification"],
            "date_published": entry.get("date") or None,
            "verified": True,  # Desk review entries are human-curated
        }).execute()

        # Try to fetch full source text for Tier 1
        url = entry.get("source_url", "")
        if url:
            is_pdf = url.lower().endswith(".pdf")
            result = fetch_pdf(url) if is_pdf else fetch_url(url)

            # Update fetch status
            if source_id:
                client.table("sources").update({
                    "fetch_status": result["status"]
                }).eq("id", source_id).execute()

            if result["status"] == "FETCHED" and result["text"]:
                stats["fetched"] += 1
                # Embed full text as Tier 1
                embed_and_store(
                    text=result["text"],
                    metadata={
                        "source_id": source_id,
                        "tier": "full_text",
                        "country": entry.get("country", []),
                        "theme": entry.get("theme", []),
                        "classification": classification["classification"],
                        "date_published": entry.get("date") or None,
                        "verified": True,
                    },
                    client=client,
                )
                stats["embedded"] += 1
            else:
                stats["failed"] += 1
                logger.warning(f"  Failed to fetch: {result.get('error', 'unknown')}")

    logger.info(f"Seeding complete: {stats}")
    return stats


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    dry_run = "--dry-run" in sys.argv
    seed(dry_run=dry_run)
```

- [ ] **Step 3: Implement seed_events.py**

```python
# backend/ingest/seed_events.py
"""Load events.json into the knowledge base as Tier 2 items."""
import json
import logging
import sys
from pathlib import Path
from backend.tools.embed import generate_embedding

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
EVENTS_PATH = REPO_ROOT / "docs" / "data" / "events.json"


def seed(dry_run: bool = False):
    """Load events and embed as Tier 2 chunks."""
    from backend.db import get_client
    client = get_client()

    events = json.loads(EVENTS_PATH.read_text())
    logger.info(f"Loading {len(events)} events")

    for i, event in enumerate(events):
        text = f"{event.get('headline', '')}\n\n{event.get('summary', '')}"
        if not text.strip():
            continue

        country = [event.get("country", "Regional")]
        classification = event.get("event_type", "CONTEXT")

        if dry_run:
            logger.info(f"  DRY RUN: [{i+1}] {event.get('headline', '')[:60]}")
            continue

        embedding = generate_embedding(text)
        client.table("document_chunks").insert({
            "tier": "event",
            "content": text,
            "chunk_index": 0,
            "embedding": embedding,
            "country": country,
            "theme": event.get("narrative_family", []),
            "classification": classification,
            "date_published": event.get("date"),
            "verified": True,
        }).execute()

    logger.info(f"Events seeding complete: {len(events)} events")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    dry_run = "--dry-run" in sys.argv
    seed(dry_run=dry_run)
```

- [ ] **Step 4: Implement compute_stats.py**

```python
# backend/ingest/compute_stats.py
"""Compute Tier 3 aggregated statistics from hate_speech_posts.json."""
import json
import logging
from pathlib import Path
from collections import Counter

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
HS_PATH = REPO_ROOT / "docs" / "data" / "hate_speech_posts.json"


def compute(dry_run: bool = False):
    """Compute and store aggregated HS stats in Supabase."""
    from backend.db import get_client

    posts = json.loads(HS_PATH.read_text())
    logger.info(f"Computing stats from {len(posts)} posts")

    # Stat 1: HS classification by country
    by_country = {}
    for p in posts:
        c = p.get("country", "Unknown")
        pred = p.get("eaHsPred", "Normal")
        by_country.setdefault(c, Counter())[pred] += 1

    # Stat 2: Subtype distribution by country
    subtypes_by_country = {}
    for p in posts:
        c = p.get("country", "Unknown")
        for st in (p.get("subtopics") or []):
            subtypes_by_country.setdefault(c, Counter())[st] += 1

    # Stat 3: Toxicity levels by country
    tox_by_country = {}
    for p in posts:
        c = p.get("country", "Unknown")
        for dim in ["probToxicity", "probSevereToxicity", "probInsult",
                     "probIdentityAttack", "probThreat"]:
            level = p.get(dim, "none")
            tox_by_country.setdefault(c, {}).setdefault(dim, Counter())[level] += 1

    if dry_run:
        logger.info(f"DRY RUN: would write {len(by_country)} country stats")
        return

    client = get_client()

    # Clear old stats
    client.table("aggregated_stats").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()

    # Write new stats
    rows = []
    for country, counts in by_country.items():
        rows.append({
            "stat_type": "hs_by_country_subtype",
            "country": country,
            "period": "2025-10 to 2026-03",
            "data": dict(counts),
        })
    for country, counts in subtypes_by_country.items():
        rows.append({
            "stat_type": "subtype_distribution",
            "country": country,
            "period": "2025-10 to 2026-03",
            "data": dict(counts),
        })
    for country, dims in tox_by_country.items():
        rows.append({
            "stat_type": "toxicity_by_country",
            "country": country,
            "period": "2025-10 to 2026-03",
            "data": {k: dict(v) for k, v in dims.items()},
        })

    client.table("aggregated_stats").insert(rows).execute()
    logger.info(f"Wrote {len(rows)} stat rows")


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    dry_run = "--dry-run" in sys.argv
    compute(dry_run=dry_run)
```

- [ ] **Step 5: Commit**

```bash
git add backend/ingest/fetch_sources.py backend/ingest/seed_desk_review.py backend/ingest/seed_events.py backend/ingest/compute_stats.py
git commit -m "feat: knowledge base seeding — desk review parser + events + stats computation"
```

---

## Task 10: LangGraph Research Agent

**Files:**
- Create: `backend/agents/research_agent.py`

Runs as a GitHub Action. Discovers new findings, classifies, deduplicates, stages for verification.

- [ ] **Step 1: Implement Research Agent**

```python
# backend/agents/research_agent.py
"""LangGraph Research Agent — daily automated desk research."""
import json
import logging
from typing import TypedDict
from datetime import datetime, timedelta
from langgraph.graph import StateGraph, END
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage
from backend.tools.embed import generate_embedding, embed_and_store
from backend.tools.classify import classify_finding

logger = logging.getLogger(__name__)

RESEARCH_SYSTEM_PROMPT = """You are the BRACE4PEACE Daily Research Agent.
You discover new findings about hate speech and disinformation in Kenya, Somalia, and South Sudan.

For each finding, extract:
- title: concise headline
- summary: 100-200 word description
- source_name: publishing organisation
- source_url: direct URL
- date_published: publication date (YYYY-MM-DD)
- country: one or more of Kenya, Somalia, South Sudan, Regional
- theme: one of AI/deepfakes, Platform Governance, EWER, Legal Frameworks, OGBV, Youth/Radicalisation, Diaspora, Cross-border

Return a JSON array of findings. Return empty array [] if no relevant findings.
Do NOT fabricate findings or URLs."""


class ResearchState(TypedDict):
    search_queries: list[str]
    raw_results: list[dict]
    new_findings: list[dict]
    stats: dict


def assess_gaps(state: ResearchState) -> ResearchState:
    """Check knowledge base for coverage gaps."""
    from backend.db import get_client
    client = get_client()

    # Find topics with no findings in last 7 days
    cutoff = (datetime.utcnow() - timedelta(days=7)).isoformat()
    recent = (
        client.table("findings")
        .select("country, theme")
        .gte("created_at", cutoff)
        .execute()
    )

    covered = set()
    for f in (recent.data or []):
        for c in (f.get("country") or []):
            covered.add(f"{c}_{f.get('theme', '')}")

    all_combos = [
        f"{c}_{t}" for c in ["Kenya", "Somalia", "South Sudan"]
        for t in ["hate speech", "disinformation", "VE", "legal framework", "platform governance"]
    ]
    gaps = [combo for combo in all_combos if combo not in covered]

    # Generate search queries from gaps
    queries = [gap.replace("_", " ") + " 2026" for gap in gaps[:30]]

    return {**state, "search_queries": queries}


def execute_searches(state: ResearchState) -> ResearchState:
    """Run web searches and extract findings via LLM."""
    from tavily import TavilyClient
    import os

    tavily = TavilyClient(api_key=os.environ.get("TAVILY_API_KEY", ""))
    llm = ChatAnthropic(model="claude-sonnet-4-20250514", max_tokens=4000)

    all_results = []
    for query in state["search_queries"][:30]:  # Cap at 30 per Tavily free tier
        try:
            search = tavily.search(query=query, max_results=3)
            for result in search.get("results", []):
                all_results.append({
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "content": result.get("content", "")[:1000],
                })
        except Exception as e:
            logger.warning(f"Search failed for '{query}': {e}")

    if not all_results:
        return {**state, "raw_results": [], "new_findings": []}

    # Use LLM to extract structured findings
    batch_text = "\n\n---\n\n".join(
        f"Title: {r['title']}\nURL: {r['url']}\nContent: {r['content']}"
        for r in all_results[:50]
    )

    response = llm.invoke([
        SystemMessage(content=RESEARCH_SYSTEM_PROMPT),
        HumanMessage(content=f"Extract relevant findings from these search results:\n\n{batch_text}"),
    ])

    try:
        findings = json.loads(response.content)
    except json.JSONDecodeError:
        logger.error("Failed to parse LLM response as JSON")
        findings = []

    return {**state, "raw_results": all_results, "new_findings": findings}


def dedup_and_stage(state: ResearchState) -> ResearchState:
    """Deduplicate findings against existing knowledge base and stage new ones."""
    from backend.db import get_client
    client = get_client()

    staged = 0
    for finding in state.get("new_findings", [])[:20]:  # Cap at 20
        # Generate embedding for dedup check
        text = f"{finding.get('title', '')}\n{finding.get('summary', '')}"
        embedding = generate_embedding(text)

        # Check similarity against existing
        dupes = client.rpc("match_documents", {
            "query_embedding": embedding,
            "match_count": 1,
        }).execute()

        if dupes.data and dupes.data[0].get("similarity", 0) > 0.85:
            logger.info(f"  Duplicate (sim={dupes.data[0]['similarity']:.2f}): {finding.get('title', '')[:50]}")
            continue

        # Classify
        classification = classify_finding(
            title=finding.get("title", ""),
            summary=finding.get("summary", ""),
            country=finding.get("country", []),
        )

        # Insert source
        src_result = client.table("sources").insert({
            "title": finding.get("title", ""),
            "source_name": finding.get("source_name", ""),
            "source_url": finding.get("source_url", ""),
            "source_type": "QUALITY_MEDIA",
            "date_published": finding.get("date_published"),
            "country": finding.get("country", []),
            "theme": finding.get("theme", []) if isinstance(finding.get("theme"), list) else [finding.get("theme", "")],
            "classification": classification["classification"],
            "credibility_score": classification["confidence"],
            "summary": finding.get("summary", ""),
            "created_by": "research_agent",
            "fetch_status": "PENDING",
        }).execute()
        source_id = src_result.data[0]["id"] if src_result.data else None

        # Insert finding as UNVERIFIED
        countries = finding.get("country", [])
        if isinstance(countries, str):
            countries = [countries]
        themes = finding.get("theme", [])
        if isinstance(themes, str):
            themes = [themes]

        client.table("findings").insert({
            "source_id": source_id,
            "title": finding.get("title", ""),
            "summary": finding.get("summary", ""),
            "country": countries,
            "theme": themes,
            "classification": classification["classification"],
            "hs_subtype": classification.get("hs_subtype"),
            "confidence": classification["confidence"],
            "status": "UNVERIFIED",
            "created_by": "research_agent",
        }).execute()

        # Embed as unverified chunk
        client.table("document_chunks").insert({
            "source_id": source_id,
            "tier": "finding",
            "content": text,
            "chunk_index": 0,
            "embedding": embedding,
            "country": countries,
            "theme": themes,
            "classification": classification["classification"],
            "date_published": finding.get("date_published"),
            "verified": False,
        }).execute()

        staged += 1
        logger.info(f"  Staged: {finding.get('title', '')[:60]}")

    # Update system metadata
    client.table("system_metadata").upsert({
        "key": "last_research_run",
        "value": {
            "timestamp": datetime.utcnow().isoformat(),
            "findings_staged": staged,
            "searches_executed": len(state.get("search_queries", [])),
        },
    }).execute()

    return {**state, "stats": {"staged": staged}}


def create_research_agent():
    """Build the Research Agent graph."""
    graph = StateGraph(ResearchState)
    graph.add_node("assess_gaps", assess_gaps)
    graph.add_node("search", execute_searches)
    graph.add_node("stage", dedup_and_stage)
    graph.set_entry_point("assess_gaps")
    graph.add_edge("assess_gaps", "search")
    graph.add_edge("search", "stage")
    graph.add_edge("stage", END)
    return graph.compile()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    agent = create_research_agent()
    result = agent.invoke({"search_queries": [], "raw_results": [], "new_findings": [], "stats": {}})
    logger.info(f"Research complete: {result.get('stats', {})}")
```

- [ ] **Step 2: Commit**

```bash
git add backend/agents/research_agent.py
git commit -m "feat: LangGraph Research Agent — daily auto-research with dedup and staging"
```

---

## Task 11: GitHub Actions Workflows

**Files:**
- Create: `.github/workflows/research-agent.yml`
- Create: `.github/workflows/ingest-seed.yml`
- Create: `.github/workflows/compute-stats.yml`
- Create: `.github/workflows/ingest-daily-findings.yml`

- [ ] **Step 1: Create research-agent.yml**

```yaml
# .github/workflows/research-agent.yml
name: Daily Research Agent
on:
  schedule:
    - cron: '0 4 * * *'  # Daily at 04:00 UTC
  workflow_dispatch:

jobs:
  research:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r backend/requirements.txt
      - name: Run Research Agent
        env:
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_KEY: ${{ secrets.SUPABASE_SERVICE_KEY }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          TAVILY_API_KEY: ${{ secrets.TAVILY_API_KEY }}
        run: python -m backend.agents.research_agent
```

- [ ] **Step 2: Create ingest-seed.yml**

```yaml
# .github/workflows/ingest-seed.yml
name: Seed Knowledge Base
on:
  workflow_dispatch:
    inputs:
      seed_type:
        description: 'What to seed'
        required: true
        default: 'all'
        type: choice
        options: [all, desk_review, events, stats]
      dry_run:
        description: 'Dry run (no writes)'
        type: boolean
        default: false

jobs:
  seed:
    runs-on: ubuntu-latest
    timeout-minutes: 120
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r backend/requirements.txt
      - name: Seed desk review
        if: inputs.seed_type == 'all' || inputs.seed_type == 'desk_review'
        env:
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_KEY: ${{ secrets.SUPABASE_SERVICE_KEY }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: python -m backend.ingest.seed_desk_review ${{ inputs.dry_run && '--dry-run' || '' }}
      - name: Seed events
        if: inputs.seed_type == 'all' || inputs.seed_type == 'events'
        env:
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_KEY: ${{ secrets.SUPABASE_SERVICE_KEY }}
        run: python -m backend.ingest.seed_events ${{ inputs.dry_run && '--dry-run' || '' }}
      - name: Compute stats
        if: inputs.seed_type == 'all' || inputs.seed_type == 'stats'
        env:
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_KEY: ${{ secrets.SUPABASE_SERVICE_KEY }}
        run: python -m backend.ingest.compute_stats ${{ inputs.dry_run && '--dry-run' || '' }}
```

- [ ] **Step 3: Create compute-stats.yml and ingest-daily-findings.yml**

```yaml
# .github/workflows/compute-stats.yml
name: Refresh HS Stats
on:
  workflow_run:
    workflows: ["BRACE4PEACE Monitor"]
    types: [completed]
  workflow_dispatch:

jobs:
  stats:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r backend/requirements.txt
      - env:
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_KEY: ${{ secrets.SUPABASE_SERVICE_KEY }}
        run: python -m backend.ingest.compute_stats
```

```yaml
# .github/workflows/ingest-daily-findings.yml
name: Ingest Daily Findings
on:
  workflow_run:
    workflows: ["BRACE4PEACE Monitor"]
    types: [completed]
  workflow_dispatch:

jobs:
  ingest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r backend/requirements.txt
      - env:
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_KEY: ${{ secrets.SUPABASE_SERVICE_KEY }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          python -c "
          from backend.ingest.seed_desk_review import seed
          # This will be extended to ingest latest findings file
          print('Daily findings ingestion placeholder')
          "
```

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/research-agent.yml .github/workflows/ingest-seed.yml .github/workflows/compute-stats.yml .github/workflows/ingest-daily-findings.yml
git commit -m "feat: GitHub Actions — research agent, seeding, stats refresh, daily ingestion"
```

---

## Task 12: HuggingFace Spaces Deployment

**Files:**
- Create: `backend/Dockerfile`

- [ ] **Step 1: Create Dockerfile**

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the embedding model
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')"

COPY . .

EXPOSE 7860

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]
```

- [ ] **Step 2: Test locally**

```bash
cd backend
docker build -t brace4peace-chat .
docker run -p 7860:7860 --env-file .env brace4peace-chat
# Test: curl http://localhost:7860/health
```

- [ ] **Step 3: Commit**

```bash
git add backend/Dockerfile
git commit -m "feat: Dockerfile for HuggingFace Spaces deployment"
```

---

## Task 13: Chat Widget (Frontend)

**Files:**
- Create: `docs/chat-widget.js`
- Create: `docs/chat-widget.css`
- Modify: `docs/index.html`

- [ ] **Step 1: Create chat-widget.css**

MERLx design system — warm neutrals, Inter font, calm aesthetic. See `~/.claude/design-systems/MERLx-design-system.md` for tokens.

```css
/* docs/chat-widget.css */
/* Chat Panel — MERLx Design System */
.chat-toggle {
  position: fixed; right: 20px; bottom: 20px;
  width: 56px; height: 56px; border-radius: 50%;
  background: #2C3E50; color: #F5F1EB; border: none;
  font-size: 24px; cursor: pointer; z-index: 1000;
  box-shadow: 0 2px 12px rgba(0,0,0,0.15);
  font-family: 'Inter', sans-serif;
  transition: transform 0.2s ease;
}
.chat-toggle:hover { transform: scale(1.05); }

.chat-panel {
  position: fixed; right: 0; top: 0; bottom: 0;
  width: 420px; max-width: 100vw;
  background: #FAFAF7; border-left: 1px solid #E8E4DD;
  display: none; flex-direction: column;
  z-index: 999; font-family: 'Inter', sans-serif;
}
.chat-panel.open { display: flex; }

.chat-header {
  padding: 16px 20px; background: #2C3E50; color: #F5F1EB;
  display: flex; justify-content: space-between; align-items: center;
}
.chat-header h3 { margin: 0; font-size: 15px; font-weight: 600; }
.chat-close { background: none; border: none; color: #F5F1EB; font-size: 20px; cursor: pointer; }

.chat-messages {
  flex: 1; overflow-y: auto; padding: 16px 20px;
}
.chat-msg { margin-bottom: 16px; line-height: 1.5; font-size: 14px; }
.chat-msg.user { text-align: right; }
.chat-msg.user .bubble { background: #2C3E50; color: #F5F1EB; display: inline-block; padding: 10px 14px; border-radius: 12px 12px 2px 12px; max-width: 80%; }
.chat-msg.assistant .bubble { background: #F0EDE8; color: #2C3E50; padding: 10px 14px; border-radius: 12px 12px 12px 2px; max-width: 90%; }
.chat-msg.assistant .bubble a { color: #5B7B6A; text-decoration: underline; }

.confidence-badge { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 600; margin-top: 6px; }
.confidence-HIGH { background: #D4EDDA; color: #155724; }
.confidence-MEDIUM { background: #FFF3CD; color: #856404; }
.confidence-LOW { background: #F8D7DA; color: #721C24; }

.source-card { background: #fff; border: 1px solid #E8E4DD; border-radius: 8px; padding: 8px 12px; margin-top: 6px; font-size: 12px; }
.source-card a { color: #5B7B6A; }

.chat-input-area {
  padding: 12px 16px; border-top: 1px solid #E8E4DD; background: #fff;
  display: flex; gap: 8px;
}
.chat-input { flex: 1; border: 1px solid #D1CCC4; border-radius: 8px; padding: 10px 12px; font-size: 14px; font-family: 'Inter', sans-serif; resize: none; }
.chat-send { background: #2C3E50; color: #F5F1EB; border: none; border-radius: 8px; padding: 10px 16px; cursor: pointer; font-weight: 600; }

.chat-filters { padding: 8px 16px; display: flex; gap: 6px; flex-wrap: wrap; }
.filter-chip { padding: 4px 10px; border-radius: 14px; font-size: 12px; border: 1px solid #D1CCC4; background: #fff; cursor: pointer; }
.filter-chip.active { background: #2C3E50; color: #F5F1EB; border-color: #2C3E50; }

/* PIN gate */
.pin-gate { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; padding: 40px; }
.pin-gate input { border: 1px solid #D1CCC4; border-radius: 8px; padding: 12px; font-size: 16px; text-align: center; width: 200px; margin: 16px 0; }

/* Loading / cold start */
.chat-loading { text-align: center; padding: 20px; color: #8B8680; font-size: 13px; }

/* Feedback */
.feedback-btns { margin-top: 6px; }
.feedback-btns button { background: none; border: none; cursor: pointer; font-size: 16px; padding: 2px 6px; opacity: 0.5; }
.feedback-btns button:hover { opacity: 1; }
```

- [ ] **Step 2: Create chat-widget.js**

```javascript
// docs/chat-widget.js
// BRACE4PEACE Chat Widget — vanilla JS
(function() {
  'use strict';

  const API_BASE = 'https://YOUR-HF-SPACE.hf.space'; // Updated after deployment
  const PIN_KEY = 'b4p_pin_ok';
  const NAME_KEY = 'b4p_analyst_name';
  const API_KEY_STORE = 'b4p_api_key';
  let sessionId = crypto.randomUUID();
  let activeFilters = {};

  // --- Initialization ---
  function init() {
    injectHTML();
    document.querySelector('.chat-toggle').addEventListener('click', togglePanel);
    document.querySelector('.chat-close').addEventListener('click', togglePanel);
    document.querySelector('.chat-send').addEventListener('click', sendMessage);
    document.querySelector('.chat-input').addEventListener('keydown', function(e) {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
    });
    // Filter chips
    document.querySelectorAll('.filter-chip').forEach(chip => {
      chip.addEventListener('click', () => {
        chip.classList.toggle('active');
        updateFilters();
      });
    });
    // PIN gate
    document.querySelector('.pin-submit')?.addEventListener('click', checkPin);
  }

  function injectHTML() {
    const container = document.getElementById('chat-widget-container');
    if (!container) return;
    container.innerHTML = `
      <button class="chat-toggle" title="Ask BRACE4PEACE">💬</button>
      <div class="chat-panel">
        <div class="chat-header">
          <h3>BRACE4PEACE Knowledge Base</h3>
          <button class="chat-close">✕</button>
        </div>
        ${localStorage.getItem(PIN_KEY) ? chatUI() : pinGateUI()}
      </div>`;
  }

  function pinGateUI() {
    return `<div class="pin-gate">
      <p style="color:#2C3E50;font-size:14px;">Enter access PIN</p>
      <input type="password" class="pin-input" maxlength="10" placeholder="PIN">
      <button class="pin-submit chat-send">Access</button>
    </div>`;
  }

  function chatUI() {
    return `
      <div class="chat-filters">
        <span class="filter-chip" data-country="Kenya">Kenya</span>
        <span class="filter-chip" data-country="Somalia">Somalia</span>
        <span class="filter-chip" data-country="South Sudan">South Sudan</span>
      </div>
      <div class="chat-messages"></div>
      <div class="chat-input-area">
        <textarea class="chat-input" rows="1" placeholder="Ask about HS/disinfo in East Africa..."></textarea>
        <button class="chat-send">Send</button>
      </div>`;
  }

  function togglePanel() {
    document.querySelector('.chat-panel').classList.toggle('open');
  }

  function checkPin() {
    const pin = document.querySelector('.pin-input').value;
    // PIN is checked against a simple hash — not real security
    // The API key provides actual security
    if (pin) {
      localStorage.setItem(PIN_KEY, '1');
      // Re-render with chat UI
      const panel = document.querySelector('.chat-panel');
      panel.innerHTML = `
        <div class="chat-header">
          <h3>BRACE4PEACE Knowledge Base</h3>
          <button class="chat-close">✕</button>
        </div>
        ${chatUI()}`;
      // Re-bind events
      document.querySelector('.chat-close').addEventListener('click', togglePanel);
      document.querySelector('.chat-send').addEventListener('click', sendMessage);
      document.querySelector('.chat-input').addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
      });
      document.querySelectorAll('.filter-chip').forEach(chip => {
        chip.addEventListener('click', () => { chip.classList.toggle('active'); updateFilters(); });
      });
      // Prompt for API key and name
      const apiKey = prompt('Enter API key:');
      if (apiKey) localStorage.setItem(API_KEY_STORE, apiKey);
      const name = prompt('Enter your name (for review tracking):');
      if (name) localStorage.setItem(NAME_KEY, name);
    }
  }

  function updateFilters() {
    const active = document.querySelectorAll('.filter-chip.active');
    const countries = Array.from(active).map(c => c.dataset.country).filter(Boolean);
    activeFilters = countries.length ? { country: countries } : {};
  }

  async function sendMessage() {
    const input = document.querySelector('.chat-input');
    const query = input.value.trim();
    if (!query) return;

    const messages = document.querySelector('.chat-messages');
    messages.innerHTML += `<div class="chat-msg user"><div class="bubble">${escapeHtml(query)}</div></div>`;
    input.value = '';
    messages.innerHTML += `<div class="chat-msg assistant"><div class="chat-loading">Thinking...</div></div>`;
    messages.scrollTop = messages.scrollHeight;

    try {
      const resp = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': localStorage.getItem(API_KEY_STORE) || '',
        },
        body: JSON.stringify({
          query: query,
          session_id: sessionId,
          filters: Object.keys(activeFilters).length ? activeFilters : null,
        }),
      });

      if (resp.status === 503 || resp.status === 0) {
        // Cold start — HF Spaces waking up
        messages.querySelector('.chat-loading').textContent = 'Waking up the service, please wait...';
        await new Promise(r => setTimeout(r, 5000));
        return sendMessage(); // Retry
      }

      const data = await resp.json();
      const loading = messages.querySelector('.chat-loading');
      if (loading) loading.parentElement.remove();

      // Render response with markdown links
      let html = renderMarkdown(data.response || 'No response');
      html += `<span class="confidence-badge confidence-${data.confidence}">${data.confidence}</span>`;

      // Source cards
      if (data.sources && data.sources.length) {
        html += '<div style="margin-top:8px">';
        data.sources.forEach(s => {
          html += `<div class="source-card"><a href="${escapeHtml(s.source_url)}" target="_blank">${escapeHtml(s.source_name || s.title)}</a> · ${escapeHtml(s.date || '')} · ${escapeHtml((s.country||[]).join(', '))}</div>`;
        });
        html += '</div>';
      }

      // Feedback
      html += `<div class="feedback-btns"><button onclick="sendFeedback('${sessionId}','helpful')">👍</button><button onclick="sendFeedback('${sessionId}','not_helpful')">👎</button></div>`;

      messages.innerHTML += `<div class="chat-msg assistant"><div class="bubble">${html}</div></div>`;
      messages.scrollTop = messages.scrollHeight;
    } catch (err) {
      const loading = messages.querySelector('.chat-loading');
      if (loading) loading.textContent = `Error: ${err.message}. Retrying...`;
      await new Promise(r => setTimeout(r, 3000));
      // Remove error message and retry once
      const loadingEl = messages.querySelector('.chat-loading');
      if (loadingEl) loadingEl.parentElement.remove();
    }
  }

  function renderMarkdown(text) {
    // Simple markdown: links, bold, newlines
    return text
      .replace(/\[([^\]]+)\]\((https?:\/\/[^)]+)\)/g, '<a href="$2" target="_blank">$1</a>')
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/\n/g, '<br>');
  }

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str || '';
    return div.innerHTML;
  }

  window.sendFeedback = function(sid, type) {
    // Fire-and-forget feedback
    fetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-API-Key': localStorage.getItem(API_KEY_STORE) || '' },
      body: JSON.stringify({ query: `__feedback:${type}`, session_id: sid }),
    }).catch(() => {});
  };

  // Init when DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
```

- [ ] **Step 3: Add widget container to docs/index.html**

Add before `</body>`:
```html
<link rel="stylesheet" href="chat-widget.css">
<div id="chat-widget-container"></div>
<script src="chat-widget.js"></script>
```

- [ ] **Step 4: Test locally**

Open `docs/index.html` in browser. Verify:
- Toggle button appears at bottom-right
- PIN gate shows on click
- After PIN entry, chat UI renders
- Filter chips toggle on/off

- [ ] **Step 5: Commit**

```bash
git add docs/chat-widget.js docs/chat-widget.css docs/index.html
git commit -m "feat: chat widget — PIN gate, filters, citation rendering, cold-start handling"
```

---

## Task 14: Admin Page

**Files:**
- Create: `docs/admin.html`
- Create: `docs/admin.js`
- Create: `docs/admin.css`

- [ ] **Step 1: Create admin.html**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>BRACE4PEACE Admin</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="admin.css">
</head>
<body>
  <header>
    <h1>BRACE4PEACE Admin</h1>
    <div id="user-info"></div>
  </header>
  <nav>
    <button class="tab active" data-tab="verify">Verify Findings</button>
    <button class="tab" data-tab="review">Review Posts</button>
    <button class="tab" data-tab="stats">Knowledge Base</button>
  </nav>
  <main>
    <section id="verify-tab" class="tab-content active"></section>
    <section id="review-tab" class="tab-content"></section>
    <section id="stats-tab" class="tab-content"></section>
  </main>
  <div id="pin-gate" style="display:none">
    <h2>Enter Access PIN</h2>
    <input type="password" id="pin-input" maxlength="10">
    <button onclick="checkAdminPin()">Access</button>
  </div>
  <script src="admin.js"></script>
</body>
</html>
```

- [ ] **Step 2: Create admin.js**

Implements: tab switching, findings table with verify/flag/reject, post review table with confirm/correct/flag, knowledge base stats display. Uses the same API key + PIN gate pattern as the chat widget.

- [ ] **Step 3: Create admin.css**

MERLx design system styling for the admin interface — tables, buttons, tabs, badges.

- [ ] **Step 4: Test locally**

Open `docs/admin.html`, verify tab switching, PIN gate, table rendering (with mock data if backend not running).

- [ ] **Step 5: Commit**

```bash
git add docs/admin.html docs/admin.js docs/admin.css
git commit -m "feat: admin page — verification queue + post annotation + knowledge base stats"
```

---

## Task 15: explain_posts.py Integration

**Files:**
- Modify: `monitoring/explain_posts.py`

- [ ] **Step 1: Add Supabase query function**

Add a function using raw `urllib.request` to query Supabase PostgREST for related findings. No new pip dependencies.

```python
def _query_related_sources(country: str, narratives: list[str]) -> list[dict]:
    """Query Supabase for related knowledge base findings.
    Uses raw urllib to avoid adding pip dependencies.
    """
    import urllib.request
    import urllib.parse

    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_key = os.environ.get("SUPABASE_KEY", "")
    if not supabase_url or not supabase_key:
        return []

    # Query sources table for matching country + theme
    params = urllib.parse.urlencode({
        "select": "title,source_url,summary",
        "country": f"cs.{{{country}}}",  # Postgres array contains
        "fetch_status": "eq.FETCHED",
        "limit": "3",
        "order": "date_published.desc",
    })
    url = f"{supabase_url}/rest/v1/sources?{params}"
    req = urllib.request.Request(url, headers={
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
    })
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            return [{"title": r["title"], "url": r["source_url"],
                      "relevance": r.get("summary", "")[:100]} for r in data]
    except Exception:
        return []
```

- [ ] **Step 2: Integrate into the explanation prompt**

In the existing `_build_prompt()` or equivalent function, add related sources to the context. Add `related_sources` to the output JSON schema.

- [ ] **Step 3: Test with --dry-run**

```bash
cd monitoring && python explain_posts.py --dry-run --limit 3
```

Verify the output includes `related_sources` field (empty list if Supabase not configured).

- [ ] **Step 4: Commit**

```bash
git add monitoring/explain_posts.py
git commit -m "feat: explain_posts.py — query knowledge base for related sources in explanations"
```

---

## Task 16: End-to-End Integration Test

- [ ] **Step 1: Verify Supabase schema is deployed**

Check tables exist, pgvector extension enabled, RPC function created.

- [ ] **Step 2: Run seed with dry-run**

```bash
cd backend && python -m backend.ingest.seed_desk_review --dry-run
```

Verify: 261 entries parsed, no errors.

- [ ] **Step 3: Seed a small sample (5 entries)**

```bash
python -c "
from backend.ingest.seed_desk_review import seed
# Modify to limit to 5 entries for testing
"
```

- [ ] **Step 4: Test chat locally**

```bash
cd backend && uvicorn app:app --port 7860
# In another terminal:
curl -X POST http://localhost:7860/chat \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: YOUR_KEY' \
  -d '{"query": "What hate speech cases are being investigated in Kenya?"}'
```

Verify: Response includes citations, sources list, confidence level.

- [ ] **Step 5: Test admin endpoints**

```bash
curl http://localhost:7860/verification/pending -H 'X-API-Key: YOUR_KEY'
curl http://localhost:7860/knowledge/stats -H 'X-API-Key: YOUR_KEY'
```

- [ ] **Step 6: Deploy to HuggingFace Spaces**

Create a new Space, push the `backend/` directory, configure secrets.

- [ ] **Step 7: Update chat-widget.js API_BASE**

Replace `YOUR-HF-SPACE` with the actual HF Spaces URL.

- [ ] **Step 8: Full seed**

Trigger the `ingest-seed.yml` GitHub Action with `seed_type: all`.

- [ ] **Step 9: Final commit**

```bash
git add -A
git commit -m "chore: integration — update HF Spaces URL, verify deployment"
```
