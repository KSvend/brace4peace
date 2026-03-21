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
