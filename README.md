# BRACE4PEACE — East Africa Hate Speech, Disinformation & VE Monitoring

Multi-source monitoring and classification system for hate speech, disinformation, and violent extremism narratives across **South Sudan**, **Kenya**, and **Somalia**, with dedicated **Al-Shabaab media tracking**.

Part of the UNDP BRACE4PEACE project. Data collected via [Phoenix](https://console.phoenix.howtobuildup.org/projects/show/133) social media gathers.

---

## Repository Structure

```
brace4peace/
├── README.md
├── data/
│   └── phoenix_csvs/           # Social media datasets from Phoenix gathers
│       ├── Kenya_*.csv          # 6 files — Delegitimization, Diaspora, Elections, Hate Speech, Peace, VE
│       ├── Somalia_*.csv        # 8 files — Delegitimization, Escalation, Hate Speech, Mixed, Peace, Unknown, VE
│       └── South_Sudan_*.csv    # 6 files — Delegitimization, Diaspora, Elections, Hate Speech, Peace, VE
├── scripts/
│   ├── classify_fast.py         # Main classification script (incremental, background-safe)
│   ├── run_all_models.sh        # Sequential model runner with cache management
│   └── models.json              # Model configurations and column mappings
├── monitoring/
│   ├── brace4peace_protocol.md  # Full monitoring protocol (Steps 1-5)
│   ├── baseline_feb26_2026.md   # Threat baseline for alert decisions
│   └── findings/                # Daily scan outputs (JSON)
│       ├── README.md            # Findings schema documentation
│       ├── state.json           # Monitor state tracking
│       └── findings_YYYY-MM-DD.json  # Daily structured findings
└── docs/
    ├── methodology.md           # Classification methodology and data schema
    └── data_dictionary.md       # Complete column reference (149 columns documented)
```

## Dataset Summary

| Country | Files | Rows | Categories |
|---------|-------|------|------------|
| Kenya | 6 | 27,405 | Delegitimization, Diaspora, Elections, Hate Speech, Peace, Violent Extremism |
| Somalia | 8 | 25,070 | Delegitimization, Escalation, Hate Speech, Mixed, Mixed Monitoring, Peace, Unknown, VE |
| South Sudan | 6 | 28,239 | Delegitimization, Diaspora, Elections, Hate Speech, Peace, Violent Extremism |
| **Total** | **20** | **80,714** | |

> **Note**: 2 additional files (`Somalia_Comments_Escalation.csv`, `Somalia_Other.csv`) are part of the full dataset (~4,067 rows) but not yet included in this repo.

## Classification Models

Four HuggingFace BERT models are applied to each row:

| Model | HF Repository | Labels | Status |
|-------|--------------|--------|--------|
| **EA-HS** | [KSvendsen/EA-HS](https://huggingface.co/KSvendsen/EA-HS) | Normal, Abusive, Hate | ✅ Complete (80,714/80,714) |
| **Polarization-Kenya** | [datavaluepeople/Polarization-Kenya](https://huggingface.co/datavaluepeople/Polarization-Kenya) | not_polarization, polarization | 🔄 In progress |
| **Afxumo Toxicity** | [datavaluepeople/Afxumo-toxicity-somaliland-SO](https://huggingface.co/datavaluepeople/Afxumo-toxicity-somaliland-SO) | not_afxumo, afxumo | ⏳ Queued |
| **HateSpeech Sudan v2** | [datavaluepeople/Hate-Speech-Sudan-v2](https://huggingface.co/datavaluepeople/Hate-Speech-Sudan-v2) | not_hate_speech, hate_speech | ⏳ Queued |

### Output Columns Per Model

Each model produces:
- `{Model}_pred` — Predicted label
- `{Model}_conf` — Confidence score (0-1)
- `{Model}_{label}` — Per-class probability scores

### Text Columns
- Primary: `post_text_pi` (post text, PII-redacted)
- Fallback: `comment_text_pi` (comment text, used when post text is empty)

## Running Classification

### Requirements
```bash
pip install torch transformers scipy pandas numpy
```

### Single Model
```bash
python scripts/classify_fast.py polarization
```

### All Models (sequential, with cache cleanup)
```bash
bash scripts/run_all_models.sh
```

The scripts are **incremental** — they skip already-classified rows and save progress every 320 items. Safe to interrupt and resume.

### Performance
- ~4-10 items/sec on 2-vCPU (CPU-only inference)
- EA-HS: ~10/sec (smaller model)
- BERT models: ~4.4/sec with 2 threads

## Monitoring Protocol

The `monitoring/` directory contains the BRACE4PEACE automated monitoring protocol and its collected output:

- **brace4peace_protocol.md** — Full 5-step scan procedure (X/Twitter searches, web monitoring, direct URL fetches, narrative classification, alert decisions)
- **baseline_feb26_2026.md** — Rolling threat baseline used to determine what constitutes "new" intelligence
- **findings/** — Structured daily scan results in JSON format, including narrative classification, source audit trails, and alert history. See `findings/README.md` for the schema.

### Narrative Classification Framework

Findings are classified against BRACE4PEACE narrative families:

| Narrative | Weight | Level |
|-----------|--------|-------|
| Ethnic Incitement | 5 | CRITICAL |
| Revenge/Retribution | 5 | CRITICAL |
| Victimhood/Grievance | 4 | HIGH |
| Religious Distortion | 4 | HIGH |
| Misinformation/Disinformation | 4 | HIGH |
| Existential Threat | 4 | HIGH |
| Collective Blame | 4 | HIGH |
| Delegitimization | 3 | MODERATE |
| Peace/Counter-Narratives | -2 | PROTECTIVE |

## Data Source

Social media data is collected via [Phoenix](https://console.phoenix.howtobuildup.org) gathers for UNDP Project 133 (BRACE4PEACE). Data is PII-redacted (`_pi` suffix columns).

## Related Repository

- [conflict-ewds](https://github.com/KSvend/conflict-ewds) — Conflict Early Warning and Decision Support System architecture and documentation

## License

This repository contains sensitive conflict monitoring data and methodology. For authorized use within the BRACE4PEACE / UNDP project only.
