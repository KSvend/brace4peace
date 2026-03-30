# IRIS Data Collection Plan — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Set up reliable monitoring for 1 month and build a gold-standard annotation workflow (350 posts, 3 human annotators + GPT-4o) to produce formal evaluation metrics for the IRIS journal papers.

**Architecture:** Two independent workstreams — (1) fix and monitor the daily pipeline, (2) build sample selection, blind annotation mode, GPT-4o annotation script, and agreement analysis. All evaluation artifacts go to `papers/evaluation/`.

**Tech Stack:** Python (existing backend stack), TypeScript/React (existing frontend), OpenAI API (GPT-4o for annotation), scikit-learn (Cohen's kappa, P/R/F1), pytest.

**Spec:** `docs/superpowers/specs/2026-03-30-data-collection-plan-design.md`

---

## File Structure

```
papers/evaluation/               # NEW directory
  select_sample.py               # Stratified sample selection
  gpt4o_annotate.py              # GPT-4o blind annotation
  compute_agreement.py           # Agreement metrics + figures
  annotation_guidelines.md       # Guidelines for human annotators
  sample_full.json               # Generated: 350 posts with predictions
  sample_blind.json              # Generated: 350 posts, predictions stripped
  sample_manifest.csv            # Generated: post IDs, strata, assignments

backend/app.py                   # MODIFY: add blind annotation endpoint
supabase/schema.sql              # MODIFY: add blind_annotations table
backend/tests/test_blind_annotation.py  # NEW: tests for blind annotation

.github/workflows/compute-stats.yml    # MODIFY: fix failing workflow
.github/workflows/monitor-health.yml   # NEW: weekly health check
```

---

### Task 1: Fix Failing Refresh HS Stats Workflow

**Files:**
- Modify: `.github/workflows/compute-stats.yml`
- Read: `backend/ingest/compute_stats.py`

- [ ] **Step 1: Check the recent failure logs**

Run: `cd /Users/kmini/Github/IRIS && gh run list --workflow=compute-stats.yml --limit 5`

Then get the logs of the most recent failed run:

Run: `gh run view <run_id> --log-failed`

Read the error output to identify the root cause.

- [ ] **Step 2: Fix the root cause**

The most likely causes are:
- Missing/expired `SUPABASE_SERVICE_KEY` secret
- Schema mismatch in `aggregated_stats` table
- Import error in `backend.ingest.compute_stats`

Fix based on what the logs reveal. If it's a Supabase connection issue, verify secrets are set:

Run: `gh secret list --repo KSvend/IRIS`

- [ ] **Step 3: Test the fix by triggering a manual run**

Run: `gh workflow run compute-stats.yml`

Then monitor:

Run: `gh run list --workflow=compute-stats.yml --limit 1`

Wait for completion and verify success.

- [ ] **Step 4: Commit any workflow changes**

```bash
git add .github/workflows/compute-stats.yml
git commit -m "fix: repair compute-stats workflow"
```

---

### Task 2: Create Weekly Health Check Workflow

**Files:**
- Create: `.github/workflows/monitor-health.yml`

- [ ] **Step 1: Write the health check workflow**

```yaml
name: Pipeline Health Check

on:
  schedule:
    - cron: '0 8 * * 1'  # Monday 08:00 UTC
  workflow_dispatch:

jobs:
  health:
    runs-on: ubuntu-latest
    steps:
      - name: Check recent monitor runs
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          echo "=== Monitor Run Health Check ==="
          echo "Checking runs from the past 7 days..."

          # Count successful and failed monitor runs
          RUNS=$(gh run list \
            --repo ${{ github.repository }} \
            --workflow "MERLx IRIS Monitor" \
            --created ">$(date -d '7 days ago' -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -v-7d -u +%Y-%m-%dT%H:%M:%SZ)" \
            --json conclusion,createdAt \
            --limit 20)

          TOTAL=$(echo "$RUNS" | jq 'length')
          SUCCESS=$(echo "$RUNS" | jq '[.[] | select(.conclusion == "success")] | length')
          FAILED=$(echo "$RUNS" | jq '[.[] | select(.conclusion == "failure")] | length')

          echo "Total runs: $TOTAL"
          echo "Successful: $SUCCESS"
          echo "Failed: $FAILED"

          # Expect at least 12 runs in 7 days (2x daily = 14 expected)
          if [ "$TOTAL" -lt 10 ]; then
            echo "::warning::Low run count: only $TOTAL runs in past 7 days (expected ~14)"
          fi

          if [ "$FAILED" -gt 2 ]; then
            echo "::error::High failure rate: $FAILED failed runs in past 7 days"
            exit 1
          fi

          echo "Pipeline health: OK ($SUCCESS/$TOTAL successful)"
```

- [ ] **Step 2: Test by triggering manually**

Run: `cd /Users/kmini/Github/IRIS && git add .github/workflows/monitor-health.yml && git commit -m "ci: add weekly pipeline health check workflow" && git push origin main`

Then trigger:

Run: `gh workflow run monitor-health.yml`

Monitor: `gh run list --workflow=monitor-health.yml --limit 1`

---

### Task 3: Create Sample Selection Script

**Files:**
- Create: `papers/evaluation/select_sample.py`
- Read: `docs/data/hate_speech_posts.json`
- Read: `data/phoenix_csvs/` (for Normal-classified posts)

- [ ] **Step 1: Write the sample selection script**

```python
"""papers/evaluation/select_sample.py — Draw stratified sample for gold-standard evaluation."""
import json
import csv
import random
import copy
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
OUT = Path(__file__).resolve().parent

COUNTRIES = ["Kenya", "Somalia", "South Sudan"]
# Per-country targets from pipeline-positive pool
STRATA = {"Hate": 40, "Abusive": 40, "Questionable": 10, "Normal": 10}
NORMAL_EXTRA_PER_COUNTRY = 17  # Additional Normal-classified posts for FN check
SHARED_OVERLAP = 10  # Per country, from Questionable, for IAA

SEED = 42

BLIND_STRIP_FIELDS = ["pr", "co", "gt", "exp", "qc", "rel", "subtopics",
                       "txd_sev", "txd_ins", "txd_idt", "txd_thr", "tx"]


def load_hs_posts():
    with open(ROOT / "docs/data/hate_speech_posts.json") as f:
        return json.load(f)


def load_normal_posts():
    """Load posts classified as Normal from the Phoenix CSVs."""
    normal = []
    csv_dir = ROOT / "data" / "phoenix_csvs"
    if not csv_dir.exists():
        print(f"Warning: {csv_dir} not found, skipping Normal posts from Phoenix")
        return normal
    for csv_file in csv_dir.glob("*.csv"):
        try:
            with open(csv_file, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    pred = row.get("EA_HS_pred", "")
                    text = row.get("post_text_pi", "") or row.get("comment_text_pi", "")
                    country = row.get("country", "")
                    if pred == "Normal" and text and len(text) >= 10 and country in COUNTRIES:
                        normal.append({
                            "i": row.get("post_id", row.get("comment_id", "")),
                            "t": text[:500],
                            "d": row.get("post_date", row.get("comment_date", "")),
                            "c": country,
                            "p": row.get("platform", ""),
                            "pr": "Normal",
                            "co": float(row.get("EA_HS_conf", 0) or 0),
                        })
        except Exception as e:
            print(f"Warning: error reading {csv_file.name}: {e}")
    return normal


def stratified_sample(posts, country, strata, rng):
    """Draw stratified sample for one country."""
    by_pred = defaultdict(list)
    for p in posts:
        if p.get("c") == country:
            by_pred[p.get("pr", "unknown")].append(p)

    sample = []
    for pred_class, target in strata.items():
        pool = by_pred.get(pred_class, [])
        n = min(target, len(pool))
        sample.extend(rng.sample(pool, n))
        if n < target:
            print(f"  Warning: {country}/{pred_class}: wanted {target}, got {n}")
    return sample


def make_blind(post):
    """Strip prediction fields for blind annotation."""
    blind = copy.deepcopy(post)
    for field in BLIND_STRIP_FIELDS:
        blind.pop(field, None)
    return blind


def assign_annotators(sample, shared_per_country=SHARED_OVERLAP):
    """Assign posts to annotators and designate shared overlap posts."""
    manifest = []
    # Group by country
    by_country = defaultdict(list)
    for p in sample:
        by_country[p.get("c", "unknown")].append(p)

    # Cross-country assignment for IAA overlap
    country_list = list(COUNTRIES)
    cross_assign = {
        country_list[0]: country_list[1],  # Kenya annotator also labels Somalia shared
        country_list[1]: country_list[2],  # Somalia annotator also labels SS shared
        country_list[2]: country_list[0],  # SS annotator also labels Kenya shared
    }

    for country in COUNTRIES:
        posts = by_country[country]
        # Mark Questionable posts as shared (first N)
        questionable = [p for p in posts if p.get("pr") == "Questionable"]
        shared_ids = {p["i"] for p in questionable[:shared_per_country]}

        for p in posts:
            is_shared = p["i"] in shared_ids
            manifest.append({
                "post_id": p["i"],
                "country": country,
                "prediction": p.get("pr", ""),
                "stratum": p.get("pr", ""),
                "primary_annotator": f"annotator_{country.lower().replace(' ', '_')}",
                "is_shared": is_shared,
                "cross_annotator": f"annotator_{cross_assign[country].lower().replace(' ', '_')}" if is_shared else "",
                "source": "pipeline_positive",
            })

    return manifest


def main():
    rng = random.Random(SEED)
    posts = load_hs_posts()
    print(f"Loaded {len(posts)} pipeline-positive posts")

    # Draw stratified sample per country
    sample = []
    for country in COUNTRIES:
        country_sample = stratified_sample(posts, country, STRATA, rng)
        sample.extend(country_sample)
        print(f"{country}: {len(country_sample)} posts sampled")

    # Draw Normal-classified posts from Phoenix CSVs
    normal_pool = load_normal_posts()
    print(f"Loaded {len(normal_pool)} Normal-classified posts from Phoenix")
    for country in COUNTRIES:
        country_normal = [p for p in normal_pool if p.get("c") == country]
        n = min(NORMAL_EXTRA_PER_COUNTRY, len(country_normal))
        extra = rng.sample(country_normal, n) if country_normal else []
        sample.extend(extra)
        print(f"{country}: {n} Normal posts added for FN check")

    print(f"\nTotal sample: {len(sample)} posts")

    # Write full sample (with predictions)
    with open(OUT / "sample_full.json", "w") as f:
        json.dump(sample, f, indent=2, ensure_ascii=False)
    print(f"Wrote sample_full.json")

    # Write blind sample (predictions stripped)
    blind = [make_blind(p) for p in sample]
    with open(OUT / "sample_blind.json", "w") as f:
        json.dump(blind, f, indent=2, ensure_ascii=False)
    print(f"Wrote sample_blind.json")

    # Write manifest
    manifest = assign_annotators(sample)
    # Add Normal-extra posts to manifest
    for p in sample:
        if not any(m["post_id"] == p["i"] for m in manifest):
            manifest.append({
                "post_id": p["i"],
                "country": p.get("c", ""),
                "prediction": p.get("pr", ""),
                "stratum": "normal_extra",
                "primary_annotator": f"annotator_{p.get('c', '').lower().replace(' ', '_')}",
                "is_shared": False,
                "cross_annotator": "",
                "source": "normal_fn_check",
            })

    with open(OUT / "sample_manifest.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["post_id", "country", "prediction", "stratum",
                                           "primary_annotator", "is_shared", "cross_annotator", "source"])
        w.writeheader()
        w.writerows(manifest)
    print(f"Wrote sample_manifest.csv ({len(manifest)} rows)")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the script**

Run: `cd /Users/kmini/Github/IRIS && mkdir -p papers/evaluation && python papers/evaluation/select_sample.py`

Expected: Three output files created. Console shows per-country counts totaling ~350 posts.

- [ ] **Step 3: Verify the sample**

Run: `python -c "import json; d=json.load(open('papers/evaluation/sample_full.json')); print(len(d)); print(set(p.get('c') for p in d))"`

Expected: ~350 posts across 3 countries.

Run: `python -c "import json; d=json.load(open('papers/evaluation/sample_blind.json')); print(any('pr' in p for p in d))"`

Expected: `False` (no prediction fields in blind version).

- [ ] **Step 4: Commit**

```bash
git add papers/evaluation/
git commit -m "papers: add sample selection script and draw 350-post evaluation set"
```

---

### Task 4: Write Annotation Guidelines

**Files:**
- Create: `papers/evaluation/annotation_guidelines.md`

- [ ] **Step 1: Write the guidelines document**

```markdown
# IRIS Hate Speech Annotation Guidelines

## Task

For each post, assign:
1. **Classification**: Normal, Abusive, or Hate
2. **Subtype** (if Abusive or Hate): one of the 8 categories below
3. **Confidence**: Low, Medium, or High

## Definitions

### Classification

**Normal** — Neutral, informational, or positive content. No harmful language targeting individuals or groups. Includes news reporting, factual statements, and peace-building content.

**Abusive** — Contains profanity, insults, disrespect, or aggressive language, but does NOT target individuals or groups based on their identity (ethnicity, religion, clan, nationality, gender). Example: general insults directed at a specific person's actions, not their group identity.

**Hate** — Content that attacks, dehumanizes, or incites violence against individuals or groups based on protected identity characteristics: ethnicity, religion, clan, nationality, or gender. Includes direct threats, dehumanizing language, calls for exclusion, and incitement to discrimination or violence.

### Subtypes (assign one if Abusive or Hate)

| Subtype | Definition |
|---------|-----------|
| Ethnic Targeting | Targets specific ethnic groups (e.g., Nuer, Dinka, Kikuyu, Luo, Bantu) |
| Clan Targeting | Targets specific clans (e.g., Hawiye, Darod, Isaaq — primarily Somalia) |
| Political Incitement | Attacks political figures/parties based on identity, calls for political violence |
| Religious Incitement | Targets religious groups or uses religious justification for violence |
| Dehumanisation | Compares people to animals, vermin, disease; denies humanity |
| Anti-Foreign | Targets foreigners, refugees, diaspora, or specific nationalities |
| General Abuse | Abusive language not fitting other categories |
| Gendered Violence | Targets based on gender; includes threats of sexual violence |

## Important Notes

- **Language**: Posts may be in English, Swahili, Somali, Arabic, or mixed. Classify based on meaning, not language.
- **Context matters**: A word that is hateful in one context may be neutral in another. Consider the full post.
- **Sarcasm/irony**: If sarcastic but the intent is clearly hateful, classify as Hate.
- **News reporting**: Reporting about hate speech is Normal, not Hate. The post must itself contain hate speech.
- **Confidence**: Use Low if you are uncertain about your classification; Medium if fairly confident; High if very confident.
```

- [ ] **Step 2: Commit**

```bash
git add papers/evaluation/annotation_guidelines.md
git commit -m "papers: add annotation guidelines for gold-standard evaluation"
```

---

### Task 5: Add Blind Annotation Support to Backend

**Files:**
- Modify: `backend/app.py`
- Modify: `supabase/schema.sql`
- Create: `backend/tests/test_blind_annotation.py`

- [ ] **Step 1: Add blind_annotations table to schema**

Add to the end of `supabase/schema.sql`:

```sql
CREATE TABLE blind_annotations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id         TEXT NOT NULL,
    reviewer        TEXT NOT NULL,
    pass            INT NOT NULL CHECK (pass IN (1, 2)),
    classification  TEXT NOT NULL CHECK (classification IN ('Normal', 'Abusive', 'Hate')),
    subtype         TEXT,
    confidence      TEXT CHECK (confidence IN ('Low', 'Medium', 'High')),
    note            TEXT,
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_blind_post ON blind_annotations(post_id);
CREATE INDEX idx_blind_reviewer ON blind_annotations(reviewer);
```

- [ ] **Step 2: Add blind annotation endpoint to backend**

Add to `backend/app.py` after the existing `/posts/annotate` endpoint:

```python
class BlindAnnotationRequest(BaseModel):
    post_id: str
    reviewer_name: str
    pass_number: int  # 1 = blind, 2 = correction
    classification: str  # Normal, Abusive, Hate
    subtype: str | None = None
    confidence: str | None = None  # Low, Medium, High
    note: str | None = None


@app.post("/posts/blind-annotate")
async def blind_annotate(req: BlindAnnotationRequest, _=Depends(verify_api_key)):
    client = get_client()
    client.table("blind_annotations").insert({
        "post_id": req.post_id,
        "reviewer": req.reviewer_name,
        "pass": req.pass_number,
        "classification": req.classification,
        "subtype": req.subtype,
        "confidence": req.confidence,
        "note": req.note,
    }).execute()
    return {"post_id": req.post_id, "pass": req.pass_number, "status": "saved"}
```

Also add a blind review queue endpoint that serves posts without predictions:

```python
@app.get("/posts/blind-review-queue")
async def blind_review_queue(
    reviewer: str,
    limit: int = 20,
    offset: int = 0,
    _=Depends(verify_api_key),
):
    """Serve evaluation posts with predictions stripped for blind annotation."""
    sample_path = Path(__file__).resolve().parent.parent / "papers" / "evaluation" / "sample_blind.json"
    manifest_path = Path(__file__).resolve().parent.parent / "papers" / "evaluation" / "sample_manifest.csv"

    if not sample_path.exists():
        raise HTTPException(404, "Blind sample not generated yet. Run select_sample.py first.")

    blind_posts = json.loads(sample_path.read_text())
    # Filter to posts assigned to this reviewer
    assigned_ids = set()
    if manifest_path.exists():
        import csv as csv_mod
        with open(manifest_path, newline="") as f:
            for row in csv_mod.DictReader(f):
                if row["primary_annotator"] == reviewer or row["cross_annotator"] == reviewer:
                    assigned_ids.add(row["post_id"])

    if assigned_ids:
        blind_posts = [p for p in blind_posts if p.get("i") in assigned_ids]

    total = len(blind_posts)
    page = blind_posts[offset:offset + limit]
    return {"posts": page, "total": total}
```

- [ ] **Step 3: Write test for blind annotation endpoint**

Create `backend/tests/test_blind_annotation.py`:

```python
import pytest
from unittest.mock import MagicMock


@pytest.mark.asyncio
async def test_blind_annotate(client, mocker):
    mock_table = MagicMock()
    mock_table.insert.return_value.execute.return_value = MagicMock()
    mock_client = MagicMock()
    mock_client.table.return_value = mock_table
    mocker.patch("backend.app.get_client", return_value=mock_client)

    resp = await client.post(
        "/posts/blind-annotate",
        json={
            "post_id": "test-123",
            "reviewer_name": "annotator_kenya",
            "pass_number": 1,
            "classification": "Hate",
            "subtype": "Ethnic Targeting",
            "confidence": "High",
        },
        headers={"X-API-Key": "test-api-key"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["post_id"] == "test-123"
    assert data["pass"] == 1
    assert data["status"] == "saved"
    mock_client.table.assert_called_with("blind_annotations")


@pytest.mark.asyncio
async def test_blind_annotate_minimal(client, mocker):
    mock_table = MagicMock()
    mock_table.insert.return_value.execute.return_value = MagicMock()
    mock_client = MagicMock()
    mock_client.table.return_value = mock_table
    mocker.patch("backend.app.get_client", return_value=mock_client)

    resp = await client.post(
        "/posts/blind-annotate",
        json={
            "post_id": "test-456",
            "reviewer_name": "annotator_somalia",
            "pass_number": 1,
            "classification": "Normal",
        },
        headers={"X-API-Key": "test-api-key"},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_blind_review_queue(client, mocker, tmp_path):
    sample = [
        {"i": "p1", "t": "test post", "d": "2026-01-01", "c": "Kenya", "p": "x"},
        {"i": "p2", "t": "another post", "d": "2026-01-02", "c": "Somalia", "p": "facebook"},
    ]
    import json
    sample_path = tmp_path / "sample_blind.json"
    sample_path.write_text(json.dumps(sample))

    mocker.patch(
        "backend.app.Path",
        side_effect=lambda *a: tmp_path / "sample_blind.json"
        if "sample_blind" in str(a) else Path(*a),
    )
    # Simpler: just mock the file read
    mocker.patch("pathlib.Path.exists", return_value=True)
    mocker.patch("pathlib.Path.read_text", return_value=json.dumps(sample))

    resp = await client.get(
        "/posts/blind-review-queue?reviewer=annotator_kenya",
        headers={"X-API-Key": "test-api-key"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "posts" in data
    assert "total" in data
```

- [ ] **Step 4: Run tests**

Run: `cd /Users/kmini/Github/IRIS && python -m pytest backend/tests/test_blind_annotation.py -v`

Expected: All tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app.py supabase/schema.sql backend/tests/test_blind_annotation.py
git commit -m "feat: add blind annotation endpoint and schema for gold-standard evaluation"
```

---

### Task 5b: Frontend Blind Mode (Deferred)

**Note:** The spec calls for a blind annotation mode in `PostDrillDown.tsx` that hides prediction badges. The backend blind review queue endpoint (Task 5) already serves posts without predictions. Two options for the frontend:

1. **Quick path:** Annotators use a simple standalone page that fetches from `/posts/blind-review-queue` and renders only text/date/country with label buttons. This can be a single new page component.
2. **Full path:** Add a `?blind=true` URL parameter to PostDrillDown.tsx that conditionally hides the prediction badge (lines 277-290) and toxicity pills (lines 308-312).

**Recommendation:** Option 1 is faster and avoids touching the production dashboard. Build a minimal `pages/annotate.tsx` or similar. Implement this when annotators are ready to start — it does not block the other tasks.

---

### Task 6: Create GPT-4o Annotation Script

**Files:**
- Create: `papers/evaluation/gpt4o_annotate.py`

- [ ] **Step 1: Add openai to requirements**

Run: `cd /Users/kmini/Github/IRIS && echo "openai>=1.30.0" >> backend/requirements.txt`

- [ ] **Step 2: Write the GPT-4o annotation script**

```python
"""papers/evaluation/gpt4o_annotate.py — Run GPT-4o blind annotation on evaluation sample."""
import json
import os
import time
from pathlib import Path

try:
    from openai import OpenAI
except ImportError:
    print("openai not installed. Run: pip install openai")
    exit(1)

ROOT = Path(__file__).resolve().parent.parent.parent
OUT = Path(__file__).resolve().parent

SYSTEM_PROMPT = """You are classifying social media posts from Kenya, Somalia, and South Sudan for hate speech content.

For each post, assign:
1. classification: "Normal", "Abusive", or "Hate"
2. subtype: one of the following (only if Abusive or Hate, otherwise null):
   - "Ethnic Targeting", "Clan Targeting", "Political Incitement", "Religious Incitement",
     "Dehumanisation", "Anti-Foreign", "General Abuse", "Gendered Violence"
3. confidence: "Low", "Medium", or "High"
4. reasoning: 1-2 sentences explaining your decision

Definitions:
- Normal: Neutral, informational, or positive content. No harmful language.
- Abusive: Profanity, insults, or aggressive language NOT targeting group identity.
- Hate: Attacks, dehumanizes, or incites violence against groups based on ethnicity, religion, clan, nationality, or gender.

Respond ONLY with valid JSON: {"classification": "...", "subtype": "..." or null, "confidence": "...", "reasoning": "..."}"""

FEW_SHOT_EXAMPLES = [
    {"role": "user", "content": "Post: 'The government needs to improve healthcare services in rural areas'"},
    {"role": "assistant", "content": '{"classification": "Normal", "subtype": null, "confidence": "High", "reasoning": "Factual policy statement with no harmful language."}'},
    {"role": "user", "content": "Post: 'These people are cockroaches that must be swept from our land'"},
    {"role": "assistant", "content": '{"classification": "Hate", "subtype": "Dehumanisation", "confidence": "High", "reasoning": "Dehumanizing language comparing a group to vermin with a call for removal."}'},
    {"role": "user", "content": "Post: 'That politician is a complete idiot and liar'"},
    {"role": "assistant", "content": '{"classification": "Abusive", "subtype": "General Abuse", "confidence": "Medium", "reasoning": "Personal insults directed at an individual\\'s actions, not group identity."}'},
]


def annotate_post(client, text, post_id):
    """Send a single post to GPT-4o for classification."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *FEW_SHOT_EXAMPLES,
        {"role": "user", "content": f"Post: '{text}'"},
    ]
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0,
            max_tokens=200,
            response_format={"type": "json_object"},
        )
        result = json.loads(response.choices[0].message.content)
        result["post_id"] = post_id
        result["model"] = "gpt-4o"
        return result
    except Exception as e:
        print(f"  Error on {post_id}: {e}")
        return {
            "post_id": post_id,
            "classification": "ERROR",
            "subtype": None,
            "confidence": None,
            "reasoning": str(e),
            "model": "gpt-4o",
        }


def main():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Set OPENAI_API_KEY environment variable")
        exit(1)

    client = OpenAI(api_key=api_key)

    sample_path = OUT / "sample_blind.json"
    if not sample_path.exists():
        print("Run select_sample.py first to generate sample_blind.json")
        exit(1)

    posts = json.loads(sample_path.read_text())
    print(f"Annotating {len(posts)} posts with GPT-4o...")

    results = []
    for i, post in enumerate(posts):
        text = post.get("t", "")
        post_id = post.get("i", f"unknown_{i}")
        if not text or len(text) < 5:
            print(f"  Skipping {post_id}: empty/short text")
            continue
        result = annotate_post(client, text, post_id)
        results.append(result)
        if (i + 1) % 50 == 0:
            print(f"  Progress: {i + 1}/{len(posts)}")
            # Save intermediate results
            with open(OUT / "gpt4o_annotations.json", "w") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)

    with open(OUT / "gpt4o_annotations.json", "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # Summary
    from collections import Counter
    classes = Counter(r["classification"] for r in results)
    print(f"\nDone. {len(results)} posts annotated.")
    print(f"Distribution: {dict(classes)}")
    errors = sum(1 for r in results if r["classification"] == "ERROR")
    if errors:
        print(f"Errors: {errors}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Test with a dry run (first 5 posts)**

Run: `cd /Users/kmini/Github/IRIS && OPENAI_API_KEY=<your-key> python -c "
import json
from papers.evaluation.gpt4o_annotate import annotate_post
from openai import OpenAI
import os
client = OpenAI(api_key=os.environ['OPENAI_API_KEY'])
posts = json.load(open('papers/evaluation/sample_blind.json'))[:5]
for p in posts:
    r = annotate_post(client, p.get('t',''), p.get('i',''))
    print(f'{r[\"post_id\"]}: {r[\"classification\"]} ({r[\"confidence\"]})')
"`

Expected: 5 classifications printed, each Normal/Abusive/Hate with confidence.

- [ ] **Step 4: Commit**

```bash
git add papers/evaluation/gpt4o_annotate.py backend/requirements.txt
git commit -m "papers: add GPT-4o blind annotation script"
```

---

### Task 7: Create Agreement Analysis Script

**Files:**
- Create: `papers/evaluation/compute_agreement.py`

- [ ] **Step 1: Write the agreement analysis script**

```python
"""papers/evaluation/compute_agreement.py — Compute inter-annotator agreement and evaluation metrics."""
import json
import csv
from collections import Counter, defaultdict
from pathlib import Path

try:
    from sklearn.metrics import (
        cohen_kappa_score,
        precision_recall_fscore_support,
        confusion_matrix,
        classification_report,
    )
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
except ImportError:
    print("Install: pip install scikit-learn matplotlib numpy")
    exit(1)

ROOT = Path(__file__).resolve().parent.parent.parent
OUT = Path(__file__).resolve().parent
FIGURES = OUT.parent / "figures"
LABELS = ["Normal", "Abusive", "Hate"]


def load_human_annotations():
    """Load human blind annotations from Supabase export or local JSON."""
    path = OUT / "human_annotations.json"
    if path.exists():
        return json.loads(path.read_text())
    print("Warning: human_annotations.json not found. Generate from Supabase after annotation.")
    return []


def load_gpt4o_annotations():
    path = OUT / "gpt4o_annotations.json"
    if path.exists():
        return json.loads(path.read_text())
    print("Warning: gpt4o_annotations.json not found. Run gpt4o_annotate.py first.")
    return []


def load_pipeline_predictions():
    path = OUT / "sample_full.json"
    if path.exists():
        return {p["i"]: p for p in json.loads(path.read_text())}
    return {}


def compute_kappa(labels_a, labels_b, name_a, name_b):
    """Compute Cohen's kappa between two annotators."""
    if len(labels_a) != len(labels_b):
        print(f"  Warning: length mismatch {name_a}={len(labels_a)} vs {name_b}={len(labels_b)}")
        min_len = min(len(labels_a), len(labels_b))
        labels_a, labels_b = labels_a[:min_len], labels_b[:min_len]
    kappa = cohen_kappa_score(labels_a, labels_b)
    agree = sum(a == b for a, b in zip(labels_a, labels_b))
    total = len(labels_a)
    return {"kappa": round(kappa, 3), "agreement": f"{agree}/{total}", "pct": round(agree / total * 100, 1)}


def compute_prf(gold, predicted, name):
    """Compute precision/recall/F1 against gold standard."""
    p, r, f, s = precision_recall_fscore_support(gold, predicted, labels=LABELS, average=None, zero_division=0)
    report = {}
    for i, label in enumerate(LABELS):
        report[label] = {"precision": round(p[i], 3), "recall": round(r[i], 3), "f1": round(f[i], 3), "support": int(s[i])}
    # Macro average
    p_m, r_m, f_m, _ = precision_recall_fscore_support(gold, predicted, labels=LABELS, average="macro", zero_division=0)
    report["macro_avg"] = {"precision": round(p_m, 3), "recall": round(r_m, 3), "f1": round(f_m, 3)}
    return report


def plot_confusion(gold, predicted, title, filename):
    """Plot and save a confusion matrix."""
    cm = confusion_matrix(gold, predicted, labels=LABELS)
    fig, ax = plt.subplots(figsize=(6, 5))
    im = ax.imshow(cm, interpolation="nearest", cmap="Blues")
    ax.set(xticks=range(len(LABELS)), yticks=range(len(LABELS)),
           xticklabels=LABELS, yticklabels=LABELS,
           ylabel="Gold Standard (Human)", xlabel="Predicted")
    ax.set_title(title)
    for i in range(len(LABELS)):
        for j in range(len(LABELS)):
            ax.text(j, i, str(cm[i, j]), ha="center", va="center",
                    color="white" if cm[i, j] > cm.max() / 2 else "black")
    plt.colorbar(im)
    plt.tight_layout()
    plt.savefig(FIGURES / filename, dpi=150)
    plt.close()
    print(f"Saved {filename}")


def main():
    human = load_human_annotations()
    gpt4o = load_gpt4o_annotations()
    pipeline = load_pipeline_predictions()

    if not human and not gpt4o:
        print("No annotations available yet. Run this after annotation is complete.")
        print("Generating template agreement_metrics.json with placeholder structure...")
        template = {
            "status": "pending_annotations",
            "note": "Re-run after human_annotations.json and gpt4o_annotations.json are available",
        }
        with open(OUT / "agreement_metrics.json", "w") as f:
            json.dump(template, f, indent=2)
        return

    metrics = {}

    # Index annotations by post_id
    human_by_id = {a["post_id"]: a for a in human} if human else {}
    gpt4o_by_id = {a["post_id"]: a for a in gpt4o} if gpt4o else {}

    # Find common post IDs
    common_ids = sorted(set(human_by_id.keys()) & set(gpt4o_by_id.keys()) & set(pipeline.keys()))
    print(f"Posts with all 3 annotations: {len(common_ids)}")

    if common_ids:
        human_labels = [human_by_id[pid]["classification"] for pid in common_ids]
        gpt4o_labels = [gpt4o_by_id[pid]["classification"] for pid in common_ids]
        pipeline_labels = [pipeline[pid].get("pr", "unknown") for pid in common_ids]

        # Kappa scores
        metrics["kappa_human_gpt4o"] = compute_kappa(human_labels, gpt4o_labels, "Human", "GPT-4o")
        metrics["kappa_human_pipeline"] = compute_kappa(human_labels, pipeline_labels, "Human", "Pipeline")
        metrics["kappa_gpt4o_pipeline"] = compute_kappa(gpt4o_labels, pipeline_labels, "GPT-4o", "Pipeline")

        # P/R/F1 against human gold standard
        metrics["pipeline_vs_human"] = compute_prf(human_labels, pipeline_labels, "Pipeline")
        metrics["gpt4o_vs_human"] = compute_prf(human_labels, gpt4o_labels, "GPT-4o")

        # Per-country breakdown
        for country in ["Kenya", "Somalia", "South Sudan"]:
            c_ids = [pid for pid in common_ids if pipeline[pid].get("c") == country]
            if len(c_ids) >= 10:
                c_human = [human_by_id[pid]["classification"] for pid in c_ids]
                c_pipeline = [pipeline[pid].get("pr", "unknown") for pid in c_ids]
                c_gpt4o = [gpt4o_by_id[pid]["classification"] for pid in c_ids]
                metrics[f"kappa_human_pipeline_{country}"] = compute_kappa(c_human, c_pipeline, "Human", "Pipeline")
                metrics[f"kappa_human_gpt4o_{country}"] = compute_kappa(c_human, c_gpt4o, "Human", "GPT-4o")
                metrics[f"pipeline_prf_{country}"] = compute_prf(c_human, c_pipeline, f"Pipeline-{country}")

        # Confusion matrices
        plot_confusion(human_labels, pipeline_labels, "IRIS Pipeline vs Human Gold Standard", "fig_confusion_pipeline.png")
        plot_confusion(human_labels, gpt4o_labels, "GPT-4o vs Human Gold Standard", "fig_confusion_gpt4o.png")

    # Save metrics
    with open(OUT / "agreement_metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"Wrote agreement_metrics.json")

    # Write narrative report
    report = ["# Gold-Standard Evaluation — Agreement Report\n"]
    report.append(f"Posts evaluated: {len(common_ids)}\n")
    if "kappa_human_gpt4o" in metrics:
        report.append(f"## Inter-Annotator Agreement (Cohen's Kappa)\n")
        report.append(f"| Pair | Kappa | Agreement |")
        report.append(f"|------|-------|-----------|")
        for key in ["kappa_human_gpt4o", "kappa_human_pipeline", "kappa_gpt4o_pipeline"]:
            if key in metrics:
                m = metrics[key]
                name = key.replace("kappa_", "").replace("_", " vs. ").title()
                report.append(f"| {name} | {m['kappa']} | {m['pct']}% |")
        report.append("")

    if "pipeline_vs_human" in metrics:
        report.append(f"## Pipeline Performance (vs. Human Gold Standard)\n")
        report.append(f"| Class | Precision | Recall | F1 | Support |")
        report.append(f"|-------|-----------|--------|----|---------|")
        for label in LABELS:
            m = metrics["pipeline_vs_human"].get(label, {})
            report.append(f"| {label} | {m.get('precision','-')} | {m.get('recall','-')} | {m.get('f1','-')} | {m.get('support','-')} |")
        macro = metrics["pipeline_vs_human"].get("macro_avg", {})
        report.append(f"| **Macro Avg** | {macro.get('precision','-')} | {macro.get('recall','-')} | {macro.get('f1','-')} | |")
        report.append("")

    with open(OUT / "agreement_report.md", "w") as f:
        f.write("\n".join(report))
    print(f"Wrote agreement_report.md")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Install scikit-learn**

Run: `pip install scikit-learn`

- [ ] **Step 3: Run the script (will produce placeholder since no human annotations yet)**

Run: `cd /Users/kmini/Github/IRIS && python papers/evaluation/compute_agreement.py`

Expected: "No annotations available yet" message, creates template `agreement_metrics.json`.

- [ ] **Step 4: Commit**

```bash
git add papers/evaluation/compute_agreement.py
git commit -m "papers: add agreement analysis script (kappa, P/R/F1, confusion matrices)"
```

---

### Task 8: End-of-Month Data Refresh Script

**Files:**
- Create: `papers/evaluation/refresh_paper_data.sh`

- [ ] **Step 1: Write the refresh script**

```bash
#!/bin/bash
# papers/evaluation/refresh_paper_data.sh — Regenerate all paper analysis with latest data.
set -e

cd "$(dirname "$0")/../.."
echo "=== IRIS Paper Data Refresh ==="
echo "Date: $(date -u +%Y-%m-%d)"

echo ""
echo "--- Step 1: Data summary ---"
python papers/analysis/load_data.py

echo ""
echo "--- Step 2: HS cross-tabulations ---"
python papers/analysis/hs_crosstabs.py

echo ""
echo "--- Step 3: Disinformation analysis ---"
python papers/analysis/disinfo_analysis.py

echo ""
echo "--- Step 4: Pipeline metrics ---"
python papers/analysis/pipeline_metrics.py

echo ""
echo "--- Step 5: Generate figures ---"
python papers/analysis/generate_figures.py

echo ""
echo "--- Step 6: Agreement analysis (if annotations available) ---"
python papers/evaluation/compute_agreement.py || echo "Skipped: annotations not yet available"

echo ""
echo "=== Refresh complete ==="
echo "Review papers/analysis/ and papers/figures/ for updated outputs."
echo "Don't forget to update paper drafts with new numbers!"
```

- [ ] **Step 2: Make it executable and test**

Run: `chmod +x /Users/kmini/Github/IRIS/papers/evaluation/refresh_paper_data.sh`

Run: `cd /Users/kmini/Github/IRIS && bash papers/evaluation/refresh_paper_data.sh`

Expected: All scripts run successfully, outputs updated.

- [ ] **Step 3: Commit**

```bash
git add papers/evaluation/refresh_paper_data.sh
git commit -m "papers: add end-of-month data refresh script"
```

---

### Task 9: Export Human Annotations Script

**Files:**
- Create: `papers/evaluation/export_annotations.py`

This script will be run after human annotators complete their work to pull annotations from Supabase into a local JSON file for the agreement analysis.

- [ ] **Step 1: Write the export script**

```python
"""papers/evaluation/export_annotations.py — Export human annotations from Supabase to JSON."""
import json
import os
from pathlib import Path

try:
    from supabase import create_client
except ImportError:
    print("supabase not installed. Run: pip install supabase")
    exit(1)

OUT = Path(__file__).resolve().parent


def main():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        print("Set SUPABASE_URL and SUPABASE_KEY environment variables")
        exit(1)

    client = create_client(url, key)

    # Fetch pass-1 (blind) annotations
    result = client.table("blind_annotations").select("*").eq("pass", 1).execute()
    annotations = result.data if result.data else []
    print(f"Fetched {len(annotations)} blind annotations (pass 1)")

    # Normalize field names for agreement analysis
    normalized = []
    for a in annotations:
        normalized.append({
            "post_id": a["post_id"],
            "reviewer": a["reviewer"],
            "classification": a["classification"],
            "subtype": a.get("subtype"),
            "confidence": a.get("confidence"),
            "note": a.get("note"),
            "created_at": a.get("created_at"),
        })

    with open(OUT / "human_annotations.json", "w") as f:
        json.dump(normalized, f, indent=2, ensure_ascii=False)
    print(f"Wrote human_annotations.json ({len(normalized)} annotations)")

    # Also fetch pass-2 (correction) annotations
    result2 = client.table("blind_annotations").select("*").eq("pass", 2).execute()
    corrections = result2.data if result2.data else []
    print(f"Fetched {len(corrections)} correction annotations (pass 2)")

    if corrections:
        with open(OUT / "pass2_corrections.json", "w") as f:
            json.dump(corrections, f, indent=2, ensure_ascii=False)
        print(f"Wrote pass2_corrections.json")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Commit**

```bash
git add papers/evaluation/export_annotations.py
git commit -m "papers: add script to export human annotations from Supabase"
```

---

### Task 10: Push All Changes

- [ ] **Step 1: Verify everything is committed**

Run: `cd /Users/kmini/Github/IRIS && git status`

Expected: Clean working tree.

- [ ] **Step 2: Push**

Run: `git push origin main`
