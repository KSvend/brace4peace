#!/usr/bin/env python3
"""
HS Apify Auto-Classification Module for BRACE4PEACE
====================================================
Classifies raw HS sweep results into confirmed hate speech posts or noise.

Design principle: NO generic English words (kill, deport, rape, etc.) — these
match millions of global tweets and waste budget on noise. Only use terms
SPECIFIC to East African hate speech.

Classification flow:
  1. Noise filter (fact check, counter-speech, too short)
  2. East Africa Relevance Gate — post MUST contain at least one EA indicator
     (140+ indicators). Exception: known toxic handles bypass this gate.
  3. HS Indicator Matching — score against 7 subtypes
  4. Confidence scoring: 3+ matches = HIGH, 2 = MEDIUM, 1 = LOW
  5. Convert to compact format and append to hate_speech_posts.json

Usage:
    python3 hs_apify_classify.py [--input items_file.json] [--dry-run]

When called from the monitoring pipeline, it reads the latest HS sweep file
and writes confirmed posts to hate_speech_posts.json.
"""

import csv
import hashlib
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

# ─── Paths ────────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent

# Data paths
HS_DATA_PATH = REPO_ROOT / "docs" / "data" / "hate_speech_posts.json"

# Config paths
HS_STRATEGY_PATH = REPO_ROOT / "monitoring" / "config" / "hs_keyword_strategy.json"

# Autolearn paths
AUTOLEARN_DIR = REPO_ROOT / "monitoring" / "autolearn"
TOXIC_HANDLES_CSV = AUTOLEARN_DIR / "toxic_handles.csv"
LEARNED_KW_HS_CSV = AUTOLEARN_DIR / "learned_keywords_hs.csv"
NARRATIVE_DISCOVERIES_CSV = AUTOLEARN_DIR / "narrative_discoveries.csv"

# Results paths
HS_RESULTS_DIR = REPO_ROOT / "monitoring" / "apify_results" / "hs"


# ─── HS Indicator Dictionary ─────────────────────────────────────────────────
# East Africa-specific local-language slurs and hate speech terms ONLY.
# NO generic English words — these match millions of global tweets.

HS_INDICATORS = {
    "HS-DEHUMANISE": {
        "display": "Dehumanisation",
        "indicators": [
            # Somali
            "xayawaan", "xoolo", "cayaanka", "qashin", "jareer", "jareereed",
            # Kenya
            "madoadoa", "mende", "kwekwe",
            # South Sudan
            "nyor", "nyornyor", "nyam nyam", "unwanted luggage",
            # Regional
            "cockroach", "infestation",
        ],
    },
    "HS-CLAN": {
        "display": "Clan Targeting",
        "indicators": [
            "mooryaan", "faqash", "xaarood", "hutuwiye", "laangaab",
            "qadaad weyn", "idoor", "eelay", "qabiil dagaal",
        ],
    },
    "HS-ETHNIC": {
        "display": "Ethnic Targeting",
        "indicators": [
            # Kenya
            "kihii", "mwiji", "ngetiik", "conoka", "muhoi", "chorik",
            "watu wa kurusha mawe",
            # South Sudan
            "jenge", "kokora", "dinkocracy", "jiengism", "monyjang power",
            "camjiec", "mathiang anyor", "warrapism", "juba na bari",
            # Somali
            "sare guraale",
        ],
    },
    "HS-RELIGIOUS": {
        "display": "Religious Incitement",
        "indicators": [
            "kaafir", "kufaar", "gaal", "gaalo", "murtad", "munaafiq",
            "mushrik", "takfir", "riddah", "saliibiyiin",
            "dimuquraadiyadda shirkiga", "calmaaniyad",
            # Kenya
            "chinja kafir",
        ],
    },
    "HS-POLITICAL": {
        "display": "Political Incitement",
        "indicators": [
            # South Sudan
            "kiiriminal", "konyo konyo regime", "tabanists",
            # Kenya
            "kura au risasi", "mungiki",
        ],
    },
    "HS-ANTI-FOREIGN": {
        "display": "Anti-Foreign",
        "indicators": [
            "wakuja", "wageni",
        ],
    },
    "HS-GENDER": {
        "display": "Gendered Violence",
        "indicators": [
            # Somali
            "gabadh sharaf la'aa", "qaniis", "gabar diin la'aa",
            "sawir iska xir",
            # Kenya
            "mundu wa nja muuki",
        ],
    },
}

# Flat lookup: indicator string → list of subtype keys it belongs to
_INDICATOR_TO_SUBTYPES: dict[str, list[str]] = {}
for _st_key, _st_val in HS_INDICATORS.items():
    for _ind in _st_val["indicators"]:
        _INDICATOR_TO_SUBTYPES.setdefault(_ind, []).append(_st_key)

# ─── Toxicity Profiles ───────────────────────────────────────────────────────
# Per-subtype toxicity dimension scores (sev=severity, ins=insult,
# idt=identity-targeting, thr=threat). Used for the txd field.

TOXICITY_PROFILES = {
    "Dehumanisation":       {"sev": 0.8, "ins": 0.9, "idt": 0.9, "thr": 0.3},
    "Clan Targeting":       {"sev": 0.5, "ins": 0.7, "idt": 0.8, "thr": 0.3},
    "Ethnic Targeting":     {"sev": 0.6, "ins": 0.6, "idt": 0.9, "thr": 0.4},
    "Religious Incitement": {"sev": 0.7, "ins": 0.5, "idt": 0.7, "thr": 0.6},
    "Political Incitement": {"sev": 0.6, "ins": 0.5, "idt": 0.4, "thr": 0.7},
    "Anti-Foreign":         {"sev": 0.5, "ins": 0.6, "idt": 0.8, "thr": 0.4},
    "Gendered Violence":    {"sev": 0.7, "ins": 0.8, "idt": 0.6, "thr": 0.7},
}

# ─── East Africa Relevance Indicators (140+) ─────────────────────────────────
# Posts MUST contain at least one of these to pass the EA relevance gate.

EAST_AFRICA_INDICATORS = [
    # Countries
    "somalia", "somali", "kenya", "kenyan", "south sudan", "sudanese",
    # Cities — Somalia
    "mogadishu", "muqdisho", "hargeisa", "berbera", "garowe", "bosaso",
    "beledweyne", "beletweyn", "kismayo", "baidoa",
    # Cities — Kenya
    "nairobi", "mombasa", "kisumu", "garissa", "wajir", "mandera",
    "lodwar", "kakuma", "eldoret", "nakuru", "thika",
    # Cities — South Sudan
    "juba", "malakal", "bentiu", "bor", "wau", "aweil", "torit",
    "nimule", "rumbek", "yambio",
    # Regions — Somalia
    "puntland", "somaliland", "jubaland", "hiiraan", "gedo", "banadir",
    "lower juba", "middle shabelle", "ogaden",
    # Regions — South Sudan
    "west equatoria", "eastern equatoria", "upper nile", "unity state",
    "central equatoria", "lakes state", "warrap", "jonglei",
    # Regions — Kenya
    "rift valley", "coast province", "western kenya", "nyanza",
    "north eastern", "central kenya",
    # Ethnic groups — Somalia
    "hawiye", "darod", "dir", "isaaq", "marehan", "abgaal",
    "habar gidir", "warsangeli", "dhulbahante", "majeerteen",
    "rahanweyn", "digil", "mirifle",
    # Ethnic groups — South Sudan
    "dinka", "nuer", "jieng", "naath", "chollo", "murle",
    "shilluk", "anuak", "fertit", "balanda", "bari",
    # Ethnic groups — Kenya
    "kikuyu", "luo", "kalenjin", "pokot", "maasai", "kamba",
    "meru", "embu", "kisii", "mijikenda",
    # Minority groups
    "bantu", "bajuni", "bravanese", "benadiri",
    # Political figures
    "kiir", "machar", "ruto", "gachagua", "olony",
    "farmaajo", "hassan sheikh", "deni", "bihi",
    # Organizations
    "igad", "amisom", "atmis", "sna", "sspdf",
    "al-shabaab", "alshabaab", "shabaab",
    # Campaigns / outlets
    "chaoscartel", "shahada", "al-kataib", "calamada", "somalimemo",
    "bbc africa", "bbcafricaeye", "bloodparliament",
    # Swahili terms
    "ukabila", "ubaguzi", "chuki",
    # Languages
    "swahili", "dholuo", "kikamba", "somali language",
    # Regional terms
    "horn of africa", "east africa", "greater horn",
    # Additional cities, regions, sub-clans to reach 140+
    "gaalkacyo", "dhuusamarreeb", "baydhabo", "ceerigaabo", "laascaanood",
    "gabiley", "burco", "boorama", "qardho", "hobyo",
    "nanyuki", "nyeri", "machakos", "kitale", "malindi", "lamu",
    "kajiado", "narok", "kericho", "bomet", "nandi",
    "yei", "maridi", "kapoeta", "pibor", "renk",
    "magwi", "pochalla", "akobo", "nasir", "leer",
]

# Convert to a set for O(1) lookup
_EA_INDICATORS_SET = set(EAST_AFRICA_INDICATORS)


# ─── Non-EA Fast Reject ──────────────────────────────────────────────────────
# Posts containing these WITHOUT any EA indicator → immediate NOISE.

NON_EA_STRONG_INDICATORS = [
    "trump", "biden", "maga", "democrat", "republican", "congress",
    "israel", "zionist", "palestinian", "hamas", "gaza",
    "ukraine", "putin", "zelensky", "nato",
    "modi", "bjp", "india", "china", "brexit",
    "bolsonaro", "brazil", "mexico", "cartel",
    "uk politics", "tory", "labour party",
    "canadian", "trudeau", "australia",
    "myanmar", "rohingya",
]


# ─── Noise and Counter-Speech Filters ────────────────────────────────────────

NOISE_MARKERS = [
    "fact check", "debunked", "false claim", "this is not true",
    "anti-hate speech", "combat hate", "fight against hate",
    "report hate speech", "breaking:", "press release",
    "misinformation alert", "fake news alert", "rated false by",
    "corrections:", "according to officials",
]

COUNTER_SPEECH = [
    "we must stop", "hate speech is wrong", "report this",
    "peace not hate", "nabad", "amani",
    "no to hate", "say no to", "stand against hate",
    "condemn hate speech", "reject tribalism",
]


# ─── Stopwords (never auto-learn) ────────────────────────────────────────────

STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "it", "that", "this", "was", "are",
    "be", "been", "being", "have", "has", "had", "do", "does", "did",
    "will", "would", "shall", "should", "may", "might", "can", "could",
    "not", "no", "nor", "so", "up", "out", "if", "about", "into", "through",
    "during", "before", "after", "above", "below", "between", "because",
    "each", "few", "more", "most", "other", "some", "such", "only", "own",
    "same", "than", "too", "very", "just", "over", "also", "back", "all",
    "its", "my", "our", "your", "their", "his", "her", "who", "what",
    "when", "where", "how", "why", "which", "there", "here", "then",
    "than", "them", "they", "we", "you", "he", "she", "me", "him",
    "these", "those", "any", "every", "both", "many", "much", "even",
    "still", "already", "again", "once", "never", "always", "often",
    "well", "like", "just", "now", "new", "one", "two", "day", "time",
    "way", "people", "think", "know", "make", "take", "come", "want",
    "look", "use", "find", "give", "tell", "work", "call", "try", "need",
    "feel", "become", "get", "got", "going", "went", "said", "say",
    # Platform / URL terms (never learn)
    "https", "http", "www", "com", "twitter", "tiktok", "facebook",
    "instagram", "youtube", "status", "photo", "video", "retweet",
    "follow", "like", "share", "comment", "reply", "quote", "thread",
}


# ─── Country Inference Map ────────────────────────────────────────────────────
# Maps indicator terms to countries for the infer_country() function.

_COUNTRY_SIGNALS: dict[str, str] = {}

_SOMALIA_TERMS = [
    "somalia", "somali", "mogadishu", "muqdisho", "hargeisa", "puntland",
    "somaliland", "jubaland", "hiiraan", "baidoa", "kismayo", "garowe",
    "bosaso", "beledweyne", "hawiye", "darod", "dir", "isaaq", "marehan",
    "abgaal", "habar gidir", "warsangeli", "dhulbahante", "majeerteen",
    "rahanweyn", "digil", "mirifle", "al-shabaab", "alshabaab", "shabaab",
    "bantu", "bajuni", "bravanese", "benadiri", "farmaajo", "hassan sheikh",
    "deni", "bihi", "gaalkacyo", "dhuusamarreeb", "ceerigaabo",
    "laascaanood", "gabiley", "burco", "boorama", "qardho", "hobyo",
    # Somali HS terms
    "xayawaan", "xoolo", "cayaanka", "qashin", "jareer", "jareereed",
    "mooryaan", "faqash", "xaarood", "hutuwiye", "laangaab", "qadaad weyn",
    "idoor", "eelay", "qabiil dagaal", "sare guraale",
    "kaafir", "kufaar", "gaal", "gaalo", "murtad", "munaafiq", "mushrik",
    "takfir", "riddah", "saliibiyiin", "dimuquraadiyadda shirkiga",
    "calmaaniyad", "gabadh sharaf la'aa", "qaniis", "gabar diin la'aa",
    "sawir iska xir",
]

_SOUTH_SUDAN_TERMS = [
    "south sudan", "juba", "malakal", "bentiu", "bor", "wau", "aweil",
    "torit", "nimule", "rumbek", "yambio", "dinka", "nuer", "jieng",
    "naath", "chollo", "murle", "shilluk", "anuak", "fertit", "balanda",
    "bari", "kiir", "machar", "olony", "sspdf",
    "west equatoria", "eastern equatoria", "upper nile", "unity state",
    "central equatoria", "lakes state", "warrap", "jonglei",
    "yei", "maridi", "kapoeta", "pibor", "renk", "magwi", "pochalla",
    "akobo", "nasir", "leer",
    # South Sudan HS terms
    "nyor", "nyornyor", "nyam nyam", "unwanted luggage",
    "jenge", "kokora", "dinkocracy", "jiengism", "monyjang power",
    "camjiec", "mathiang anyor", "warrapism", "juba na bari",
    "kiiriminal", "konyo konyo regime", "tabanists",
]

_KENYA_TERMS = [
    "kenya", "kenyan", "nairobi", "mombasa", "kisumu", "garissa",
    "wajir", "mandera", "lodwar", "kakuma", "eldoret", "nakuru", "thika",
    "rift valley", "coast province", "western kenya", "nyanza",
    "kikuyu", "luo", "kalenjin", "pokot", "maasai", "kamba", "meru",
    "embu", "kisii", "mijikenda", "ruto", "gachagua",
    "nanyuki", "nyeri", "machakos", "kitale", "malindi", "lamu",
    "kajiado", "narok", "kericho", "bomet", "nandi",
    # Kenya HS terms
    "madoadoa", "mende", "kwekwe", "kihii", "mwiji", "ngetiik",
    "conoka", "muhoi", "chorik", "watu wa kurusha mawe",
    "chinja kafir", "kura au risasi", "mungiki",
    "wakuja", "wageni", "mundu wa nja muuki",
]

for _t in _SOMALIA_TERMS:
    _COUNTRY_SIGNALS[_t] = "Somalia"
for _t in _SOUTH_SUDAN_TERMS:
    _COUNTRY_SIGNALS[_t] = "South Sudan"
for _t in _KENYA_TERMS:
    _COUNTRY_SIGNALS[_t] = "Kenya"


# ─── Subtype display → toxicity level mapping ────────────────────────────────

def _tox_level(score: float) -> str:
    """Convert numeric toxicity score to level string."""
    if score >= 0.7:
        return "high"
    if score >= 0.4:
        return "medium"
    return "low"


def _compute_toxicity_dimensions(display_name: str) -> dict:
    """Get toxicity dimension scores for a given subtype display name."""
    profile = TOXICITY_PROFILES.get(display_name)
    if not profile:
        return {"sev": "medium", "ins": "medium", "idt": "medium", "thr": "low"}
    return {k: _tox_level(v) for k, v in profile.items()}


def _compute_overall_toxicity(display_name: str) -> str:
    """Determine overall toxicity level from the subtype's profile."""
    profile = TOXICITY_PROFILES.get(display_name)
    if not profile:
        return "medium"
    avg = sum(profile.values()) / len(profile)
    return _tox_level(avg)


# ─── Text Extraction Helpers ─────────────────────────────────────────────────

def extract_text(item: dict) -> str:
    """Extract the main text content from an Apify item regardless of platform."""
    # X/Twitter
    text = item.get("text") or item.get("full_text") or ""
    # Facebook
    if not text:
        text = item.get("postText") or item.get("message") or ""
    # TikTok
    if not text:
        text = item.get("desc") or item.get("description") or ""
    # Fallback
    if not text:
        text = item.get("content") or ""
    return text.strip()


def extract_url(item: dict) -> str:
    """Extract the source URL from an Apify item."""
    url = item.get("url") or item.get("postUrl") or item.get("webVideoUrl") or ""
    if not url:
        tweet_id = item.get("id") or item.get("id_str")
        author_obj = item.get("author", {})
        if isinstance(author_obj, dict):
            username = author_obj.get("userName") or author_obj.get("screen_name")
        else:
            username = None
        if tweet_id and username:
            url = f"https://x.com/{username}/status/{tweet_id}"
    return url


def extract_author(item: dict) -> str:
    """Extract author handle/name from an Apify item."""
    # X/Twitter
    author = item.get("author", {})
    if isinstance(author, dict):
        handle = (author.get("userName") or author.get("screen_name")
                  or author.get("name", ""))
        if handle:
            return f"@{handle}" if not handle.startswith("@") else handle
    # Facebook
    page_name = item.get("pageName") or ""
    if not page_name:
        user_obj = item.get("user", {})
        if isinstance(user_obj, dict):
            page_name = user_obj.get("name", "")
    if page_name:
        return page_name
    # TikTok
    author_meta = item.get("authorMeta", {})
    if isinstance(author_meta, dict):
        tiktok_name = author_meta.get("name", "")
        if tiktok_name:
            return f"@{tiktok_name}"
    return "Unknown"


def extract_date(item: dict) -> str:
    """Extract post date from an Apify item as YYYY-MM-DD string."""
    date_str = (item.get("createdAt") or item.get("time")
                or item.get("timestamp") or item.get("createTime") or "")
    if date_str:
        try:
            if isinstance(date_str, (int, float)):
                dt = datetime.fromtimestamp(date_str, tz=timezone.utc)
            else:
                dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            return dt.strftime("%Y-%m-%d")
        except (ValueError, TypeError, OSError):
            pass
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def extract_platform(item: dict) -> str:
    """Determine which platform this item came from (compact label)."""
    # Check sweep metadata first
    meta = item.get("_brace4peace", {})
    if isinstance(meta, dict):
        p = meta.get("platform", "")
        if p:
            return p  # already compact: x, facebook, tiktok

    # Infer from _platform field (hs_apify_sweep uses this)
    p = item.get("_platform", "")
    if p:
        return p

    # Infer from URL
    url = extract_url(item)
    if "x.com" in url or "twitter.com" in url:
        return "x"
    if "facebook.com" in url or "fb.com" in url:
        return "facebook"
    if "tiktok.com" in url:
        return "tiktok"
    return "x"  # default for HS sweeps (primarily X/Twitter)


# ─── Post ID Generation ──────────────────────────────────────────────────────

def generate_post_id(text: str, author: str, date: str) -> str:
    """Generate deterministic post ID: apify-<md5(text[:100]|author|date)[:12]>."""
    raw = f"{text[:100]}|{author}|{date}"
    digest = hashlib.md5(raw.encode("utf-8", errors="replace")).hexdigest()[:12]
    return f"apify-{digest}"


# ─── Noise / Counter-Speech Filter ───────────────────────────────────────────

def check_noise(text: str) -> tuple[bool, str]:
    """
    Check if text is noise or counter-speech.

    Returns:
        (is_noise, reason) — True if the post should be discarded.
    """
    if len(text) < 10:
        return True, "text_too_short"

    text_lower = text.lower()

    # Check noise markers
    for marker in NOISE_MARKERS:
        if marker in text_lower:
            return True, f"noise_marker:{marker}"

    # Check counter-speech
    for marker in COUNTER_SPEECH:
        if marker in text_lower:
            return True, f"counter_speech:{marker}"

    return False, ""


# ─── East Africa Relevance Gate ───────────────────────────────────────────────

def check_ea_relevance(text: str) -> tuple[bool, list[str]]:
    """
    Check if text contains East Africa relevance indicators.

    Returns:
        (is_relevant, matched_indicators)
    """
    text_lower = text.lower()
    matched = []
    for indicator in EAST_AFRICA_INDICATORS:
        if indicator in text_lower:
            matched.append(indicator)
    return len(matched) > 0, matched


def _has_non_ea_indicators(text: str) -> bool:
    """Check if text contains strong non-EA indicators (fast reject)."""
    text_lower = text.lower()
    for term in NON_EA_STRONG_INDICATORS:
        if term in text_lower:
            return True
    return False


# ─── HS Indicator Matching ────────────────────────────────────────────────────

def match_hs_indicators(text: str) -> dict[str, list[str]]:
    """
    Match text against all 7 HS subtype indicator lists.

    Returns:
        dict mapping subtype key → list of matched indicator strings.
        Only subtypes with at least one match are included.
    """
    text_lower = text.lower()
    matches: dict[str, list[str]] = {}

    for subtype_key, subtype_def in HS_INDICATORS.items():
        subtype_matches = []
        for indicator in subtype_def["indicators"]:
            if indicator in text_lower:
                subtype_matches.append(indicator)
        if subtype_matches:
            matches[subtype_key] = subtype_matches

    return matches


# ─── Country Inference ────────────────────────────────────────────────────────

def infer_country(text: str, item_meta: dict | None = None) -> str:
    """
    Determine country from content indicators or sweep metadata.

    Priority:
      1. Explicit _hs_country from sweep metadata
      2. Country signals from text content
      3. Default: "Regional"
    """
    # Check sweep metadata
    if item_meta:
        country = item_meta.get("_hs_country", "")
        if country and country in ("Somalia", "South Sudan", "Kenya", "Regional"):
            return country

    text_lower = text.lower()
    country_scores: Counter = Counter()

    for term, country in _COUNTRY_SIGNALS.items():
        if term in text_lower:
            country_scores[country] += 1

    if not country_scores:
        return "Regional"

    # Return the country with the most signals
    top_country, top_count = country_scores.most_common(1)[0]
    return top_country


# ─── Toxic Handles Loading ────────────────────────────────────────────────────

def load_toxic_handles() -> dict[str, dict]:
    """
    Load toxic handles from CSV.

    Returns:
        dict mapping handle (lowercase) → row dict with fields from CSV.
    """
    handles: dict[str, dict] = {}
    if not TOXIC_HANDLES_CSV.exists():
        return handles

    try:
        with open(TOXIC_HANDLES_CSV, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                handle = row.get("handle", "").strip().lower()
                if handle:
                    handles[handle] = row
    except (OSError, csv.Error):
        pass

    return handles


# ─── Learned Keywords Loading ─────────────────────────────────────────────────

def load_learned_keywords() -> list[str]:
    """
    Load active learned HS keywords from CSV.

    Returns:
        list of keyword strings with status 'active' or 'proposed'.
    """
    keywords: list[str] = []
    if not LEARNED_KW_HS_CSV.exists():
        return keywords

    try:
        with open(LEARNED_KW_HS_CSV, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                kw = row.get("keyword", "").strip().lower()
                status = row.get("confidence", "").strip().lower()
                if kw and status in ("active", "proposed", ""):
                    keywords.append(kw)
    except (OSError, csv.Error):
        pass

    return keywords


# ─── Existing HS Post ID Loading ─────────────────────────────────────────────

def load_existing_post_ids() -> set[str]:
    """Load all existing post IDs from hate_speech_posts.json for dedup."""
    ids: set[str] = set()
    if not HS_DATA_PATH.exists():
        return ids

    try:
        with open(HS_DATA_PATH, encoding="utf-8") as f:
            posts = json.load(f)
        if isinstance(posts, list):
            for post in posts:
                pid = post.get("i", "")
                if pid:
                    ids.add(pid)
    except (json.JSONDecodeError, OSError):
        pass

    return ids


# ─── Core Classification ─────────────────────────────────────────────────────

def classify_hs_item(
    item: dict,
    toxic_handles: dict[str, dict],
    learned_keywords: list[str] | None = None,
) -> dict | None:
    """
    Classify a single raw Apify HS sweep item.

    Returns:
        Classification result dict if confirmed HS, or None if noise/rejected.

        Result dict keys:
          classification: "HS_CONFIRMED" | "NOISE"
          confidence: "HIGH" | "MEDIUM" | "LOW"
          confidence_score: float 0-1
          subtypes: list of {subtype_key, display, matched_indicators}
          best_subtype_key: str
          best_subtype_display: str
          match_count: int (total indicator matches across all subtypes)
          country: str
          justification: str
          ea_indicators: list of matched EA indicators
          is_toxic_handle: bool
    """
    text = extract_text(item)
    author = extract_author(item)
    author_lower = author.lower().lstrip("@")

    # ── Step 1: Noise filter ──
    is_noise, noise_reason = check_noise(text)
    if is_noise:
        return None

    # ── Step 1b: Check if author is a known toxic handle ──
    is_toxic_handle = False
    author_variants = [author_lower, f"@{author_lower}"]
    for variant in author_variants:
        if variant in toxic_handles:
            is_toxic_handle = True
            break

    # ── Step 2: East Africa Relevance Gate ──
    ea_relevant, ea_matched = check_ea_relevance(text)

    if not ea_relevant and not is_toxic_handle:
        # Check non-EA fast reject
        if _has_non_ea_indicators(text):
            return None
        # Even without non-EA markers, no EA relevance → reject
        return None

    # ── Step 3: HS Indicator Matching ──
    hs_matches = match_hs_indicators(text)

    # Also check learned keywords (add to match count but not to subtypes)
    learned_kw_hits: list[str] = []
    if learned_keywords:
        text_lower = text.lower()
        for kw in learned_keywords:
            if kw in text_lower:
                learned_kw_hits.append(kw)

    # Total match count = indicator matches + learned keyword hits
    indicator_match_count = sum(len(v) for v in hs_matches.values())
    total_match_count = indicator_match_count + len(learned_kw_hits)

    if total_match_count == 0:
        # No HS indicators found at all
        return None

    # ── Step 4: Confidence scoring ──
    if total_match_count >= 3:
        confidence = "HIGH"
        confidence_score = min(0.95, 0.7 + total_match_count * 0.05)
    elif total_match_count == 2:
        confidence = "MEDIUM"
        confidence_score = 0.65
    else:
        confidence = "LOW"
        confidence_score = 0.45

    # Boost confidence for toxic handles
    if is_toxic_handle:
        confidence_score = min(0.99, confidence_score + 0.1)
        if confidence == "LOW":
            confidence = "MEDIUM"
            confidence_score = max(confidence_score, 0.6)

    # ── Build subtype list ──
    subtypes_list: list[dict] = []
    for st_key, matched_indicators in hs_matches.items():
        display = HS_INDICATORS[st_key]["display"]
        score = min(1.0, len(matched_indicators) * 0.3 + 0.2)
        subtypes_list.append({
            "subtype_key": st_key,
            "display": display,
            "matched_indicators": matched_indicators,
            "score": round(score, 2),
        })

    # Sort by score descending
    subtypes_list.sort(key=lambda x: x["score"], reverse=True)

    # Best subtype
    if subtypes_list:
        best_subtype_key = subtypes_list[0]["subtype_key"]
        best_subtype_display = subtypes_list[0]["display"]
    else:
        # Only learned keyword hits, no dictionary indicator matches
        best_subtype_key = "HS-UNKNOWN"
        best_subtype_display = "Unknown HS Type"

    # Country inference
    country = infer_country(text, item)

    # Build justification
    matched_terms = []
    for st in subtypes_list:
        matched_terms.extend(st["matched_indicators"])
    if learned_kw_hits:
        matched_terms.extend([f"(learned:{kw})" for kw in learned_kw_hits])
    justification = (
        f"{confidence} confidence: {total_match_count} indicator(s) matched "
        f"[{', '.join(matched_terms[:8])}]"
    )
    if is_toxic_handle:
        justification += f" | toxic handle: {author}"

    # Prediction label: HIGH/MEDIUM → "Hate", LOW → "Abusive"
    prediction = "Hate" if confidence in ("HIGH", "MEDIUM") else "Abusive"

    return {
        "classification": "HS_CONFIRMED",
        "confidence": confidence,
        "confidence_score": round(confidence_score, 3),
        "prediction": prediction,
        "subtypes": subtypes_list,
        "best_subtype_key": best_subtype_key,
        "best_subtype_display": best_subtype_display,
        "match_count": total_match_count,
        "country": country,
        "justification": justification,
        "ea_indicators": ea_matched,
        "is_toxic_handle": is_toxic_handle,
        "learned_kw_hits": learned_kw_hits,
    }


# ─── Compact Format Conversion ───────────────────────────────────────────────

def to_compact_format(
    item: dict,
    result: dict,
    sweep_date: str | None = None,
) -> dict:
    """
    Convert a classified item + result into the compact HS post format
    used by hate_speech_posts.json.
    """
    text = extract_text(item)
    author = extract_author(item)
    date = extract_date(item)
    url = extract_url(item)
    platform = extract_platform(item)
    post_id = generate_post_id(text, author, date)

    if sweep_date is None:
        sweep_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Gather topic from sweep metadata
    hs_group = ""
    if isinstance(item, dict):
        hs_group = item.get("_hs_group", "")
        if not hs_group:
            meta = item.get("_brace4peace", {})
            if isinstance(meta, dict):
                hs_group = meta.get("keyword_group", "")

    # Build subtypes array for compact format
    st_compact = []
    for st in result.get("subtypes", []):
        st_compact.append({
            "n": st["display"],
            "s": st["score"],
        })

    # Toxicity dimensions from best subtype
    best_display = result.get("best_subtype_display", "")
    txd = _compute_toxicity_dimensions(best_display)
    tx_level = _compute_overall_toxicity(best_display)

    return {
        "i": post_id,
        "t": text[:300],
        "d": date,
        "c": result.get("country", "Regional"),
        "p": platform,
        "a": author,
        "l": url,
        "pr": result.get("prediction", "Hate"),
        "co": result.get("confidence_score", 0.5),
        "tx": tx_level,
        "gt": hs_group,
        "en": {"l": 0, "s": 0, "c": 0},
        "ma": result.get("match_count", 1),
        "st": st_compact,
        "txd": txd,
        "qc": "auto_sweep",
        "_source": "hs_apify_sweep",
        "_sweep_date": sweep_date,
    }


# ─── Autolearning: Toxic Handles ─────────────────────────────────────────────

def _update_toxic_handles(
    classified_items: list[tuple[dict, dict]],
    existing_handles: dict[str, dict],
) -> list[dict]:
    """
    Track authors with 2+ HS posts in this sweep as toxic handles.

    Args:
        classified_items: list of (raw_item, classification_result) tuples
        existing_handles: dict from load_toxic_handles()

    Returns:
        list of new/updated handle dicts to write
    """
    author_counts: Counter = Counter()
    author_meta: dict[str, dict] = {}

    for item, result in classified_items:
        author = extract_author(item)
        author_lower = author.lower()
        author_counts[author_lower] += 1
        if author_lower not in author_meta:
            author_meta[author_lower] = {
                "handle": author,
                "platform": extract_platform(item),
                "country": result.get("country", "Regional"),
                "subtypes": set(),
            }
        for st in result.get("subtypes", []):
            author_meta[author_lower]["subtypes"].add(st["subtype_key"])

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    new_handles: list[dict] = []

    for author_lower, count in author_counts.items():
        if count < 2:
            continue

        meta = author_meta[author_lower]
        existing = existing_handles.get(author_lower)

        if existing:
            # Update existing entry
            prev_flags = int(existing.get("flags", "0") or "0")
            total = prev_flags + count
            new_handles.append({
                "handle": meta["handle"],
                "platform": meta["platform"],
                "country": meta["country"],
                "first_seen": existing.get("first_seen", today),
                "last_seen": today,
                "flags": str(total),
            })
        else:
            # New toxic handle
            new_handles.append({
                "handle": meta["handle"],
                "platform": meta["platform"],
                "country": meta["country"],
                "first_seen": today,
                "last_seen": today,
                "flags": str(count),
            })

    return new_handles


def _write_toxic_handles(
    new_handles: list[dict],
    existing_handles: dict[str, dict],
) -> int:
    """
    Write toxic handles to CSV (merge with existing).

    Returns:
        Number of new handles added.
    """
    if not new_handles:
        return 0

    AUTOLEARN_DIR.mkdir(parents=True, exist_ok=True)

    # Merge: keep all existing, update/add new
    merged: dict[str, dict] = {}

    # Load existing rows as-is
    if TOXIC_HANDLES_CSV.exists():
        try:
            with open(TOXIC_HANDLES_CSV, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    handle = row.get("handle", "").strip().lower()
                    if handle:
                        merged[handle] = row
        except (OSError, csv.Error):
            pass

    added = 0
    for entry in new_handles:
        key = entry["handle"].lower()
        if key not in merged:
            added += 1
        merged[key] = entry

    # Write back
    fieldnames = ["handle", "platform", "country", "first_seen", "last_seen", "flags"]
    with open(TOXIC_HANDLES_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in sorted(merged.values(), key=lambda r: r.get("handle", "")):
            writer.writerow({k: row.get(k, "") for k in fieldnames})

    return added


# ─── Autolearning: Learned Keywords ──────────────────────────────────────────

def _extract_candidate_keywords(
    classified_items: list[tuple[dict, dict]],
) -> Counter:
    """
    Extract candidate keywords from confirmed HS texts.

    Tokenises texts and counts word frequency across all classified items.
    Filters out stopwords, short words, and known indicators.
    """
    word_counts: Counter = Counter()

    # Build set of all known indicator terms
    known_indicators: set[str] = set()
    for st_def in HS_INDICATORS.values():
        for ind in st_def["indicators"]:
            known_indicators.add(ind.lower())
    for ea in EAST_AFRICA_INDICATORS:
        known_indicators.add(ea.lower())

    for item, result in classified_items:
        text = extract_text(item).lower()
        # Strip URLs
        text = re.sub(r'https?://\S+', '', text)
        # Strip mentions
        text = re.sub(r'@\w+', '', text)
        # Strip hashtag symbols (keep the word)
        text = text.replace("#", "")
        # Tokenise
        words = re.findall(r'[a-z\u00c0-\u024f]{4,}', text)
        unique_words = set(words)
        for word in unique_words:
            if word in STOPWORDS:
                continue
            if word in known_indicators:
                continue
            word_counts[word] += 1

    return word_counts


def _update_learned_keywords(
    classified_items: list[tuple[dict, dict]],
) -> int:
    """
    Words appearing in 3+ confirmed HS texts, min 4 chars, not stopwords
    → add to learned_keywords_hs.csv as 'proposed'.

    Returns:
        Number of new keywords added.
    """
    if len(classified_items) < 3:
        return 0

    word_counts = _extract_candidate_keywords(classified_items)

    # Filter: must appear in 3+ texts
    candidates = [
        (word, count) for word, count in word_counts.items()
        if count >= 3
    ]
    if not candidates:
        return 0

    # Load existing keywords
    existing_kw: set[str] = set()
    if LEARNED_KW_HS_CSV.exists():
        try:
            with open(LEARNED_KW_HS_CSV, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    kw = row.get("keyword", "").strip().lower()
                    if kw:
                        existing_kw.add(kw)
        except (OSError, csv.Error):
            pass

    # Filter out already-known
    new_candidates = [
        (word, count) for word, count in candidates
        if word not in existing_kw
    ]

    if not new_candidates:
        return 0

    # Sort by frequency, take top 10
    new_candidates.sort(key=lambda x: x[1], reverse=True)
    new_candidates = new_candidates[:10]

    AUTOLEARN_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    fieldnames = [
        "keyword", "language", "country", "category", "confidence",
        "source", "added_date",
    ]

    # Append to CSV
    write_header = not LEARNED_KW_HS_CSV.exists() or os.path.getsize(LEARNED_KW_HS_CSV) == 0
    # Check if file has content beyond header
    if LEARNED_KW_HS_CSV.exists():
        with open(LEARNED_KW_HS_CSV, encoding="utf-8") as f:
            content = f.read().strip()
            # Only header line
            if content and "\n" not in content:
                write_header = False

    with open(LEARNED_KW_HS_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        for word, count in new_candidates:
            writer.writerow({
                "keyword": word,
                "language": "unknown",
                "country": "",
                "category": "auto_extracted",
                "confidence": "proposed",
                "source": f"hs_sweep_freq_{count}",
                "added_date": today,
            })

    return len(new_candidates)


# ─── Autolearning: Narrative Discoveries ──────────────────────────────────────

def _update_narrative_discoveries(
    classified_items: list[tuple[dict, dict]],
) -> int:
    """
    Extract potential new narrative claims from classified HS items.
    Claims are text excerpts that could represent emerging narrative patterns.

    Returns:
        Number of new narrative claims written.
    """
    if len(classified_items) < 2:
        return 0

    # Simple claim extraction: look for declarative patterns
    claim_patterns = [
        re.compile(r'((?:all|every|these)\s+\w+\s+(?:are|is|must|should|will)\s+.{10,50})', re.I),
        re.compile(r'(\w+\s+(?:regime|government|administration)\s+.{10,40})', re.I),
    ]

    claims: list[dict] = []
    seen_claims: set[str] = set()

    # Load existing discoveries
    if NARRATIVE_DISCOVERIES_CSV.exists():
        try:
            with open(NARRATIVE_DISCOVERIES_CSV, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    claim = row.get("narrative_claim", "").strip().lower()
                    if claim:
                        seen_claims.add(claim[:50])
        except (OSError, csv.Error):
            pass

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    for item, result in classified_items:
        text = extract_text(item)
        url = extract_url(item)
        country = result.get("country", "Regional")

        for pattern in claim_patterns:
            for match in pattern.finditer(text):
                claim_text = match.group(1).strip()
                claim_key = claim_text[:50].lower()
                if claim_key in seen_claims:
                    continue
                seen_claims.add(claim_key)
                claims.append({
                    "narrative_claim": claim_text[:100],
                    "country": country,
                    "source_type": "hs_sweep",
                    "first_seen": today,
                    "times_seen": "1",
                    "example_url": url,
                    "status": "proposed",
                    "notes": "",
                })

        # Cap at 5 per run
        if len(claims) >= 5:
            break

    if not claims:
        return 0

    AUTOLEARN_DIR.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "narrative_claim", "country", "source_type", "first_seen",
        "times_seen", "example_url", "status", "notes",
    ]

    file_exists = NARRATIVE_DISCOVERIES_CSV.exists()
    file_has_content = False
    if file_exists:
        file_has_content = os.path.getsize(NARRATIVE_DISCOVERIES_CSV) > 0

    with open(NARRATIVE_DISCOVERIES_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_has_content:
            writer.writeheader()
        for claim in claims:
            writer.writerow(claim)

    return len(claims)


# ─── Combined Autolearning Entry Point ────────────────────────────────────────

def update_autolearning(
    classified_items: list[tuple[dict, dict]],
    toxic_handles: dict[str, dict],
) -> dict:
    """
    Run all autolearning updates.

    Args:
        classified_items: list of (raw_item, classification_result) tuples
        toxic_handles: existing toxic handles dict

    Returns:
        Summary dict with counts of what was updated.
    """
    summary = {
        "new_toxic_handles": 0,
        "new_learned_keywords": 0,
        "new_narrative_discoveries": 0,
    }

    if not classified_items:
        return summary

    # 1. Toxic handles
    new_handles = _update_toxic_handles(classified_items, toxic_handles)
    summary["new_toxic_handles"] = _write_toxic_handles(new_handles, toxic_handles)

    # 2. Learned keywords
    summary["new_learned_keywords"] = _update_learned_keywords(classified_items)

    # 3. Narrative discoveries
    summary["new_narrative_discoveries"] = _update_narrative_discoveries(classified_items)

    return summary


# ─── Find Latest Sweep File ──────────────────────────────────────────────────

def _find_latest_sweep_file() -> Path | None:
    """Find the most recent HS sweep results file."""
    if not HS_RESULTS_DIR.exists():
        return None

    sweep_files = sorted(
        HS_RESULTS_DIR.glob("hs_sweep_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return sweep_files[0] if sweep_files else None


# ─── Load Items ───────────────────────────────────────────────────────────────

def _load_items(items_file: str | Path | None = None) -> list[dict]:
    """Load raw sweep items from file."""
    if items_file:
        path = Path(items_file)
    else:
        path = _find_latest_sweep_file()

    if not path or not path.exists():
        print(f"[hs_classify] No items file found: {path}")
        return []

    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "items" in data:
            return data["items"]
        return []
    except (json.JSONDecodeError, OSError) as e:
        print(f"[hs_classify] Error loading {path}: {e}")
        return []


# ─── Append to HS Data ───────────────────────────────────────────────────────

def _append_to_hs_data(new_posts: list[dict], dry_run: bool = False) -> int:
    """
    Append new HS posts to hate_speech_posts.json, deduplicating by ID.

    Returns:
        Number of posts actually appended.
    """
    if not new_posts:
        return 0

    if dry_run:
        return len(new_posts)

    # Load existing
    existing: list[dict] = []
    if HS_DATA_PATH.exists():
        try:
            with open(HS_DATA_PATH, encoding="utf-8") as f:
                existing = json.load(f)
            if not isinstance(existing, list):
                existing = []
        except (json.JSONDecodeError, OSError):
            existing = []

    existing_ids = {p.get("i", "") for p in existing}

    # Filter out duplicates
    to_add = [p for p in new_posts if p.get("i", "") not in existing_ids]

    if not to_add:
        return 0

    # Append
    existing.extend(to_add)

    # Write atomically: write to temp file then rename
    HS_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = HS_DATA_PATH.with_suffix(".tmp")
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, separators=(",", ":"))
        tmp_path.replace(HS_DATA_PATH)
    except OSError as e:
        print(f"[hs_classify] Error writing {HS_DATA_PATH}: {e}")
        if tmp_path.exists():
            tmp_path.unlink()
        return 0

    return len(to_add)


# ─── Subtype Proposal Check ──────────────────────────────────────────────────

def _check_subtype_proposal(
    unclassified_items: list[tuple[dict, str]],
) -> list[dict]:
    """
    If 5+ items from the same HS keyword group can't be classified by
    existing indicators, propose a new subtype for review.

    Args:
        unclassified_items: list of (raw_item, hs_group) for items that
            passed the EA gate but had zero indicator matches.

    Returns:
        list of proposal dicts (for logging/review).
    """
    group_counts: Counter = Counter()
    group_examples: dict[str, list[str]] = defaultdict(list)

    for item, hs_group in unclassified_items:
        if not hs_group:
            continue
        group_counts[hs_group] += 1
        if len(group_examples[hs_group]) < 3:
            text = extract_text(item)
            group_examples[hs_group].append(text[:100])

    proposals: list[dict] = []
    for group, count in group_counts.items():
        if count >= 5:
            proposals.append({
                "proposed_subtype": f"HS-NEW-{group}",
                "hs_group": group,
                "unclassified_count": count,
                "examples": group_examples[group],
                "status": "needs_review",
            })

    return proposals


# ─── Main Entry Point ────────────────────────────────────────────────────────

def main(items_file: str | None = None, dry_run: bool = False) -> dict:
    """
    Main classification pipeline entry point.

    Args:
        items_file: path to items JSON file (or None for latest)
        dry_run: if True, don't write to files

    Returns:
        Summary dict with classification statistics.
    """
    summary = {
        "total_items": 0,
        "noise_filtered": 0,
        "ea_rejected": 0,
        "no_indicators": 0,
        "hs_confirmed": 0,
        "hs_high": 0,
        "hs_medium": 0,
        "hs_low": 0,
        "duplicates_skipped": 0,
        "posts_appended": 0,
        "autolearning": {},
        "subtype_proposals": [],
        "subtype_distribution": {},
        "country_distribution": {},
    }

    # Load items
    items = _load_items(items_file)
    summary["total_items"] = len(items)

    if not items:
        print("[hs_classify] No items to classify.")
        return summary

    # Load reference data
    toxic_handles = load_toxic_handles()
    learned_keywords = load_learned_keywords()
    existing_ids = load_existing_post_ids()

    # Determine sweep date
    sweep_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Classify each item
    classified_items: list[tuple[dict, dict]] = []
    new_posts: list[dict] = []
    unclassified_ea_items: list[tuple[dict, str]] = []

    subtype_counts: Counter = Counter()
    country_counts: Counter = Counter()

    for item in items:
        text = extract_text(item)
        author = extract_author(item)
        date = extract_date(item)

        # Classify
        result = classify_hs_item(item, toxic_handles, learned_keywords)

        if result is None:
            # Determine why it was rejected for stats
            is_noise, _ = check_noise(text)
            if is_noise:
                summary["noise_filtered"] += 1
            else:
                ea_relevant, _ = check_ea_relevance(text)
                if not ea_relevant:
                    summary["ea_rejected"] += 1
                else:
                    summary["no_indicators"] += 1
                    # Track for subtype proposal
                    hs_group = item.get("_hs_group", "")
                    if hs_group:
                        unclassified_ea_items.append((item, hs_group))
            continue

        # Confirmed HS
        classified_items.append((item, result))
        summary["hs_confirmed"] += 1

        confidence = result["confidence"]
        if confidence == "HIGH":
            summary["hs_high"] += 1
        elif confidence == "MEDIUM":
            summary["hs_medium"] += 1
        else:
            summary["hs_low"] += 1

        # Track distributions
        subtype_counts[result["best_subtype_display"]] += 1
        country_counts[result["country"]] += 1

        # Convert to compact format
        compact = to_compact_format(item, result, sweep_date)

        # Check for duplicate
        if compact["i"] in existing_ids:
            summary["duplicates_skipped"] += 1
            continue

        existing_ids.add(compact["i"])
        new_posts.append(compact)

    # Write new posts
    appended = _append_to_hs_data(new_posts, dry_run=dry_run)
    summary["posts_appended"] = appended

    # Update distributions
    summary["subtype_distribution"] = dict(subtype_counts.most_common())
    summary["country_distribution"] = dict(country_counts.most_common())

    # Run autolearning
    if not dry_run:
        summary["autolearning"] = update_autolearning(
            classified_items, toxic_handles,
        )
    else:
        summary["autolearning"] = {
            "new_toxic_handles": 0,
            "new_learned_keywords": 0,
            "new_narrative_discoveries": 0,
        }

    # Check for subtype proposals
    proposals = _check_subtype_proposal(unclassified_ea_items)
    summary["subtype_proposals"] = proposals

    # Print summary
    print(f"\n{'='*60}")
    print(f"HS APIFY CLASSIFICATION SUMMARY")
    print(f"{'='*60}")
    print(f"Total items:           {summary['total_items']}")
    print(f"Noise filtered:        {summary['noise_filtered']}")
    print(f"EA rejected:           {summary['ea_rejected']}")
    print(f"No indicators:         {summary['no_indicators']}")
    print(f"HS confirmed:          {summary['hs_confirmed']}")
    print(f"  - HIGH confidence:   {summary['hs_high']}")
    print(f"  - MEDIUM confidence: {summary['hs_medium']}")
    print(f"  - LOW confidence:    {summary['hs_low']}")
    print(f"Duplicates skipped:    {summary['duplicates_skipped']}")
    print(f"Posts appended:        {summary['posts_appended']}")

    if summary["subtype_distribution"]:
        print(f"\nSubtype distribution:")
        for st, count in sorted(
            summary["subtype_distribution"].items(),
            key=lambda x: x[1], reverse=True,
        ):
            print(f"  {st}: {count}")

    if summary["country_distribution"]:
        print(f"\nCountry distribution:")
        for c, count in sorted(
            summary["country_distribution"].items(),
            key=lambda x: x[1], reverse=True,
        ):
            print(f"  {c}: {count}")

    al = summary["autolearning"]
    if any(al.values()):
        print(f"\nAutolearning:")
        print(f"  New toxic handles:         {al['new_toxic_handles']}")
        print(f"  New learned keywords:      {al['new_learned_keywords']}")
        print(f"  New narrative discoveries: {al['new_narrative_discoveries']}")

    if proposals:
        print(f"\nSubtype proposals ({len(proposals)}):")
        for p in proposals:
            print(f"  {p['proposed_subtype']}: {p['unclassified_count']} items from {p['hs_group']}")

    if dry_run:
        print(f"\n[DRY RUN — no files were modified]")

    print(f"{'='*60}\n")

    return summary


# ─── CLI Entry Point ─────────────────────────────────────────────────────────

def _parse_args(argv: list[str] | None = None) -> dict:
    """Parse command-line arguments (stdlib only, no argparse dependency)."""
    args = argv if argv is not None else sys.argv[1:]
    parsed = {
        "items_file": None,
        "dry_run": False,
    }

    i = 0
    while i < len(args):
        arg = args[i]
        if arg in ("--input", "-i") and i + 1 < len(args):
            parsed["items_file"] = args[i + 1]
            i += 2
        elif arg == "--dry-run":
            parsed["dry_run"] = True
            i += 1
        elif arg in ("--help", "-h"):
            print(__doc__)
            sys.exit(0)
        else:
            # Positional arg: treat as items file
            if not parsed["items_file"]:
                parsed["items_file"] = arg
            i += 1

    return parsed


if __name__ == "__main__":
    opts = _parse_args()
    result = main(
        items_file=opts["items_file"],
        dry_run=opts["dry_run"],
    )

    # Exit with non-zero if no items were processed
    if result["total_items"] == 0:
        sys.exit(1)
