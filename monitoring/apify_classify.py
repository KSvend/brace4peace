#!/usr/bin/env python3
"""
Apify Auto-Classification Module for BRACE4PEACE
=================================================
Takes raw Apify sweep results and classifies each item as:
  - DISINFO → goes to timeline as PRIMARY event
  - HS_ONLY → routed to HS database (not timeline)
  - NOISE   → discarded (news reports, counter-speech, irrelevant)

Also handles:
  - Narrative family matching
  - Coordination detection (copy-paste, synchronized posting)
  - New keyword extraction for autolearning loop
  - New handle/source discovery

Usage:
    python3 apify_classify.py [--input items_file.json] [--dry-run]

When called from the monitoring cron, it reads the latest items file and
writes classified results to the findings structure.
"""

import json
import re
import os
from datetime import datetime, timezone
from pathlib import Path
from collections import Counter, defaultdict

# ─── Paths ────────────────────────────────────────────────────────────────────

WORKSPACE = Path("/home/user/workspace")
RESULTS_DIR = WORKSPACE / "brace4peace/monitoring/apify_results"
STRATEGY_PATH = WORKSPACE / "brace4peace/monitoring/apify_keyword_strategy.json"
NARRATIVES_PATH = WORKSPACE / "brace4peace-platform/data/narratives.json"
WATCHLIST_PATH = WORKSPACE / "brace4peace/monitoring/watchlist.json"
WEIGHTS_PATH = WORKSPACE / "narrative_family_weights.json"
TIMELINE_PATH = WORKSPACE / "brace4peace_timeline.json"
EVENTS_PATH = WORKSPACE / "brace4peace-platform/data/events.json"
SIGNAL_METRICS_PATH = WORKSPACE / "brace4peace/monitoring/signal_metrics.json"


# ─── Classification Rules ────────────────────────────────────────────────────

# Designated VE propaganda outlets — output is definitionally VE propaganda
# NOTE: "wakaalada wararka" means "news agency" in Somali — too generic on its own.
# Only match it when paired with VE-specific context, not when it's just "wakaalada wararka ee @Reuters".
VE_OUTLETS_EXACT = {
    "shahada news", "al-kataib", "al kataib", "al-kataib media",
    "manjaniq media", "manjaniq", "voice of munasir", "al hijratain",
    "al hijraytain", "calamada", "somalimemo"
}
# These require ADDITIONAL context to classify as VE (generic Somali terms)
VE_OUTLETS_CONTEXTUAL = {
    "wakaalada wararka": ["al-shabaab", "shahada", "mujahideen", "ghazwa", "dagaal", "gantaal"],
    "al-furqan": ["al-shabaab", "jihad", "dawla", "mujahideen"],
    "al furqan": ["al-shabaab", "jihad", "dawla", "mujahideen"],
    "shahada": ["al-shabaab", "attack", "claim", "mujahideen", "soldiers killed"]
}

# Coordinated campaign hashtags — high confidence when found in clusters
COORD_HASHTAGS = {
    "#dogsofwar", "#chaoscartel", "#toxicactivists", "#bbcforchaos",
    "#bloodparliament", "#527bloggers", "#43against1"
}

# Known troll network indicators
TROLL_INDICATORS = [
    "dogs of war", "toxic activists", "chaos cartel", "foreign-funded",
    "paid agents", "soros", "abducted themselves", "bbc for chaos",
    "blood parliament"
]

# Hate speech markers (WITHOUT false claims — these are HS only)
HS_MARKERS = [
    "cockroach", "vermin", "exterminate", "wipe out", "kill all",
    "deserve to die", "animals", "subhuman", "cleanse"
]

# Counter-speech / fact-check markers → NOISE
COUNTER_MARKERS = [
    "fact check", "false claim", "debunked", "misinformation alert",
    "this is not true", "misleading post", "fake news alert",
    "rated false by", "corrections:"
]

# News reporting markers → NOISE (Method A territory, not Method B)
NEWS_MARKERS = [
    "according to", "reports suggest", "sources say", "breaking:",
    "developing:", "just in:", "press release", "statement from"
]


# ─── Core Classification ─────────────────────────────────────────────────────

def load_config():
    """Load all reference data."""
    with open(STRATEGY_PATH) as f:
        strategy = json.load(f)
    with open(NARRATIVES_PATH) as f:
        narratives = json.load(f)
    with open(WEIGHTS_PATH) as f:
        weights = json.load(f)
    
    watchlist = {}
    if WATCHLIST_PATH.exists():
        with open(WATCHLIST_PATH) as f:
            watchlist = json.load(f)
    
    return strategy, narratives, weights, watchlist


def extract_text(item):
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


def extract_url(item):
    """Extract the source URL from an Apify item."""
    url = item.get("url") or item.get("postUrl") or item.get("webVideoUrl") or ""
    if not url:
        # Construct X URL from id
        tweet_id = item.get("id") or item.get("id_str")
        username = item.get("author", {}).get("userName") or item.get("user", {}).get("screen_name")
        if tweet_id and username:
            url = f"https://x.com/{username}/status/{tweet_id}"
    return url


def extract_author(item):
    """Extract author handle/name from an Apify item."""
    # X/Twitter
    author = item.get("author", {})
    if isinstance(author, dict):
        handle = author.get("userName") or author.get("screen_name") or author.get("name", "")
        if handle:
            return f"@{handle}" if not handle.startswith("@") else handle
    # Facebook
    page_name = item.get("pageName") or item.get("user", {}).get("name", "")
    if page_name:
        return page_name
    # TikTok
    tiktok_author = item.get("authorMeta", {}).get("name", "")
    if tiktok_author:
        return f"@{tiktok_author}"
    return "Unknown"


def extract_date(item):
    """Extract post date from an Apify item."""
    date_str = (item.get("createdAt") or item.get("time") or 
                item.get("timestamp") or item.get("createTime") or "")
    if date_str:
        try:
            # Handle various date formats
            if isinstance(date_str, (int, float)):
                dt = datetime.fromtimestamp(date_str, tz=timezone.utc)
            else:
                # Try ISO format first
                dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            return dt.strftime("%Y-%m-%d")
        except (ValueError, TypeError, OSError):
            pass
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def extract_hashtags(text):
    """Extract hashtags from text."""
    return set(re.findall(r'#\w+', text.lower()))


def extract_platform(item):
    """Determine which platform this item came from."""
    meta = item.get("_brace4peace", {})
    platform = meta.get("platform", "")
    if platform:
        return {"x": "X (Twitter)", "facebook": "Facebook", "tiktok": "TikTok"}.get(platform, platform)
    
    url = extract_url(item)
    if "x.com" in url or "twitter.com" in url:
        return "X (Twitter)"
    if "facebook.com" in url or "fb.com" in url:
        return "Facebook"
    if "tiktok.com" in url:
        return "TikTok"
    return "Unknown"


def classify_item(item, strategy, narratives, weights):
    """
    Classify a single Apify item.
    
    Returns dict with:
      - classification: DISINFO | HS_ONLY | NOISE
      - confidence: HIGH | MEDIUM | LOW
      - justification: why
      - narrative_ids: matched narrative IDs
      - narrative_families: matched families with intensity
      - coordination_score: 0-1 (how likely part of coordinated campaign)
      - is_ve_propaganda: bool
      - new_claims: list of potential new false claims for autolearning
    """
    text = extract_text(item)
    text_lower = text.lower()
    hashtags = extract_hashtags(text)
    meta = item.get("_brace4peace", {})
    keyword_group = meta.get("keyword_group", "")
    group_narrative_ids = meta.get("narrative_ids", [])
    
    result = {
        "classification": "NOISE",
        "confidence": "LOW",
        "justification": "",
        "narrative_ids": [],
        "narrative_families": [],
        "coordination_score": 0.0,
        "is_ve_propaganda": False,
        "new_claims": [],
        "disinfo_subtype": None,
        "hs_overlap": False
    }
    
    if not text or len(text) < 15:
        result["justification"] = "Content too short or empty to classify"
        return result
    
    # ── RULE 1: VE Propaganda Outlet ──
    # Geographic relevance check: Manjaniq Media is also an Indonesian Islamic publisher.
    # Only classify as VE propaganda if content has East Africa context.
    ea_geo_terms = ["somalia", "somali", "puntland", "mogadishu", "muqdisho",
                    "kenya", "south sudan", "al-shabaab", "alshabaab", "wilayah",
                    "amisom", "atmis", "sna ", "sspdf", "spla"]
    has_ea_context = any(term in text_lower for term in ea_geo_terms)
    
    # 1a: Exact-match outlets (unambiguous names)
    for outlet in VE_OUTLETS_EXACT:
        if outlet in text_lower:
            # For Manjaniq, require East Africa context (it's also an Indonesian publisher)
            if "manjaniq" in outlet and not has_ea_context:
                # Check if it's Indonesian content (common false positive)
                indonesian_terms = ["buku", "penerbit", "terjemahan", "syaikh", "mengkafirkan"]
                if any(term in text_lower for term in indonesian_terms):
                    result["classification"] = "NOISE"
                    result["justification"] = f"References '{outlet}' but content is Indonesian Islamic publishing, not ISS-Somalia VE propaganda. No East Africa context."
                    return result
            result["classification"] = "DISINFO"
            result["confidence"] = "HIGH"
            result["is_ve_propaganda"] = True
            result["disinfo_subtype"] = "propaganda"
            result["justification"] = f"Content references designated VE propaganda outlet '{outlet}'; all output is definitionally VE propaganda."
            result["narrative_ids"] = group_narrative_ids
            _assign_families(result, "VE_PROPAGANDA", weights)
            return result
    # 1b: Contextual outlets (generic Somali terms that need VE-context)
    for outlet, context_terms in VE_OUTLETS_CONTEXTUAL.items():
        if outlet in text_lower:
            if any(ctx in text_lower for ctx in context_terms):
                result["classification"] = "DISINFO"
                result["confidence"] = "HIGH"
                result["is_ve_propaganda"] = True
                result["disinfo_subtype"] = "propaganda"
                matched_ctx = [c for c in context_terms if c in text_lower][:2]
                result["justification"] = f"Content references '{outlet}' with VE context ({', '.join(matched_ctx)}); classified as VE propaganda."
                result["narrative_ids"] = group_narrative_ids
                _assign_families(result, "VE_PROPAGANDA", weights)
                return result
    
    # ── RULE 2: Coordinated Campaign Indicators ──
    coord_hashtag_matches = hashtags & COORD_HASHTAGS
    troll_matches = [t for t in TROLL_INDICATORS if t in text_lower]
    
    if coord_hashtag_matches or len(troll_matches) >= 2:
        result["classification"] = "DISINFO"
        result["confidence"] = "HIGH" if coord_hashtag_matches else "MEDIUM"
        result["coordination_score"] = min(1.0, (len(coord_hashtag_matches) * 0.3 + len(troll_matches) * 0.2))
        result["disinfo_subtype"] = "coordinated_campaign"
        indicators = list(coord_hashtag_matches) + troll_matches
        result["justification"] = f"Coordinated campaign indicators: {', '.join(indicators[:5])}. Matches documented troll network pattern."
        result["narrative_ids"] = group_narrative_ids or ["NAR-KE-003a"]
        _assign_families(result, "COORDINATED", weights)
        
        # Check for HS overlap
        if any(m in text_lower for m in HS_MARKERS):
            result["hs_overlap"] = True
        return result
    
    # ── RULE 3: Counter-speech / Fact-check → NOISE ──
    if any(m in text_lower for m in COUNTER_MARKERS):
        result["classification"] = "NOISE"
        result["justification"] = "Counter-speech or fact-checking content — not disinformation itself."
        return result
    
    # ── RULE 4: News Reporting → NOISE (Method A territory) ──
    news_count = sum(1 for m in NEWS_MARKERS if m in text_lower)
    if news_count >= 2:
        result["classification"] = "NOISE"
        result["justification"] = f"News reporting language detected ({news_count} markers). This is Method A territory — a report about disinfo, not the disinfo itself."
        return result
    
    # ── RULE 5: Keyword Group Specific Rules ──
    group_config = strategy.get("keyword_groups", {}).get(keyword_group, {})
    disinfo_type = group_config.get("disinfo_type", "")
    
    # Check for specific false claim patterns by group
    if keyword_group in ("AS_CASUALTY_FABRICATION", "ISS_PROPAGANDA"):
        # Look for specific casualty numbers or attack claims
        casualty_patterns = re.findall(r'\b(\d+)\s*(soldiers?|troops?|killed|dead|casualties)', text_lower)
        if casualty_patterns:
            result["classification"] = "DISINFO"
            result["confidence"] = "MEDIUM"
            result["disinfo_subtype"] = "propaganda"
            result["justification"] = f"Specific casualty claim ({casualty_patterns[0][0]} {casualty_patterns[0][1]}) in VE-associated context. Requires cross-reference against verified reports."
            result["narrative_ids"] = group_narrative_ids
            _assign_families(result, "CASUALTY_FABRICATION", weights)
            return result
    
    elif keyword_group == "SS_FABRICATED_NARRATIVES":
        # Look for fabricated South Sudan claims
        ss_disinfo_terms = ["mass grave", "genocide", "fabricated", "crush rebellion", "7 days",
                           "rescued", "defended", "liberated", "fake images", "manipulated"]
        ss_matches = [t for t in ss_disinfo_terms if t in text_lower]
        if len(ss_matches) >= 2:
            result["classification"] = "DISINFO"
            result["confidence"] = "MEDIUM"
            result["disinfo_subtype"] = "misinformation"
            result["justification"] = f"South Sudan fabricated narrative indicators: {', '.join(ss_matches[:3])}. Contains claims requiring verification."
            result["narrative_ids"] = group_narrative_ids
            _assign_families(result, "SS_FABRICATION", weights)
            return result
    
    elif keyword_group == "SOMALI_DEEPFAKES_FABRICATION":
        # Require Somalia/East Africa context — "deepfake" alone matches global content
        somali_context = any(t in text_lower for t in [
            "somalia", "somali", "puntland", "mogadishu", "faroole", "banadir",
            "clan", "election", "senator", "mp ", "politician", "minister",
            "kenya", "south sudan", "nuer", "dinka"
        ])
        deepfake_terms = ["deepfake", "fake audio", "fabricated video", "ai-generated",
                         "manipulated audio", "fake recording", "doctored"]
        df_matches = [t for t in deepfake_terms if t in text_lower]
        if df_matches and somali_context:
            result["classification"] = "DISINFO"
            result["confidence"] = "MEDIUM"
            result["disinfo_subtype"] = "deepfake"
            result["justification"] = f"Deepfake/fabricated media indicators in East Africa context: {', '.join(df_matches)}."
            result["narrative_ids"] = group_narrative_ids
            _assign_families(result, "DEEPFAKE", weights)
            return result
    
    elif keyword_group == "KE_FALSE_ETHNIC_CLAIMS":
        # Require Kenya/East Africa context for these claims
        ke_context = any(t in text_lower for t in ["kenya", "kikuyu", "gachagua", "somali", "eastleigh", "nairobi", "ruto"])
        
        # High-confidence ethnic disinfo markers (specific to Kenya)
        ethnic_disinfo_strong = ["minnesota fraud", "bbs mall", "terrorism funding eastleigh", "#43against1"]
        # Weaker markers — need Kenya context
        ethnic_disinfo_weak = ["must lead", "kikuyus must", "tribal mobilization"]
        
        strong_matches = [t for t in ethnic_disinfo_strong if t in text_lower]
        weak_matches = [t for t in ethnic_disinfo_weak if t in text_lower] if ke_context else []
        
        if strong_matches or weak_matches:
            result["classification"] = "DISINFO"
            result["confidence"] = "MEDIUM" if not strong_matches else "HIGH"
            result["disinfo_subtype"] = "misinformation"
            all_matches = strong_matches + weak_matches
            result["justification"] = f"False ethnic claim indicators: {', '.join(all_matches)}. Contains verifiably false factual assertions in Kenya context."
            result["narrative_ids"] = group_narrative_ids
            _assign_families(result, "ETHNIC_DISINFO", weights)
            return result
    
    elif keyword_group == "FOREIGN_DISINFO_OPERATIONS":
        foreign_markers = ["sputnik", "rt africa", "tass", "cgtn", "xinhua", "china daily",
                          "neo-colonialism", "western interference", "win-win"]
        foreign_matches = [t for t in foreign_markers if t in text_lower]
        if len(foreign_matches) >= 2:
            result["classification"] = "DISINFO"
            result["confidence"] = "MEDIUM"
            result["disinfo_subtype"] = "foreign_propaganda"
            result["justification"] = f"State media false framing: {', '.join(foreign_matches[:3])}."
            result["narrative_ids"] = group_narrative_ids
            _assign_families(result, "FOREIGN_INFLUENCE", weights)
            return result
    
    # ── RULE 6: Pure HS without false claims → HS_ONLY ──
    if any(m in text_lower for m in HS_MARKERS):
        result["classification"] = "HS_ONLY"
        result["justification"] = "Contains hate speech markers but no identifiable false factual claims. Route to HS database."
        return result
    
    # ── RULE 7: Single troll indicator → LOW confidence DISINFO ──
    if troll_matches:
        result["classification"] = "DISINFO"
        result["confidence"] = "LOW"
        result["disinfo_subtype"] = "coordinated_campaign"
        result["justification"] = f"Single troll network indicator: '{troll_matches[0]}'. Insufficient evidence for high confidence."
        result["narrative_ids"] = group_narrative_ids
        return result
    
    # ── DEFAULT: NOISE ──
    result["justification"] = f"No disinfo, HS, or coordination indicators detected in content from keyword group {keyword_group}."
    return result


def _assign_families(result, category, weights):
    """Assign narrative families based on content category."""
    families_map = {
        "VE_PROPAGANDA": [("Attack Claim", 3), ("Recruitment", 2)],
        "COORDINATED": [("Misinformation/Disinformation", 3), ("Delegitimization", 3)],
        "CASUALTY_FABRICATION": [("Misinformation/Disinformation", 3), ("Attack Claim", 2)],
        "SS_FABRICATION": [("Misinformation/Disinformation", 3), ("Ethnic Incitement", 2)],
        "DEEPFAKE": [("Misinformation/Disinformation", 4)],
        "ETHNIC_DISINFO": [("Ethnic Incitement", 3), ("Misinformation/Disinformation", 3)],
        "FOREIGN_INFLUENCE": [("Foreign Influence Operation", 3)]
    }
    
    families = families_map.get(category, [("Misinformation/Disinformation", 2)])
    result["narrative_families"] = [
        {"family": f, "intensity": i, "calibrated": False, 
         "calibration_note": "Auto-classified by apify_classify.py"}
        for f, i in families
    ]


# ─── Coordination Detection ──────────────────────────────────────────────────

def detect_coordination(items):
    """
    Detect coordinated campaigns across items.
    Returns groups of items that appear coordinated (copy-paste, synchronized).
    """
    # Group by near-identical text
    text_groups = defaultdict(list)
    for idx, item in enumerate(items):
        text = extract_text(item)
        if len(text) < 30:
            continue
        # Normalize: strip hashtags, links, @mentions for comparison
        normalized = re.sub(r'https?://\S+', '', text)
        normalized = re.sub(r'@\w+', '', normalized)
        normalized = re.sub(r'#\w+', '', normalized)
        normalized = re.sub(r'\s+', ' ', normalized).strip().lower()
        
        # Use first 100 chars as key (handles minor variations)
        key = normalized[:100]
        text_groups[key].append(idx)
    
    # Find groups with 2+ identical/near-identical posts
    coordinated_groups = []
    for key, indices in text_groups.items():
        if len(indices) >= 2:
            coordinated_groups.append({
                "text_key": key[:80],
                "item_indices": indices,
                "count": len(indices),
                "authors": list(set(extract_author(items[i]) for i in indices))
            })
    
    return coordinated_groups


# ─── Autolearning: Extract New Claims ─────────────────────────────────────────

# Hashtags too generic to be useful as search queries — will match noise
GARBAGE_HASHTAGS = {
    # Global generic
    "#ai", "#money", "#rich", "#fyp", "#viral", "#news", "#breaking",
    "#trending", "#follow", "#like", "#share", "#retweet", "#rt",
    # Country/region names (too broad)
    "#somalia", "#kenya", "#southsudan", "#ethiopia", "#amhara", "#tigray",
    "#africa", "#eastafrica", "#mogadishu", "#nairobi", "#juba",
    # Generic political (no disinfo signal)
    "#politics", "#government", "#election", "#democracy", "#peace",
    "#justice", "#humanrights", "#refugees", "#un", "#au",
    # Generic conflict (too broad for targeted monitoring)
    "#war", "#conflict", "#military", "#soldiers", "#army",
    "#sna", "#sspdf", "#amisom", "#atmis",
    "#alshabaab", "#shabaab", "#isis", "#iss",
    # Generic tech/media terms
    "#deepfake", "#fakenews", "#misinformation", "#disinformation",
    # Palestine/Gaza (not East Africa disinfo unless VE-linked)
    "#freepalestine", "#palestine", "#gaza", "#ceasefire",
    # Generic social media fluff
    "#bb", "#thread", "#update", "#alert", "#opinion",
    # Platform-specific
    "#tiktok", "#facebook", "#twitter", "#x",
}

# Known campaign/disinfo hashtags we ALREADY track — don't re-learn
ALREADY_TRACKED_HASHTAGS = COORD_HASHTAGS | {
    "#bbcafricaeye", "#banbbc", "#bbcpaidpropaganda",
    "#resistkikuyucolonialism", "#rejecttribalwamunyoro",
}


def _is_useful_hashtag(tag):
    """Check if a hashtag is specific enough to be a useful search query."""
    tag_lower = tag.lower().strip()
    if tag_lower in GARBAGE_HASHTAGS:
        return False
    if tag_lower in ALREADY_TRACKED_HASHTAGS:
        return False
    # Too short (e.g. #bb, #ai)
    if len(tag_lower) <= 3:
        return False
    # Must contain at least one letter (not just # + numbers)
    if not re.search(r'[a-z]', tag_lower):
        return False
    return True


def _extract_claim_phrases(text):
    """
    Extract potential false claim phrases from social media text.
    Uses multiple strategies beyond just 'X claimed that Y'.
    """
    claims = []
    
    # Strategy 1: Explicit claim language (original regex, enhanced)
    explicit = re.findall(
        r'(?:claim|said|allege|report|accuse|reveal|confirm|prove|expos|uncover|admit|confess)'
        r'\w*\s+(?:that\s+)?(.{20,120}?)(?:\.|!|$)',
        text, re.IGNORECASE
    )
    claims.extend(explicit)
    
    # Strategy 2: Numbered casualty claims ("X soldiers killed", "killed X troops")
    casualty = re.findall(
        r'(\d+[\s-]*(?:soldiers?|troops?|fighters?|militants?|civilians?)\s+'
        r'(?:killed|dead|wounded|captured|surrendered)\b.{0,60})',
        text, re.IGNORECASE
    )
    claims.extend(casualty)
    
    # Strategy 3: False attribution ("X is funded/backed/controlled by Y")
    attribution = re.findall(
        r'([\w\s]+(?:funded|backed|controlled|operated|sponsored|paid)\s+by\s+.{10,80}?)(?:\.|!|$)',
        text, re.IGNORECASE
    )
    claims.extend(attribution)
    
    # Strategy 4: Fabricated event claims ("X happened in Y", "attack on Z")
    event_claims = re.findall(
        r'((?:attack|raid|ambush|battle|massacre|bombing)\s+(?:on|in|near|at)\s+.{10,80}?)(?:\.|!|$)',
        text, re.IGNORECASE
    )
    claims.extend(event_claims)
    
    # Strategy 5: Deepfake/fabrication language
    fabrication = re.findall(
        r'((?:deepfake|fabricat|fake|doctor|manipulat|forged|staged)\w*\s+.{10,80}?)(?:\.|!|$)',
        text, re.IGNORECASE
    )
    claims.extend(fabrication)
    
    # Deduplicate and clean
    seen = set()
    cleaned = []
    for c in claims:
        c_clean = c.strip()
        if len(c_clean) >= 20 and c_clean.lower() not in seen:
            seen.add(c_clean.lower())
            cleaned.append(c_clean)
    
    return cleaned[:5]


# East Africa relevance terms — content must contain at least one to be learned
EA_RELEVANCE_TERMS = {
    # Countries/regions
    'somalia', 'somali', 'kenya', 'kenyan', 'south sudan', 'sudanese',
    'mogadishu', 'nairobi', 'juba', 'garissa', 'mombasa', 'kisumu',
    'puntland', 'somaliland', 'jubaland', 'hiiraan', 'baidoa', 'kismayo',
    # Ethnic/clan groups  
    'dinka', 'nuer', 'kikuyu', 'luo', 'kalenjin', 'hawiye', 'darod', 'dir',
    # Key actors
    'shabaab', 'al-shabaab', 'alshabaab', 'kiir', 'machar', 'ruto', 'gachagua',
    'olony', 'igad', 'amisom', 'atmis', 'sna', 'sspdf',
    # Disinfo-specific handles/campaigns
    'chaoscartel', 'shahada', 'al-kataib', 'calamada', 'somalimemo',
    'bbc africa', 'bbcafricaeye', 'bloodparliament',
}


def _is_ea_relevant(text):
    """Check if text is about East Africa — must contain at least one EA term."""
    text_lower = text.lower()
    return any(term in text_lower for term in EA_RELEVANCE_TERMS)


def extract_new_claims(classified_items, strategy):
    """
    From DISINFO-classified items, extract potential new false claims
    not yet tracked in the keyword strategy.
    
    Returns list of potential new keyword entries for the autolearning loop.
    Quality-gated: only returns claims with usable search queries.
    EA-gated: only learns from content that is demonstrably about East Africa.
    """
    existing_queries = set()
    for group in strategy.get("keyword_groups", {}).values():
        for q in group.get("queries", []):
            existing_queries.add(q.lower().strip())
    
    # Also check learned keywords
    learned = strategy.get("autolearning", {}).get("learned_keywords", {}).get("entries", [])
    for entry in learned:
        for q in entry.get("search_queries", []):
            existing_queries.add(q.lower().strip())
    
    new_claims = []
    seen_texts = set()
    
    for item_data in classified_items:
        if item_data["classification"] != "DISINFO":
            continue
        if item_data.get("confidence") == "LOW":
            continue  # Only learn from HIGH/MEDIUM confidence items
        
        text = item_data.get("text", "")
        if not text or text[:50].lower() in seen_texts:
            continue
        seen_texts.add(text[:50].lower())
        
        # EA relevance gate: skip content not about East Africa
        if not _is_ea_relevant(text):
            continue
        
        # Extract claim phrases using enhanced multi-strategy extraction
        claim_phrases = _extract_claim_phrases(text)
        
        # Extract useful hashtags (quality-gated)
        hashtags = extract_hashtags(text)
        useful_hashtags = [t for t in hashtags if _is_useful_hashtag(t)]
        
        # Check if any extracted query is actually new
        new_query_phrases = []
        for c in claim_phrases:
            cleaned = re.sub(r'[^\w\s]', '', c).strip()
            if len(cleaned) > 15 and cleaned.lower() not in existing_queries:
                new_query_phrases.append(cleaned)
        
        new_tags = [t for t in useful_hashtags 
                    if t.lower() not in existing_queries]
        
        # Quality gate: must have at least one usable new query
        if new_query_phrases or new_tags:
            new_claims.append({
                "source_text": text[:200],
                "potential_claims": new_query_phrases[:3],
                "novel_hashtags": new_tags[:3],
                "keyword_group": item_data.get("keyword_group", ""),
                "narrative_ids": item_data.get("narrative_ids", []),
                "url": item_data.get("url", ""),
                "author": item_data.get("author", "")
            })
    
    return new_claims


# ─── Handle Discovery ────────────────────────────────────────────────────────

def discover_new_handles(classified_items, watchlist):
    """
    From classified items, identify new handles/accounts worth monitoring.
    Only DISINFO-classified items with HIGH or MEDIUM confidence qualify.
    """
    # Get existing watchlist handles — nested structure:
    # watchlist.hs_disinfo_sources.ve_propaganda_producers[] and .hs_disinfo_producers[]
    existing_handles = set()
    hs_sources = watchlist.get("hs_disinfo_sources", {})
    for section_key in ["ve_propaganda_producers", "hs_disinfo_producers"]:
        sources_list = hs_sources.get(section_key, [])
        if isinstance(sources_list, list):
            for source in sources_list:
                if isinstance(source, dict):
                    name = source.get("name") or ""
                    url = source.get("url") or ""
                    existing_handles.add(name.lower())
                    if url:
                        existing_handles.add(url.lower())
    
    author_counts = Counter()
    author_items = defaultdict(list)
    
    for item_data in classified_items:
        if item_data["classification"] != "DISINFO":
            continue
        if item_data["confidence"] not in ("HIGH", "MEDIUM"):
            continue
        
        author = item_data.get("author", "Unknown")
        if author.lower() in existing_handles or author == "Unknown":
            continue
        
        author_counts[author] += 1
        author_items[author].append(item_data)
    
    # Authors with 2+ disinfo posts are good discovery candidates
    discoveries = []
    for author, count in author_counts.most_common(10):
        if count >= 2:
            sample_item = author_items[author][0]
            discoveries.append({
                "handle": author,
                "platform": sample_item.get("platform", "Unknown"),
                "url": sample_item.get("url", ""),
                "type": "HS_DISINFO",
                "country": _infer_country(sample_item),
                "reason": f"Posted {count} classified disinfo items in single sweep. Groups: {', '.join(set(i.get('keyword_group','') for i in author_items[author]))}",
                "proposed_source_basis": "pattern_observed",
                "proposed_confidence_floor": "MEDIUM",
                "discovery_strategy": "D_FOLLOW_PLATFORMS"
            })
    
    return discoveries


def _infer_country(item_data):
    """Infer country from keyword group or content."""
    kg = item_data.get("keyword_group", "")
    if "KE_" in kg or "kenya" in kg.lower():
        return "Kenya"
    elif "SS_" in kg or "south_sudan" in kg.lower():
        return "South Sudan"
    elif "AS_" in kg or "ISS_" in kg or "SOMALI" in kg:
        return "Somalia"
    return "Regional"


# ─── Build Timeline Events ───────────────────────────────────────────────────

def build_timeline_events(classified_items, coordination_groups):
    """
    Group classified DISINFO items into timeline events.
    
    Strategy:
    1. Text-identical coordination groups → single campaign event
    2. Hashtag-based coordination (same coord hashtags, same keyword group) → single campaign event
    3. Remaining items grouped by keyword_group → one event per group
    
    This prevents 50 individual troll posts from becoming 50 timeline entries.
    """
    events = []
    used_indices = set()
    now = datetime.now(timezone.utc)
    
    # 1. Text-identical coordination groups first
    for cg in coordination_groups:
        if len(cg["item_indices"]) < 2:
            continue
        
        campaign_items = [classified_items[i] for i in cg["item_indices"]
                         if i < len(classified_items)]
        
        disinfo_items = [ci for ci in campaign_items if ci["classification"] == "DISINFO"]
        if not disinfo_items:
            continue
        
        used_indices.update(cg["item_indices"])
        
        best_confidence = "HIGH" if any(ci["confidence"] == "HIGH" for ci in disinfo_items) else "MEDIUM"
        
        event = _build_event(
            items=disinfo_items,
            headline_prefix="Coordinated copy-paste campaign:",
            is_coordinated=True,
            confidence=best_confidence,
            now=now
        )
        if event:
            events.append(event)
    
    # 2. Group remaining DISINFO items by keyword_group (combines coordinated + individual)
    #    This ensures a troll campaign of 48 posts becomes 1 event, not 48
    group_buckets = defaultdict(list)
    for idx, ci in enumerate(classified_items):
        if idx in used_indices:
            continue
        if ci["classification"] != "DISINFO":
            continue
        if ci["confidence"] not in ("HIGH", "MEDIUM"):
            continue
        used_indices.add(idx)
        group_buckets[ci.get("keyword_group", "UNKNOWN")].append(ci)
    
    for group_name, group_items in group_buckets.items():
        if not group_items:
            continue
        
        best_confidence = "HIGH" if any(ci["confidence"] == "HIGH" for ci in group_items) else "MEDIUM"
        is_coord = len(group_items) >= 3  # 3+ posts in same keyword group = likely coordinated
        
        prefix = "Coordinated campaign:" if is_coord else f"{group_name}:"
        event = _build_event(
            items=group_items,
            headline_prefix=prefix,
            is_coordinated=is_coord,
            confidence=best_confidence,
            now=now
        )
        if event:
            events.append(event)
    
    return events


# ─── Keyword group context for content-focused headline generation ────────────
# Maps keyword_group to disinfo context used to produce analyst-quality headlines.
# Each entry describes WHAT kind of false claims the group tracks.
KEYWORD_GROUP_CONTEXT = {
    "AS_CASUALTY_FABRICATION": {
        "theme": "fabricated military casualty claims",
        "country": "Somalia",
        "actor_type": "al-Shabaab media outlets",
        "claim_type": "inflated/fabricated casualty numbers from military operations"
    },
    "AS_GOVERNANCE_PROPAGANDA": {
        "theme": "al-Shabaab governance propaganda",
        "country": "Somalia",
        "actor_type": "al-Shabaab-linked accounts",
        "claim_type": "false framing of al-Shabaab as legitimate governance, federal government as collapsed"
    },
    "AS_GAZA_RECRUITMENT": {
        "theme": "Gaza instrumentalization for recruitment",
        "country": "Somalia",
        "actor_type": "al-Shabaab/AQ-affiliated accounts",
        "claim_type": "false framing of AQ/AS as defenders of Palestine, recruitment propaganda"
    },
    "ISS_PROPAGANDA": {
        "theme": "ISIS-Somalia fabricated victory claims",
        "country": "Somalia",
        "actor_type": "ISS media outlets",
        "claim_type": "fabricated territorial gains, inflated casualty numbers, caliphate propaganda"
    },
    "SOMALI_DEEPFAKES_FABRICATION": {
        "theme": "fabricated audio/video attributed to Somali politicians",
        "country": "Somalia",
        "actor_type": "disinformation operators",
        "claim_type": "deepfakes, fabricated recordings, manufactured clan conflict triggers"
    },
    "SOMALILAND_FALSE_CLAIMS": {
        "theme": "fabricated claims about Somaliland recognition",
        "country": "Somalia",
        "actor_type": "disinformation accounts",
        "claim_type": "fake diplomatic recognition claims, fabricated official statements, partition conspiracies"
    },
    "SS_FABRICATED_NARRATIVES": {
        "theme": "fabricated military narratives in South Sudan conflict",
        "country": "South Sudan",
        "actor_type": "conflict-aligned accounts",
        "claim_type": "fabricated casualty claims, staged images, false atrocity attribution"
    },
    "SS_MACHAR_FABRICATION": {
        "theme": "fabricated claims about Machar trial",
        "country": "South Sudan",
        "actor_type": "political operatives",
        "claim_type": "fabricated trial evidence, false legal process claims, manufactured political narratives"
    },
    "KE_COORDINATED_DISINFO": {
        "theme": "coordinated troll campaigns targeting Kenyan activists and opposition",
        "country": "Kenya",
        "actor_type": "coordinated troll network",
        "claim_type": "false accusations (foreign funding, self-abduction), AI-generated smear content"
    },
    "KE_FALSE_ETHNIC_CLAIMS": {
        "theme": "fabricated ethnic/tribal claims in Kenya",
        "country": "Kenya",
        "actor_type": "ethno-nationalist accounts",
        "claim_type": "false ethnic stereotyping, fabricated crime statistics, manufactured tribal grievances"
    },
    "FOREIGN_DISINFO_OPERATIONS": {
        "theme": "foreign state media disinformation targeting East Africa",
        "country": "Regional",
        "actor_type": "state-affiliated media",
        "claim_type": "false framing of Western engagement, manufactured anti-democratic narratives"
    },
    "KE_MONEY_LAUNDERING_DISINFO": {
        "theme": "fabricated money laundering accusations in Kenya",
        "country": "Kenya",
        "actor_type": "political operatives",
        "claim_type": "false financial crime accusations against political opponents"
    }
}


def _extract_key_claims(items):
    """Extract the core false claims from post texts for headline/summary generation.
    
    PRIORITY: Find the actual disinformation CONTENT — what false claims are being
    pushed, what specific lies are being told. The headline/summary must describe
    the disinformation itself, not the detection process.
    
    Returns dict with: claims, hashtags, key_phrases, sample_quote, best_content_excerpt
    """
    all_texts = [i.get("text", "") for i in items if i.get("text")]
    if not all_texts:
        return {"claims": [], "hashtags": set(), "key_phrases": [], "sample_quote": "", "best_content_excerpt": ""}
    
    all_hashtags = set()
    for text in all_texts:
        all_hashtags.update(re.findall(r'#\w+', text))
    
    # Remove generic/platform hashtags, keep content-relevant ones
    generic_tags = {"#breaking", "#news", "#africa", "#trending", "#viral", "#thread"}
    content_hashtags = all_hashtags - generic_tags
    
    # Extract specific claims: look for numbers + context (casualty claims, dates, etc.)
    claims = []
    for text in all_texts[:5]:
        text_lower = text.lower()
        # Casualty/number claims
        number_claims = re.findall(r'(\d+[\+]?\s*(?:soldiers?|troops?|killed|dead|casualties|wounded|captured|arrested|civilians?))', text_lower)
        if number_claims:
            claims.extend(number_claims[:2])
        # "X is Y" type false framing claims
        framing_claims = re.findall(r'(?:is a |are |was |were |have been )(?:spy|agent|terrorist|traitor|foreign.?funded|paid|puppet)', text_lower)
        if framing_claims:
            claims.extend(framing_claims[:2])
    
    # Find the BEST content excerpt — the most substantive post that represents
    # the actual disinfo claim. Prefer posts with East Africa context AND original text.
    ea_context_terms = ["kenya", "somali", "south sudan", "nuer", "dinka", "kikuyu",
                        "nairobi", "mogadishu", "juba", "gachagua", "ruto", "bbc",
                        "activist", "protest", "al-shabaab", "shabaab", "olony",
                        "machar", "puntland", "amisom", "clan", "tribe"]
    
    # Score each post: substantial text + EA relevance
    scored_texts = []
    for text in all_texts:
        cleaned = re.sub(r'https?://\S+', '', text)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        non_meta = re.sub(r'[@#]\w+', '', cleaned).strip()
        
        score = 0
        if len(non_meta) > 30:
            score += 10  # Has substantial text
        score += min(len(non_meta), 200) / 20  # Length bonus (up to 10)
        # East Africa relevance bonus
        text_lower = text.lower()
        ea_matches = sum(1 for t in ea_context_terms if t in text_lower)
        score += ea_matches * 5  # Strong bonus for EA context
        
        scored_texts.append((score, non_meta, cleaned))
    
    scored_texts.sort(key=lambda x: -x[0])
    
    best_content_excerpt = ""
    best_quote = ""
    for score, non_meta, cleaned in scored_texts[:3]:
        if len(non_meta) > 30:
            best_content_excerpt = non_meta[:250]
            best_quote = cleaned[:200]
            break
    
    # Fallback: even if mostly hashtags, pick highest scored
    if not best_quote and scored_texts:
        _, non_meta, cleaned = scored_texts[0]
        if len(cleaned) > 20:
            best_content_excerpt = non_meta[:250] if non_meta else cleaned[:250]
            best_quote = cleaned[:200]
    
    # Extract key phrases: words/phrases that appear in multiple posts (campaign messaging)
    key_phrases = []
    if len(all_texts) >= 3:
        from collections import Counter as PhraseCounter
        word_freq = PhraseCounter()
        for text in all_texts:
            words = set(text.lower().split())
            stopwords = {"the", "is", "at", "in", "on", "a", "an", "and", "or", "of", "to", "for", "rt", "via"}
            words = {w for w in words if len(w) > 3 and w not in stopwords and not w.startswith("http") and not w.startswith("@")}
            word_freq.update(words)
        threshold = max(2, len(all_texts) * 0.4)
        key_phrases = [word for word, count in word_freq.most_common(10) if count >= threshold]
    
    return {
        "claims": list(set(claims))[:5],
        "hashtags": content_hashtags,
        "key_phrases": key_phrases[:8],
        "sample_quote": best_quote,
        "best_content_excerpt": best_content_excerpt
    }


def _build_content_headline(items, keyword_group, is_coordinated, content_analysis):
    """Generate a headline that describes the actual FALSE CLAIMS being spread.
    
    Headline MUST describe the disinformation content itself. Not the campaign mechanics.
    
    GOOD: 'Claims BBC Africa Eye is a foreign intelligence operation to destabilize Kenya'
    GOOD: 'False claim: 47 SNA soldiers killed in al-Shabaab ambush near Halgan'
    BAD:  'Coordinated push of fabricated military casualty claims across 11 posts'
    BAD:  '#ChaosCartel campaign pushes coordinated troll campaigns'
    """
    group_ctx = KEYWORD_GROUP_CONTEXT.get(keyword_group, {})
    
    hashtags = content_analysis.get("hashtags", set())
    claims = content_analysis.get("claims", [])
    excerpt = content_analysis.get("best_content_excerpt", "")
    sample = content_analysis.get("sample_quote", "")
    
    # Find campaign hashtags if present
    campaign_hashtags = hashtags & {h.lower() for h in COORD_HASHTAGS} if hashtags else set()
    if not campaign_hashtags:
        campaign_hashtags = {h for h in hashtags if h.lower().lstrip('#') in 
                           {t.lstrip('#') for t in COORD_HASHTAGS}}
    tag_prefix = ', '.join(sorted(campaign_hashtags)[:2]) + ': ' if campaign_hashtags else ''
    
    # Priority 1: Use the best content excerpt to describe what's ACTUALLY being said
    if excerpt and len(excerpt) > 30:
        # Trim to headline length
        headline_text = excerpt[:120]
        if len(excerpt) > 120:
            # Cut at last word boundary
            headline_text = headline_text[:headline_text.rfind(' ')] if ' ' in headline_text[80:] else headline_text
        return f"{tag_prefix}{headline_text}"
    
    # Priority 2: Use extracted claims with context
    if claims:
        claim_text = claims[0]
        if keyword_group and keyword_group.startswith("AS_"):
            return f"{tag_prefix}False claim: {claim_text} attributed to al-Shabaab sources"
        elif keyword_group and keyword_group.startswith("ISS_"):
            return f"{tag_prefix}ISIS-Somalia media claims {claim_text}"
        elif keyword_group and keyword_group.startswith("SS_"):
            return f"{tag_prefix}False claim in South Sudan: {claim_text}"
        elif keyword_group and keyword_group.startswith("KE_"):
            return f"{tag_prefix}False claim: {claim_text}"
        return f"{tag_prefix}False claim: {claim_text}"
    
    # Priority 3: Use sample quote directly (truncated)
    if sample and len(sample) > 30:
        headline_text = sample[:120]
        if len(sample) > 120:
            headline_text = headline_text[:headline_text.rfind(' ')] if ' ' in headline_text[80:] else headline_text
        return f"{tag_prefix}{headline_text}"
    
    # Last resort: generic (should rarely happen with real data)
    theme = group_ctx.get("theme", "disinformation")
    return f"{tag_prefix}{theme.capitalize()}"


def _build_content_summary(items, keyword_group, is_coordinated, content_analysis):
    """Generate a summary that describes the actual disinformation content.
    
    Summary structure:
    1. LEAD: The actual content — what posts say, what claims they make
    2. SCALE: How many posts/accounts, coordination note if applicable
    3. KEY HASHTAGS: Campaign hashtags if present (brief)
    
    The summary must read like a description of what is being said online,
    NOT like a detection report.
    
    GOOD: 'Posts claim BBC Africa Eye documentary is a \"hit job\" funded by foreign
           interests to destabilize Kenya. The narrative frames activists as foreign
           agents. 8 near-identical posts from 7 accounts suggest coordinated amplification.'
    BAD:  'Posts on X spread false accusations. The posts use hashtags #ChaosCartel,
           #June25th. The campaign shows coordination indicators: 8 posts from 7 accounts.'
    """
    group_ctx = KEYWORD_GROUP_CONTEXT.get(keyword_group, {})
    
    excerpt = content_analysis.get("best_content_excerpt", "")
    sample_quote = content_analysis.get("sample_quote", "")
    claims = content_analysis.get("claims", [])
    hashtags = content_analysis.get("hashtags", set())
    n_items = len(items)
    
    platform_set = list(set(i.get("platform", "Unknown") for i in items))
    authors_set = list(set(i.get("author", "Unknown") for i in items))
    
    parts = []
    
    # 1. LEAD — the actual content
    if excerpt and len(excerpt) > 30:
        # Use the excerpt as the opening — this IS the disinformation
        parts.append(f"{excerpt.rstrip('.')}.") 
    elif sample_quote and len(sample_quote) > 30:
        parts.append(f"{sample_quote.rstrip('.')}.") 
    else:
        claim_type = group_ctx.get("claim_type", "false claims")
        parts.append(f"Posts on {', '.join(platform_set)} push {claim_type}.")
    
    # 2. SCALE NOTE — brief, secondary
    if is_coordinated and n_items >= 3:
        parts.append(f"{n_items} near-identical posts from {len(authors_set)} accounts suggest coordinated amplification.")
    elif n_items >= 2:
        parts.append(f"Observed across {n_items} posts from {len(authors_set)} accounts on {', '.join(platform_set)}.")
    
    # 3. KEY HASHTAGS — brief, only campaign-relevant ones
    campaign_tags = {h for h in hashtags if h.lower().lstrip('#') in 
                    {t.lstrip('#') for t in COORD_HASHTAGS}}
    if campaign_tags:
        parts.append(f"Campaign hashtags: {', '.join(sorted(campaign_tags)[:3])}.")
    
    return " ".join(parts)


def _build_event(items, headline_prefix, is_coordinated, confidence, now):
    """Build a single timeline event from classified items.
    
    Events describe the DISINFORMATION CONTENT — what false claims are being spread,
    who is targeted, and what narrative family it belongs to. Detection methodology
    and coordination details are secondary metadata, not the headline.
    """
    if not items:
        return None
    
    # Determine country
    countries = [_infer_country(i) for i in items]
    country_counts = Counter(countries)
    primary_country = country_counts.most_common(1)[0][0]
    
    # Collect all narrative IDs
    all_narrative_ids = []
    for item in items:
        all_narrative_ids.extend(item.get("narrative_ids", []))
    all_narrative_ids = list(set(all_narrative_ids))
    
    # Collect narrative families
    all_families = []
    seen_families = set()
    for item in items:
        for fam in item.get("narrative_families", []):
            fname = fam.get("family", "")
            if fname not in seen_families:
                seen_families.add(fname)
                all_families.append(fam)
    
    # ── Content analysis: extract what false claims are being pushed ──
    keyword_group = items[0].get("keyword_group", "UNKNOWN")
    content_analysis = _extract_key_claims(items)
    
    # ── Generate content-focused headline and summary ──
    headline = _build_content_headline(items, keyword_group, is_coordinated, content_analysis)
    summary = _build_content_summary(items, keyword_group, is_coordinated, content_analysis)
    
    # Justification from classifier
    justification = items[0].get("justification", "Classified via content pattern analysis")
    
    # Determine threat level
    if confidence == "HIGH" and is_coordinated:
        threat_level = "P2 HIGH"
    elif confidence == "HIGH":
        threat_level = "P2 HIGH"
    else:
        threat_level = "P3 MODERATE"
    
    # Determine event type — platform UI uses DISINFO vs CONTEXT only
    # VE propaganda info is stored in ve_related field
    is_ve = any(i.get("is_ve_propaganda") for i in items)
    event_type = "DISINFO"  # Apify sweep items are always disinfo (that's the whole point)
    
    # Collect actor and platform info
    platform_set = list(set(i.get("platform", "Unknown") for i in items))
    authors_set = list(set(i.get("author", "Unknown") for i in items))
    
    event_id = f"APF-{now.strftime('%Y-%m-%d')}-{abs(hash(headline)) % 1000:03d}"
    
    event = {
        "id": event_id,
        "date": items[0].get("date", now.strftime("%Y-%m-%d")),
        "country": primary_country,
        "event_type": event_type,
        "disinfo_subtype": items[0].get("disinfo_subtype"),
        "threat_level": threat_level,
        "headline": headline[:200],
        "summary": summary,
        "actors": authors_set[:10],
        "platforms": platform_set,
        "sources": [
            {"publisher": "MERLx Social Media Monitoring — Direct content observation",
             "url": items[0].get("url", ""),
             "date": now.strftime("%Y-%m-%d")}
        ],
        "spread": min(5, len(items)),
        "disinfo_narratives": all_narrative_ids,
        "related_events": [],
        "disinfo_confidence": confidence,
        "disinfo_justification": justification,
        "detection_method": "direct_tracking",
        "content_observed": True,
        "source_basis": "pattern_observed",
        "verification_status": "confirmed" if confidence == "HIGH" else "pattern_match",
        "narrative_families": all_families,
        "ve_related": is_ve,
        "al_shabaab_related": any("AS_" in (i.get("keyword_group", "") or "") for i in items),
        "tags": ["auto_classified"],
        "data_source": "social_media_monitoring",
        "detected_by": f"brace4peace_classify_{now.strftime('%Y-%m-%d')}",
        "detection_timestamp": now.isoformat()
    }
    
    return event


# ─── Main Pipeline ────────────────────────────────────────────────────────────

def run_classification(items_file=None, dry_run=False):
    """
    Main pipeline: load items → classify → detect coordination → build events → write output.
    
    Returns dict with results summary for the monitoring cron to use.
    """
    strategy, narratives, weights, watchlist = load_config()
    now = datetime.now(timezone.utc)
    
    # Find latest items file if not specified
    if items_file is None:
        items_files = sorted(RESULTS_DIR.glob("items_*.json"), reverse=True)
        if not items_files:
            return {"error": "No items files found", "events_added": 0}
        items_file = items_files[0]
    else:
        items_file = Path(items_file)
    
    print(f"📂 Loading items from: {items_file}")
    with open(items_file) as f:
        raw_items = json.load(f)
    
    print(f"📊 {len(raw_items)} raw items to classify")
    
    # Classify each item
    classified = []
    for item in raw_items:
        result = classify_item(item, strategy, narratives, weights)
        result["text"] = extract_text(item)
        result["url"] = extract_url(item)
        result["author"] = extract_author(item)
        result["date"] = extract_date(item)
        result["platform"] = extract_platform(item)
        result["keyword_group"] = item.get("_brace4peace", {}).get("keyword_group", "")
        classified.append(result)
    
    # Count classifications
    counts = Counter(c["classification"] for c in classified)
    confidence_counts = Counter(c["confidence"] for c in classified if c["classification"] == "DISINFO")
    
    print(f"\n📋 Classification Results:")
    print(f"   DISINFO: {counts.get('DISINFO', 0)} (HIGH: {confidence_counts.get('HIGH', 0)}, MEDIUM: {confidence_counts.get('MEDIUM', 0)}, LOW: {confidence_counts.get('LOW', 0)})")
    print(f"   HS_ONLY: {counts.get('HS_ONLY', 0)}")
    print(f"   NOISE:   {counts.get('NOISE', 0)}")
    
    # Detect coordination
    coordination_groups = detect_coordination(raw_items)
    if coordination_groups:
        print(f"\n🔗 Coordination Detected: {len(coordination_groups)} group(s)")
        for cg in coordination_groups:
            print(f"   - {cg['count']} posts by {', '.join(cg['authors'][:3])}")
    
    # Build timeline events (only HIGH and MEDIUM)
    timeline_events = build_timeline_events(classified, coordination_groups)
    print(f"\n📅 Timeline events to add: {len(timeline_events)}")
    
    # Extract new claims for autolearning
    new_claims = extract_new_claims(classified, strategy)
    print(f"🧠 New claims for autolearning: {len(new_claims)}")
    
    # Discover new handles
    new_handles = discover_new_handles(classified, watchlist)
    print(f"🔍 New handles discovered: {len(new_handles)}")
    
    if dry_run:
        print("\n[DRY RUN] Skipping writes.")
        return {
            "events_added": 0,
            "classified_count": len(classified),
            "disinfo_count": counts.get("DISINFO", 0),
            "hs_only_count": counts.get("HS_ONLY", 0),
            "noise_count": counts.get("NOISE", 0),
            "coordination_groups": len(coordination_groups),
            "new_claims": len(new_claims),
            "new_handles": len(new_handles),
            "timeline_events": timeline_events,
            "handle_discoveries": new_handles,
            "claim_discoveries": new_claims
        }
    
    # Write timeline events (HIGH and MEDIUM confidence only)
    # DEDUPLICATION: check existing events to avoid re-creating events for ongoing campaigns
    events_added = 0
    events_merged = 0
    if timeline_events:
        with open(TIMELINE_PATH) as f:
            timeline = json.load(f)
        
        with open(EVENTS_PATH) as f:
            events_json = json.load(f)
        
        # Build index of existing events for dedup matching
        # Match on: same keyword_group + overlapping actors within last 7 days
        from datetime import timedelta
        recent_cutoff = (now - timedelta(days=7)).strftime("%Y-%m-%d")
        
        existing_by_group = defaultdict(list)
        for e in events_json:
            # Index by keyword_group tag or by headline keywords
            e_date = e.get("date", "")
            if e_date >= recent_cutoff:
                # Try to determine keyword group from tags or data_source
                e_tags = set(e.get("tags", []))
                e_headline = e.get("headline", "").lower()
                e_actors = set(e.get("actors", []))
                existing_by_group["_recent"].append({
                    "id": e.get("id"),
                    "headline": e_headline,
                    "actors": e_actors,
                    "hashtags": set(re.findall(r'#\w+', e_headline)),
                    "event": e
                })
        
        for event in timeline_events:
            if event["disinfo_confidence"] not in ("HIGH", "MEDIUM"):
                continue
            
            # Check for duplicate/overlap with recent existing events
            new_headline = event["headline"].lower()
            new_actors = set(event.get("actors", []))
            new_hashtags = set(re.findall(r'#\w+', new_headline))
            is_duplicate = False
            
            for existing in existing_by_group.get("_recent", []):
                # Match 1: Significant hashtag overlap (campaign hashtags)
                if new_hashtags and existing["hashtags"]:
                    common_tags = new_hashtags & existing["hashtags"]
                    if len(common_tags) >= 1 and any(t.lower() in {
                        '#bbcforchaos', '#bloodparliament', '#dogsofwar',
                        '#chaoscartel', '#toxicactivists', '#43against1',
                        '#527bloggers'
                    } for t in common_tags):
                        # Same campaign — merge actors into existing event
                        existing_event = existing["event"]
                        merged_actors = set(existing_event.get("actors", [])) | new_actors
                        existing_event["actors"] = sorted(merged_actors)
                        is_duplicate = True
                        events_merged += 1
                        print(f"   🔄 Merged into existing {existing['id']}: {event['headline'][:60]}")
                        break
                
                # Match 2: Very similar headline (>60% word overlap)
                new_words = set(new_headline.split())
                exist_words = set(existing["headline"].split())
                if new_words and exist_words:
                    overlap = len(new_words & exist_words) / max(len(new_words), len(exist_words))
                    if overlap > 0.6:
                        existing_event = existing["event"]
                        merged_actors = set(existing_event.get("actors", [])) | new_actors
                        existing_event["actors"] = sorted(merged_actors)
                        is_duplicate = True
                        events_merged += 1
                        print(f"   🔄 Merged into existing {existing['id']}: {event['headline'][:60]}")
                        break
            
            if not is_duplicate:
                timeline.append(event)
                events_json.append(event)
                events_added += 1
                print(f"   ✅ Added: {event['headline'][:80]}")
        
        with open(TIMELINE_PATH, 'w') as f:
            json.dump(timeline, f, indent=2)
        
        with open(EVENTS_PATH, 'w') as f:
            json.dump(events_json, f, indent=2)
        
        if events_merged:
            print(f"\n🔄 {events_merged} events merged into existing entries")
        print(f"✅ {events_added} new events added to timeline + events.json")
    
    # Return results for cron integration
    return {
        "events_added": events_added,
        "classified_count": len(classified),
        "disinfo_count": counts.get("DISINFO", 0),
        "hs_only_count": counts.get("HS_ONLY", 0),
        "noise_count": counts.get("NOISE", 0),
        "high_confidence_count": confidence_counts.get("HIGH", 0),
        "medium_confidence_count": confidence_counts.get("MEDIUM", 0),
        "low_confidence_count": confidence_counts.get("LOW", 0),
        "coordination_groups": len(coordination_groups),
        "new_claims": new_claims,
        "new_handles": new_handles,
        "timeline_events": timeline_events,
        "items_file": str(items_file)
    }


# ─── Autolearning: Write Updates ──────────────────────────────────────────────

def update_autolearning(new_claims, strategy_path=STRATEGY_PATH):
    """
    Write new claims to the autolearning section of the keyword strategy.
    Called after classification when new claims are discovered.
    
    Quality gates applied:
    - Only claims with usable search queries (already filtered by extract_new_claims)
    - Dedup against existing learned keywords
    - Max 5 new entries per run
    - Max 50 total learned keywords
    """
    if not new_claims:
        return 0
    
    with open(strategy_path) as f:
        strategy = json.load(f)
    
    learned = strategy.get("autolearning", {}).get("learned_keywords", {}).get("entries", [])
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    added = 0
    
    # Build set of existing queries for dedup
    existing_queries = set()
    for entry in learned:
        for q in entry.get("search_queries", []):
            existing_queries.add(q.lower().strip())
    
    for claim in new_claims[:5]:  # Max 5 new claims per run
        # Skip if we already have too many
        if len(learned) >= 50:
            break
        
        # EA relevance double-check (belt and suspenders)
        source_text = claim.get("source_text", "")
        if source_text and not _is_ea_relevant(source_text):
            print(f"   ⛔ Skipped non-EA claim: {source_text[:60]}...")
            continue
        
        # Build search queries from pre-extracted claim phrases and hashtags
        search_queries = []
        
        for potential_claim in claim.get("potential_claims", [])[:2]:
            cleaned = re.sub(r'[^\w\s]', '', potential_claim).strip()
            # Min 15 chars, max 50 chars — longer phrases are too specific to ever hit
            if 15 < len(cleaned) <= 50:
                query = f'"{cleaned}"'
                if query.lower() not in existing_queries:
                    search_queries.append(query)
            elif len(cleaned) > 50:
                # Truncate to first meaningful phrase (up to 50 chars)
                truncated = cleaned[:50].rsplit(' ', 1)[0].strip()
                if len(truncated) > 15:
                    query = f'"{truncated}"'
                    if query.lower() not in existing_queries:
                        search_queries.append(query)
        
        for hashtag in claim.get("novel_hashtags", [])[:2]:
            # Double-check against garbage filter (belt and suspenders)
            if _is_useful_hashtag(hashtag) and hashtag.lower() not in existing_queries:
                search_queries.append(hashtag)
        
        # Quality gate: skip if no usable queries survived
        if not search_queries:
            continue
        
        entry = {
            "claim_text": claim.get("source_text", "")[:200],
            "search_queries": search_queries,
            "narrative_id": claim.get("narrative_ids", ["UNKNOWN"])[0] if claim.get("narrative_ids") else "UNKNOWN",
            "source_run_id": f"apify_classify_{now}",
            "date_added": now,
            "keyword_group": claim.get("keyword_group", "UNKNOWN"),
            "language": "en",
            "performance": {
                "rotations_run": 0,
                "hits": 0,
                "last_hit": None,
                "status": "active"
            }
        }
        
        learned.append(entry)
        existing_queries.update(q.lower() for q in search_queries)
        added += 1
        print(f"   🧠 Learned: {search_queries} → {claim.get('keyword_group', '?')}")
    
    # Write back
    strategy["autolearning"]["learned_keywords"]["entries"] = learned
    
    with open(strategy_path, 'w') as f:
        json.dump(strategy, f, indent=2)
    
    print(f"🧠 Autolearning: {added} new claim keywords added (total: {len(learned)})")
    return added


# ─── CLI Entry Point ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="BRACE4PEACE Apify Auto-Classification")
    parser.add_argument("--input", type=str, help="Path to items JSON file")
    parser.add_argument("--dry-run", action="store_true", help="Classify without writing")
    args = parser.parse_args()
    
    print("=" * 60)
    print("🤖 BRACE4PEACE Auto-Classification Pipeline")
    print("=" * 60)
    
    results = run_classification(items_file=args.input, dry_run=args.dry_run)
    
    # Run autolearning update
    if not args.dry_run and results.get("new_claims"):
        update_autolearning(results["new_claims"])
    
    print(f"\n{'=' * 60}")
    print(f"✅ Classification complete")
    print(f"   Items classified: {results.get('classified_count', 0)}")
    print(f"   DISINFO: {results.get('disinfo_count', 0)}")
    print(f"   Events added to timeline: {results.get('events_added', 0)}")
    print(f"{'=' * 60}")
