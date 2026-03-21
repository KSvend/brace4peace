"""Tests for desk review markdown parser."""
import pytest
from pathlib import Path

from backend.ingest.parse_desk_review import parse_entry_block, parse_desk_review

DESK_REVIEW_PATH = (
    Path(__file__).resolve().parents[2]
    / "documentation"
    / "desk-review-update-oct2025-mar2026.md"
)


# ---------------------------------------------------------------------------
# Unit tests — parse_entry_block
# ---------------------------------------------------------------------------

STANDARD_ENTRY = """\
#### 1.1 NPS–NCIC Joint Investigations: 12 Hate Speech Cases Under Probe
- **Date:** 25 February 2026
- **Source:** Capital FM Kenya / Allafrica (reporting on Senate testimony by Inspector General Douglas Kanja)
- **URL:** [Capital FM Kenya](https://www.capitalfm.co.ke/news/2026/02/kenya-police-probe-hate-speech-cases-2027-elections/)
- **Relevance:** Hate speech enforcement pipeline
- **Key takeaway:** Inspector General Douglas Kanja told the Senate Standing Committee on National Cohesion that the NPS and NCIC investigated 12 cases.
- **[FLAG]:** This is the first publicly confirmed quantitative disclosure.
"""

ENTRY_NO_FLAG = """\
#### 1.2 MP Peter Salassia Charged Over Inciteful Social Media Posts
- **Date:** 20 January 2026
- **Source:** KTN News Kenya (via YouTube transcript)
- **URL:** [KTN News Kenya](https://www.youtube.com/watch?v=jB9SxmWM4B0)
- **Relevance:** Prosecutorial precedent — sitting MP
- **Key takeaway:** Mumias East MP Peter Salassia appeared before a court.
"""

ENTRY_MULTIPLE_URLS = """\
#### 2.1 Raila Odinga Dies: October 15, 2025
- **Date:** 15 October 2025 / Analysis: 24 October 2025
- **Source:** Stratfor Worldview / Wikipedia – Orange Democratic Movement
- **URL:** [Stratfor Worldview](https://worldview.stratfor.com/article/what-raila-odingas-death-means-kenyan-politics) | [Wikipedia – ODM](https://en.wikipedia.org/wiki/Orange_Democratic_Movement)
- **Relevance:** Foundational political shift
- **Key takeaway:** Raila Odinga died on 15 October 2025 in India.
- **[FLAG]:** This is the single most significant political event.
"""

ENTRY_DATE_RANGE = """\
#### 1.3 NCIC: 28 Politicians Summoned by December 2025
- **Date:** 20–21 January 2026 (reporting on December 2025 figure)
- **Source:** KTN News Kenya / NCIC
- **URL:** [KTN News Kenya](https://www.youtube.com/watch?v=jB9SxmWM4B0)
- **Relevance:** Enforcement scale indicator
- **Key takeaway:** By December 2025, NCIC had summoned at least 28 politicians.
"""

ENTRY_MONTH_ONLY = """\
#### A5. AI Deepfakes: Regional Example
- **Date:** February 2026
- **Source:** Democracy Action
- **URL:** [Democracy Action](https://democracyactionsd.org/example)
- **Key takeaway:** Introduces the concept of demand-side vulnerabilities.
"""


class TestParseEntryBlock:
    def test_parse_entry_extracts_all_fields(self):
        entry = parse_entry_block(STANDARD_ENTRY, country=["Kenya"], theme=["Hate Speech Incidents"])
        assert entry["title"] == "NPS–NCIC Joint Investigations: 12 Hate Speech Cases Under Probe"
        assert entry["date"] == "2026-02-25"
        assert "Capital FM Kenya" in entry["source_name"]
        assert entry["source_url"] == "https://www.capitalfm.co.ke/news/2026/02/kenya-police-probe-hate-speech-cases-2027-elections/"
        assert entry["country"] == ["Kenya"]
        assert entry["theme"] == ["Hate Speech Incidents"]
        assert entry["relevance"] == "Hate speech enforcement pipeline"
        assert "Inspector General" in entry["summary"]
        assert entry["flagged"] is True

    def test_parse_entry_handles_missing_flag(self):
        entry = parse_entry_block(ENTRY_NO_FLAG, country=["Kenya"], theme=["Electoral Cycle"])
        assert entry["flagged"] is False
        assert entry["title"] == "MP Peter Salassia Charged Over Inciteful Social Media Posts"

    def test_parse_entry_handles_multiple_urls(self):
        entry = parse_entry_block(ENTRY_MULTIPLE_URLS, country=["Kenya"], theme=["Electoral Cycle"])
        assert entry["source_url"] == "https://worldview.stratfor.com/article/what-raila-odingas-death-means-kenyan-politics"
        assert len(entry["additional_urls"]) >= 1
        assert "https://en.wikipedia.org/wiki/Orange_Democratic_Movement" in entry["additional_urls"]

    def test_parse_entry_normalizes_date_range(self):
        entry = parse_entry_block(ENTRY_DATE_RANGE, country=["Kenya"], theme=["Enforcement"])
        assert entry["date"] == "2026-01-20"

    def test_parse_entry_normalizes_month_only_date(self):
        entry = parse_entry_block(ENTRY_MONTH_ONLY, country=["Regional"], theme=["AI Deepfakes"])
        assert entry["date"] == "2026-02-01"


# ---------------------------------------------------------------------------
# Integration tests — full document parse
# ---------------------------------------------------------------------------

class TestFullDocumentParse:
    @pytest.fixture(scope="class")
    def entries(self):
        assert DESK_REVIEW_PATH.exists(), f"Desk review file not found: {DESK_REVIEW_PATH}"
        return parse_desk_review(DESK_REVIEW_PATH)

    def test_parse_full_document_count(self, entries):
        assert abs(len(entries) - 261) <= 1, (
            f"Expected ~261 entries, got {len(entries)}"
        )

    def test_all_entries_have_required_fields(self, entries):
        for i, e in enumerate(entries):
            assert e.get("title"), f"Entry {i} missing title"
            assert e.get("source_url"), f"Entry {i} ({e.get('title', '?')}) missing source_url"
            assert e.get("country"), f"Entry {i} ({e.get('title', '?')}) missing country"
            assert e.get("summary"), f"Entry {i} ({e.get('title', '?')}) missing summary"
