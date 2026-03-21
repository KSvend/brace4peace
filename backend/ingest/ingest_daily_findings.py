#!/usr/bin/env python3
"""Ingest the latest daily monitoring findings into the knowledge base."""
import json
import logging
import sys
from pathlib import Path
from backend.tools.embed import generate_embedding
from backend.tools.classify import classify_finding

logger = logging.getLogger(__name__)
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
FINDINGS_DIR = REPO_ROOT / "monitoring" / "findings"


def ingest(dry_run: bool = False):
    from backend.db import get_client
    client = get_client()

    # Find the latest findings file
    files = sorted(FINDINGS_DIR.glob("findings_*.json"), reverse=True)
    if not files:
        logger.info("No findings files found")
        return

    latest = files[0]
    logger.info(f"Ingesting from {latest.name}")
    data = json.loads(latest.read_text())
    items = data.get("new_items", [])
    logger.info(f"Found {len(items)} new items")

    for i, item in enumerate(items):
        title = item.get("summary", "")[:100]
        summary = item.get("summary", "")
        country = [item.get("country", "Regional")]
        source_url = item.get("source", {}).get("url", "")
        source_name = item.get("source", {}).get("publisher", "")
        date = item.get("source", {}).get("date", "")

        if dry_run:
            logger.info(f"  DRY RUN: [{i+1}] {title[:60]}")
            continue

        classification = classify_finding(title=title, summary=summary, country=country)

        # Insert source
        src_result = client.table("sources").insert({
            "title": title, "source_name": source_name, "source_url": source_url or "N/A",
            "source_type": "QUALITY_MEDIA", "date_published": date or None,
            "country": country, "theme": item.get("narrative_family", []),
            "summary": summary, "created_by": "daily_ingestion",
        }).execute()
        source_id = src_result.data[0]["id"] if src_result.data else None

        # Insert finding as UNVERIFIED
        client.table("findings").insert({
            "source_id": source_id, "title": title, "summary": summary,
            "country": country, "theme": item.get("narrative_family", []) or item.get("category", []),
            "classification": classification["classification"],
            "hs_subtype": classification.get("hs_subtype"),
            "confidence": classification["confidence"],
            "status": "UNVERIFIED", "created_by": "daily_ingestion",
        }).execute()

        # Embed
        text = f"{title}\n\n{summary}"
        embedding = generate_embedding(text)
        client.table("document_chunks").insert({
            "source_id": source_id, "tier": "finding", "content": text,
            "chunk_index": 0, "embedding": embedding,
            "country": country, "theme": item.get("narrative_family", []),
            "classification": classification["classification"],
            "date_published": date or None, "verified": False,
        }).execute()

    logger.info(f"Ingested {len(items)} findings")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    dry_run = "--dry-run" in sys.argv
    ingest(dry_run=dry_run)
