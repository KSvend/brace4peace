#!/usr/bin/env python3
"""
ML classification using local HuggingFace transformers models.

Runs 5 BERT models locally (downloaded on first use, ~440MB each):
  1. KSvendsen/EA-HS — 3-class hate speech (Normal/Abusive/Hate)
  2. textdetox/bert-multilingual-toxicity-classifier — toxicity scoring
  3. datavaluepeople/Polarization-Kenya — Kenya polarization
  4. datavaluepeople/Afxumo-toxicity-somaliland-SO — Somali toxicity
  5. datavaluepeople/Hate-Speech-Sudan-v2 — Sudan/SS hate speech

Plus zero-shot subtopic classification via HF Inference API (bart-large-mnli).

Requires: pip install torch transformers scipy
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np
import torch
from scipy.special import softmax
from transformers import AutoModelForSequenceClassification, AutoTokenizer

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
HS_DATA_PATH = REPO_ROOT / "docs" / "data" / "hate_speech_posts.json"

# ---------------------------------------------------------------------------
# Model definitions
# ---------------------------------------------------------------------------
MODELS = {
    "ea_hs": {
        "hf_name": "KSvendsen/EA-HS",
        "labels": ["Normal", "Abusive", "Hate"],
    },
    "toxicity": {
        "hf_name": "textdetox/bert-multilingual-toxicity-classifier",
        "labels": ["non-toxic", "toxic"],
    },
    "kenya": {
        "hf_name": "datavaluepeople/Polarization-Kenya",
        "labels": ["not_polarization", "polarization"],
    },
    "somalia": {
        "hf_name": "datavaluepeople/Afxumo-toxicity-somaliland-SO",
        "labels": ["not_afxumo", "afxumo"],
    },
    "south_sudan": {
        "hf_name": "datavaluepeople/Hate-Speech-Sudan-v2",
        "labels": ["not_hate_speech", "hate_speech"],
    },
}

COUNTRY_MODEL_MAP = {
    "Kenya": "kenya",
    "Somalia": "somalia",
    "South Sudan": "south_sudan",
}

# ---------------------------------------------------------------------------
# Zero-shot subtopic labels (via API — bart-large-mnli is too large for local)
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

SUBTOPIC_TXD_PROFILES = {
    "Ethnic Targeting": {"sev": 0.6, "ins": 0.6, "idt": 0.9, "thr": 0.4},
    "Clan Targeting": {"sev": 0.5, "ins": 0.7, "idt": 0.8, "thr": 0.3},
    "Anti-Foreign": {"sev": 0.5, "ins": 0.6, "idt": 0.8, "thr": 0.4},
    "Religious Incitement": {"sev": 0.7, "ins": 0.5, "idt": 0.7, "thr": 0.6},
    "Dehumanisation": {"sev": 0.8, "ins": 0.9, "idt": 0.9, "thr": 0.3},
    "Gendered Violence": {"sev": 0.7, "ins": 0.8, "idt": 0.6, "thr": 0.7},
    "Political Incitement": {"sev": 0.6, "ins": 0.5, "idt": 0.4, "thr": 0.7},
    "Diaspora Stigma": {"sev": 0.3, "ins": 0.5, "idt": 0.6, "thr": 0.2},
    "Militarisation": {"sev": 0.7, "ins": 0.3, "idt": 0.5, "thr": 0.8},
    "Disinfo/Conspiracy": {"sev": 0.6, "ins": 0.7, "idt": 0.6, "thr": 0.5},
}

# Zero-shot API
ZS_API_URL = "https://router.huggingface.co/hf-inference/models/facebook/bart-large-mnli"

BATCH_SIZE = 32
MAX_LEN = 256

# ---------------------------------------------------------------------------
# Local model inference
# ---------------------------------------------------------------------------

_loaded_models = {}


def _load_model(key):
    """Load a model + tokenizer, caching in memory."""
    if key in _loaded_models:
        return _loaded_models[key]
    cfg = MODELS[key]
    print(f"  Loading {cfg['hf_name']}...", flush=True)
    tokenizer = AutoTokenizer.from_pretrained(cfg["hf_name"])
    model = AutoModelForSequenceClassification.from_pretrained(cfg["hf_name"])
    model.eval()
    _loaded_models[key] = (tokenizer, model, cfg["labels"])
    return tokenizer, model, cfg["labels"]


def _classify_batch(key, texts):
    """Classify a batch of texts with a local model. Returns list of (label, score)."""
    tokenizer, model, labels = _load_model(key)
    inputs = tokenizer(
        texts, padding=True, truncation=True, max_length=MAX_LEN, return_tensors="pt"
    )
    with torch.no_grad():
        logits = model(**inputs).logits.numpy()
    results = []
    for row in logits:
        probs = softmax(row)
        best_idx = int(np.argmax(probs))
        results.append((labels[best_idx], round(float(probs[best_idx]), 4)))
    return results


def _classify_single(key, text):
    """Classify a single text."""
    results = _classify_batch(key, [text])
    return results[0]


# ---------------------------------------------------------------------------
# Zero-shot subtopic classification (API-based)
# ---------------------------------------------------------------------------

def _zero_shot_api(text, token):
    """Call bart-large-mnli via HF router for zero-shot classification."""
    if not token:
        return []
    payload = json.dumps({
        "inputs": text[:256],
        "parameters": {"candidate_labels": SUBTOPIC_CANDIDATES},
    }).encode()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }
    for attempt in range(3):
        req = urllib.request.Request(ZS_API_URL, data=payload, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode())
                # Return top-2 subtopics with score > 0.15
                subtopics = []
                for label, score in zip(result["labels"], result["scores"]):
                    if score > 0.15 and len(subtopics) < 2:
                        display = SUBTOPIC_DISPLAY.get(label, label)
                        subtopics.append({"n": display, "s": round(score, 3)})
                return subtopics
        except urllib.error.HTTPError as e:
            if e.code == 503:
                time.sleep(20)
            elif e.code == 429:
                time.sleep(10)
            else:
                break
        except Exception:
            time.sleep(5)
    return []


# ---------------------------------------------------------------------------
# Toxicity dimension estimation
# ---------------------------------------------------------------------------

def _estimate_txd(subtopics, tox_score):
    """Estimate toxicity dimensions from subtopic + toxicity score."""
    if not subtopics:
        base = {"sev": 0.5, "ins": 0.5, "idt": 0.5, "thr": 0.5}
    else:
        top_label = subtopics[0]["n"]
        base = SUBTOPIC_TXD_PROFILES.get(top_label, {"sev": 0.5, "ins": 0.5, "idt": 0.5, "thr": 0.5})

    def to_level(s):
        v = s * tox_score
        if v >= 0.7:
            return "high"
        if v >= 0.4:
            return "medium"
        return "low"

    return {k: to_level(v) for k, v in base.items()}


def _tox_level(score):
    if score >= 0.85:
        return "very_high"
    if score >= 0.6:
        return "high"
    if score >= 0.35:
        return "medium"
    return "low"


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def _save_posts(posts):
    """Save posts to disk."""
    with open(HS_DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False, separators=(",", ":"))


def _needs_ml(post):
    """Check if a post needs ML classification."""
    # New sweep posts not yet ML-classified
    if post.get("qc") == "auto_sweep":
        return True
    # Posts where API failed (co=0 with a prediction of Normal)
    if post.get("co", 0) == 0 and post.get("pr") == "Normal":
        return True
    # Posts from Apify sweep missing proper toxicity dimensions
    if str(post.get("i", "")).startswith("apify-"):
        txd = post.get("txd") or {}
        if not txd or txd == {"sev": "medium", "ins": "medium", "idt": "medium", "thr": "low"}:
            return True
    return False


def classify_posts(skip_zero_shot=False):
    """
    Classify posts needing ML enrichment.
    Uses local transformers models + optional API for zero-shot.
    Saves after each model pass for resilience.
    """
    hf_token = os.environ.get("HF_TOKEN", "")
    torch.set_num_threads(2)

    if not HS_DATA_PATH.exists():
        print(f"Data file not found: {HS_DATA_PATH}")
        return {"classified": 0, "total": 0}

    with open(HS_DATA_PATH, "r", encoding="utf-8") as f:
        posts = json.load(f)

    total = len(posts)

    # Find posts needing classification
    indices = [i for i, p in enumerate(posts) if _needs_ml(p)]

    if not indices:
        print(f"No posts need ML classification. Total: {total}")
        return {"classified": 0, "total": total}

    print(f"Found {len(indices)} posts to classify out of {total} total.", flush=True)

    texts = [(posts[i].get("t") or "")[:MAX_LEN] for i in indices]
    non_empty = [(i, t) for i, t in zip(indices, texts) if t.strip()]

    if not non_empty:
        print("All posts have empty text.")
        return {"classified": 0, "total": total}

    batch_indices = [i for i, _ in non_empty]
    batch_texts = [t for _, t in non_empty]

    # 1. EA-HS (primary hate speech classifier)
    print(f"  Running EA-HS on {len(batch_texts)} texts...", flush=True)
    ea_results = []
    for start in range(0, len(batch_texts), BATCH_SIZE):
        batch = batch_texts[start:start + BATCH_SIZE]
        ea_results.extend(_classify_batch("ea_hs", batch))
    for idx, (label, score) in zip(batch_indices, ea_results):
        posts[idx]["pr"] = label
        posts[idx]["co"] = score
    _save_posts(posts)
    _loaded_models.pop("ea_hs", None)
    print(f"  EA-HS done. Saved.", flush=True)

    # 2. Toxicity
    print(f"  Running toxicity classifier...", flush=True)
    tox_results = []
    for start in range(0, len(batch_texts), BATCH_SIZE):
        batch = batch_texts[start:start + BATCH_SIZE]
        tox_results.extend(_classify_batch("toxicity", batch))
    tox_scores = {}
    for idx, (label, score) in zip(batch_indices, tox_results):
        tox_score = score if label == "toxic" else 1 - score
        posts[idx]["tx"] = _tox_level(tox_score)
        tox_scores[idx] = round(tox_score, 4)
    _save_posts(posts)
    _loaded_models.pop("toxicity", None)
    print(f"  Toxicity done. Saved.", flush=True)

    # 3. Country-specific models (one at a time to save memory)
    for country, model_key in COUNTRY_MODEL_MAP.items():
        country_indices = [i for i in batch_indices if posts[i].get("c") == country]
        if not country_indices:
            continue
        country_texts = [(posts[i].get("t") or "")[:MAX_LEN] for i in country_indices]
        print(f"  Running {MODELS[model_key]['hf_name']} on {len(country_texts)} {country} posts...", flush=True)
        results = []
        for start in range(0, len(country_texts), BATCH_SIZE):
            batch = country_texts[start:start + BATCH_SIZE]
            results.extend(_classify_batch(model_key, batch))
        for idx, (label, score) in zip(country_indices, results):
            posts[idx]["_country_model"] = {"label": label, "score": score}
        _loaded_models.pop(model_key, None)
    _save_posts(posts)
    print(f"  Country models done. Saved.", flush=True)

    # 4. Zero-shot subtopics (API-based, rate limited — skip if told to)
    if not skip_zero_shot and hf_token:
        print(f"  Running zero-shot subtopics on {len(batch_indices)} posts...", flush=True)
        for count, idx in enumerate(batch_indices):
            text = (posts[idx].get("t") or "")[:256]
            if text.strip():
                subtopics = _zero_shot_api(text, hf_token)
                if subtopics:
                    posts[idx]["st"] = subtopics
                time.sleep(0.5)
            if (count + 1) % 20 == 0:
                print(f"    Subtopics: {count + 1}/{len(batch_indices)}", flush=True)
                _save_posts(posts)
    elif skip_zero_shot:
        print("  Skipping zero-shot (--skip-zero-shot flag).", flush=True)
    else:
        print("  Skipping zero-shot (no HF_TOKEN).", flush=True)

    # 5. Estimate toxicity dimensions from subtopics + toxicity score
    for idx in batch_indices:
        ts = tox_scores.get(idx, 0.5)
        subtopics = posts[idx].get("st", [])
        posts[idx]["txd"] = _estimate_txd(subtopics, ts)

    # 6. Mark as ml_classified (only for auto_sweep posts, preserve QC labels from LLM QA)
    classified = 0
    for idx in batch_indices:
        if posts[idx].get("qc") == "auto_sweep":
            posts[idx]["qc"] = "ml_classified"
        classified += 1

    _save_posts(posts)
    _loaded_models.clear()

    print(f"Done. Classified {classified}/{len(indices)} posts.", flush=True)
    return {"classified": classified, "total": total}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-zero-shot", action="store_true", help="Skip slow zero-shot API calls")
    args = parser.parse_args()
    stats = classify_posts(skip_zero_shot=args.skip_zero_shot)
    print(json.dumps(stats, indent=2))
