"""
Classify 7,631 unclassified comments — full pipeline:
  Step 1: ML classify with 4 BERT models
  Step 2: Write results back to all_data_cleaned.csv
  Step 3: Convert Abusive/Hate comments to compact format → append to hate_speech_posts.json
  Step 4: Run LLM QA (Claude Sonnet) on new posts → exp, qc, rel, tx, txd
  Step 5: Quality gate — remove misclassified / not_relevant

Usage:
  python3 scripts/classify_comments.py              # full pipeline
  python3 scripts/classify_comments.py --step 1     # ML only
  python3 scripts/classify_comments.py --step 3     # convert + QA + gate (skip ML if already done)
"""
import sys, os, time, gc, json, argparse, uuid
import pandas as pd
import numpy as np

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
MODELS = {
    'ea_hs': {
        'hf_name': 'KSvendsen/EA-HS',
        'pred_col': 'EA_HS_pred', 'conf_col': 'EA_HS_conf',
        'score_cols': ['EA_HS_Normal', 'EA_HS_Abusive', 'EA_HS_Hate'],
        'labels': ['Normal', 'Abusive', 'Hate'],
    },
    'polarization': {
        'hf_name': 'datavaluepeople/Polarization-Kenya',
        'pred_col': 'Polarization_Kenya_pred', 'conf_col': 'Polarization_Kenya_conf',
        'score_cols': ['Polarization_Kenya_not_polarization', 'Polarization_Kenya_polarization'],
        'labels': ['not_polarization', 'polarization'],
    },
    'afxumo': {
        'hf_name': 'datavaluepeople/Afxumo-toxicity-somaliland-SO',
        'pred_col': 'Afxumo_Somali_pred', 'conf_col': 'Afxumo_Somali_conf',
        'score_cols': ['Afxumo_Somali_not_afxumo', 'Afxumo_Somali_afxumo'],
        'labels': ['not_afxumo', 'afxumo'],
    },
    'hatespeech_sudan': {
        'hf_name': 'datavaluepeople/Hate-Speech-Sudan-v2',
        'pred_col': 'HateSpeech_Sudan_pred', 'conf_col': 'HateSpeech_Sudan_conf',
        'score_cols': ['HateSpeech_Sudan_not_hate_speech', 'HateSpeech_Sudan_hate_speech'],
        'labels': ['not_hate_speech', 'hate_speech'],
    },
}

BASE = "/Users/kmini/Documents/PID_0240_UNDP_Hate_Speech/09 Online Monitoring"
UNCLASSIFIED = os.path.join(BASE, "unclassified_comments_7631.csv")
MASTER = os.path.join(BASE, "cleaned_pivoted", "all_data_cleaned.csv")

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HS_POSTS_PATH = os.path.join(REPO_ROOT, "docs", "data", "hate_speech_posts.json")

BATCH_SIZE = 64
MAX_LEN = 256
SAVE_EVERY = 5

# LLM QA config
LLM_MODEL = "claude-sonnet-4-20250514"
LLM_BATCH_SIZE = 10
LLM_MAX_TOKENS = 4096
LLM_SYSTEM_PROMPT = """You are a hate speech analyst reviewing social media posts from East Africa (Somalia, South Sudan, Kenya).

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


# ===================================================================
# Step 1: ML Classification
# ===================================================================
def step1_ml_classify():
    """Run 4 BERT models on unclassified comments."""
    import torch
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    from scipy.special import softmax

    torch.set_num_threads(8)

    print("\n" + "=" * 60)
    print("STEP 1: ML Classification (4 BERT models)")
    print("=" * 60)

    df = pd.read_csv(UNCLASSIFIED, low_memory=False)
    print(f"  {len(df)} rows loaded", flush=True)

    texts = df['comment_text_pi'].fillna('').astype(str)
    has_text = texts.str.strip().str.len() > 0
    print(f"  {has_text.sum()} rows with text", flush=True)

    grand_start = time.time()

    for model_key, cfg in MODELS.items():
        print(f"\n--- {cfg['hf_name']} ---", flush=True)

        for col in cfg['score_cols'] + [cfg['pred_col'], cfg['conf_col']]:
            if col not in df.columns:
                df[col] = np.nan

        needs_pred = df[cfg['pred_col']].isna()
        to_classify = needs_pred & has_text
        n_todo = int(to_classify.sum())

        if n_todo == 0:
            print("  Already classified, skipping.", flush=True)
            continue

        print(f"  {n_todo} items to classify", flush=True)

        t0 = time.time()
        tokenizer = AutoTokenizer.from_pretrained(cfg['hf_name'])
        model = AutoModelForSequenceClassification.from_pretrained(cfg['hf_name'])
        model.eval()
        print(f"  Model loaded in {time.time()-t0:.0f}s", flush=True)

        indices = df.index[to_classify].tolist()
        all_texts = texts[to_classify].tolist()
        classified = 0
        dirty = False
        batch_count = 0

        for i in range(0, len(all_texts), BATCH_SIZE):
            bt = all_texts[i:i+BATCH_SIZE]
            bi = indices[i:i+BATCH_SIZE]
            valid = [(t, idx) for t, idx in zip(bt, bi) if t.strip()]
            if not valid:
                continue

            v_texts = [v[0] for v in valid]
            v_indices = [v[1] for v in valid]

            try:
                inputs = tokenizer(v_texts, padding=True, truncation=True,
                                   max_length=MAX_LEN, return_tensors='pt')
                with torch.no_grad():
                    outputs = model(**inputs)
                probs = softmax(outputs.logits.cpu().numpy(), axis=1)

                for j, idx in enumerate(v_indices):
                    for k, sc in enumerate(cfg['score_cols']):
                        df.at[idx, sc] = float(probs[j][k])
                    pred_idx = int(np.argmax(probs[j]))
                    df.at[idx, cfg['pred_col']] = cfg['labels'][pred_idx]
                    df.at[idx, cfg['conf_col']] = float(probs[j][pred_idx])
                    classified += 1
                    dirty = True
            except Exception as e:
                print(f"    ERR batch {i}: {e}", flush=True)
                continue

            batch_count += 1
            if dirty and batch_count % SAVE_EVERY == 0:
                df.to_csv(UNCLASSIFIED, index=False)
                dirty = False
                elapsed = time.time() - grand_start
                print(f"    SAVED {classified}/{n_todo} ({classified/elapsed:.1f}/sec)", flush=True)

        if dirty:
            df.to_csv(UNCLASSIFIED, index=False)

        print(f"  DONE: {classified}/{n_todo} classified", flush=True)
        del model, tokenizer
        gc.collect()

    elapsed = time.time() - grand_start
    print(f"\nALL MODELS COMPLETE in {elapsed:.0f}s", flush=True)
    return df


# ===================================================================
# Step 2: Write results back to all_data_cleaned.csv
# ===================================================================
def step2_write_master(df):
    """Merge ML results back into all_data_cleaned.csv by comment_id."""
    print("\n" + "=" * 60)
    print("STEP 2: Write results to all_data_cleaned.csv")
    print("=" * 60)

    master = pd.read_csv(MASTER, low_memory=False)
    print(f"  Master file: {len(master)} rows", flush=True)

    result_cols = []
    for cfg in MODELS.values():
        result_cols += cfg['score_cols'] + [cfg['pred_col'], cfg['conf_col']]

    classified_df = df[['comment_id'] + result_cols].dropna(subset=['EA_HS_pred'])
    classified_lookup = classified_df.set_index('comment_id')
    print(f"  {len(classified_lookup)} classified comments to merge", flush=True)

    # Vectorised merge via temporary index
    master_idx = master.set_index('comment_id', drop=False)
    overlap = master_idx.index.intersection(classified_lookup.index)
    # Only update rows that are still unclassified
    unclassified_mask = master_idx.loc[overlap, 'EA_HS_pred'].isna()
    to_update = overlap[unclassified_mask]

    for col in result_cols:
        if col in classified_lookup.columns:
            master_idx.loc[to_update, col] = classified_lookup.loc[to_update, col]

    master = master_idx.reset_index(drop=True)
    updated = len(to_update)

    print(f"  Updated {updated} rows in master", flush=True)
    master.to_csv(MASTER, index=False)
    print(f"  Master file saved.", flush=True)
    return updated


# ===================================================================
# Step 3: Convert flagged comments to compact format → hate_speech_posts.json
# ===================================================================
def step3_convert_to_dashboard(df):
    """Convert Abusive/Hate comments to compact format and append to hate_speech_posts.json."""
    print("\n" + "=" * 60)
    print("STEP 3: Convert to dashboard format")
    print("=" * 60)

    # Filter: only Abusive or Hate predictions, or flagged by country-specific models
    flagged = df[
        (df['EA_HS_pred'].isin(['Abusive', 'Hate'])) |
        (df.get('Polarization_Kenya_pred', pd.Series(dtype=str)) == 'polarization') |
        (df.get('Afxumo_Somali_pred', pd.Series(dtype=str)) == 'afxumo') |
        (df.get('HateSpeech_Sudan_pred', pd.Series(dtype=str)) == 'hate_speech')
    ].copy()
    print(f"  {len(flagged)} comments flagged (Abusive/Hate or country-model positive)", flush=True)

    if len(flagged) == 0:
        print("  Nothing to add to dashboard.", flush=True)
        return []

    # Load existing posts to check for duplicates
    existing_posts = []
    if os.path.exists(HS_POSTS_PATH):
        with open(HS_POSTS_PATH, 'r', encoding='utf-8') as f:
            existing_posts = json.load(f)
    existing_ids = {p.get('i') for p in existing_posts}
    print(f"  {len(existing_posts)} existing posts in dashboard", flush=True)

    # Convert to compact format
    new_posts = []
    for _, row in flagged.iterrows():
        post_id = str(row.get('comment_id', ''))
        if not post_id or post_id in existing_ids:
            continue

        # Map toxicity prob to level
        tox_prob = row.get('prob_toxicity', '')
        if tox_prob == 'very_high':
            tx = 'very_high'
        elif tox_prob == 'high':
            tx = 'high'
        elif tox_prob == 'medium':
            tx = 'medium'
        else:
            tx = 'low'

        post = {
            "i": post_id,
            "t": str(row.get('comment_text_pi', '')),
            "d": str(row.get('comment_date', '')),
            "c": str(row.get('country', '')),
            "p": str(row.get('platform', 'x')),
            "a": str(row.get('comment_author_name_pi', '')),
            "l": str(row.get('comment_link_pi', '')),
            "pr": str(row.get('EA_HS_pred', '')),
            "co": float(row['EA_HS_conf']) if pd.notna(row.get('EA_HS_conf')) else 0.0,
            "tx": tx,
            "gt": str(row.get('gather_topic', '')),
            "st": [],  # subtopics — will be populated by zero-shot if available
            "qc": "ml_classified",  # triggers LLM QA
            "rel": "",
            "exp": "",
            "src": "backfill_comments",  # mark origin for traceability
        }
        new_posts.append(post)

    print(f"  {len(new_posts)} new posts to add ({len(flagged) - len(new_posts)} duplicates skipped)", flush=True)

    if new_posts:
        existing_posts.extend(new_posts)
        with open(HS_POSTS_PATH, 'w', encoding='utf-8') as f:
            json.dump(existing_posts, f, indent=2, ensure_ascii=False)
            f.write('\n')
        print(f"  Saved {len(existing_posts)} total posts to hate_speech_posts.json", flush=True)

    return new_posts


# ===================================================================
# Step 4: LLM QA via Claude Sonnet API
# ===================================================================
def step4_llm_qa(new_post_ids=None):
    """Run LLM QA on posts marked ml_classified. Uses raw urllib (no pip deps)."""
    import urllib.request
    import urllib.error

    print("\n" + "=" * 60)
    print("STEP 4: LLM QA (Claude Sonnet)")
    print("=" * 60)

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        # Try loading from .env
        env_path = os.path.join(REPO_ROOT, ".env")
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    if line.startswith("ANTHROPIC_API_KEY="):
                        api_key = line.strip().split("=", 1)[1].strip('"').strip("'")
                        break
    if not api_key:
        print("  [SKIP] ANTHROPIC_API_KEY not set. Run step 4 separately after setting it.")
        return 0

    with open(HS_POSTS_PATH, 'r', encoding='utf-8') as f:
        posts = json.load(f)

    # Find posts needing QA — either new ones or any ml_classified
    if new_post_ids:
        to_explain = [(i, p) for i, p in enumerate(posts) if p['i'] in new_post_ids]
    else:
        to_explain = [(i, p) for i, p in enumerate(posts)
                      if p.get('qc') in ('ml_classified', 'auto_sweep')]

    total = len(to_explain)
    print(f"  {total} posts needing LLM QA", flush=True)

    if total == 0:
        return 0

    explained = 0

    for batch_start in range(0, total, LLM_BATCH_SIZE):
        batch = to_explain[batch_start:batch_start + LLM_BATCH_SIZE]
        batch_num = batch_start // LLM_BATCH_SIZE + 1
        total_batches = (total + LLM_BATCH_SIZE - 1) // LLM_BATCH_SIZE

        # Build prompt
        lines = []
        for local_idx, (global_idx, post) in enumerate(batch):
            text = (post.get('t') or '')[:250]
            country = post.get('c', '?')
            pred = post.get('pr', '?')
            tox = post.get('tx', '?')
            lines.append(f"[{local_idx}] Country:{country} | Class:{pred} | Tox:{tox}\n{text}")
        user_prompt = "\n\n".join(lines)

        # Call API
        payload = json.dumps({
            "model": LLM_MODEL,
            "max_tokens": LLM_MAX_TOKENS,
            "system": LLM_SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": user_prompt}],
        }).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        }

        result = None
        for attempt in range(3):
            req = urllib.request.Request(
                "https://api.anthropic.com/v1/messages",
                data=payload, headers=headers, method="POST"
            )
            try:
                with urllib.request.urlopen(req, timeout=120) as resp:
                    body = json.loads(resp.read().decode("utf-8"))
                    text_parts = [b["text"] for b in body.get("content", []) if b.get("type") == "text"]
                    raw = "".join(text_parts).strip()
                    if raw.startswith("```"):
                        raw = raw.split("\n", 1)[-1]
                    if raw.endswith("```"):
                        raw = raw.rsplit("```", 1)[0]
                    result = json.loads(raw.strip())
                    break
            except urllib.error.HTTPError as e:
                if e.code == 429 and attempt < 2:
                    wait = 2 ** (attempt + 2)
                    print(f"    Rate limited, waiting {wait}s...", flush=True)
                    time.sleep(wait)
                else:
                    error_body = ""
                    try:
                        error_body = e.read().decode("utf-8")[:300]
                    except Exception:
                        pass
                    print(f"    HTTP {e.code}: {error_body}", flush=True)
                    break
            except json.JSONDecodeError as e:
                print(f"    JSON parse error: {e}", flush=True)
                if attempt < 2:
                    time.sleep(2 ** (attempt + 1))
            except Exception as e:
                print(f"    Error: {e}", flush=True)
                if attempt < 2:
                    time.sleep(2 ** (attempt + 1))

        if not result:
            print(f"  [WARN] Batch {batch_num}/{total_batches} failed, skipping.", flush=True)
            continue

        # Apply results
        mapping = {item['id']: item for item in result if isinstance(item, dict) and 'id' in item}
        for local_idx, (global_idx, post) in enumerate(batch):
            if local_idx in mapping:
                r = mapping[local_idx]
                posts[global_idx]['exp'] = r.get('exp', '')
                posts[global_idx]['qc'] = r.get('qc', '')
                posts[global_idx]['rel'] = r.get('rel', '')
                if 'tx' in r:
                    posts[global_idx]['tx'] = r['tx']
                if 'txd' in r and isinstance(r['txd'], dict):
                    posts[global_idx]['txd'] = r['txd']
                if r.get('qc') == 'questionable':
                    posts[global_idx]['pr'] = 'Questionable'
                explained += 1

        # Save after each batch
        with open(HS_POSTS_PATH, 'w', encoding='utf-8') as f:
            json.dump(posts, f, indent=2, ensure_ascii=False)
            f.write('\n')

        print(f"  Batch {batch_num}/{total_batches}: {explained}/{total} explained", flush=True)
        if batch_start + LLM_BATCH_SIZE < total:
            time.sleep(2)

    print(f"  LLM QA complete: {explained}/{total}", flush=True)
    return explained


# ===================================================================
# Step 5: Quality gate
# ===================================================================
def step5_quality_gate():
    """Remove misclassified / not_relevant posts from hate_speech_posts.json."""
    from datetime import datetime, timezone

    print("\n" + "=" * 60)
    print("STEP 5: Quality Gate")
    print("=" * 60)

    with open(HS_POSTS_PATH, 'r', encoding='utf-8') as f:
        posts = json.load(f)

    to_keep = []
    to_remove = []
    for post in posts:
        qc = (post.get('qc') or '').lower()
        rel = (post.get('rel') or '').lower()
        if qc == 'misclassified' or rel == 'not_relevant':
            to_remove.append(post)
        else:
            to_keep.append(post)

    removed = len(to_remove)
    if removed == 0:
        print(f"  No posts to remove. {len(posts)} remain.", flush=True)
        return 0

    # Archive removed
    archive_dir = os.path.join(REPO_ROOT, "data", "run_history")
    os.makedirs(archive_dir, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    archive_path = os.path.join(archive_dir, f"misclassified_{today}.json")

    existing_archive = []
    if os.path.exists(archive_path):
        with open(archive_path) as f:
            existing_archive = json.load(f)
    existing_archive.extend(to_remove)
    with open(archive_path, 'w') as f:
        json.dump(existing_archive, f, indent=2, default=str)

    with open(HS_POSTS_PATH, 'w', encoding='utf-8') as f:
        json.dump(to_keep, f, indent=2, ensure_ascii=False)
        f.write('\n')

    # Count how many removed were from our backfill
    backfill_removed = sum(1 for p in to_remove if p.get('src') == 'backfill_comments')
    print(f"  Removed {removed} posts ({backfill_removed} from this backfill)", flush=True)
    print(f"  {len(to_keep)} posts remain in dashboard", flush=True)
    print(f"  Archived to {archive_path}", flush=True)
    return removed


# ===================================================================
# Main
# ===================================================================
def main():
    parser = argparse.ArgumentParser(description="Classify unclassified comments — full pipeline")
    parser.add_argument('--step', type=int, default=0,
                        help='Start from step N (1=ML, 2=write master, 3=convert, 4=QA, 5=gate)')
    args = parser.parse_args()
    start_step = args.step or 1

    t0 = time.time()

    # Step 1: ML Classification
    if start_step <= 1:
        df = step1_ml_classify()
    else:
        df = pd.read_csv(UNCLASSIFIED, low_memory=False)

    # Step 2: Write to master CSV
    if start_step <= 2:
        step2_write_master(df)

    # Step 3: Convert to dashboard format
    if start_step <= 3:
        new_posts = step3_convert_to_dashboard(df)
        new_ids = {p['i'] for p in new_posts} if new_posts else None
    else:
        new_ids = None

    # Step 4: LLM QA
    if start_step <= 4:
        step4_llm_qa(new_ids)

    # Step 5: Quality gate
    if start_step <= 5:
        step5_quality_gate()

    elapsed = time.time() - t0
    print(f"\n{'=' * 60}")
    print(f"PIPELINE COMPLETE in {elapsed:.0f}s")
    print(f"{'=' * 60}")


if __name__ == '__main__':
    main()
