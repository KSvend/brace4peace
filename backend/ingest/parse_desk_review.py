"""Parse the BRACE4PEACE desk review markdown into structured entries."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Date normalisation
# ---------------------------------------------------------------------------

_MONTHS = {
    "january": "01", "february": "02", "march": "03", "april": "04",
    "may": "05", "june": "06", "july": "07", "august": "08",
    "september": "09", "october": "10", "november": "11", "december": "12",
}

_DATE_DMY = re.compile(
    r"(\d{1,2})\s+(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{4})",
    re.IGNORECASE,
)
_DATE_MY = re.compile(
    r"(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{4})",
    re.IGNORECASE,
)
_DATE_RANGE_DMY = re.compile(
    r"(\d{1,2})\s*[–—-]\s*\d{1,2}\s+(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{4})",
    re.IGNORECASE,
)
_DATE_YEAR_ONLY = re.compile(r"\b(20\d{2})\b")


def normalise_date(raw: str) -> str:
    """Best-effort normalisation to YYYY-MM-DD. Falls back to raw string."""
    if not raw:
        return ""
    # Try date range first ("20–21 January 2026" → first day)
    m = _DATE_RANGE_DMY.search(raw)
    if m:
        day, month, year = m.group(1), m.group(2), m.group(3)
        return f"{year}-{_MONTHS[month.lower()]}-{int(day):02d}"
    # Full day-month-year
    m = _DATE_DMY.search(raw)
    if m:
        day, month, year = m.group(1), m.group(2), m.group(3)
        return f"{year}-{_MONTHS[month.lower()]}-{int(day):02d}"
    # Month-year only
    m = _DATE_MY.search(raw)
    if m:
        month, year = m.group(1), m.group(2)
        return f"{year}-{_MONTHS[month.lower()]}-01"
    # Year only
    m = _DATE_YEAR_ONLY.search(raw)
    if m:
        return f"{m.group(1)}-01-01"
    return raw.strip()


# ---------------------------------------------------------------------------
# Field extraction helpers
# ---------------------------------------------------------------------------

_URL_RE = re.compile(r"\[([^\]]*)\]\((https?://[^)]+)\)")
_MD_LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")

# Heading number prefix patterns: "1.1 ", "A1. ", "1.4–1.5 ", etc.
_HEADING_NUM_PREFIX = re.compile(r"^[\dA-Z]+[\.\d–—-]*\s*")


def _extract_field(block: str, label: str) -> str:
    """Extract a **Label:** value from a bullet line."""
    pattern = re.compile(
        rf"[-*]\s*\*\*{re.escape(label)}:?\*\*:?\s*(.*)",
        re.IGNORECASE,
    )
    m = pattern.search(block)
    return m.group(1).strip() if m else ""


def _strip_md_links(text: str) -> str:
    """Replace [text](url) with just text."""
    return _MD_LINK_RE.sub(r"\1", text)


def parse_entry_block(
    block: str,
    country: list[str] | None = None,
    theme: list[str] | None = None,
) -> dict[str, Any]:
    """Parse a single entry block (starting with #### heading) into a dict."""
    lines = block.strip().splitlines()
    if not lines:
        return {}

    # Title from first line (strip #### and optional numbering prefix)
    title_line = lines[0].lstrip("#").strip()
    title = _HEADING_NUM_PREFIX.sub("", title_line).strip()

    # Rejoin remaining lines for field extraction
    body = "\n".join(lines[1:])

    # Date
    raw_date = _extract_field(body, "Date")
    date = normalise_date(raw_date)

    # Source
    raw_source = _extract_field(body, "Source")
    source_name = _strip_md_links(raw_source).strip()

    # URLs
    raw_url_line = _extract_field(body, "URL")
    urls = _URL_RE.findall(raw_url_line)  # list of (text, url)
    source_url = urls[0][1] if urls else ""
    additional_urls = [u[1] for u in urls[1:]] if len(urls) > 1 else []

    # If no URL found in the URL field, try to find one anywhere in the body
    if not source_url:
        all_urls = _URL_RE.findall(body)
        if all_urls:
            source_url = all_urls[0][1]
            additional_urls = [u[1] for u in all_urls[1:]]

    # Relevance
    relevance = _extract_field(body, "Relevance")

    # Key takeaway / summary
    summary = _extract_field(body, "Key takeaway")

    # Flag
    flagged = bool(re.search(r"\*\*\[FLAG\]", body) or re.search(r"\*\*\[NEW/SIGNIFICANT UPDATE\]", body))

    return {
        "title": title,
        "date": date,
        "source_name": source_name,
        "source_url": source_url,
        "additional_urls": additional_urls,
        "country": country or ["Regional"],
        "theme": theme or [],
        "relevance": relevance,
        "summary": summary,
        "flagged": flagged,
    }


# ---------------------------------------------------------------------------
# Document-level parser
# ---------------------------------------------------------------------------

_PART_RE = re.compile(r"^# Part \d", re.MULTILINE)
_H2_RE = re.compile(r"^## (.+)$", re.MULTILINE)
_H3_RE = re.compile(r"^### (.+)$", re.MULTILINE)
_H4_RE = re.compile(r"^#### (.+)$", re.MULTILINE)

# Countries recognised in Part 1
_COUNTRIES = {"Kenya", "Somalia", "South Sudan"}


def _split_by_heading(text: str, pattern: re.Pattern) -> list[tuple[str, str]]:
    """Split text into (heading_text, body) pairs at each heading match."""
    matches = list(pattern.finditer(text))
    if not matches:
        return [("", text)]
    result: list[tuple[str, str]] = []
    for i, m in enumerate(matches):
        heading = m.group(1) if m.lastindex else m.group(0)
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        result.append((heading.strip(), text[start:end]))
    return result


def _split_entries(text: str) -> list[str]:
    """Split a section into entry blocks on #### headings."""
    parts = re.split(r"(?=^#### )", text, flags=re.MULTILINE)
    return [p.strip() for p in parts if p.strip().startswith("#### ")]


def _clean_theme(raw: str) -> str:
    """Extract a readable theme name from ### or ## heading text."""
    # Remove "TOPIC N:" prefix
    cleaned = re.sub(r"^TOPIC\s+\d+[\s:–—-]*", "", raw, flags=re.IGNORECASE)
    # Remove "N. " or "A. " prefix
    cleaned = re.sub(r"^[A-Z0-9]+[\.\)]\s*", "", cleaned)
    # Remove "Topics N–M:" prefix
    cleaned = re.sub(r"^Topics?\s+[\d–—-]+[\s:]*", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip() or raw.strip()


def parse_desk_review(path: str | Path) -> list[dict[str, Any]]:
    """Parse the full desk review markdown file and return a list of entries."""
    text = Path(path).read_text(encoding="utf-8")
    entries: list[dict[str, Any]] = []

    # Split into parts at "# Part N" headings
    part_splits = list(_PART_RE.finditer(text))
    if not part_splits:
        return entries

    parts: list[tuple[str, str]] = []
    for i, m in enumerate(part_splits):
        # Get the full heading line
        line_end = text.index("\n", m.start()) if "\n" in text[m.start():] else len(text)
        heading = text[m.start():line_end].strip()
        start = line_end
        end = part_splits[i + 1].start() if i + 1 < len(part_splits) else len(text)
        # Stop at appendix if present
        appendix_match = re.search(r"^# Appendix", text[start:end], re.MULTILINE)
        if appendix_match:
            end = start + appendix_match.start()
        parts.append((heading, text[start:end]))

    for part_heading, part_body in parts:
        is_part1 = "Part 1" in part_heading

        # Split by ## headings
        h2_sections = _split_by_heading(part_body, _H2_RE)

        for h2_heading, h2_body in h2_sections:
            # Determine country
            if is_part1:
                country = [h2_heading.strip()] if h2_heading.strip() in _COUNTRIES else ["Regional"]
            else:
                country = ["Regional"]

            # Check for ### sub-sections
            h3_sections = _split_by_heading(h2_body, _H3_RE)

            if h3_sections and h3_sections[0][0]:
                # Has ### headings — use them as themes
                for h3_heading, h3_body in h3_sections:
                    theme = [_clean_theme(h3_heading)]
                    for entry_block in _split_entries(h3_body):
                        e = parse_entry_block(entry_block, country=country, theme=theme)
                        if e and e.get("title"):
                            entries.append(e)
            else:
                # No ### headings — entries directly under ##
                theme = [_clean_theme(h2_heading)] if h2_heading else []
                section_text = h2_body if not h3_sections else h3_sections[0][1]
                for entry_block in _split_entries(section_text):
                    e = parse_entry_block(entry_block, country=country, theme=theme)
                    if e and e.get("title"):
                        entries.append(e)

    return entries


if __name__ == "__main__":
    import json
    import sys

    path = sys.argv[1] if len(sys.argv) > 1 else "documentation/desk-review-update-oct2025-mar2026.md"
    results = parse_desk_review(path)
    print(f"Parsed {len(results)} entries")
    # Print first 3 as sample
    for r in results[:3]:
        print(json.dumps(r, indent=2, ensure_ascii=False))
