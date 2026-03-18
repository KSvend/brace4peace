#!/usr/bin/env python3
"""
HS Post Explanation Generator for BRACE4PEACE
==============================================
Reads hate_speech_posts.json, finds posts that need human-readable explanations
(ML-classified or auto-swept without proper review), and uses the Anthropic API
to generate structured explanations with QC labels.

Usage:
    python3 explain_posts.py [--dry-run] [--limit N]

Requires ANTHROPIC_API_KEY environment variable.
Pure stdlib — no pip dependencies.
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error
import argparse
from pathlib import Path

# ─── Paths ────────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent
HS_DATA_PATH = REPO_ROOT / "docs" / "data" / "hate_speech_posts.json"

# ─── Anthropic API Config ─────────────────────────────────────────────────────

API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 4096
BATCH_SIZE = 10
SLEEP_BETWEEN_BATCHES = 2
MAX_RETRIES = 3
TEXT_TRUNCATE_LEN = 250

# ─── System Prompt ────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a hate speech analyst reviewing social media posts from East Africa (Somalia, South Sudan, Kenya).

You have deep knowledge of local-language hate speech terms:
- Somali: mooryaan (bandit/clan slur), faqash (regime supporter slur), jareer (Bantu racial slur), xayawaan (animal/dehumanising), gaal/gaalo (infidel), kaafir/kufaar (infidel), murtad (apostate), idoor (Isaaq slur), laangaab (minority clan slur), reer (clan prefix)
- South Sudan: kokora (ethnic separation/purge), dinkocracy (Dinka domination), jiengism (Dinka supremacism), jenge (anti-Dinka slur), nyam nyam (cannibals), mathiang anyor (Dinka militia)
- Kenya: madoadoa (stains/outsiders), kihii (uncircumcised/insult), conoka (anti-Kikuyu), muhoi (squatter), mungiki (Kikuyu militia), wakuja (foreigners)

For each post, provide:
1. "exp": 1-2 analytical sentences explaining what the post says, translating any local-language terms with their meaning and cultural context. If not hate speech, explain why.
2. "qc": "correct" (genuinely hateful/abusive toward a group), "questionable" (borderline — political criticism, sarcasm, ambiguous), or "misclassified" (NOT hate speech — news, counter-speech, personal frustration, unrelated)
3. "rel": "relevant" (about East Africa), "possibly_relevant", or "not_relevant"
4. "tx": your assessment of toxicity level — "low", "medium", "high", or "very_high". Base this on the severity of language used (slurs, dehumanization = high/very_high; insults = medium; political criticism = low).
5. "txd": toxicity dimensions object with "sev" (severity), "ins" (insult), "idt" (identity attack), "thr" (threat) — each "low", "medium", or "high". Assess each dimension independently based on content.

Respond ONLY with a JSON array. No markdown fences.
Format: [{"id": 0, "exp": "...", "qc": "correct", "rel": "relevant", "tx": "medium", "txd": {"sev": "medium", "ins": "high", "idt": "low", "thr": "low"}}, ...]"""


# ─── Helpers ──────────────────────────────────────────────────────────────────

def load_posts():
    """Load hate speech posts from JSON file."""
    if not HS_DATA_PATH.exists():
        print(f"[ERROR] Data file not found: {HS_DATA_PATH}")
        return None
    with open(HS_DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_posts(posts):
    """Save hate speech posts back to JSON file."""
    with open(HS_DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(posts, f, indent=2, ensure_ascii=False)
        f.write("\n")


def needs_explanation(post):
    """Check if a post needs an explanation generated."""
    qc = post.get("qc", "")
    exp = post.get("exp", "")

    # Posts classified by ML or auto-sweep need explanation
    if qc in ("ml_classified", "auto_sweep"):
        return True

    # Posts with lazy auto-detected explanations from old pipeline
    if isinstance(exp, str) and exp.startswith("Auto-detected"):
        return True

    return False


def build_batch_prompt(batch):
    """Build the user prompt for a batch of posts."""
    lines = []
    for idx, post in batch:
        country = post.get("country", "Unknown")
        subtopic = post.get("subtopic", "Unknown")
        toxicity = post.get("toxicity", "Unknown")
        text = post.get("text", "")
        if len(text) > TEXT_TRUNCATE_LEN:
            text = text[:TEXT_TRUNCATE_LEN] + "..."
        lines.append(f"[{idx}] Country:{country} | Class:{subtopic} | Tox:{toxicity}")
        lines.append(text)
        lines.append("")
    return "\n".join(lines).strip()


def call_anthropic(api_key, batch_text):
    """Make a raw urllib POST to the Anthropic Messages API with retry on 429."""
    payload = json.dumps({
        "model": MODEL,
        "max_tokens": MAX_TOKENS,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": batch_text}],
    }).encode("utf-8")

    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    }

    for attempt in range(1, MAX_RETRIES + 1):
        req = urllib.request.Request(API_URL, data=payload, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                # Extract text from the response content blocks
                text_parts = [
                    block["text"]
                    for block in body.get("content", [])
                    if block.get("type") == "text"
                ]
                return "".join(text_parts)
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < MAX_RETRIES:
                backoff = 2 ** attempt
                print(f"  [429] Rate limited. Retrying in {backoff}s (attempt {attempt}/{MAX_RETRIES})...")
                time.sleep(backoff)
                continue
            error_body = ""
            try:
                error_body = e.read().decode("utf-8")
            except Exception:
                pass
            print(f"  [ERROR] HTTP {e.code}: {error_body[:300]}")
            return None
        except Exception as e:
            print(f"  [ERROR] Request failed: {e}")
            return None

    return None


def parse_response(response_text, batch):
    """Parse the JSON array response and map results back to post indices."""
    if not response_text:
        return {}

    # Strip any accidental markdown fences
    text = response_text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]
    text = text.strip()

    try:
        results = json.loads(text)
    except json.JSONDecodeError as e:
        print(f"  [ERROR] Failed to parse API response as JSON: {e}")
        print(f"  Response preview: {text[:200]}")
        return {}

    if not isinstance(results, list):
        print(f"  [ERROR] Expected JSON array, got {type(results).__name__}")
        return {}

    # Build a mapping from id -> result
    mapping = {}
    for item in results:
        if isinstance(item, dict) and "id" in item:
            mapping[item["id"]] = item

    return mapping


def explain_posts(dry_run=False, limit=None):
    """Main function: find posts needing explanation and process them in batches."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("[SKIP] ANTHROPIC_API_KEY not set in environment. Exiting.")
        return {"explained": 0, "total": 0}

    posts = load_posts()
    if posts is None:
        return {"explained": 0, "total": 0}

    # Find posts that need explanation, keeping track of their index
    to_explain = []
    for i, post in enumerate(posts):
        if needs_explanation(post):
            to_explain.append((i, post))

    total = len(to_explain)
    if limit is not None:
        to_explain = to_explain[:limit]

    print(f"[INFO] Found {total} posts needing explanation. Processing {len(to_explain)}.")

    if dry_run:
        print("[DRY RUN] Would process the following posts:")
        for idx, post in to_explain[:5]:
            print(f"  #{idx}: qc={post.get('qc')}, exp={str(post.get('exp', ''))[:60]}")
        if len(to_explain) > 5:
            print(f"  ... and {len(to_explain) - 5} more")
        return {"explained": 0, "total": total}

    explained = 0

    # Process in batches
    for batch_start in range(0, len(to_explain), BATCH_SIZE):
        batch = to_explain[batch_start : batch_start + BATCH_SIZE]
        batch_num = batch_start // BATCH_SIZE + 1
        total_batches = (len(to_explain) + BATCH_SIZE - 1) // BATCH_SIZE

        print(f"\n[BATCH {batch_num}/{total_batches}] Processing {len(batch)} posts...")

        batch_text = build_batch_prompt(batch)
        response_text = call_anthropic(api_key, batch_text)
        mapping = parse_response(response_text, batch)

        if not mapping:
            print(f"  [WARN] No valid results for batch {batch_num}. Skipping.")
            continue

        # Apply results back to posts
        for idx, post in batch:
            if idx in mapping:
                result = mapping[idx]
                post["exp"] = result.get("exp", post.get("exp", ""))
                post["qc"] = result.get("qc", post.get("qc", ""))
                if "rel" in result:
                    post["rel"] = result["rel"]
                if "tx" in result:
                    post["tx"] = result["tx"]
                if "txd" in result and isinstance(result["txd"], dict):
                    post["txd"] = result["txd"]
                explained += 1

        # Save after each batch to preserve progress
        save_posts(posts)
        print(f"  Saved. {explained} posts explained so far.")

        # Sleep between batches to avoid rate limits
        if batch_start + BATCH_SIZE < len(to_explain):
            time.sleep(SLEEP_BETWEEN_BATCHES)

    print(f"\n[DONE] Explained {explained}/{total} posts.")
    return {"explained": explained, "total": total}


# ─── CLI ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate explanations for hate speech posts")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be processed without calling API")
    parser.add_argument("--limit", type=int, default=None, help="Max number of posts to process")
    args = parser.parse_args()

    result = explain_posts(dry_run=args.dry_run, limit=args.limit)
    print(json.dumps(result, indent=2))
