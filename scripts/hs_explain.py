#!/usr/bin/env python3
"""Generate hate speech explanations for posts missing the `exp` field.

Reads docs/data/hate_speech_posts.json, calls Claude API in batches of 10,
saves progress after every batch to docs/data/hs_explain_progress.json,
and merges results back into hate_speech_posts.json when done.
"""

import json
import os
import sys
import time
import traceback
from pathlib import Path

from dotenv import load_dotenv
import anthropic

# Load .env from project root
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# ── Config ──────────────────────────────────────────────────────────────────
POSTS_PATH = "docs/data/hate_speech_posts.json"
PROGRESS_PATH = "docs/data/hs_explain_progress.json"
BATCH_SIZE = 10
MAX_RETRIES = 3
MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 4096

SYSTEM_PROMPT = """\
You are a hate speech analyst reviewing social media posts from East Africa (Somalia, South Sudan, Kenya) for UNDP's BRACE4PEACE monitoring platform. Your audience is third-party analysts and policymakers.

You have deep knowledge of local-language hate speech terms:
- Somali: mooryaan (bandit/clan slur against minority clans), faqash (Siad Barre regime supporter slur), jareer/jareereed (Bantu racial slur, literally "hard hair"), xayawaan (animal/dehumanising), gaal/gaalo (infidel/non-Muslim), kaafir/kufaar (infidel), murtad (apostate), idoor (anti-Isaaq slur), laangaab (minority clan slur, "short lineage"), reer (clan prefix), qashin (trash), cayaanka (filth), xoolo (livestock/subhuman), eelay (minority clan), qabiil dagaal (clan warfare), qadaad weyn (big forehead — Darod slur)
- South Sudan: kokora (ethnic separation/purge — refers to 1983 policy of regional division), dinkocracy (Dinka political domination), jiengism (Dinka supremacism — Jieng is Dinka self-name), jenge (anti-Dinka slur), nyam nyam (cannibals — colonial-era slur), mathiang anyor (Dinka militia, literally "brown caterpillar"), warrapism (Warrap state favoritism), camjiec (derogatory for Nuer), monyjang (Dinka self-name used pejoratively)
- Kenya: madoadoa (stains/spots — used to label outsiders during election violence), kihii (uncircumcised — Kikuyu insult for Luo/Kalenjin men), conoka (anti-Kikuyu slur), muhoi (squatter/tenant — used against landless communities), mungiki (Kikuyu militia/gang), wakuja (foreigners/outsiders in Swahili), wageni (guests/foreigners), kwekwe (derogatory for Somali-Kenyans), mende (derogatory for dark-skinned)

For each post, provide:
1. "exp": 1-2 analytical sentences. If the post contains local-language terms, TRANSLATE them and explain their cultural significance. If the post targets a specific group, name the group and explain the context. Be specific — reference the actual words/phrases used. If the post is NOT hate speech, explain why.
2. "qc": "correct" (genuinely hateful/abusive toward a group), "questionable" (borderline — political criticism, sarcasm, or ambiguous), or "misclassified" (NOT hate speech — news, counter-speech, personal frustration, or unrelated content)
3. "rel": "relevant" (about Somalia/South Sudan/Kenya/East Africa), "possibly_relevant" (unclear regional context), or "not_relevant" (clearly about other regions)

Respond ONLY with a JSON array. Use numeric index as id. No markdown fences.
Format: [{"id": 0, "exp": "...", "qc": "correct|questionable|misclassified", "rel": "relevant|possibly_relevant|not_relevant"}, ...]
"""


def load_json(path):
    if not os.path.exists(path):
        return {} if path == PROGRESS_PATH else []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))


def format_batch(batch):
    """Format a batch of (index, post) pairs into the user prompt."""
    lines = []
    for idx, post in batch:
        text = (post.get("t") or "")[:250]
        country = post.get("c", "?")
        pred = post.get("pr", "?")
        tox = post.get("tx", "?")
        subtopics = ", ".join(s.get("n", "") for s in (post.get("st") or []))
        lines.append(
            f"[{idx}] Country:{country} | Class:{pred} | Tox:{tox} | Sub:{subtopics}\n{text}"
        )
    return "\n\n".join(lines)


def call_api(client, user_prompt):
    """Call Claude API with retries and exponential backoff."""
    for attempt in range(MAX_RETRIES):
        try:
            resp = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )
            text = resp.content[0].text.strip()
            # Strip markdown fences if present
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
                if text.endswith("```"):
                    text = text[: text.rfind("```")]
            return json.loads(text)
        except json.JSONDecodeError as e:
            print(f"  JSON parse error (attempt {attempt+1}): {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** (attempt + 1))
        except anthropic.RateLimitError:
            wait = 2 ** (attempt + 2)
            print(f"  Rate limited, waiting {wait}s...")
            time.sleep(wait)
        except Exception as e:
            print(f"  API error (attempt {attempt+1}): {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** (attempt + 1))
    return None


def main():
    posts = load_json(POSTS_PATH)
    progress = load_json(PROGRESS_PATH)
    client = anthropic.Anthropic()

    # Find unprocessed posts
    todo = [(i, p) for i, p in enumerate(posts) if p["i"] not in progress]
    total = len(todo)
    print(f"Total posts: {len(posts)} | Already done: {len(progress)} | To process: {total}")

    if total == 0:
        print("Nothing to process. Merging and exiting.")
    else:
        processed = 0
        for batch_start in range(0, total, BATCH_SIZE):
            batch = todo[batch_start : batch_start + BATCH_SIZE]
            user_prompt = format_batch([(j, p) for j, (_, p) in enumerate(batch)])
            results = call_api(client, user_prompt)

            if results:
                for item in results:
                    idx_in_batch = item.get("id", -1)
                    if 0 <= idx_in_batch < len(batch):
                        _, post = batch[idx_in_batch]
                        progress[post["i"]] = {
                            "exp": item.get("exp", ""),
                            "qc": item.get("qc", ""),
                            "rel": item.get("rel", ""),
                        }
            else:
                print(f"  Batch starting at {batch_start} failed after retries, skipping.")

            # Save progress after every batch
            save_json(PROGRESS_PATH, progress)
            processed += len(batch)

            if processed % 50 < BATCH_SIZE or processed == total:
                pct = processed / total * 100
                print(f"Processed {processed}/{total} ({pct:.1f}%)")

    # ── Merge into posts ────────────────────────────────────────────────────
    merged = 0
    for post in posts:
        if post["i"] in progress:
            entry = progress[post["i"]]
            post["exp"] = entry["exp"]
            post["qc"] = entry["qc"]
            post["rel"] = entry["rel"]
            merged += 1

    save_json(POSTS_PATH, posts)
    print(f"Merged {merged} explanations into {POSTS_PATH}")

    # ── Summary ─────────────────────────────────────────────────────────────
    qc_counts = {}
    rel_counts = {}
    for v in progress.values():
        qc_counts[v.get("qc", "?")] = qc_counts.get(v.get("qc", "?"), 0) + 1
        rel_counts[v.get("rel", "?")] = rel_counts.get(v.get("rel", "?"), 0) + 1

    print(f"\nProgress entries: {len(progress)}")
    print(f"QC breakdown: {json.dumps(qc_counts, indent=2)}")
    print(f"Relevance breakdown: {json.dumps(rel_counts, indent=2)}")


if __name__ == "__main__":
    main()
