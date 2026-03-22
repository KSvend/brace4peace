#!/usr/bin/env python3
"""Orchestrate knowledge base seeding from desk review."""
import logging
import re
import sys
from pathlib import Path
from backend.ingest.parse_desk_review import parse_desk_review
from backend.ingest.fetch_sources import fetch_url, fetch_pdf
from backend.tools.embed import embed_and_store, generate_embedding
from backend.tools.classify import classify_finding

logger = logging.getLogger(__name__)
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DESK_REVIEW_PATH = REPO_ROOT / "documentation" / "desk-review-update-oct2025-mar2026.md"

SOURCE_TYPE_MAP = {
    "UNDP": "UN_AGENCY", "UNHCR": "UN_AGENCY", "UNOCHA": "UN_AGENCY",
    "UNESCO": "UN_AGENCY", "UN Human Rights": "UN_AGENCY", "OHCHR": "UN_AGENCY",
    "IGAD": "REGIONAL_BODY", "African Union": "REGIONAL_BODY", "EAC": "REGIONAL_BODY",
    "ICG": "THINK_TANK", "Crisis Group": "THINK_TANK", "ISS Africa": "THINK_TANK",
    "ACLED": "THINK_TANK", "Rift Valley": "THINK_TANK", "Small Arms Survey": "THINK_TANK",
    "Africa Center": "THINK_TANK",
    "HRW": "NGO_CSO", "Human Rights Watch": "NGO_CSO", "Amnesty": "NGO_CSO",
    "DRF": "NGO_CSO", "211Check": "FACT_CHECKER", "Africa Check": "FACT_CHECKER",
    "PesaCheck": "FACT_CHECKER",
}


def _valid_date(date_str: str | None) -> str | None:
    """Return date only if it looks like YYYY-MM-DD, else None."""
    if not date_str:
        return None
    if re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        return date_str
    return None


def _infer_source_type(source_name: str) -> str:
    for key, stype in SOURCE_TYPE_MAP.items():
        if key.lower() in source_name.lower():
            return stype
    return "QUALITY_MEDIA"


def seed(dry_run: bool = False, limit: int | None = None):
    from backend.db import get_client
    client = get_client()
    entries = parse_desk_review(str(DESK_REVIEW_PATH))
    if limit:
        entries = entries[:limit]
    logger.info(f"Parsed {len(entries)} desk review entries")
    stats = {"total": len(entries), "fetched": 0, "failed": 0, "embedded": 0}

    for i, entry in enumerate(entries):
        logger.info(f"[{i+1}/{len(entries)}] {entry['title'][:60]}...")
        source_type = _infer_source_type(entry.get("source_name", ""))
        source_row = {
            "title": entry["title"],
            "source_name": entry.get("source_name", ""),
            "source_url": entry.get("source_url", ""),
            "source_type": source_type,
            "date_published": _valid_date(entry.get("date")),
            "country": entry.get("country", []),
            "theme": entry.get("theme", []),
            "summary": entry.get("summary", ""),
            "created_by": "seed_desk_review",
        }
        if dry_run:
            logger.info(f"  DRY RUN: would insert source ({source_type})")
            continue

        src_result = client.table("sources").insert(source_row).execute()
        source_id = src_result.data[0]["id"] if src_result.data else None

        classification = classify_finding(
            title=entry["title"], summary=entry.get("summary", ""),
            country=entry.get("country"),
        )
        if source_id:
            client.table("sources").update({
                "classification": classification["classification"],
                "credibility_score": classification["confidence"],
            }).eq("id", source_id).execute()

        # Tier 2: embed summary
        summary_text = f"{entry['title']}\n\n{entry.get('summary', '')}"
        embedding = generate_embedding(summary_text)
        client.table("document_chunks").insert({
            "source_id": source_id, "tier": "finding", "content": summary_text,
            "chunk_index": 0, "embedding": embedding,
            "country": entry.get("country", []), "theme": entry.get("theme", []),
            "classification": classification["classification"],
            "date_published": _valid_date(entry.get("date")), "verified": True,
        }).execute()

        # Tier 1: fetch full text
        url = entry.get("source_url", "")
        if url:
            is_pdf = url.lower().endswith(".pdf")
            result = fetch_pdf(url) if is_pdf else fetch_url(url)
            if source_id:
                client.table("sources").update({"fetch_status": result["status"]}).eq("id", source_id).execute()
            if result["status"] == "FETCHED" and result["text"]:
                stats["fetched"] += 1
                embed_and_store(text=result["text"], metadata={
                    "source_id": source_id, "tier": "full_text",
                    "country": entry.get("country", []), "theme": entry.get("theme", []),
                    "classification": classification["classification"],
                    "date_published": _valid_date(entry.get("date")), "verified": True,
                }, client=client)
                stats["embedded"] += 1
            else:
                stats["failed"] += 1

    logger.info(f"Seeding complete: {stats}")
    return stats


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    dry_run = "--dry-run" in sys.argv
    limit = None
    for i, arg in enumerate(sys.argv):
        if arg == "--limit" and i + 1 < len(sys.argv):
            limit = int(sys.argv[i + 1])
    seed(dry_run=dry_run, limit=limit)
