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
STRATA = {"Hate": 40, "Abusive": 40, "Questionable": 10, "Normal": 10}
NORMAL_EXTRA_PER_COUNTRY = 17
SHARED_OVERLAP = 10
SEED = 42
BLIND_STRIP_FIELDS = ["pr", "co", "gt", "exp", "qc", "rel", "subtopics",
                       "txd_sev", "txd_ins", "txd_idt", "txd_thr", "tx"]


def load_hs_posts():
    with open(ROOT / "docs/data/hate_speech_posts.json") as f:
        return json.load(f)


def load_normal_posts():
    """Load posts classified as Normal from Phoenix CSVs."""
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
    blind = copy.deepcopy(post)
    for field in BLIND_STRIP_FIELDS:
        blind.pop(field, None)
    return blind


def assign_annotators(sample):
    manifest = []
    by_country = defaultdict(list)
    for p in sample:
        by_country[p.get("c", "unknown")].append(p)
    cross_assign = {
        "Kenya": "Somalia",
        "Somalia": "South Sudan",
        "South Sudan": "Kenya",
    }
    for country in COUNTRIES:
        posts = by_country[country]
        questionable = [p for p in posts if p.get("pr") == "Questionable"]
        shared_ids = {p["i"] for p in questionable[:SHARED_OVERLAP]}
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

    sample = []
    for country in COUNTRIES:
        country_sample = stratified_sample(posts, country, STRATA, rng)
        sample.extend(country_sample)
        print(f"{country}: {len(country_sample)} posts sampled")

    normal_pool = load_normal_posts()
    print(f"Loaded {len(normal_pool)} Normal-classified posts from Phoenix")
    for country in COUNTRIES:
        country_normal = [p for p in normal_pool if p.get("c") == country]
        n = min(NORMAL_EXTRA_PER_COUNTRY, len(country_normal))
        extra = rng.sample(country_normal, n) if country_normal else []
        sample.extend(extra)
        print(f"{country}: {n} Normal posts added for FN check")

    print(f"\nTotal sample: {len(sample)} posts")

    with open(OUT / "sample_full.json", "w") as f:
        json.dump(sample, f, indent=2, ensure_ascii=False)
    print(f"Wrote sample_full.json")

    blind = [make_blind(p) for p in sample]
    with open(OUT / "sample_blind.json", "w") as f:
        json.dump(blind, f, indent=2, ensure_ascii=False)
    print(f"Wrote sample_blind.json")

    manifest = assign_annotators(sample)
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
