#!/usr/bin/env python3
"""
BRACE4PEACE Monitoring Pipeline — GitHub Actions Entry Point
=============================================================
Orchestrates:
  1. Apify sweeps (disinfo + HS)
  2. Keyword classification
  3. ML classification (HF Inference API)
  4. Explanation generation (Anthropic API)
  5. Event dedup + lifecycle
  6. Reach tracking
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
    log(f"{'='*50}")
    log(f"PHASE: {name}")
    log(f"{'='*50}")
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


def phase_ml_classify():
    """Run ML classification via HuggingFace Inference API."""
    from ml_classify import classify_posts
    return classify_posts()


def phase_explain():
    """Generate explanations via Anthropic API."""
    from explain_posts import explain_posts
    return explain_posts()


def phase_event_lifecycle():
    """Run event lifecycle status updates."""
    from event_lifecycle import update_statuses, load_events, save_events
    events = load_events()
    changes = update_statuses(events)
    save_events(events)
    return changes


def phase_reach_tracking():
    """Re-fetch engagement metrics for recent posts."""
    from reach_tracker import main as reach_main
    return reach_main()


def main():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    run_sweeps = os.environ.get("RUN_SWEEPS", "true").lower() == "true"
    run_ml = os.environ.get("RUN_ML", "true").lower() == "true"
    run_reach = os.environ.get("RUN_REACH", "true").lower() == "true"

    log(f"BRACE4PEACE Pipeline — {today}")
    log(f"  Sweeps: {'ON' if run_sweeps else 'OFF'}")
    log(f"  ML/Explain: {'ON' if run_ml else 'OFF'}")
    log(f"  Reach: {'ON' if run_reach else 'OFF'}")

    results = {}

    # Phase 1: ML Enrichment (classify unprocessed posts)
    if run_ml:
        results["ml"] = run_phase("ML Classification (HF API)", phase_ml_classify)
        results["explain"] = run_phase("Explanations (Anthropic)", phase_explain)

    # Phase 2: Event Management
    results["lifecycle"] = run_phase("Event Lifecycle", phase_event_lifecycle)

    # Phase 3: Reach Tracking
    if run_reach:
        results["reach"] = run_phase("Reach Tracking", phase_reach_tracking)

    # Save run log
    run_data = REPO_ROOT / "data"
    run_data.mkdir(exist_ok=True)
    (run_data / "run_history").mkdir(exist_ok=True)

    run_log = {
        "date": today,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "results": results
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
    state["pipeline_version"] = "2.0-github-actions"
    with open(state_path, "w") as f:
        json.dump(state, f, indent=2)

    log(f"\nPipeline complete. Log: {log_path}")


if __name__ == "__main__":
    main()
