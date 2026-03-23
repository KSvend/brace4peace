#!/usr/bin/env python3
"""
MERLx IRIS Two-Pipeline Orchestrator
======================================
Pipeline 1 (Disinfo):
  1A  Watchlist checker — check VE/HS sources via Apify web scraper
  1B  Apify disinfo sweep (apify_sweep.py)
  1C  Disinfo classification (apify_classify.py) — includes event dedup
  1D  Event lifecycle updates

Pipeline 2 (Hate Speech):
  2A  HS Apify sweep (hs_apify_sweep.py)
  2B  HS classification (hs_apify_classify.py) — rule-based, local-language
  2C  ML enrichment (ml_classify.py) — HF API zero-shot subtopics + toxicity
  2D  LLM QA + analysis (explain_posts.py) — Anthropic API
  2E  Quality gate — remove misclassified posts from platform data

Shared:
  3A  Reach tracking (reach_tracker.py)
  3B  Save run log

Environment variables:
  RUN_SWEEPS  — controls 1A/1B/2A (Apify calls, costs money)
  RUN_ML      — controls 2C/2D (API calls)
  RUN_REACH   — controls 3A

Phases 1C, 1D, 2B, 2E always run (free, local processing).
"""

import os
import sys
import json
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "monitoring"))


def log(msg):
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] {msg}", flush=True)


def run_phase(name, func):
    """Run a pipeline phase with timing and error handling."""
    log(f"{'='*60}")
    log(f"PHASE: {name}")
    log(f"{'='*60}")
    start = time.time()
    try:
        result = func()
        elapsed = time.time() - start
        log(f"  Completed in {elapsed:.1f}s: {result}")
        return result
    except Exception as e:
        elapsed = time.time() - start
        log(f"  FAILED after {elapsed:.1f}s: {e}")
        traceback.print_exc()
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Pipeline 1: Disinfo
# ---------------------------------------------------------------------------

def phase_1a_watchlist():
    """Check VE/HS watchlist sources via Apify web scraper."""
    from watchlist_checker import main as watchlist_main
    return watchlist_main()


def phase_1b_disinfo_sweep():
    """Run Apify keyword sweep for disinformation content."""
    from apify_sweep import main as sweep_main
    return sweep_main()


def phase_1c_disinfo_classify():
    """Classify disinfo sweep results and deduplicate events."""
    from apify_classify import run_classification
    return run_classification()


def phase_1e_event_review():
    """LLM QA: validate events, extract claims, propose keywords."""
    from review_events import main as review_main
    return review_main()


def phase_1d_event_lifecycle():
    """Update event statuses (active -> dormant -> resolved)."""
    from event_lifecycle import update_statuses, load_events, save_events
    events = load_events()
    changes = update_statuses(events)
    save_events(events)
    return changes


def phase_1f_event_enrich():
    """Auto-link related events + smart threat level assignment."""
    from event_enrich import main as enrich_main
    return enrich_main()


# ---------------------------------------------------------------------------
# Pipeline 2: Hate Speech
# ---------------------------------------------------------------------------

def phase_2a_hs_sweep():
    """Run Apify keyword sweep for hate speech content."""
    from hs_apify_sweep import main as hs_sweep_main
    return hs_sweep_main()


def phase_2b_hs_classify():
    """Rule-based HS classification with local-language indicators."""
    from hs_apify_classify import main as hs_classify_main
    return hs_classify_main()


def phase_2c_ml_enrich():
    """ML enrichment: local HF models + optional zero-shot subtopics."""
    from ml_classify import classify_posts
    return classify_posts(skip_zero_shot=True)


def phase_2d_llm_qa():
    """LLM QA + analysis via Anthropic API."""
    from explain_posts import explain_posts
    return explain_posts()


def phase_2e_quality_gate():
    """Remove misclassified posts from hate_speech_posts.json."""
    hs_path = REPO_ROOT / "docs" / "data" / "hate_speech_posts.json"
    if not hs_path.exists():
        return {"skipped": True, "reason": "hate_speech_posts.json not found"}

    with open(hs_path) as f:
        posts = json.load(f)

    original_count = len(posts)

    # Identify misclassified posts
    to_remove = []
    to_keep = []
    for post in posts:
        qc = post.get("qc", "").lower()
        rel = post.get("rel", "").lower()
        if qc == "misclassified" or rel == "not_relevant":
            to_remove.append(post)
        else:
            to_keep.append(post)

    removed_count = len(to_remove)
    if removed_count == 0:
        return {"removed": 0, "remaining": original_count}

    # Archive removed posts
    archive_dir = REPO_ROOT / "data" / "run_history"
    archive_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    archive_path = archive_dir / f"misclassified_{today}.json"

    # Append to existing archive if it exists (multiple runs per day)
    existing_archive = []
    if archive_path.exists():
        with open(archive_path) as f:
            existing_archive = json.load(f)
    existing_archive.extend(to_remove)
    with open(archive_path, "w") as f:
        json.dump(existing_archive, f, indent=2, default=str)

    # Write cleaned posts back
    with open(hs_path, "w") as f:
        json.dump(to_keep, f, indent=2, default=str)

    log(f"  Quality gate: removed {removed_count} posts "
        f"(qc=misclassified or rel=not_relevant)")
    log(f"  Archived to {archive_path}")

    return {
        "removed": removed_count,
        "remaining": len(to_keep),
        "archived_to": str(archive_path),
    }


# ---------------------------------------------------------------------------
# Phase 0: Process user submissions
# ---------------------------------------------------------------------------

def phase_0_submissions():
    """Process user-submitted posts from the dashboard."""
    submissions_path = REPO_ROOT / "docs" / "data" / "submissions.json"
    if not submissions_path.exists():
        return {"processed": 0}

    with open(submissions_path) as f:
        submissions = json.load(f)

    if not submissions:
        return {"processed": 0}

    pending = [s for s in submissions if s.get("status") == "pending"]
    if not pending:
        return {"processed": 0}

    log(f"  Found {len(pending)} pending submissions")

    hs_path = REPO_ROOT / "docs" / "data" / "hate_speech_posts.json"
    events_path = REPO_ROOT / "docs" / "data" / "events.json"

    hs_added = 0
    events_added = 0

    for sub in pending:
        sub["status"] = "processed"
        sub["processed_at"] = datetime.now(timezone.utc).isoformat()
        date = sub.get("date", datetime.now(timezone.utc).strftime("%Y-%m-%d"))
        url = sub.get("url", "")
        note = sub.get("note", "")
        country = sub.get("country", "Regional")
        platform = sub.get("platform", "Unknown")

        if sub.get("type") == "hatespeech":
            # Add to hate_speech_posts.json as auto_sweep for ML pipeline
            import hashlib
            post_id = "sub-" + hashlib.md5(f"{url}|{date}".encode()).hexdigest()[:12]
            plat_short = {"X (Twitter)": "x", "Facebook": "facebook", "TikTok": "tiktok"}.get(platform, "web")
            new_post = {
                "i": post_id, "t": note or "Submitted — pending analysis",
                "d": date, "c": country, "p": plat_short,
                "a": "submitted", "l": url,
                "pr": "Hate", "co": 0, "tx": "medium",
                "st": [], "txd": {"sev": "medium", "ins": "medium", "idt": "medium", "thr": "medium"},
                "en": {"l": 0, "s": 0, "c": 0},
                "qc": "auto_sweep", "_source": "user_submission"
            }
            with open(hs_path) as f:
                posts = json.load(f)
            # Dedup check
            if not any(p.get("l") == url for p in posts):
                posts.append(new_post)
                with open(hs_path, "w") as f:
                    json.dump(posts, f, ensure_ascii=False, separators=(",", ":"))
                hs_added += 1
                log(f"    HS post added: {url[:60]}")
            else:
                log(f"    HS post duplicate, skipped: {url[:60]}")

        elif sub.get("type") == "disinfo":
            # Add to events.json as pending event
            with open(events_path) as f:
                events = json.load(f)
            event_id = f"SUB-{date}-{abs(hash(url)) % 1000:03d}"
            if not any(e.get("id") == event_id for e in events):
                new_event = {
                    "id": event_id, "date": date, "country": country,
                    "event_type": "DISINFO", "disinfo_subtype": "pending_classification",
                    "threat_level": "P3 MODERATE",
                    "headline": f"Submitted link — pending analysis",
                    "summary": note or "Link submitted for automated review.",
                    "actors": [], "platforms": [platform],
                    "sources": [{"publisher": "User submission", "url": url, "date": date}],
                    "spread": 1, "disinfo_narratives": [], "related_events": [],
                    "disinfo_confidence": "PENDING",
                    "detection_method": "manual_submission",
                    "content_observed": False, "source_basis": "user_submission",
                    "verification_status": "pending_review",
                    "narrative_families": [], "tags": ["user_submission"],
                    "data_source": "manual", "detected_by": "user",
                    "detection_timestamp": sub.get("submitted_at", ""),
                    "last_seen": date, "status": "active",
                    "observations": [{"date": date, "url": url, "summary": "User submission", "platforms": [platform], "reach": {}}],
                    "observation_count": 1
                }
                events.append(new_event)
                with open(events_path, "w") as f:
                    json.dump(events, f, ensure_ascii=False, indent=2)
                events_added += 1
                log(f"    Disinfo event added: {url[:60]}")
            else:
                log(f"    Disinfo event duplicate, skipped: {url[:60]}")

    # Save updated submissions (mark as processed)
    with open(submissions_path, "w") as f:
        json.dump(submissions, f, indent=2)

    return {"processed": len(pending), "hs_added": hs_added, "events_added": events_added}


# ---------------------------------------------------------------------------
# Shared
# ---------------------------------------------------------------------------

def phase_3a_reach():
    """Re-fetch engagement metrics for recent posts."""
    from reach_tracker import main as reach_main
    return reach_main()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    run_sweeps = os.environ.get("RUN_SWEEPS", "true").lower() == "true"
    run_ml = os.environ.get("RUN_ML", "true").lower() == "true"
    run_reach = os.environ.get("RUN_REACH", "true").lower() == "true"

    log(f"MERLx IRIS Two-Pipeline Orchestrator — {today}")
    log(f"  RUN_SWEEPS : {'ON' if run_sweeps else 'OFF'}  (1A/1B/2A — Apify)")
    log(f"  RUN_ML     : {'ON' if run_ml else 'OFF'}  (2C/2D — HF + Anthropic)")
    log(f"  RUN_REACH  : {'ON' if run_reach else 'OFF'}  (3A — engagement)")
    log("")

    results = {}

    # ===== PHASE 0: PROCESS SUBMISSIONS =====
    results["0_submissions"] = run_phase(
        "0 — Process User Submissions", phase_0_submissions)

    # ===== PIPELINE 1: DISINFO =====
    log(f"{'#'*60}")
    log(f"# PIPELINE 1: DISINFORMATION")
    log(f"{'#'*60}")

    if run_sweeps:
        results["1a_watchlist"] = run_phase(
            "1A — Watchlist Checker (Apify)", phase_1a_watchlist)
        results["1b_disinfo_sweep"] = run_phase(
            "1B — Disinfo Apify Sweep", phase_1b_disinfo_sweep)

    # Always run (free, local)
    results["1c_disinfo_classify"] = run_phase(
        "1C — Disinfo Classification + Event Dedup", phase_1c_disinfo_classify)
    results["1d_event_lifecycle"] = run_phase(
        "1D — Event Lifecycle Updates", phase_1d_event_lifecycle)
    results["1f_event_enrich"] = run_phase(
        "1F — Auto-Link Related Events + Threat Levels", phase_1f_event_enrich)

    if run_ml:
        results["1e_event_review"] = run_phase(
            "1E — Event QA + Intelligence Extraction", phase_1e_event_review)

    # ===== PIPELINE 2: HATE SPEECH =====
    log(f"\n{'#'*60}")
    log(f"# PIPELINE 2: HATE SPEECH")
    log(f"{'#'*60}")

    if run_sweeps:
        results["2a_hs_sweep"] = run_phase(
            "2A — HS Apify Sweep", phase_2a_hs_sweep)

    # Always run (free, local)
    results["2b_hs_classify"] = run_phase(
        "2B — HS Rule-Based Classification", phase_2b_hs_classify)

    # Inject any pending recovery posts before ML/QA phases
    pending_path = REPO_ROOT / "data" / "pending_hs_recovery.json"
    if pending_path.exists():
        log("  Injecting pending recovery posts into HS data...")
        hs_path = REPO_ROOT / "docs" / "data" / "hate_speech_posts.json"
        with open(hs_path) as f:
            posts = json.load(f)
        existing_ids = {p["i"] for p in posts}
        with open(pending_path) as f:
            pending = json.load(f)
        added = 0
        for p in pending:
            if p["i"] not in existing_ids:
                posts.append(p)
                existing_ids.add(p["i"])
                added += 1
        with open(hs_path, "w") as f:
            json.dump(posts, f, indent=2, ensure_ascii=False)
            f.write("\n")
        pending_path.unlink()
        log(f"  Injected {added} pending posts for QA processing.")

    if run_ml:
        results["2c_ml_enrich"] = run_phase(
            "2C — ML Enrichment (HF API)", phase_2c_ml_enrich)
        results["2d_llm_qa"] = run_phase(
            "2D — LLM QA + Analysis (Anthropic)", phase_2d_llm_qa)

    # Always run (free, local)
    results["2e_quality_gate"] = run_phase(
        "2E — Quality Gate (remove misclassified)", phase_2e_quality_gate)

    # ===== SHARED =====
    log(f"\n{'#'*60}")
    log(f"# SHARED PHASES")
    log(f"{'#'*60}")

    if run_reach:
        results["3a_reach"] = run_phase(
            "3A — Reach Tracking", phase_3a_reach)

    # Phase 3B: Save run log
    log(f"\n{'='*60}")
    log(f"PHASE: 3B — Save Run Log")
    log(f"{'='*60}")

    run_data = REPO_ROOT / "data"
    run_data.mkdir(exist_ok=True)
    (run_data / "run_history").mkdir(exist_ok=True)

    run_log = {
        "date": today,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "config": {
            "run_sweeps": run_sweeps,
            "run_ml": run_ml,
            "run_reach": run_reach,
        },
        "results": results,
    }
    log_path = run_data / "run_history" / f"run_{today}.json"
    with open(log_path, "w") as f:
        json.dump(run_log, f, indent=2, default=str)

    # Update state
    state_path = run_data / "state.json"
    state = {}
    if state_path.exists():
        with open(state_path) as f:
            state = json.load(f)
    state["last_run"] = datetime.now(timezone.utc).isoformat()
    state["pipeline_version"] = "3.0-two-pipeline"
    with open(state_path, "w") as f:
        json.dump(state, f, indent=2)

    log(f"\nPipeline complete. Log saved to {log_path}")

    # Summary
    errors = {k: v for k, v in results.items()
              if isinstance(v, dict) and "error" in v}
    if errors:
        log(f"\nWARNING: {len(errors)} phase(s) had errors:")
        for phase, result in errors.items():
            log(f"  {phase}: {result['error']}")
    else:
        log(f"\nAll phases completed successfully.")


if __name__ == "__main__":
    main()
