#!/usr/bin/env python3
"""
Reach Tracker — Re-fetch engagement metrics for recent HS posts.
================================================================
For posts from the last 7 days, attempts to update engagement data.
Uses Apify API to re-scrape individual post URLs.

This is a lightweight pass — if a post can't be re-fetched, skip it.
"""

import json
import os
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HS_DATA_PATH = REPO_ROOT / "docs" / "data" / "hate_speech_posts.json"

APIFY_TOKEN = os.environ.get("APIFY_TOKEN", "")
APIFY_BASE = "https://api.apify.com/v2"

# Only re-fetch posts from the last N days
LOOKBACK_DAYS = 7


def fetch_x_engagement(url):
    """Fetch engagement for an X/Twitter post via Apify."""
    if not APIFY_TOKEN or not url:
        return None
    # Use the tweet scraper to get a single tweet by URL
    # This is a lightweight call (~$0.001)
    payload = json.dumps({
        "startUrls": [{"url": url}],
        "maxItems": 1,
        "addUserInfo": False
    }).encode()

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {APIFY_TOKEN}"
    }

    actor_url = f"{APIFY_BASE}/acts/apidojo~tweet-scraper/run-sync-get-dataset-items?timeout=30"
    req = urllib.request.Request(actor_url, data=payload, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            items = json.loads(resp.read().decode())
            if items and len(items) > 0:
                item = items[0]
                return {
                    "l": item.get("likeCount") or item.get("favoriteCount") or 0,
                    "s": item.get("retweetCount") or item.get("shareCount") or 0,
                    "c": item.get("replyCount") or item.get("commentCount") or 0,
                }
    except Exception as e:
        pass
    return None


def main():
    """Update engagement metrics for recent posts."""
    if not APIFY_TOKEN:
        print("No APIFY_TOKEN set, skipping reach tracking")
        return {"updated": 0, "error": "no API token"}

    with open(HS_DATA_PATH) as f:
        posts = json.load(f)

    cutoff = (datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)).strftime("%Y-%m-%d")

    # Find recent posts that might benefit from reach updates
    candidates = [
        p for p in posts
        if p.get("d", "") >= cutoff
        and p.get("p") == "x"  # Only X/Twitter for now (Apify actor available)
        and p.get("l")  # Must have a URL
    ]

    print(f"Reach tracking: {len(candidates)} recent X posts to check")

    # Limit to avoid excessive Apify costs (~$0.001 per call)
    MAX_CHECKS = 50
    candidates = candidates[:MAX_CHECKS]

    updated = 0
    for i, p in enumerate(candidates):
        engagement = fetch_x_engagement(p["l"])
        if engagement:
            old_en = p.get("en", {})
            # Only update if we got meaningful data
            if engagement["l"] > 0 or engagement["s"] > 0 or engagement["c"] > 0:
                p["en"] = engagement
                updated += 1

        if (i + 1) % 10 == 0:
            print(f"  Checked {i+1}/{len(candidates)} ({updated} updated)")

        time.sleep(1)  # Rate limit

    if updated > 0:
        with open(HS_DATA_PATH, "w") as f:
            json.dump(posts, f, separators=(",", ":"))

    print(f"Reach tracking: {updated}/{len(candidates)} posts updated")
    return {"updated": updated, "checked": len(candidates)}


if __name__ == "__main__":
    main()
