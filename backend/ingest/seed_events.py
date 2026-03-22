#!/usr/bin/env python3
"""Load events.json into the knowledge base as Tier 2 items."""
import json, logging, sys
from pathlib import Path
from backend.tools.embed import generate_embedding

logger = logging.getLogger(__name__)
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
EVENTS_PATH = REPO_ROOT / "docs" / "data" / "events.json"


def seed(dry_run: bool = False):
    from backend.db import get_client
    client = get_client()
    events = json.loads(EVENTS_PATH.read_text())
    logger.info(f"Loading {len(events)} events")
    for i, event in enumerate(events):
        text = f"{event.get('headline', '')}\n\n{event.get('summary', '')}"
        if not text.strip():
            continue
        country = [event.get("country", "Regional")]
        # Map event_type to schema values (events.json uses "DISINFO" not "HS_DISINFO")
        raw_type = event.get("event_type", "CONTEXT")
        type_map = {"DISINFO": "HS_DISINFO", "CONTEXT": "CONTEXT", "VE_PROPAGANDA": "VE_PROPAGANDA"}
        classification = type_map.get(raw_type, "CONTEXT")
        # NOTE: field is "narrative_family" (list) in events.json
        themes = event.get("narrative_family", [])
        if isinstance(themes, str):
            themes = [themes]
        if dry_run:
            logger.info(f"  DRY RUN: [{i+1}] {event.get('headline', '')[:60]}")
            continue
        embedding = generate_embedding(text)
        client.table("document_chunks").insert({
            "tier": "event", "content": text, "chunk_index": 0,
            "embedding": embedding, "country": country, "theme": themes,
            "classification": classification,
            "date_published": event.get("date"), "verified": True,
        }).execute()
    logger.info(f"Events seeding complete: {len(events)} events")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    dry_run = "--dry-run" in sys.argv
    seed(dry_run=dry_run)
