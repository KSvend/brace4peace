#!/usr/bin/env python3
"""
ML classification via HuggingFace Inference API.

Classifies hate speech posts using remote HF models (no local inference).
Pure stdlib — no pip dependencies required.

Models used:
  1. KSvendsen/EA-HS — primary 3-class hate speech classifier
  2. textdetox/bert-multilingual-toxicity-classifier — toxicity scoring
  3. facebook/bart-large-mnli — zero-shot subtopic classification
  4. Country-specific models (Kenya, Somalia, South Sudan)
"""

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
HS_DATA_PATH = REPO_ROOT / "docs" / "data" / "hate_speech_posts.json"

# ---------------------------------------------------------------------------
# HuggingFace Inference API
# ---------------------------------------------------------------------------
HF_API_BASE = "https://api-inference.huggingface.co/models"

MODELS = {
    "ea_hs": "KSvendsen/EA-HS",
    "toxicity": "textdetox/bert-multilingual-toxicity-classifier",
    "zero_shot": "facebook/bart-large-mnli",
    # Country-specific
    "kenya": "datavaluepeople/Polarization-Kenya",
    "somalia": "datavaluepeople/Afxumo-toxicity-somaliland-SO",
    "south_sudan": "datavaluepeople/Hate-Speech-Sudan-v2",
}

COUNTRY_MODEL_MAP = {
    "Kenya": "kenya",
    "Somalia": "somalia",
    "South Sudan": "south_sudan",
}

# ---------------------------------------------------------------------------
# Subtopic labels (zero-shot candidate labels)
# ---------------------------------------------------------------------------
SUBTOPIC_CANDIDATES = [
    "ethnic hatred and tribal targeting",
    "clan-based discrimination and hierarchy",
    "anti-foreign sentiment and xenophobia",
    "religious incitement and sectarian hatred",
    "racial slurs and dehumanization",
    "gendered violence and misogynistic hate",
    "political incitement and threats",
    "diaspora stigma and refugee targeting",
    "militarization and armed group glorification",
    "disinformation and conspiracy theories",
]

SUBTOPIC_DISPLAY = {
    "ethnic hatred and tribal targeting": "Ethnic Targeting",
    "clan-based discrimination and hierarchy": "Clan Targeting",
    "anti-foreign sentiment and xenophobia": "Anti-Foreign",
    "religious incitement and sectarian hatred": "Religious Incitement",
    "racial slurs and dehumanization": "Dehumanisation",
    "gendered violence and misogynistic hate": "Gendered Violence",
    "political incitement and threats": "Political Incitement",
    "diaspora stigma and refugee targeting": "Diaspora Stigma",
    "militarization and armed group glorification": "Militarisation",
    "disinformation and conspiracy theories": "Disinfo/Conspiracy",
}

# Toxicity-dimension profiles per subtopic: (sev, ins, idt, thr)
# Base scores scaled by confidence at classification time.
SUBTOPIC_TXD_PROFILES = {
    "ethnic hatred and tribal targeting":           {"sev": 0.8, "ins": 0.7, "idt": 0.9, "thr": 0.5},
    "clan-based discrimination and hierarchy":      {"sev": 0.7, "ins": 0.6, "idt": 0.9, "thr": 0.4},
    "anti-foreign sentiment and xenophobia":        {"sev": 0.7, "ins": 0.8, "idt": 0.8, "thr": 0.5},
    "religious incitement and sectarian hatred":     {"sev": 0.8, "ins": 0.8, "idt": 0.7, "thr": 0.7},
    "racial slurs and dehumanization":              {"sev": 0.9, "ins": 0.9, "idt": 0.8, "thr": 0.4},
    "gendered violence and misogynistic hate":      {"sev": 0.8, "ins": 0.8, "idt": 0.6, "thr": 0.7},
    "political incitement and threats":             {"sev": 0.7, "ins": 0.6, "idt": 0.5, "thr": 0.9},
    "diaspora stigma and refugee targeting":        {"sev": 0.6, "ins": 0.7, "idt": 0.8, "thr": 0.4},
    "militarization and armed group glorification": {"sev": 0.8, "ins": 0.5, "idt": 0.5, "thr": 0.9},
    "disinformation and conspiracy theories":       {"sev": 0.6, "ins": 0.7, "idt": 0.6, "thr": 0.5},
}

# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------
MAX_RETRIES = 3
CALL_DELAY = 0.5  # seconds between API calls


def _hf_token():
    """Return HF_TOKEN from environment or raise."""
    token = os.environ.get("HF_TOKEN")
    if not token:
        raise RuntimeError("HF_TOKEN environment variable is not set")
    return token


def _api_call(model_key, payload, token):
    """
    POST to HuggingFace Inference API with retry logic.

    Handles:
      - 503: model loading — wait 20 s and retry
      - 429: rate limit — wait 10 s and retry
    Returns parsed JSON response.
    """
    model_name = MODELS[model_key]
    url = f"{HF_API_BASE}/{model_name}"
    data = json.dumps(payload).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    for attempt in range(1, MAX_RETRIES + 1):
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                body = resp.read().decode("utf-8")
                return json.loads(body)
        except urllib.error.HTTPError as exc:
            if exc.code == 503 and attempt < MAX_RETRIES:
                print(f"  [503] Model {model_name} loading, waiting 20 s (attempt {attempt}/{MAX_RETRIES})")
                time.sleep(20)
                continue
            if exc.code == 429 and attempt < MAX_RETRIES:
                print(f"  [429] Rate limited for {model_name}, waiting 10 s (attempt {attempt}/{MAX_RETRIES})")
                time.sleep(10)
                continue
            # Read error body for diagnostics
            err_body = ""
            try:
                err_body = exc.read().decode("utf-8", errors="replace")
            except Exception:
                pass
            raise RuntimeError(
                f"HF API error {exc.code} for {model_name} (attempt {attempt}): {err_body}"
            ) from exc
        except urllib.error.URLError as exc:
            if attempt < MAX_RETRIES:
                print(f"  [URLError] {exc.reason} for {model_name}, retrying in 5 s (attempt {attempt}/{MAX_RETRIES})")
                time.sleep(5)
                continue
            raise

    raise RuntimeError(f"Exhausted {MAX_RETRIES} retries for {model_name}")


# ---------------------------------------------------------------------------
# Classification steps
# ---------------------------------------------------------------------------

def classify_ea_hs(text, token):
    """
    EA-HS 3-class classifier: Normal / Abusive / Hate.
    Returns (prediction_label, confidence_score).
    """
    result = _api_call("ea_hs", {"inputs": text}, token)
    # Response: [[{"label": "Hate", "score": 0.95}, ...]]
    if isinstance(result, list) and result and isinstance(result[0], list):
        labels = result[0]
    elif isinstance(result, list) and result and isinstance(result[0], dict):
        labels = result
    else:
        raise ValueError(f"Unexpected EA-HS response format: {result}")

    top = max(labels, key=lambda x: x["score"])
    return top["label"], round(top["score"], 4)


def classify_toxicity(text, token):
    """
    Toxicity classifier.
    Returns toxicity score (float 0-1) and level string.
    """
    result = _api_call("toxicity", {"inputs": text}, token)
    # Response: [[{"label": "toxic", "score": 0.85}, {"label": "non-toxic", ...}]]
    if isinstance(result, list) and result and isinstance(result[0], list):
        labels = result[0]
    elif isinstance(result, list) and result and isinstance(result[0], dict):
        labels = result
    else:
        raise ValueError(f"Unexpected toxicity response format: {result}")

    toxic_score = 0.0
    for item in labels:
        if item["label"].lower() == "toxic":
            toxic_score = item["score"]
            break

    # Map score to level
    if toxic_score >= 0.85:
        level = "very_high"
    elif toxic_score >= 0.6:
        level = "high"
    elif toxic_score >= 0.35:
        level = "medium"
    else:
        level = "low"

    return round(toxic_score, 4), level


def classify_subtopics(text, token):
    """
    Zero-shot subtopic classification via bart-large-mnli.
    Returns top-2 subtopics with score > 0.15 as list of {n, s}.
    """
    payload = {
        "inputs": text,
        "parameters": {"candidate_labels": SUBTOPIC_CANDIDATES},
    }
    result = _api_call("zero_shot", payload, token)
    # Response: {"labels": [...], "scores": [...]}
    labels = result.get("labels", [])
    scores = result.get("scores", [])

    top = []
    for label, score in zip(labels, scores):
        if score > 0.15 and len(top) < 2:
            top.append({
                "n": SUBTOPIC_DISPLAY.get(label, label),
                "s": round(score, 4),
            })

    return top, list(zip(labels, scores))


def estimate_txd(subtopic_results):
    """
    Estimate toxicity dimensions from subtopic classification results.
    Uses the profile lookup table, weighting by confidence score.

    subtopic_results: list of (label, score) tuples (full zero-shot output).
    Returns dict {sev, ins, idt, thr} with values 0-1.
    """
    txd = {"sev": 0.0, "ins": 0.0, "idt": 0.0, "thr": 0.0}
    total_weight = 0.0

    for label, score in subtopic_results:
        profile = SUBTOPIC_TXD_PROFILES.get(label)
        if profile is None:
            continue
        weight = score
        total_weight += weight
        for dim in txd:
            txd[dim] += profile[dim] * weight

    if total_weight > 0:
        for dim in txd:
            txd[dim] = round(txd[dim] / total_weight, 4)

    return txd


def classify_country_model(text, country, token):
    """
    Run country-specific model if available.
    Returns result dict or None.
    """
    model_key = COUNTRY_MODEL_MAP.get(country)
    if model_key is None:
        return None

    result = _api_call(model_key, {"inputs": text}, token)
    # Normalize: may be [[{...}]] or [{...}]
    if isinstance(result, list) and result and isinstance(result[0], list):
        labels = result[0]
    elif isinstance(result, list) and result and isinstance(result[0], dict):
        labels = result
    else:
        return None

    top = max(labels, key=lambda x: x["score"])
    return {"label": top["label"], "score": round(top["score"], 4), "model": MODELS[model_key]}


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def load_posts():
    """Load posts from JSON file."""
    if not HS_DATA_PATH.exists():
        raise FileNotFoundError(f"Data file not found: {HS_DATA_PATH}")
    with open(HS_DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_posts(posts):
    """Save posts back to JSON file."""
    with open(HS_DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)


def classify_posts():
    """
    Classify all posts with qc='auto_sweep'.
    Returns dict {"classified": N, "total": M}.
    """
    token = _hf_token()
    posts = load_posts()
    total = len(posts)

    # Find posts needing classification
    sweep_indices = [
        i for i, p in enumerate(posts) if p.get("qc") == "auto_sweep"
    ]
    to_classify = len(sweep_indices)

    if to_classify == 0:
        print("No posts with qc='auto_sweep' found. Nothing to classify.")
        return {"classified": 0, "total": total}

    print(f"Found {to_classify} posts to classify out of {total} total.")

    classified = 0

    for batch_num, idx in enumerate(sweep_indices):
        post = posts[idx]
        text = post.get("text", "") or post.get("content", "") or ""
        country = post.get("country", "")

        if not text.strip():
            # Skip empty posts, mark as classified with low confidence
            post["pr"] = "Normal"
            post["co"] = 0.0
            post["tx"] = "low"
            post["st"] = []
            post["txd"] = {"sev": 0.0, "ins": 0.0, "idt": 0.0, "thr": 0.0}
            post["qc"] = "ml_classified"
            classified += 1
            continue

        try:
            # 1. EA-HS primary classifier
            prediction, confidence = classify_ea_hs(text, token)
            post["pr"] = prediction
            post["co"] = confidence
            time.sleep(CALL_DELAY)

            # 2. Toxicity scoring
            tox_score, tox_level = classify_toxicity(text, token)
            post["tx"] = tox_level
            time.sleep(CALL_DELAY)

            # 3. Zero-shot subtopic classification
            subtopics, full_subtopic_results = classify_subtopics(text, token)
            post["st"] = subtopics
            time.sleep(CALL_DELAY)

            # 4. Estimate toxicity dimensions from subtopics
            post["txd"] = estimate_txd(full_subtopic_results)

            # 5. Country-specific model (if applicable)
            if country in COUNTRY_MODEL_MAP:
                country_result = classify_country_model(text, country, token)
                if country_result:
                    post["country_model"] = country_result
                time.sleep(CALL_DELAY)

            # Mark as classified
            post["qc"] = "ml_classified"
            classified += 1

        except Exception as exc:
            print(f"  ERROR classifying post index {idx}: {exc}")
            # Leave qc unchanged so it can be retried
            continue

        # Progress and save checkpoint every 10 posts
        if classified % 10 == 0:
            print(f"  Progress: {classified}/{to_classify} classified")
            save_posts(posts)

    # Final save
    save_posts(posts)
    print(f"Done. Classified {classified}/{to_classify} posts.")

    return {"classified": classified, "total": total}


if __name__ == "__main__":
    stats = classify_posts()
    print(json.dumps(stats, indent=2))
