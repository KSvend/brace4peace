#!/usr/bin/env python3
"""
Reach Tracker — Re-fetch engagement metrics for recent HS posts.
================================================================
For posts from the last 7 days, updates engagement data via Apify:
  - X/Twitter: apidojo~tweet-scraper
  - Facebook: apify~facebook-posts-scraper (with session cookies)
  - TikTok: clockworks~tiktok-scraper

Lightweight pass — if a post can't be re-fetched, skip it.
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

LOOKBACK_DAYS = 7
MAX_CHECKS_PER_PLATFORM = 30


def _apify_call(actor_id, payload, timeout=60):
    """Run an Apify actor synchronously and return dataset items."""
    if not APIFY_TOKEN:
        return None
    url = f"{APIFY_BASE}/acts/{actor_id}/run-sync-get-dataset-items?token={APIFY_TOKEN}&timeout={timeout}"
    data = json.dumps(payload).encode()
    headers = {"Content-Type": "application/json"}
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout + 10) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"    Apify error: {e}")
        return None


def fetch_x_engagement(url):
    """Fetch engagement for an X/Twitter post."""
    items = _apify_call("apidojo~tweet-scraper", {
        "startUrls": [{"url": url}],
        "maxItems": 1,
        "addUserInfo": False
    }, timeout=30)
    if items and len(items) > 0:
        item = items[0]
        return {
            "l": item.get("likeCount") or item.get("favoriteCount") or 0,
            "s": item.get("retweetCount") or item.get("shareCount") or 0,
            "c": item.get("replyCount") or item.get("commentCount") or 0,
        }
    return None


def fetch_fb_engagement(url):
    """Fetch engagement for a Facebook post using session cookies."""
    cookies_str = os.environ.get("FB_COOKIES", "")
    if not cookies_str:
        return None
    try:
        cookies = json.loads(cookies_str)
    except json.JSONDecodeError:
        return None

    items = _apify_call("apify~facebook-posts-scraper", {
        "startUrls": [{"url": url}],
        "maxPosts": 1,
        "cookies": cookies,
    }, timeout=45)
    if items and len(items) > 0:
        item = items[0]
        return {
            "l": item.get("likes") or item.get("reactionsCount") or 0,
            "s": item.get("shares") or item.get("sharesCount") or 0,
            "c": item.get("comments") or item.get("commentsCount") or 0,
        }
    return None


def fetch_tiktok_engagement(url):
    """Fetch engagement for a TikTok post."""
    items = _apify_call("clockworks~tiktok-scraper", {
        "startUrls": [{"url": url}],
        "resultsPerPage": 1,
    }, timeout=30)
    if items and len(items) > 0:
        item = items[0]
        stats = item.get("stats") or item.get("videoMeta") or {}
        return {
            "l": stats.get("diggCount") or stats.get("heartCount") or item.get("diggCount") or 0,
            "s": stats.get("shareCount") or item.get("shareCount") or 0,
            "c": stats.get("commentCount") or item.get("commentCount") or 0,
            "v": stats.get("playCount") or item.get("playCount") or 0,
        }
    return None


PLATFORM_FETCHERS = {
    "x": fetch_x_engagement,
    "facebook": fetch_fb_engagement,
    "tiktok": fetch_tiktok_engagement,
}


def main():
    """Update engagement metrics for recent posts."""
    if not APIFY_TOKEN:
        print("No APIFY_TOKEN set, skipping reach tracking")
        return {"updated": 0, "error": "no API token"}

    with open(HS_DATA_PATH) as f:
        posts = json.load(f)

    cutoff = (datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)).strftime("%Y-%m-%d")

    # Group candidates by platform
    by_platform = {}
    for p in posts:
        if p.get("d", "") >= cutoff and p.get("l"):
            plat = p.get("p", "")
            if plat in PLATFORM_FETCHERS:
                by_platform.setdefault(plat, []).append(p)

    total_updated = 0
    total_checked = 0

    for platform, candidates in by_platform.items():
        candidates = candidates[:MAX_CHECKS_PER_PLATFORM]
        fetcher = PLATFORM_FETCHERS[platform]
        updated = 0

        print(f"  Reach tracking: {len(candidates)} recent {platform} posts")

        for i, p in enumerate(candidates):
            engagement = fetcher(p["l"])
            if engagement:
                has_data = any(v > 0 for v in engagement.values())
                if has_data:
                    p["en"] = engagement
                    updated += 1

            if (i + 1) % 10 == 0:
                print(f"    {platform}: checked {i+1}/{len(candidates)} ({updated} updated)")

            time.sleep(1)

        total_updated += updated
        total_checked += len(candidates)
        print(f"  {platform}: {updated}/{len(candidates)} updated")

    if total_updated > 0:
        with open(HS_DATA_PATH, "w") as f:
            json.dump(posts, f, ensure_ascii=False, separators=(",", ":"))

    print(f"Reach tracking total: {total_updated}/{total_checked} posts updated")
    return {"updated": total_updated, "checked": total_checked}


if __name__ == "__main__":
    main()
