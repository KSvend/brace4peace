"""Shared path definitions for all monitoring scripts."""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_DATA = REPO_ROOT / "docs" / "data"
MONITORING = REPO_ROOT / "monitoring"
CONFIG = MONITORING / "config"
AUTOLEARN = MONITORING / "autolearn"
RUN_DATA = REPO_ROOT / "data"

# Data files
EVENTS_PATH = DOCS_DATA / "events.json"
NARRATIVES_PATH = DOCS_DATA / "narratives.json"
HS_DATA_PATH = DOCS_DATA / "hate_speech_posts.json"
HS_PROGRESS_PATH = DOCS_DATA / "hs_explain_progress.json"

# Config files
WATCHLIST_PATH = CONFIG / "watchlist.json"
QUERIES_PATH = CONFIG / "queries.json"
HS_STRATEGY_PATH = CONFIG / "hs_keyword_strategy.json"
DISINFO_STRATEGY_PATH = CONFIG / "apify_keyword_strategy.json"
WEIGHTS_PATH = CONFIG / "narrative_family_weights.json"
SIGNAL_METRICS_PATH = CONFIG / "signal_metrics.json"
TIMELINE_PATH = MONITORING / "brace4peace_timeline.json"

# Autolearn
TOXIC_HANDLES_CSV = AUTOLEARN / "toxic_handles.csv"
LEARNED_KW_HS_CSV = AUTOLEARN / "learned_keywords_hs.csv"
LEARNED_KW_DISINFO_CSV = AUTOLEARN / "learned_keywords_disinfo.csv"

# State
STATE_PATH = RUN_DATA / "state.json"
COST_LOG_PATH = RUN_DATA / "apify_cost_log.json"
