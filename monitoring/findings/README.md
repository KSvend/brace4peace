# BRACE4PEACE Monitoring Findings

This directory contains structured output from the automated BRACE4PEACE East Africa monitoring system.

## How It Works

An automated daily scan (06:00 UTC) monitors web sources, news outlets, and analysis platforms for new hate speech, disinformation, and violent extremism developments across South Sudan, Kenya, and Somalia, with dedicated Al-Shabaab media tracking. See [`../brace4peace_protocol.md`](../brace4peace_protocol.md) for the full protocol.

Each scan produces a JSON findings file. Alerts are only issued when genuinely new intelligence is detected beyond the rolling baseline documented in [`../baseline_feb26_2026.md`](../baseline_feb26_2026.md).

## File Format

### `findings_YYYY-MM-DD.json`

```json
{
  "run_timestamp_utc": "2026-03-15T06:00:00Z",
  "run_timestamp_local": "2026-03-15T07:00:00+01:00",
  "notable_new_intel": [
    {
      "region": "South Sudan",
      "threat_level": "P1 CRITICAL",
      "headline": "Brief description of finding",
      "why_new_vs_baseline": "Explanation of why this is new intelligence",
      "sources": [
        { "title": "Article title", "url": "https://..." }
      ],
      "narrative_classification": [
        {
          "family": "Victimhood/Grievance",
          "weight": 4,
          "note": "Analytical note",
          "evidence": "Supporting evidence from source"
        }
      ],
      "ve_related": false,
      "al_shabaab_related": false,
      "confidence": "high"
    }
  ],
  "items_checked": {
    "x_twitter": { "status": "not_executed", "reason": "..." },
    "web": [
      {
        "topic": "Search topic",
        "url": "https://...",
        "relevance": "High/Moderate/Low",
        "assessment": "Analytical assessment"
      }
    ],
    "direct_fetch": [
      { "url": "https://...", "result": "ok/blocked/partial", "issue": "..." }
    ]
  }
}
```

### Key Fields

| Field | Description |
|-------|-------------|
| `notable_new_intel` | Array of findings that constitute genuinely new intelligence beyond baseline |
| `threat_level` | P1 CRITICAL / P2 HIGH / P3 MODERATE (see protocol for criteria) |
| `narrative_classification` | Mapping to BRACE4PEACE narrative families with weighted scores |
| `items_checked.web` | All web sources checked with relevance and analytical assessment |
| `items_checked.direct_fetch` | Direct URL fetches attempted with success/failure status |

### `state.json`

Tracks the monitoring system's state:

```json
{
  "last_run": "2026-03-15T06:00:00Z",
  "latest_findings_file": "findings_2026-03-15.json",
  "notified": [
    {
      "timestamp_utc": "2026-03-15T06:00:00Z",
      "item_key": "south-sudan_akobo_evacuation-order_fighting_aid-suspension"
    }
  ]
}
```

## Collected Findings

| Date | New Intel | Key Finding |
|------|-----------|-------------|
| 2026-03-14 | None | Routine scan; South Sudan HS legal enforcement and tracking device acquisition noted but not new vs. baseline |
| 2026-03-15 | 1 (P1 CRITICAL) | South Sudan: Akobo evacuation order + SSPDF–SPLA-IO fighting; aid agencies suspended; 280K+ displaced |

## Known Limitations

- **X/Twitter**: Social media search not available in automated environment; X queries from the protocol (24 searches) are not executed
- **Eye Radio**: Blocked by robots.txt — articles cannot be fetched automatically
- **Garowe Online**: Index page extraction returns partial results without full article URLs
- **Frequency**: Currently running once daily; some fast-moving developments may be detected with delay
