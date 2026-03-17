#!/usr/bin/env python3
"""
Apify Keyword Sweep Orchestrator for BRACE4PEACE Disinfo Monitoring
===================================================================
This script runs targeted keyword searches on X/Twitter, Facebook, and TikTok
using Apify actors. It follows the rotation schedule defined in apify_keyword_strategy.json.

Usage:
    python3 apify_sweep.py [--day N] [--dry-run] [--budget-cap USD]

The script:
1. Reads the rotation schedule to determine today's keyword groups
2. Runs searches on each platform using the appropriate Apify actor
3. Saves raw results to workspace for classification by the monitoring cron
4. Tracks costs and respects budget caps
"""

import json
import os
import sys
import time
import argparse
from datetime import datetime, timezone
from pathlib import Path

# ─── Configuration ───────────────────────────────────────────────────────────

APIFY_TOKEN = os.environ.get("APIFY_TOKEN", "")  # Set via environment variable
BASE_URL = "https://api.apify.com/v2"

# Actor IDs (from Apify store) — use tilde notation for API paths
ACTORS = {
    "x": "apidojo~tweet-scraper",
    "facebook": "apify~facebook-posts-scraper",
    "tiktok": "clockworks~tiktok-scraper"
}

# Budget limits per run
DEFAULT_BUDGET_CAP_USD = 1.50  # Max spend per sweep run
MAX_ITEMS_PER_QUERY = {
    "x": 50,
    "facebook": 10,
    "tiktok": 5  # TikTok is expensive (~$0.02/item) — keep volume low
}

# Paths
WORKSPACE = Path("/home/user/workspace")
STRATEGY_PATH = WORKSPACE / "brace4peace/monitoring/apify_keyword_strategy.json"
RESULTS_DIR = WORKSPACE / "brace4peace/monitoring/apify_results"
COST_LOG = WORKSPACE / "brace4peace/monitoring/apify_cost_log.json"

# ─── HTTP helpers (using urllib to avoid dependency) ─────────────────────────

import urllib.request
import urllib.error

def api_get(path):
    """GET request to Apify API."""
    url = f"{BASE_URL}{path}{'&' if '?' in path else '?'}token={APIFY_TOKEN}"
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        return {"error": {"type": str(e.code), "message": body}}

def api_post(path, data):
    """POST request to Apify API."""
    url = f"{BASE_URL}{path}{'&' if '?' in path else '?'}token={APIFY_TOKEN}"
    body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body_text = e.read().decode() if e.fp else ""
        return {"error": {"type": str(e.code), "message": body_text}}


# ─── Core Functions ──────────────────────────────────────────────────────────

def load_strategy():
    """Load the keyword strategy JSON."""
    with open(STRATEGY_PATH) as f:
        return json.load(f)

def get_todays_groups(strategy, day_override=None):
    """Determine which keyword groups to run today based on rotation schedule."""
    schedule = strategy.get("rotation_schedule", {})
    mode = schedule.get("mode", "rotating")

    if mode == "all_daily":
        # Run all groups every day
        group_names = list(strategy.get("keyword_groups", {}).keys())
        print(f"📅 Mode: all_daily — running all {len(group_names)} groups")
        return group_names, 0

    # Rotating mode: 10-day cycle
    if day_override is not None:
        day_num = day_override
    else:
        epoch = datetime(2026, 3, 16, tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        days_since = (now - epoch).days
        day_num = (days_since % 10) + 1

    day_key = f"day_{day_num:02d}"
    group_names = schedule.get(day_key, [])

    print(f"📅 Rotation day {day_num} ({day_key}): {group_names}")
    return group_names, day_num

def build_x_search(queries, max_items=50):
    """Build input for apidojo/tweet-scraper."""
    return {
        "searchTerms": queries,
        "maxItems": max_items,
        "sort": "Latest"
    }

def build_facebook_search(queries, max_items=20, page_urls=None):
    """Build input for apify/facebook-posts-scraper.
    
    Facebook search requires login, so we monitor known pages instead.
    page_urls: list of Facebook page URLs to check for new posts.
    If page_urls is provided, we scrape those pages. Otherwise skip.
    """
    if page_urls:
        urls = [{"url": u} for u in page_urls]
    else:
        # No pages to monitor — can't do FB keyword search without login
        return None
    return {
        "startUrls": urls,
        "resultsLimit": max_items
    }

def build_tiktok_search(queries, max_items=20):
    """Build input for clockworks/tiktok-scraper."""
    return {
        "searchQueries": queries,
        "resultsPerPage": max_items,
        "shouldDownloadVideos": False,
        "shouldDownloadCovers": False
    }

def run_actor(actor_name, input_data):
    """Start an Apify actor run and return run metadata."""
    path = f"/acts/{actor_name}/runs"
    result = api_post(path, input_data)

    if "error" in result:
        return {"error": result["error"], "actor": actor_name}

    run_data = result.get("data", {})
    return {
        "run_id": run_data.get("id"),
        "dataset_id": run_data.get("defaultDatasetId"),
        "status": run_data.get("status"),
        "actor": actor_name
    }

def wait_for_run(run_id, timeout_seconds=120):
    """Poll until a run completes or times out."""
    start = time.time()
    while time.time() - start < timeout_seconds:
        result = api_get(f"/actor-runs/{run_id}")
        if "error" in result:
            return {"status": "ERROR", "error": result["error"]}

        status = result.get("data", {}).get("status", "UNKNOWN")
        if status in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
            data = result["data"]
            return {
                "status": status,
                "usage_usd": data.get("usageTotalUsd", 0),
                "events": data.get("chargedEventCounts", {}),
                "finished_at": data.get("finishedAt")
            }
        time.sleep(5)

    return {"status": "TIMEOUT", "error": f"Run {run_id} did not complete within {timeout_seconds}s"}

def get_dataset_items(dataset_id, limit=100):
    """Retrieve items from a dataset."""
    result = api_get(f"/datasets/{dataset_id}/items?limit={limit}&format=json")
    if isinstance(result, list):
        return result
    if "error" in result:
        return []
    return result.get("data", {}).get("items", []) if isinstance(result, dict) else []

def run_keyword_group(group_name, group_config, strategy, dry_run=False):
    """Run searches for a single keyword group across all its platforms."""
    queries = group_config.get("queries", [])
    platforms = group_config.get("platforms", [])
    results = {
        "group": group_name,
        "narrative_ids": group_config.get("narrative_ids", []),
        "disinfo_type": group_config.get("disinfo_type", ""),
        "platforms_searched": [],
        "runs": [],
        "total_results": 0,
        "total_cost_usd": 0.0,
        "items": []
    }

    for platform in platforms:
        if platform == "telegram_via_web":
            # Skip Telegram — we monitor via web/browser_task
            continue

        actor = ACTORS.get(platform)
        if not actor:
            print(f"  ⚠️  No actor for platform '{platform}', skipping")
            continue

        max_items = MAX_ITEMS_PER_QUERY.get(platform, 20)

        if platform == "x":
            input_data = build_x_search(queries, max_items)
        elif platform == "facebook":
            # Facebook keyword search requires login — use known page URLs instead
            fb_pages = group_config.get("facebook_pages", [])
            if not fb_pages:
                print(f"  ⚠️  No facebook_pages defined for {group_name}, skipping FB")
                continue
            input_data = build_facebook_search(queries, max_items, page_urls=fb_pages)
            if input_data is None:
                continue
        elif platform == "tiktok":
            input_data = build_tiktok_search(queries, max_items)
        else:
            continue

        if dry_run:
            print(f"  🏃 [DRY RUN] Would run {actor} with {len(queries)} queries")
            results["platforms_searched"].append(platform)
            continue

        print(f"  🏃 Running {actor} for {platform}...")
        run_info = run_actor(actor, input_data)

        if "error" in run_info:
            print(f"  ❌ Error starting {platform}: {run_info['error']}")
            results["runs"].append({"platform": platform, "error": str(run_info["error"])})
            continue

        run_id = run_info["run_id"]
        dataset_id = run_info["dataset_id"]
        print(f"  ⏳ Run {run_id} started, waiting...")

        completion = wait_for_run(run_id, timeout_seconds=180)
        status = completion.get("status", "UNKNOWN")
        cost = completion.get("usage_usd", 0)

        print(f"  {'✅' if status == 'SUCCEEDED' else '❌'} {platform}: {status}, cost=${cost:.4f}")

        run_record = {
            "platform": platform,
            "actor": actor,
            "run_id": run_id,
            "dataset_id": dataset_id,
            "status": status,
            "cost_usd": cost,
            "events": completion.get("events", {})
        }

        if status == "SUCCEEDED":
            items = get_dataset_items(dataset_id, limit=max_items)
            # Filter out "noResults" placeholder items
            real_items = [i for i in items if not i.get("noResults")]
            run_record["item_count"] = len(real_items)
            results["total_results"] += len(real_items)

            # Tag items with platform and group metadata
            for item in real_items:
                item["_brace4peace"] = {
                    "keyword_group": group_name,
                    "platform": platform,
                    "narrative_ids": group_config.get("narrative_ids", []),
                    "sweep_timestamp": datetime.now(timezone.utc).isoformat()
                }
            results["items"].extend(real_items)

        results["runs"].append(run_record)
        results["total_cost_usd"] += cost
        results["platforms_searched"].append(platform)

    return results


def save_results(all_results, day_num, run_timestamp):
    """Save sweep results to disk."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    date_str = run_timestamp.strftime("%Y-%m-%d")
    time_str = "morning" if run_timestamp.hour < 12 else "afternoon"

    # Save full results
    output_path = RESULTS_DIR / f"sweep_{date_str}_{time_str}.json"
    output = {
        "run_timestamp_utc": run_timestamp.isoformat(),
        "rotation_day": day_num,
        "groups_searched": [r["group"] for r in all_results],
        "total_results": sum(r["total_results"] for r in all_results),
        "total_cost_usd": sum(r["total_cost_usd"] for r in all_results),
        "group_results": []
    }

    # Separate items into their own file (can be large)
    all_items = []
    for r in all_results:
        items = r.pop("items", [])
        all_items.extend(items)
        output["group_results"].append(r)

    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n📄 Sweep summary saved to: {output_path}")

    if all_items:
        items_path = RESULTS_DIR / f"items_{date_str}_{time_str}.json"
        with open(items_path, "w") as f:
            json.dump(all_items, f, indent=2)
        print(f"📄 {len(all_items)} items saved to: {items_path}")

    # Update cost log
    update_cost_log(output["total_cost_usd"], date_str, len(all_items))

    return output_path


def update_cost_log(cost_usd, date_str, item_count):
    """Track cumulative Apify spend."""
    if COST_LOG.exists():
        with open(COST_LOG) as f:
            log = json.load(f)
    else:
        log = {"runs": [], "cumulative_usd": 0.0, "month_start": date_str[:7]}

    # Reset monthly counter if new month
    current_month = date_str[:7]
    if log.get("month_start") != current_month:
        log["monthly_usd"] = 0.0
        log["month_start"] = current_month

    log["runs"].append({
        "date": date_str,
        "cost_usd": round(cost_usd, 4),
        "items": item_count
    })
    log["cumulative_usd"] = round(log.get("cumulative_usd", 0) + cost_usd, 4)
    log["monthly_usd"] = round(log.get("monthly_usd", 0) + cost_usd, 4)

    with open(COST_LOG, "w") as f:
        json.dump(log, f, indent=2)


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="BRACE4PEACE Apify Keyword Sweep")
    parser.add_argument("--day", type=int, help="Override rotation day (1-10)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would run without executing")
    parser.add_argument("--budget-cap", type=float, default=DEFAULT_BUDGET_CAP_USD,
                        help=f"Max USD to spend this run (default: ${DEFAULT_BUDGET_CAP_USD})")
    parser.add_argument("--groups", nargs="+", help="Override: run specific groups instead of rotation")
    args = parser.parse_args()

    print("=" * 60)
    print("🔍 BRACE4PEACE Apify Keyword Sweep")
    print("=" * 60)

    strategy = load_strategy()
    run_timestamp = datetime.now(timezone.utc)

    if args.groups:
        group_names = args.groups
        day_num = 0
        print(f"📋 Manual override: running groups {group_names}")
    else:
        group_names, day_num = get_todays_groups(strategy, args.day)

    if not group_names:
        print("⚠️  No groups scheduled for today. Exiting.")
        return

    keyword_groups = strategy.get("keyword_groups", {})
    total_cost = 0.0
    all_results = []

    for gname in group_names:
        gconfig = keyword_groups.get(gname)
        if not gconfig:
            print(f"\n⚠️  Group '{gname}' not found in strategy, skipping")
            continue

        print(f"\n{'─' * 40}")
        print(f"🎯 {gname}: {gconfig.get('disinfo_type', '')[:80]}")
        print(f"   Queries: {len(gconfig.get('queries', []))}, Platforms: {gconfig.get('platforms', [])}")

        if total_cost >= args.budget_cap:
            print(f"  💰 Budget cap ${args.budget_cap} reached (spent ${total_cost:.4f}), skipping remaining groups")
            break

        result = run_keyword_group(gname, gconfig, strategy, dry_run=args.dry_run)
        all_results.append(result)
        total_cost += result["total_cost_usd"]

    # Save results
    if not args.dry_run:
        save_results(all_results, day_num, run_timestamp)

    print(f"\n{'=' * 60}")
    print(f"✅ Sweep complete")
    print(f"   Groups: {len(all_results)}")
    print(f"   Total results: {sum(r['total_results'] for r in all_results)}")
    print(f"   Total cost: ${total_cost:.4f}")
    print(f"   Budget remaining: ${args.budget_cap - total_cost:.4f}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
