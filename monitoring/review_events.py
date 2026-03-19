#!/usr/bin/env python3
"""
Disinfo Event QA + Intelligence Extraction via Anthropic API
=============================================================
Reviews new/pending disinfo events and:
1. Validates classification (DISINFO vs CONTEXT)
2. Checks headline quality (must describe the false claim)
3. Validates threat level and confidence
4. Extracts specific disinfo claims from CONTEXT events (reports ABOUT disinfo)
5. Proposes new search keywords from extracted claims

Pure stdlib — no pip dependencies.
"""

import json
import os
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
EVENTS_PATH = REPO_ROOT / "docs" / "data" / "events.json"
STRATEGY_PATH = REPO_ROOT / "monitoring" / "config" / "apify_keyword_strategy.json"

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 4096
BATCH_SIZE = 5
MAX_RETRIES = 3

SYSTEM_PROMPT = """\
You are a disinformation analyst for UNDP's BRACE4PEACE early warning platform monitoring East Africa (Somalia, South Sudan, Kenya).

You review events detected by the automated monitoring pipeline. Each event has a headline, summary, and classification.

For each event, provide:

1. "classification_correct": true if the event_type is right, false if it should change.
2. "suggested_type": "DISINFO" (false claims being spread) or "CONTEXT" (news/reports/actions ABOUT disinformation, not disinformation itself).
   - The Bridge Test: is the primary substance CONTENT (false claims) or ACTION (events, reports)?
   - A partner report about disinformation → CONTEXT
   - Social media posts spreading false claims → DISINFO
   - Government action against disinformation → CONTEXT

3. "headline_ok": true if headline describes the false claim. false if it describes detection mechanics.
   - GOOD: "Claims BBC Africa Eye is a foreign intelligence operation"
   - BAD: "Coordinated push of fabricated claims across 11 posts"
4. "suggested_headline": improved headline if headline_ok is false, otherwise null.

5. "threat_ok": true if threat level matches content severity.
6. "suggested_threat": "P1 CRITICAL" | "P2 HIGH" | "P3 MODERATE" if threat_ok is false, otherwise null.

7. "extracted_claims": Array of specific false claims or disinfo narratives mentioned in this event. For CONTEXT events (reports about disinfo), extract EVERY distinct disinformation claim the report discusses. Each claim should be a concise string describing what is being falsely claimed. This is critical — these become search targets.
   Format: [{"claim": "...", "country": "Somalia|South Sudan|Kenya|Regional", "actors": ["..."], "keywords": ["..."]}]

8. "proposed_keywords": New search keywords extracted from this event that should be added to the monitoring sweep. Only propose terms specific to East African disinformation — not generic words. Max 5.
   Format: [{"keyword": "...", "country": "...", "reason": "..."}]

9. "summary_ok": true if summary is accurate and analytical. false if it's generic, mechanical, or needs improvement.
10. "suggested_summary": improved summary if summary_ok is false, otherwise null. Should be 2-3 sentences describing what happened, who is involved, and why it matters.

11. "notes": Brief analytical note (1-2 sentences) about this event's significance.

Respond ONLY with a JSON array. No markdown fences.
Format: [{"id": 0, "classification_correct": true, "suggested_type": "DISINFO", "headline_ok": true, "suggested_headline": null, "threat_ok": true, "suggested_threat": null, "summary_ok": true, "suggested_summary": null, "extracted_claims": [...], "proposed_keywords": [...], "notes": "..."}, ...]"""


def call_anthropic(batch_text):
    """Call Anthropic API."""
    if not ANTHROPIC_API_KEY:
        return None
    payload = json.dumps({
        "model": MODEL,
        "max_tokens": MAX_TOKENS,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": batch_text}]
    }).encode()
    headers = {
        "Content-Type": "application/json",
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01"
    }
    for attempt in range(MAX_RETRIES):
        req = urllib.request.Request(API_URL, data=payload, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read().decode())
                text = result["content"][0]["text"].strip()
                if text.startswith("```"):
                    text = text.split("\n", 1)[1]
                    if text.endswith("```"):
                        text = text[:text.rfind("```")]
                return json.loads(text)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(30)
            else:
                body = e.read().decode()[:200]
                print(f"  Anthropic error {e.code}: {body}")
                if attempt == MAX_RETRIES - 1:
                    return None
                time.sleep(5)
        except json.JSONDecodeError:
            print(f"  JSON parse error from response")
            return None
        except Exception as e:
            print(f"  Error: {e}")
            time.sleep(5)
    return None


def format_event_batch(events_batch):
    """Format events for the LLM prompt."""
    lines = []
    for idx, event in events_batch:
        headline = event.get("headline", "")[:200]
        summary = event.get("summary", "")[:400]
        etype = event.get("event_type", "?")
        country = event.get("country", "?")
        threat = event.get("threat_level", "?")
        confidence = event.get("disinfo_confidence", "?")
        actors = ", ".join(event.get("actors", [])[:5])
        platforms = ", ".join(event.get("platforms", [])[:3])
        sources = "; ".join(s.get("publisher", "") for s in event.get("sources", [])[:2])
        narr = ", ".join(event.get("disinfo_narratives", [])[:3])

        lines.append(
            f"[{idx}] Type:{etype} | Country:{country} | Threat:{threat} | Confidence:{confidence}\n"
            f"Actors: {actors}\n"
            f"Platforms: {platforms}\n"
            f"Narratives: {narr}\n"
            f"Sources: {sources}\n"
            f"Headline: {headline}\n"
            f"Summary: {summary}"
        )
    return "\n\n---\n\n".join(lines)


def main(dry_run=False, review_all=False):
    """Review events and extract intelligence."""
    if not ANTHROPIC_API_KEY:
        print("No ANTHROPIC_API_KEY set, skipping event review")
        return {"reviewed": 0, "error": "no API key"}

    with open(EVENTS_PATH) as f:
        events = json.load(f)

    # Find events needing review:
    # - New events without _reviewed flag
    # - Events with pending_classification subtype
    # - Or all events if review_all is set
    if review_all:
        to_review = [(i, e) for i, e in enumerate(events)]
    else:
        to_review = [
            (i, e) for i, e in enumerate(events)
            if not e.get("_reviewed")
            or e.get("disinfo_subtype") == "pending_classification"
            or e.get("verification_status") == "pending_review"
        ]

    if not to_review:
        print(f"No events need review. Total: {len(events)}")
        return {"reviewed": 0, "total": len(events)}

    print(f"Reviewing {len(to_review)} events out of {len(events)} total.")

    reviewed = 0
    reclassified = 0
    claims_extracted = 0
    keywords_proposed = 0
    all_proposed_keywords = []
    all_extracted_claims = []

    for batch_start in range(0, len(to_review), BATCH_SIZE):
        batch = to_review[batch_start:batch_start + BATCH_SIZE]
        prompt = format_event_batch([(j, e) for j, (_, e) in enumerate(batch)])

        if dry_run:
            print(f"  [DRY RUN] Would review batch of {len(batch)} events")
            continue

        results = call_anthropic(prompt)
        if not results:
            print(f"  Batch at {batch_start} failed, skipping.")
            continue

        for item in results:
            idx_in_batch = item.get("id", -1)
            if idx_in_batch < 0 or idx_in_batch >= len(batch):
                continue

            real_idx, event = batch[idx_in_batch]

            # Apply classification fix
            if not item.get("classification_correct", True):
                old_type = event.get("event_type")
                new_type = item.get("suggested_type", old_type)
                if new_type != old_type:
                    event["event_type"] = new_type
                    event["_reclassified_from"] = old_type
                    reclassified += 1
                    print(f"    Reclassified {event.get('id')}: {old_type} → {new_type}")

            # Apply headline fix
            if not item.get("headline_ok", True) and item.get("suggested_headline"):
                event["_original_headline"] = event.get("headline")
                event["headline"] = item["suggested_headline"]

            # Apply summary fix
            if not item.get("summary_ok", True) and item.get("suggested_summary"):
                event["_original_summary"] = event.get("summary")
                event["summary"] = item["suggested_summary"]

            # Apply threat fix
            if not item.get("threat_ok", True) and item.get("suggested_threat"):
                event["threat_level"] = item["suggested_threat"]

            # Store extracted claims
            extracted = item.get("extracted_claims", [])
            if extracted:
                event["extracted_claims"] = [
                    c.get("claim", "") for c in extracted if c.get("claim")
                ]
                all_extracted_claims.extend(extracted)
                claims_extracted += len(extracted)

            # Collect proposed keywords
            proposed = item.get("proposed_keywords", [])
            if proposed:
                all_proposed_keywords.extend(proposed)
                keywords_proposed += len(proposed)

            # Store notes
            if item.get("notes"):
                event["_review_notes"] = item["notes"]

            event["_reviewed"] = datetime.now(timezone.utc).isoformat()
            reviewed += 1

        time.sleep(2)
        print(f"  Reviewed {min(batch_start + BATCH_SIZE, len(to_review))}/{len(to_review)}")

    if not dry_run:
        # Save events
        with open(EVENTS_PATH, "w") as f:
            json.dump(events, f, ensure_ascii=False, indent=2)

        # Save extracted intelligence
        if all_extracted_claims or all_proposed_keywords:
            intel_dir = REPO_ROOT / "data" / "run_history"
            intel_dir.mkdir(parents=True, exist_ok=True)
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            intel_path = intel_dir / f"extracted_intel_{today}.json"
            intel = {
                "date": today,
                "extracted_claims": all_extracted_claims,
                "proposed_keywords": all_proposed_keywords,
                "events_reviewed": reviewed,
                "events_reclassified": reclassified,
            }
            with open(intel_path, "w") as f:
                json.dump(intel, f, indent=2)
            print(f"  Intelligence saved to {intel_path}")

        # Append proposed keywords to autolearning in strategy
        if all_proposed_keywords and STRATEGY_PATH.exists():
            try:
                with open(STRATEGY_PATH) as f:
                    strategy = json.load(f)
                autolearn = strategy.setdefault("autolearning", {})
                learned = autolearn.setdefault("learned_keywords", {"entries": [], "max_total": 50, "max_per_run": 5})
                existing = set(e.get("keyword", "").lower() for e in learned["entries"])
                added = 0
                for kw in all_proposed_keywords[:5]:
                    keyword = kw.get("keyword", "").strip().lower()
                    if keyword and keyword not in existing and len(keyword) >= 4:
                        learned["entries"].append({
                            "keyword": keyword,
                            "country": kw.get("country", "Regional"),
                            "source": "event_review_extraction",
                            "reason": kw.get("reason", ""),
                            "date_added": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                            "status": "proposed",
                            "hits": 0, "rotations_run": 0
                        })
                        existing.add(keyword)
                        added += 1
                if added:
                    with open(STRATEGY_PATH, "w") as f:
                        json.dump(strategy, f, indent=2)
                    print(f"  Added {added} proposed keywords to strategy")
            except Exception as e:
                print(f"  Could not update strategy: {e}")

    summary = {
        "reviewed": reviewed,
        "reclassified": reclassified,
        "claims_extracted": claims_extracted,
        "keywords_proposed": keywords_proposed,
        "total_events": len(events),
    }
    print(f"\nEvent review complete: {json.dumps(summary)}")
    return summary


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--review-all", action="store_true", help="Review all events, not just unreviewed")
    args = parser.parse_args()
    main(dry_run=args.dry_run, review_all=args.review_all)
