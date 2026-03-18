#!/usr/bin/env python3
"""
Watchlist Checker for BRACE4PEACE
==================================
Lightweight daily check of VE/HS watchlist sources and research partner sites
using Apify Google Search and Web Scraper actors.

Replaces the manual Perplexity Method A + Method B website checking.

Reads:  monitoring/config/watchlist.json
Writes: data/run_history/watchlist_YYYY-MM-DD.json

Environment:
  APIFY_TOKEN — required

Budget: ~$0.10 per run (~20 API calls max)
Pure stdlib — no pip dependencies.
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WATCHLIST_PATH = REPO_ROOT / "monitoring" / "config" / "watchlist.json"
OUTPUT_DIR = REPO_ROOT / "data" / "run_history"

APIFY_GOOGLE_SEARCH = "apify~google-search-scraper"
APIFY_WEB_SCRAPER = "apify~web-scraper"
APIFY_BASE = "https://api.apify.com/v2/acts"

# East Africa relevance keywords — used to filter results
EA_COUNTRIES = [
    "kenya", "somalia", "south sudan", "ethiopia", "uganda",
    "tanzania", "djibouti", "eritrea", "east africa",
]
EA_ACTORS = [
    "al-shabaab", "al shabaab", "alshabaab",
    "kiir", "machar", "riek", "salva",
    "ruto", "odinga", "gachagua",
    "farmajo", "hassan sheikh",
    "abiy", "tplf", "fano",
]
HS_TERMS = [
    "hate speech", "incitement", "dehumaniz", "genocide", "ethnic cleansing",
    "tribal", "clan", "madoadoa", "kwekwe", "cockroach",
    "jareer", "xayawaan", "nyam nyam",
    "disinformation", "disinfo", "propaganda", "fake news", "false claim",
    "violent extremism", "radicali",
]

RATE_LIMIT_SECONDS = 2
MAX_API_CALLS = 20


def log(msg):
    print(f"[watchlist] {msg}", flush=True)


def apify_request(actor_id, body, token, timeout=30):
    """Make a synchronous Apify actor run and return dataset items."""
    url = (f"{APIFY_BASE}/{actor_id}/run-sync-get-dataset-items"
           f"?token={token}&timeout={timeout}")
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout + 10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")[:500]
        log(f"  HTTP {e.code}: {error_body}")
        return None
    except (urllib.error.URLError, TimeoutError) as e:
        log(f"  Request failed: {e}")
        return None


def google_search(query, token):
    """Search via Apify Google Search Scraper."""
    body = {
        "queries": query,
        "maxPagesPerQuery": 1,
        "resultsPerPage": 5,
    }
    return apify_request(APIFY_GOOGLE_SEARCH, body, token)


def fetch_url(url, token):
    """Fetch a URL via Apify Web Scraper."""
    body = {
        "startUrls": [{"url": url}],
        "pageFunction": (
            "async function pageFunction(context) {"
            "  return {"
            "    title: document.title,"
            "    text: document.body.innerText.substring(0, 2000)"
            "  };"
            "}"
        ),
    }
    return apify_request(APIFY_WEB_SCRAPER, body, token, timeout=30)


def is_ea_relevant(text):
    """Check if text contains East Africa-relevant content."""
    if not text:
        return False
    text_lower = text.lower()
    # Must mention at least one country/actor AND one HS/disinfo term
    has_country = any(c in text_lower for c in EA_COUNTRIES + EA_ACTORS)
    has_term = any(t in text_lower for t in HS_TERMS)
    return has_country and has_term


def check_source_search(source, token):
    """Check a source via Google Search."""
    name = source.get("name", "unknown")
    queries = source.get("search_queries", [])
    if not queries:
        # Build a default query from the source name
        queries = [f'"{name}" site:{source.get("url", "")}']
        if not source.get("url"):
            queries = [f'"{name}" East Africa']

    findings = []
    for query in queries[:2]:  # Max 2 queries per source
        results = google_search(query, token)
        if not results:
            continue
        for item in results:
            title = item.get("title", "")
            snippet = item.get("description", "") or item.get("snippet", "")
            link = item.get("url", "") or item.get("link", "")
            combined = f"{title} {snippet}"
            if is_ea_relevant(combined):
                findings.append({
                    "title": title,
                    "snippet": snippet[:300],
                    "url": link,
                    "relevant": True,
                })
        time.sleep(RATE_LIMIT_SECONDS)

    return findings


def check_source_fetch(source, token):
    """Check a source by directly fetching its URL."""
    url = source.get("url")
    if not url:
        return []

    results = fetch_url(url, token)
    if not results:
        return []

    findings = []
    for item in results:
        title = item.get("title", "")
        text = item.get("text", "")
        combined = f"{title} {text}"
        if is_ea_relevant(combined):
            findings.append({
                "title": title,
                "snippet": text[:300],
                "url": url,
                "relevant": True,
            })
    time.sleep(RATE_LIMIT_SECONDS)
    return findings


def check_research_partner(partner, token):
    """Check a research partner site for new EA HS/disinfo content."""
    url = partner.get("url")
    name = partner.get("name", "unknown")
    if not url:
        return []

    results = fetch_url(url, token)
    if not results:
        return []

    findings = []
    for item in results:
        title = item.get("title", "")
        text = item.get("text", "")
        combined = f"{title} {text}"
        if is_ea_relevant(combined):
            findings.append({
                "source": name,
                "title": title,
                "snippet": text[:300],
                "url": url,
                "relevant": True,
            })
    time.sleep(RATE_LIMIT_SECONDS)
    return findings


def main():
    """Run watchlist checks. Returns summary dict."""
    token = os.environ.get("APIFY_TOKEN", "")
    if not token:
        log("APIFY_TOKEN not set — skipping watchlist check")
        return {"skipped": True, "reason": "no APIFY_TOKEN"}

    # Load watchlist config
    if not WATCHLIST_PATH.exists():
        log(f"Watchlist config not found at {WATCHLIST_PATH}")
        return {"skipped": True, "reason": "watchlist.json not found"}

    with open(WATCHLIST_PATH) as f:
        watchlist = json.load(f)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    api_calls = 0
    all_findings = []
    source_results = []

    # --- Check HS/disinfo sources ---
    hs_disinfo = watchlist.get("hs_disinfo_sources", {})
    source_lists = []
    for key in ("ve_propaganda_producers", "hs_disinfo_producers"):
        source_lists.extend(hs_disinfo.get(key, []))

    log(f"Checking {len(source_lists)} watchlist sources...")
    for source in source_lists:
        if not source.get("active", True):
            continue
        if api_calls >= MAX_API_CALLS:
            log(f"  Budget cap reached ({MAX_API_CALLS} calls)")
            break

        name = source.get("name", "unknown")
        method = source.get("check_method", "search_web")

        if method == "fetch_url":
            findings = check_source_fetch(source, token)
        else:  # search_web or default
            findings = check_source_search(source, token)

        api_calls += 1
        result = {
            "name": name,
            "method": method,
            "new_content_found": len(findings) > 0,
            "finding_count": len(findings),
        }
        source_results.append(result)
        all_findings.extend(findings)

        if findings:
            log(f"  {name}: {len(findings)} relevant finding(s)")
        else:
            log(f"  {name}: no new relevant content")

    # --- Check research partners ---
    partners = watchlist.get("research_partners", [])
    partner_results = []

    log(f"Checking {len(partners)} research partner sites...")
    for partner in partners:
        if not partner.get("active", True):
            continue
        if api_calls >= MAX_API_CALLS:
            log(f"  Budget cap reached ({MAX_API_CALLS} calls)")
            break

        name = partner.get("name", "unknown")
        findings = check_research_partner(partner, token)
        api_calls += 1

        result = {
            "name": name,
            "new_content_found": len(findings) > 0,
            "finding_count": len(findings),
        }
        partner_results.append(result)
        all_findings.extend(findings)

        if findings:
            log(f"  {name}: {len(findings)} relevant finding(s)")
        else:
            log(f"  {name}: no new relevant content")

    # --- Save results ---
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output = {
        "date": today,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "api_calls": api_calls,
        "summary": {
            "sources_checked": len(source_results),
            "partners_checked": len(partner_results),
            "total_findings": len(all_findings),
            "sources_with_new_content": sum(
                1 for r in source_results if r["new_content_found"]),
            "partners_with_new_content": sum(
                1 for r in partner_results if r["new_content_found"]),
        },
        "source_results": source_results,
        "partner_results": partner_results,
        "findings": all_findings,
    }

    output_path = OUTPUT_DIR / f"watchlist_{today}.json"
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2, default=str)

    log(f"Watchlist check complete: {len(all_findings)} finding(s) "
        f"from {api_calls} API call(s)")
    log(f"Results saved to {output_path}")

    return output["summary"]


if __name__ == "__main__":
    result = main()
    print(json.dumps(result, indent=2))
