"""papers/analysis/disinfo_analysis.py — Analyse disinformation events for Paper D."""
import json
import csv
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
OUT = Path(__file__).resolve().parent

def load_events():
    with open(ROOT / "docs/data/events.json") as f:
        return json.load(f)

def load_claims():
    rows = []
    path = ROOT / "outputs/extracted_disinfo_claims.csv"
    if path.exists():
        with open(path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                rows.append(row)
    return rows

def main():
    events = load_events()
    print(f"Total events: {len(events)}")

    # Country x Event Type
    ct = defaultdict(Counter)
    for e in events:
        ct[e.get("country", "unknown")][e.get("event_type", "unknown")] += 1
    with open(OUT / "disinfo_country_type.csv", "w", newline="") as f:
        types = sorted({e.get("event_type", "unknown") for e in events})
        w = csv.writer(f)
        w.writerow(["Country"] + types + ["Total"])
        for country in sorted(ct):
            counts = [ct[country].get(t, 0) for t in types]
            w.writerow([country] + counts + [sum(counts)])
    print("Wrote disinfo_country_type.csv")

    # Narrative family frequency
    narrative_counts = Counter()
    for e in events:
        for n in e.get("disinfo_narratives", []):
            if isinstance(n, str):
                narrative_counts[n] += 1
            elif isinstance(n, dict):
                narrative_counts[n.get("family", n.get("id", "unknown"))] += 1
    with open(OUT / "disinfo_narrative_families.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Narrative Family", "Event Count"])
        for fam, count in narrative_counts.most_common():
            w.writerow([fam, count])
    print("Wrote disinfo_narrative_families.csv")

    # Event status distribution
    status_counts = Counter(e.get("status", "unknown") for e in events)
    print(f"Event status: {dict(status_counts)}")

    # Actor count
    all_actors = []
    for e in events:
        all_actors.extend(e.get("actors", []))
    print(f"Total actor mentions: {len(all_actors)}")
    print(f"Unique actors: {len(set(str(a) for a in all_actors))}")

    # Claims summary
    claims = load_claims()
    print(f"Extracted claims: {len(claims)}")
    if claims:
        with open(OUT / "disinfo_claims_summary.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["Total Claims", "Unique Events Referenced"])
            event_refs = set()
            for c in claims:
                for key in c:
                    if "event" in key.lower():
                        event_refs.add(c[key])
            w.writerow([len(claims), len(event_refs)])
        print("Wrote disinfo_claims_summary.csv")

if __name__ == "__main__":
    main()
