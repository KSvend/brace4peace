#!/usr/bin/env python3
"""Compute Tier 3 aggregated statistics from hate_speech_posts.json."""
import json, logging, sys
from pathlib import Path
from collections import Counter

logger = logging.getLogger(__name__)
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
HS_PATH = REPO_ROOT / "docs" / "data" / "hate_speech_posts.json"


def compute(dry_run: bool = False):
    from backend.db import get_client
    posts = json.loads(HS_PATH.read_text())
    logger.info(f"Computing stats from {len(posts)} posts")

    by_country = {}
    for p in posts:
        c = p.get("country", "Unknown")
        pred = p.get("eaHsPred", "Normal")
        by_country.setdefault(c, Counter())[pred] += 1

    subtypes_by_country = {}
    for p in posts:
        c = p.get("country", "Unknown")
        for st in (p.get("subtopics") or []):
            subtypes_by_country.setdefault(c, Counter())[st] += 1

    tox_by_country = {}
    for p in posts:
        c = p.get("country", "Unknown")
        for dim in ["probToxicity", "probSevereToxicity", "probInsult", "probIdentityAttack", "probThreat"]:
            level = p.get(dim, "none")
            tox_by_country.setdefault(c, {}).setdefault(dim, Counter())[level] += 1

    if dry_run:
        logger.info(f"DRY RUN: would write stats for {len(by_country)} countries")
        return

    client = get_client()
    # Clear old stats — use a guaranteed-false condition as workaround for Supabase delete
    client.table("aggregated_stats").delete().neq("stat_type", "__nonexistent__").execute()

    rows = []
    for country, counts in by_country.items():
        rows.append({"stat_type": "hs_by_country_subtype", "country": country,
                      "period": "2025-10 to 2026-03", "data": dict(counts)})
    for country, counts in subtypes_by_country.items():
        rows.append({"stat_type": "subtype_distribution", "country": country,
                      "period": "2025-10 to 2026-03", "data": dict(counts)})
    for country, dims in tox_by_country.items():
        rows.append({"stat_type": "toxicity_by_country", "country": country,
                      "period": "2025-10 to 2026-03",
                      "data": {k: dict(v) for k, v in dims.items()}})
    client.table("aggregated_stats").insert(rows).execute()
    logger.info(f"Wrote {len(rows)} stat rows")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    dry_run = "--dry-run" in sys.argv
    compute(dry_run=dry_run)
