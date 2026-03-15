# Classification Methodology

## Overview

The BRACE4PEACE classification pipeline applies four pre-trained BERT models to social media text data collected from East African platforms via Phoenix gathers. The models detect hate speech, political polarization, toxicity (Somali-language), and Sudan-specific hate speech.

## Data Pipeline

```
Phoenix Gathers (Project 133)
    ↓
CSV Export (per country × narrative category)
    ↓
Text Extraction (post_text_pi → comment_text_pi fallback)
    ↓
Model Inference (4 BERT models, sequential)
    ↓
Per-row predictions + confidence scores
    ↓
Incremental save to CSV
```

## Model Details

### 1. EA-HS (East Africa Hate Speech)
- **Repository**: `KSvendsen/EA-HS`
- **Architecture**: `bert-base-multilingual-cased` fine-tuned
- **Labels**: Normal (0), Abusive (1), Hate (2)
- **Training data**: East African social media content
- **Output**: 3-class probabilities via softmax

### 2. Polarization-Kenya
- **Repository**: `datavaluepeople/Polarization-Kenya`
- **Architecture**: BERT fine-tuned
- **Labels**: not_polarization (0), polarization (1)
- **Training data**: Kenyan political discourse
- **Output**: Binary probabilities via softmax

### 3. Afxumo Toxicity (Somaliland)
- **Repository**: `datavaluepeople/Afxumo-toxicity-somaliland-SO`
- **Architecture**: BERT fine-tuned
- **Labels**: not_afxumo (0), afxumo (1)
- **Training data**: Somali-language content
- **Output**: Binary probabilities via softmax

### 4. Hate Speech Sudan v2
- **Repository**: `datavaluepeople/Hate-Speech-Sudan-v2`
- **Architecture**: BERT fine-tuned
- **Labels**: not_hate_speech (0), hate_speech (1)
- **Training data**: Sudan/South Sudan content
- **Output**: Binary probabilities via softmax

## Inference Configuration

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Batch size | 64 | Optimized for 2-vCPU machines |
| Max token length | 256 | Social media posts rarely exceed this; reduces padding overhead |
| Torch threads | 2 | Matches available CPU cores |
| Save frequency | Every 320 items | Balance between I/O overhead and crash recovery |

## Processing Order

Models are run sequentially to manage memory (each BERT model requires ~640MB-1.1GB RAM):

1. EA-HS (3-class, fastest at ~10 items/sec)
2. Polarization-Kenya (~4.4 items/sec)
3. Afxumo Toxicity (~4.4 items/sec)
4. HateSpeech Sudan v2 (~4.4 items/sec)

Model cache is cleared between runs to free disk space.

## CSV Column Schema

### Input Columns
- `post_text_pi` — Primary text field (PII-redacted post text)
- `comment_text_pi` — Fallback text field (PII-redacted comment text)

### Output Columns (per model)
- `{Model}_pred` — Predicted label string
- `{Model}_conf` — Confidence score (highest class probability)
- `{Model}_{label}` — Individual class probability scores

### Example
```
EA_HS_pred: "Hate"
EA_HS_conf: 0.9955
EA_HS_Normal: 0.0040
EA_HS_Abusive: 0.0005
EA_HS_Hate: 0.9955
```

## Data Files

### File Naming Convention
`{Country}_{NarrativeCategory}.csv`

### Countries
- `Kenya_` — 6 files
- `Somalia_` — 8 files (+ 2 additional pending: Comments_Escalation, Other)
- `South_Sudan_` — 6 files

### Narrative Categories
Delegitimization, Diaspora, Elections, Escalation, Hate_Speech, Mixed, Mixed_Monitoring, Other, Peace, Unknown, Violent_Extremism

## Known Limitations

1. **Cross-lingual coverage**: Models primarily trained on English and specific local languages; may underperform on code-switched text
2. **Temporal drift**: Models trained on historical data may not capture evolving linguistic patterns
3. **Platform bias**: Training data may not fully represent all platforms in the Phoenix gathers
4. **Classification overlap**: A single post may be flagged by multiple models (e.g., both EA-HS and HateSpeech Sudan)
