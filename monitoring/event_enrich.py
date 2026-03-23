#!/usr/bin/env python3
"""
Event Enrichment for MERLx IRIS
================================
Post-classification enrichment that runs after events are created/updated:

1. Auto-link related events (shared narratives, actors, country, temporal proximity)
2. Smart threat_level assignment with P1 CRITICAL criteria

Designed to run as phase 1F in the pipeline, after classification and lifecycle.
Can also be run standalone to backfill existing events.
"""

import json
import re
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent
EVENTS_PATH = WORKSPACE / "docs" / "data" / "events.json"
NARRATIVES_PATH = WORKSPACE / "docs" / "data" / "narratives.json"

# ── Narrative family weights (from monitoring protocol) ──────────────────
FAMILY_WEIGHTS = {
    "Ethnic Incitement": 5,
    "Revenge/Retribution": 5,
    "Victimhood/Grievance": 4,
    "Religious Distortion": 4,
    "Misinformation/Disinformation": 4,
    "Existential Threat": 4,
    "Collective Blame": 4,
    "Delegitimization": 3,
    "Foreign Influence": 3,
    "Peace/Counter-Narratives": -2,
}

# ── Threat level criteria ────────────────────────────────────────────────
# P1 CRITICAL: confirmed + high-weight family + any escalation signal
# P2 HIGH:     confirmed + medium-weight family, OR potential + high-weight
# P3 MODERATE: everything else

THREAT_RANK = {"P1 CRITICAL": 3, "P2 HIGH": 2, "P3 MODERATE": 1}


def load_events():
    return json.loads(EVENTS_PATH.read_text())


def load_narratives():
    return json.loads(NARRATIVES_PATH.read_text())


def save_events(events):
    EVENTS_PATH.write_text(json.dumps(events, indent=2, ensure_ascii=False))


# =========================================================================
# 1. AUTO-LINK RELATED EVENTS
# =========================================================================

def compute_link_score(a, b, narratives):
    """
    Score how related two events are for cross-linking (not dedup).
    Returns 0.0 - 1.0. Threshold for linking: 0.25

    Different from event_dedup.compute_similarity — that merges duplicates,
    this connects distinct-but-related events (e.g., a context report about
    an active disinfo campaign).
    """
    score = 0.0

    # 1. Shared narrative IDs (strong signal)
    narr_a = set(a.get("disinfo_narratives") or [])
    narr_b = set(b.get("disinfo_narratives") or [])
    if narr_a and narr_b:
        overlap = len(narr_a & narr_b)
        if overlap > 0:
            score += 0.35 * (overlap / max(len(narr_a | narr_b), 1))

    # 2. Shared narrative family (medium signal)
    fam_a = get_families(a, narratives)
    fam_b = get_families(b, narratives)
    if fam_a and fam_b:
        fam_overlap = len(fam_a & fam_b)
        if fam_overlap > 0:
            score += 0.20 * (fam_overlap / max(len(fam_a | fam_b), 1))

    # 3. Shared actors (medium signal)
    actors_a = set(x.lower() for x in (a.get("actors") or []) if x != "Unknown")
    actors_b = set(x.lower() for x in (b.get("actors") or []) if x != "Unknown")
    if actors_a and actors_b:
        actor_overlap = len(actors_a & actors_b)
        if actor_overlap > 0:
            score += 0.20 * min(actor_overlap / 2, 1.0)

    # 4. Same country (weak signal, but required baseline)
    same_country = a.get("country") == b.get("country")
    if same_country:
        score += 0.10
    elif a.get("country") == "Regional" or b.get("country") == "Regional":
        score += 0.05  # Regional events partially match any country

    # 5. Temporal proximity — events within 14 days are more likely related
    try:
        date_a = datetime.strptime(a.get("last_seen") or a.get("date", ""), "%Y-%m-%d")
        date_b = datetime.strptime(b.get("last_seen") or b.get("date", ""), "%Y-%m-%d")
        days_apart = abs((date_a - date_b).days)
        if days_apart <= 7:
            score += 0.15
        elif days_apart <= 14:
            score += 0.10
        elif days_apart <= 30:
            score += 0.05
    except (ValueError, TypeError):
        pass

    return min(score, 1.0)


def get_families(event, narratives):
    """Get all narrative families for an event."""
    families = set()
    for nid in (event.get("disinfo_narratives") or []):
        if nid in narratives and narratives[nid].get("family"):
            families.add(narratives[nid]["family"])
    for nf in (event.get("narrative_families") or []):
        if nf.get("family"):
            families.add(nf["family"])
    return families


def auto_link_events(events, narratives, threshold=0.35, max_links=6):
    """
    Populate related_events for all events based on similarity scoring.

    Only adds new links — doesn't remove existing ones.
    Bidirectional: if A links to B, B also links to A.
    """
    event_map = {e["id"]: e for e in events}
    links_added = 0

    # Build index by narrative for faster lookup
    narr_index = defaultdict(set)
    family_index = defaultdict(set)
    country_index = defaultdict(set)

    for e in events:
        eid = e["id"]
        for nid in (e.get("disinfo_narratives") or []):
            narr_index[nid].add(eid)
        for fam in get_families(e, narratives):
            family_index[fam].add(eid)
        country_index[e.get("country", "")].add(eid)

    for e in events:
        eid = e["id"]
        existing_links = set(e.get("related_events") or [])

        # Candidate pool: events sharing narrative, family, or country
        candidates = set()
        for nid in (e.get("disinfo_narratives") or []):
            candidates |= narr_index.get(nid, set())
        for fam in get_families(e, narratives):
            candidates |= family_index.get(fam, set())
        candidates |= country_index.get(e.get("country", ""), set())
        candidates.discard(eid)
        candidates -= existing_links

        # Score and rank
        scored = []
        for cid in candidates:
            if cid not in event_map:
                continue
            sc = compute_link_score(e, event_map[cid], narratives)
            if sc >= threshold:
                scored.append((cid, sc))

        scored.sort(key=lambda x: -x[1])

        # Add top links (up to max_links total)
        slots = max_links - len(existing_links)
        for cid, sc in scored[:max(0, slots)]:
            existing_links.add(cid)
            # Bidirectional
            other = event_map[cid]
            other_links = set(other.get("related_events") or [])
            if eid not in other_links and len(other_links) < max_links:
                other_links.add(eid)
                other["related_events"] = sorted(other_links)
            links_added += 1

        e["related_events"] = sorted(existing_links)

    return links_added


# =========================================================================
# 2. SMART THREAT LEVEL ASSIGNMENT
# =========================================================================

def compute_threat_level(event, narratives):
    """
    Compute threat level based on multiple signals:

    P1 CRITICAL — any of:
      - Confirmed + CRITICAL-weight family (Ethnic Incitement, Revenge/Retribution)
        + at least one escalation signal (spread >= 3, coordinated, VE-related)
      - Confirmed + active VE propaganda with high spread
      - Any event with coordinated campaign + ethnic incitement + confirmed

    P2 HIGH — any of:
      - Confirmed + HIGH-weight family (Victimhood, Religious, Misinfo, Existential, Collective)
      - Confirmed + spread >= 3
      - Potential + CRITICAL-weight family
      - Confirmed + coordinated campaign flag

    P3 MODERATE — everything else
    """
    event_type = event.get("event_type", "CONTEXT")
    is_confirmed = event_type == "CONFIRMED"
    is_potential = event_type == "POTENTIAL"
    spread = event.get("spread", 1)
    is_ve = event.get("ve_related", False)
    is_coordinated = event.get("coordination_score", 0) > 0.5 or "coordinated" in (event.get("disinfo_subtype") or "")

    families = get_families(event, narratives)
    max_weight = max((FAMILY_WEIGHTS.get(f, 0) for f in families), default=0)

    # ── P1 CRITICAL ──
    # Confirmed + CRITICAL-weight family + high spread OR other escalation.
    if is_confirmed and max_weight >= 5:  # Ethnic Incitement or Revenge/Retribution
        if spread >= 5:
            return "P1 CRITICAL"
        escalation_signals = sum([
            spread >= 3,
            is_coordinated,
            is_ve,
            event.get("observation_count", 0) >= 3,
        ])
        if escalation_signals >= 2:
            return "P1 CRITICAL"

    if is_confirmed and is_ve and spread >= 4:
        return "P1 CRITICAL"

    # ── P2 HIGH ──
    if is_confirmed and max_weight >= 5:
        return "P2 HIGH"  # CRITICAL-weight family but didn't meet P1 bar

    if is_confirmed and max_weight >= 4 and spread >= 2:
        return "P2 HIGH"

    if is_confirmed and spread >= 4:
        return "P2 HIGH"

    if is_confirmed and is_coordinated:
        return "P2 HIGH"

    if is_potential and max_weight >= 5:
        return "P2 HIGH"

    # ── P3 MODERATE ──
    return "P3 MODERATE"


def update_threat_levels(events, narratives):
    """
    Recompute threat levels for all events.
    Only upgrades — never downgrades existing threat levels
    (analysts may have manually set them).
    """
    upgraded = 0
    for e in events:
        current = e.get("threat_level", "P3 MODERATE")
        computed = compute_threat_level(e, narratives)

        # Only upgrade, never downgrade
        if THREAT_RANK.get(computed, 0) > THREAT_RANK.get(current, 0):
            e["threat_level"] = computed
            upgraded += 1

    return upgraded


# =========================================================================
# MAIN
# =========================================================================

def main():
    """Run both enrichment steps."""
    events = load_events()
    narratives = load_narratives()

    print(f"Enriching {len(events)} events...")

    # 1. Auto-link
    links = auto_link_events(events, narratives)
    print(f"  Auto-link: {links} new links added")

    # 2. Threat levels
    upgrades = update_threat_levels(events, narratives)
    print(f"  Threat levels: {upgrades} events upgraded")

    save_events(events)
    print("  Saved.")

    return {"links_added": links, "threat_upgrades": upgrades}


if __name__ == "__main__":
    main()
