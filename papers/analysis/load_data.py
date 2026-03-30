"""papers/analysis/load_data.py — Load and summarise IRIS datasets."""
import json
import csv
import os
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent

def load_hs_posts():
    """Load hate speech posts from docs/data/hate_speech_posts.json."""
    with open(ROOT / "docs/data/hate_speech_posts.json") as f:
        return json.load(f)

def load_events():
    """Load disinformation events from docs/data/events.json."""
    with open(ROOT / "docs/data/events.json") as f:
        return json.load(f)

def load_hs_csv():
    """Load detailed HS data from outputs/hate_speech_posts.csv."""
    rows = []
    with open(ROOT / "outputs/hate_speech_posts.csv", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows

def summarise_hs(posts):
    """Print basic summary statistics for HS posts."""
    print(f"Total posts: {len(posts)}")
    print(f"By country: {Counter(p.get('c','unknown') for p in posts)}")
    print(f"By platform: {Counter(p.get('p','unknown') for p in posts)}")
    print(f"By prediction: {Counter(p.get('pr','unknown') for p in posts)}")
    print(f"By subtype: {Counter(p.get('gt','unknown') for p in posts)}")

def summarise_events(events):
    """Print basic summary statistics for disinformation events."""
    print(f"Total events: {len(events)}")
    print(f"By country: {Counter(e.get('country','unknown') for e in events)}")
    print(f"By type: {Counter(e.get('event_type','unknown') for e in events)}")
    print(f"By status: {Counter(e.get('status','unknown') for e in events)}")

if __name__ == "__main__":
    print("=== Hate Speech Posts ===")
    posts = load_hs_posts()
    summarise_hs(posts)
    print("\n=== Disinformation Events ===")
    events = load_events()
    summarise_events(events)
