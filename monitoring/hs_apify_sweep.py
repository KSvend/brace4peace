#!/usr/bin/env python3
"""
HS Apify Sweep Orchestrator for BRACE4PEACE Hate Speech Monitoring
===================================================================
Separate pipeline from the disinfo sweep. Targets HS-specific keyword groups
defined in monitoring/config/hs_keyword_strategy.json.

Usage:
    python3 hs_apify_sweep.py [--dry-run] [--budget-cap USD]

The script:
1. Reads hs_keyword_strategy.json for HS keyword groups
2. Loads toxic_handles.csv for direct monitoring of known offenders
3. Loads learned_keywords_hs.csv for auto-learned keyword enrichment
4. Runs X/Twitter and TikTok actors (Facebook skipped — requires login)
5. Annotates items with _hs_group, _hs_subtype, _hs_country, _platform, _sweep_date
6. Saves to monitoring/apify_results/hs/hs_sweep_YYYY-MM-DD.json
7. Budget cap: $0.50/run
"""

import json
import os
import sys
import csv
import time
import argparse
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ─── Configuration ───────────────────────────────────────────────────────────

APIFY_TOKEN = os.environ.get("APIFY_TOKEN", "")
BASE_URL = "https://api.apify.com/v2"

# Actor IDs (from Apify store) — tilde notation for API paths
ACTORS = {
    "x": "apidojo~tweet-scraper",
    "tiktok": "clockworks~tiktok-scraper",
}

# Budget limits
DEFAULT_BUDGET_CAP_USD = 0.50

# Max items per query per platform
MAX_ITEMS_PER_QUERY = {
    "x": 50,
    "tiktok": 5,  # TikTok is expensive (~$0.02/item) — keep volume low
}

# Paths (relative to repo root)
REPO_ROOT = Path(__file__).resolve().parent.parent
STRATEGY_PATH = REPO_ROOT / "monitoring" / "config" / "hs_keyword_strategy.json"
TOXIC_HANDLES_PATH = REPO_ROOT / "monitoring" / "autolearn" / "toxic_handles.csv"
LEARNED_KW_PATH = REPO_ROOT / "monitoring" / "autolearn" / "learned_keywords_hs.csv"
RESULTS_DIR = REPO_ROOT / "monitoring" / "apify_results" / "hs"
COST_LOG = REPO_ROOT / "data" / "apify_cost_log.json"


# ─── HTTP helpers (pure urllib — no pip dependencies) ─────────────────────────

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
    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body_text = e.read().decode() if e.fp else ""
        return {"error": {"type": str(e.code), "message": body_text}}


# ─── Data Loading ────────────────────────────────────────────────────────────

def load_strategy():
    """Load the HS keyword strategy JSON."""
    if not STRATEGY_PATH.exists():
        print(f"ERROR: Strategy file not found: {STRATEGY_PATH}")
        sys.exit(1)
    with open(STRATEGY_PATH) as f:
        return json.load(f)


def load_toxic_handles():
    """Load active toxic handles from CSV for direct monitoring.

    Expected CSV columns: handle, platform, status, toxicity_score,
                          total_posts, first_seen, last_seen
    Returns list of dicts for handles with status='active'.
    """
    handles = []
    if not TOXIC_HANDLES_PATH.exists():
        print("  (i) No toxic_handles.csv found — skipping handle monitoring")
        return handles

    with open(TOXIC_HANDLES_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("status", "").strip().lower() == "active":
                handles.append({
                    "handle": row.get("handle", "").strip(),
                    "platform": row.get("platform", "x").strip().lower(),
                    "toxicity_score": float(row.get("toxicity_score", 0.5)),
                })
    print(f"  Loaded {len(handles)} active toxic handles")
    return handles


def load_learned_keywords():
    """Load active auto-learned HS keywords from CSV.

    Expected CSV columns: keyword, hs_subtype, country, status,
                          hit_count, first_seen, last_seen
    Returns list of dicts for keywords with status='active'.
    """
    keywords = []
    if not LEARNED_KW_PATH.exists():
        print("  (i) No learned_keywords_hs.csv found — skipping learned enrichment")
        return keywords

    with open(LEARNED_KW_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("status", "").strip().lower() == "active":
                keywords.append({
                    "keyword": row.get("keyword", "").strip(),
                    "hs_subtype": row.get("hs_subtype", "").strip(),
                    "country": row.get("country", "").strip(),
                })
    print(f"  Loaded {len(keywords)} active learned keywords")
    return keywords


# ─── Date Filtering ──────────────────────────────────────────────────────────

def get_date_range():
    """Return (since, until) date strings for last-24h filtering.

    Used to append 'since:YYYY-MM-DD until:YYYY-MM-DD' to X/Twitter queries
    so we avoid re-fetching old posts.
    """
    now = datetime.now(timezone.utc)
    until_date = now.strftime("%Y-%m-%d")
    since_date = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    return since_date, until_date


def apply_date_filter(query, since, until):
    """Append date range to a search query string (X/Twitter format)."""
    return f"{query} since:{since} until:{until}"


# ─── Query Building ──────────────────────────────────────────────────────────

def build_queries_for_group(group_name, group_config, toxic_handles, learned_kw,
                            since, until):
    """Build the full query list for a keyword group.

    Combines:
    - Base queries from hs_keyword_strategy.json
    - Learned keywords matching this group's hs_subtype / country
    - Toxic handle direct searches (only for X platform)

    Returns dict keyed by platform with lists of query strings.
    """
    base_queries = group_config.get("queries", [])
    hs_subtype = group_config.get("hs_subtype", "")
    country = group_config.get("country", "")
    platforms = group_config.get("platforms", [])

    # Enrich with learned keywords matching this group
    extra_queries = []
    for lk in learned_kw:
        # Match by subtype or country
        if lk["hs_subtype"] == hs_subtype or lk["country"] == country:
            kw = lk["keyword"]
            if kw and kw not in base_queries:
                extra_queries.append(kw)

    if extra_queries:
        print(f"    + {len(extra_queries)} learned keywords added")

    all_queries = base_queries + extra_queries

    queries_by_platform = {}

    for platform in platforms:
        if platform not in ACTORS:
            # Skip unsupported platforms (e.g. facebook)
            continue

        if platform == "x":
            # Apply date filter for X/Twitter
            filtered = [apply_date_filter(q, since, until) for q in all_queries]
            queries_by_platform["x"] = filtered
        elif platform == "tiktok":
            # TikTok search — no date filter syntax, just raw queries
            queries_by_platform["tiktok"] = list(all_queries)

    return queries_by_platform


def build_toxic_handle_queries(toxic_handles, since, until):
    """Build direct search queries for known toxic handles.

    For each active handle on X, creates 'from:{handle}' with date filter.
    Returns dict keyed by platform.
    """
    x_queries = []
    for h in toxic_handles:
        handle = h["handle"].lstrip("@")
        if not handle:
            continue
        if h["platform"] == "x":
            q = f"from:{handle}"
            x_queries.append(apply_date_filter(q, since, until))

    return {"x": x_queries} if x_queries else {}


# ─── Actor Input Builders ────────────────────────────────────────────────────

def build_x_input(queries, max_items=50):
    """Build input payload for apidojo/tweet-scraper."""
    return {
        "searchTerms": queries,
        "maxItems": max_items,
        "sort": "Latest",
    }


def build_tiktok_input(queries, max_items=5):
    """Build input payload for clockworks/tiktok-scraper."""
    return {
        "searchQueries": queries,
        "resultsPerPage": max_items,
        "shouldDownloadVideos": False,
        "shouldDownloadCovers": False,
    }


# ─── Actor Execution ─────────────────────────────────────────────────────────

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
        "actor": actor_name,
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
                "finished_at": data.get("finishedAt"),
            }
        time.sleep(5)

    return {
        "status": "TIMEOUT",
        "error": f"Run {run_id} did not complete within {timeout_seconds}s",
    }


def get_dataset_items(dataset_id, limit=100):
    """Retrieve items from an Apify dataset."""
    result = api_get(f"/datasets/{dataset_id}/items?limit={limit}&format=json")
    if isinstance(result, list):
        return result
    if isinstance(result, dict):
        if "error" in result:
            return []
        return result.get("data", {}).get("items", [])
    return []


# ─── Sweep Execution ─────────────────────────────────────────────────────────

def run_platform_search(platform, queries, group_name, group_config,
                        sweep_date, dry_run=False):
    """Run a single platform search and return annotated items + cost."""
    actor = ACTORS.get(platform)
    if not actor:
        return [], 0.0, None

    max_items = MAX_ITEMS_PER_QUERY.get(platform, 20)

    if platform == "x":
        input_data = build_x_input(queries, max_items)
    elif platform == "tiktok":
        input_data = build_tiktok_input(queries, max_items)
    else:
        return [], 0.0, None

    if dry_run:
        print(f"    [DRY RUN] Would run {actor} with {len(queries)} queries")
        return [], 0.0, {"platform": platform, "dry_run": True}

    print(f"    Running {actor} ({len(queries)} queries)...")
    run_info = run_actor(actor, input_data)

    if "error" in run_info:
        print(f"    ERROR starting {platform}: {run_info['error']}")
        return [], 0.0, {
            "platform": platform,
            "error": str(run_info["error"]),
        }

    run_id = run_info["run_id"]
    dataset_id = run_info["dataset_id"]
    print(f"    Run {run_id} started, waiting...")

    completion = wait_for_run(run_id, timeout_seconds=180)
    status = completion.get("status", "UNKNOWN")
    cost = completion.get("usage_usd", 0)

    ok = status == "SUCCEEDED"
    print(f"    {'OK' if ok else 'FAIL'} {platform}: {status}, cost=${cost:.4f}")

    run_record = {
        "platform": platform,
        "actor": actor,
        "run_id": run_id,
        "dataset_id": dataset_id,
        "status": status,
        "cost_usd": cost,
        "events": completion.get("events", {}),
    }

    items = []
    if ok:
        raw = get_dataset_items(dataset_id, limit=max_items)
        # Filter out "noResults" placeholder items
        real = [i for i in raw if not i.get("noResults")]
        run_record["item_count"] = len(real)

        # Annotate each item with HS metadata
        for item in real:
            item["_hs_group"] = group_name
            item["_hs_subtype"] = group_config.get("hs_subtype", "")
            item["_hs_country"] = group_config.get("country", "")
            item["_platform"] = platform
            item["_sweep_date"] = sweep_date
        items = real

    return items, cost, run_record


def run_group(group_name, group_config, queries_by_platform,
              sweep_date, dry_run=False):
    """Run all platform searches for one keyword group."""
    group_items = []
    group_cost = 0.0
    group_runs = []

    for platform, queries in queries_by_platform.items():
        if not queries:
            continue
        items, cost, record = run_platform_search(
            platform, queries, group_name, group_config, sweep_date, dry_run
        )
        group_items.extend(items)
        group_cost += cost
        if record:
            group_runs.append(record)

    return {
        "group": group_name,
        "hs_subtype": group_config.get("hs_subtype", ""),
        "country": group_config.get("country", ""),
        "platforms_searched": list(queries_by_platform.keys()),
        "runs": group_runs,
        "total_results": len(group_items),
        "total_cost_usd": group_cost,
        "items": group_items,
    }


# ─── Results Saving ──────────────────────────────────────────────────────────

def save_results(all_results, sweep_date, run_timestamp):
    """Save sweep results to monitoring/apify_results/hs/."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    time_str = "morning" if run_timestamp.hour < 12 else "afternoon"

    # Collect all items, then strip from group results for the summary file
    all_items = []
    group_summaries = []
    for r in all_results:
        items = r.pop("items", [])
        all_items.extend(items)
        group_summaries.append(r)

    summary = {
        "run_timestamp_utc": run_timestamp.isoformat(),
        "pipeline": "hs_apify_sweep",
        "groups_searched": [r["group"] for r in group_summaries],
        "total_results": len(all_items),
        "total_cost_usd": sum(r["total_cost_usd"] for r in group_summaries),
        "group_results": group_summaries,
    }

    # Save summary
    summary_path = RESULTS_DIR / f"hs_sweep_{sweep_date}_{time_str}.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nSweep summary saved to: {summary_path}")

    # Save items
    if all_items:
        items_path = RESULTS_DIR / f"hs_sweep_{sweep_date}.json"
        with open(items_path, "w") as f:
            json.dump(all_items, f, indent=2)
        print(f"{len(all_items)} items saved to: {items_path}")

    # Update cost log
    update_cost_log(summary["total_cost_usd"], sweep_date, len(all_items))

    return summary_path, all_items


def update_cost_log(cost_usd, date_str, item_count):
    """Track cumulative Apify spend in data/apify_cost_log.json."""
    COST_LOG.parent.mkdir(parents=True, exist_ok=True)

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
        "pipeline": "hs_sweep",
        "cost_usd": round(cost_usd, 4),
        "items": item_count,
    })
    log["cumulative_usd"] = round(log.get("cumulative_usd", 0) + cost_usd, 4)
    log["monthly_usd"] = round(log.get("monthly_usd", 0) + cost_usd, 4)

    with open(COST_LOG, "w") as f:
        json.dump(log, f, indent=2)


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="BRACE4PEACE HS Apify Keyword Sweep"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would run without executing"
    )
    parser.add_argument(
        "--budget-cap", type=float, default=DEFAULT_BUDGET_CAP_USD,
        help=f"Max USD to spend this run (default: ${DEFAULT_BUDGET_CAP_USD})"
    )
    parser.add_argument(
        "--groups", nargs="+",
        help="Override: run only specific groups instead of all"
    )
    args = parser.parse_args()

    if not APIFY_TOKEN and not args.dry_run:
        print("ERROR: APIFY_TOKEN environment variable not set.")
        sys.exit(1)

    print("=" * 60)
    print("BRACE4PEACE HS Apify Keyword Sweep")
    print("=" * 60)

    run_timestamp = datetime.now(timezone.utc)
    sweep_date = run_timestamp.strftime("%Y-%m-%d")
    since, until = get_date_range()
    print(f"Date range: {since} to {until}")
    print(f"Budget cap: ${args.budget_cap:.2f}")
    print()

    # ── Load strategy + enrichment sources ──
    strategy = load_strategy()
    mode = strategy.get("mode", "all_daily")
    groups = strategy.get("groups", {})

    print(f"Strategy mode: {mode}")
    print(f"Groups defined: {len(groups)}")

    toxic_handles = load_toxic_handles()
    learned_kw = load_learned_keywords()
    print()

    # ── Determine which groups to run ──
    if args.groups:
        group_names = args.groups
        print(f"Manual override: running groups {group_names}")
    else:
        group_names = list(groups.keys())
        print(f"Running all {len(group_names)} groups")

    if not group_names:
        print("No groups to run. Exiting.")
        return {"total_results": 0, "total_cost_usd": 0.0}

    # ── Execute sweeps ──
    total_cost = 0.0
    all_results = []

    for gname in group_names:
        gconfig = groups.get(gname)
        if not gconfig:
            print(f"\nGroup '{gname}' not found in strategy, skipping")
            continue

        print(f"\n{'─' * 50}")
        hs_sub = gconfig.get("hs_subtype", "")
        country = gconfig.get("country", "")
        n_queries = len(gconfig.get("queries", []))
        platforms = gconfig.get("platforms", [])
        print(f"  {gname}")
        print(f"  Subtype: {hs_sub} | Country: {country}")
        print(f"  Queries: {n_queries} | Platforms: {platforms}")

        # Budget check
        if total_cost >= args.budget_cap:
            print(f"  Budget cap ${args.budget_cap:.2f} reached "
                  f"(spent ${total_cost:.4f}), skipping remaining groups")
            break

        # Build queries (base + learned enrichment)
        queries_by_platform = build_queries_for_group(
            gname, gconfig, toxic_handles, learned_kw, since, until
        )

        result = run_group(gname, gconfig, queries_by_platform,
                           sweep_date, dry_run=args.dry_run)
        all_results.append(result)
        total_cost += result["total_cost_usd"]

    # ── Toxic handle direct monitoring ──
    if toxic_handles:
        print(f"\n{'─' * 50}")
        print(f"  TOXIC_HANDLES (direct monitoring)")
        handle_queries = build_toxic_handle_queries(toxic_handles, since, until)
        x_queries = handle_queries.get("x", [])

        if x_queries and total_cost < args.budget_cap:
            print(f"  {len(x_queries)} handle queries on X")
            handle_config = {
                "hs_subtype": "TOXIC_HANDLE",
                "country": "Regional",
                "platforms": ["x"],
                "queries": [],
            }
            items, cost, record = run_platform_search(
                "x", x_queries, "TOXIC_HANDLES", handle_config,
                sweep_date, dry_run=args.dry_run
            )
            handle_result = {
                "group": "TOXIC_HANDLES",
                "hs_subtype": "TOXIC_HANDLE",
                "country": "Regional",
                "platforms_searched": ["x"],
                "runs": [record] if record else [],
                "total_results": len(items),
                "total_cost_usd": cost,
                "items": items,
            }
            all_results.append(handle_result)
            total_cost += cost
        elif x_queries:
            print(f"  Skipping — budget cap reached")

    # ── Save results ──
    total_items = sum(r.get("total_results", 0) for r in all_results)

    if not args.dry_run and all_results:
        save_results(all_results, sweep_date, run_timestamp)

    # ── Summary ──
    print(f"\n{'=' * 60}")
    print(f"HS Sweep complete")
    print(f"  Groups searched: {len(all_results)}")
    print(f"  Total results: {total_items}")
    print(f"  Total cost: ${total_cost:.4f}")
    print(f"  Budget remaining: ${args.budget_cap - total_cost:.4f}")
    print(f"{'=' * 60}")

    return {
        "groups_searched": len(all_results),
        "total_results": total_items,
        "total_cost_usd": round(total_cost, 4),
        "budget_remaining_usd": round(args.budget_cap - total_cost, 4),
        "sweep_date": sweep_date,
    }


if __name__ == "__main__":
    main()
