# BRACE4PEACE: Full Migration to GitHub Actions

## Overview

Migrate the entire monitoring pipeline from Perplexity Computer to GitHub Actions. Zero dependency on external compute. All data versioned in the repo, all processing via APIs (HF Inference, Anthropic, Apify).

## Architecture

```
GitHub Actions (scheduled + manual)
  1. apify_sweep.py         → Raw posts from X/FB/TikTok
  2. apify_classify.py      → Rule-based DISINFO classification
  3. ml_classify.py [NEW]   → HF Inference API (EA-HS models + zero-shot subtopics)
  4. explain_posts.py [NEW] → Anthropic API explanations
  5. event_dedup.py          → Merge duplicate events
  6. event_lifecycle.py      → Status updates (active/dormant/resolved)
  7. reach_tracker.py [NEW] → Engagement re-fetch via Apify
  8. Git commit + push       → Auto-deploys to GitHub Pages
```

## Key Design Decisions

1. **No local ML models** — HF Inference API for all classification
2. **No pip dependencies** — pure stdlib (urllib, json, csv) + `requests` optional
3. **All data in repo** — committed after each run, versioned, persistent
4. **All config in repo** — `monitoring/config/` subdirectory
5. **Relative paths only** — `monitoring/paths.py` shared path helper
6. **Two triggers**: scheduled (weekdays 06:00 + 14:00 UTC) + manual button

## New Files

| File | Purpose |
|------|---------|
| `monitoring/paths.py` | Shared path definitions (replaces hardcoded /home/user/workspace) |
| `monitoring/run_pipeline.py` | Main orchestrator (GitHub Actions entry point) |
| `monitoring/ml_classify.py` | HF Inference API: EA-HS + toxicity + zero-shot subtopics |
| `monitoring/explain_posts.py` | Anthropic API: batch explanation generation |
| `monitoring/reach_tracker.py` | Apify re-fetch for engagement metrics |
| `.github/workflows/monitor.yml` | GitHub Actions workflow definition |

## Existing Files to Modify

| File | Changes |
|------|---------|
| `monitoring/apify_sweep.py` | Replace `/home/user/workspace` with paths.py imports |
| `monitoring/apify_classify.py` | Replace hardcoded paths with paths.py imports |
| `monitoring/event_dedup.py` | Already uses relative paths (OK) |
| `monitoring/event_lifecycle.py` | Already uses relative paths (OK) |
| `monitoring/push_to_github.sh` | Replace with `run_pipeline.py` (no longer needed separately) |

## Directory Restructuring

```
monitoring/config/          ← Move from monitoring/ root
  apify_keyword_strategy.json
  signal_metrics.json
  baseline_feb26_2026.md
  brace4peace_protocol.md

monitoring/autolearn/       ← NEW
  toxic_handles.csv
  learned_keywords_hs.csv
  learned_keywords_disinfo.csv

data/                       ← Working data
  state.json
  apify_cost_log.json
  run_history/
```

## ML Classification Pipeline (ml_classify.py)

For each new sweep post:
1. **EA-HS model** (`KSvendsen/EA-HS`) → `pr` (Hate/Abusive/Normal), `co` (confidence)
2. **Country-specific models** via HF API:
   - `datavaluepeople/Polarization-Kenya` (Kenya posts)
   - `datavaluepeople/Afxumo-toxicity-somaliland-SO` (Somalia posts)
   - `datavaluepeople/Hate-Speech-Sudan-v2` (South Sudan posts)
3. **Toxicity** (`textdetox/bert-multilingual-toxicity-classifier`) → `tx`, `txd`
4. **Zero-shot subtopics** (`facebook/bart-large-mnli`) → `st` array

Posts flagged as Hate/Abusive → appended to `hate_speech_posts.json`.

## GitHub Secrets Required

| Secret | Purpose |
|--------|---------|
| `APIFY_TOKEN` | Apify sweeps + reach tracking |
| `HF_TOKEN` | HuggingFace Inference API |
| `ANTHROPIC_API_KEY` | Explanation generation |

## Cost Estimate

~$40/month (Apify $38.50, Anthropic ~$1.10, HF free, GitHub Actions free tier)
