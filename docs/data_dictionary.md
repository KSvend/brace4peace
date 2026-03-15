# BRACE4PEACE Data Dictionary

## Overview

This repository contains **80,714 social media records** collected via [Phoenix](https://console.phoenix.howtobuildup.org) gathers (Project 133) for the UNDP BRACE4PEACE programme. The data covers online hate speech, disinformation, and violent extremism narratives across three East African countries.

Each record is a single social media **post** or **comment**, harvested from Facebook, X (Twitter), and TikTok. All personally identifiable information has been redacted — columns with the `_pi` suffix contain PII-processed content.

---

## Dataset at a Glance

| Dimension | Value |
|-----------|-------|
| Total records | 80,714 |
| CSV files | 20 (+ 2 pending: `Somalia_Comments_Escalation`, `Somalia_Other`) |
| Columns per file | 149 |
| Countries | Kenya (26,006), Somalia (27,006), South Sudan (27,702) |
| Platforms | Facebook (44,821), X/Twitter (32,653), TikTok (3,240) |
| Date range — posts | Jun 2007 – Feb 2026 |
| Date range — comments | Jan 2012 – Feb 2026 |
| Record types | Posts: 62,306 (77%) · Comments: 19,354 (24%) · Both: 1,273 · Neither: 327 |

---

## File Structure

Files are stored in `data/phoenix_csvs/` and follow the naming convention:

```
{Country}_{GatherTopic}.csv
```

### File Inventory

| File | Rows | Country | Topic |
|------|------|---------|-------|
| `Kenya_Delegitimization.csv` | 777 | Kenya | Delegitimization |
| `Kenya_Diaspora.csv` | 2,942 | Kenya | Diaspora |
| `Kenya_Elections.csv` | 2,463 | Kenya | Elections |
| `Kenya_Hate_Speech.csv` | 7,174 | Kenya | Hate Speech |
| `Kenya_Peace.csv` | 7,340 | Kenya | Peace |
| `Kenya_Violent_Extremism.csv` | 5,310 | Kenya | Violent Extremism |
| `Somalia_Delegitimization.csv` | 1,277 | Somalia | Delegitimization |
| `Somalia_Escalation.csv` | 299 | Somalia | Escalation |
| `Somalia_Hate_Speech.csv` | 6,055 | Somalia | Hate Speech |
| `Somalia_Mixed.csv` | 2 | Somalia | Mixed |
| `Somalia_Mixed_Monitoring.csv` | 863 | Somalia | Mixed/Monitoring |
| `Somalia_Peace.csv` | 1,199 | Somalia | Peace |
| `Somalia_Unknown.csv` | 12,803 | Somalia | Unknown |
| `Somalia_Violent_Extremism.csv` | 4,508 | Somalia | Violent Extremism |
| `South_Sudan_Delegitimization.csv` | 2,309 | South Sudan | Delegitimization |
| `South_Sudan_Diaspora.csv` | 1,440 | South Sudan | Diaspora |
| `South_Sudan_Elections.csv` | 2,744 | South Sudan | Elections |
| `South_Sudan_Hate_Speech.csv` | 8,141 | South Sudan | Hate Speech |
| `South_Sudan_Peace.csv` | 8,385 | South Sudan | Peace |
| `South_Sudan_Violent_Extremism.csv` | 4,683 | South Sudan | Violent Extremism |

### Topic Distribution

| Gather Topic | Records | Share |
|-------------|---------|-------|
| Hate Speech | 21,370 | 26.5% |
| Peace | 16,924 | 21.0% |
| Violent Extremism | 14,501 | 18.0% |
| Unknown | 12,803 | 15.9% |
| Elections | 5,207 | 6.4% |
| Diaspora | 4,382 | 5.4% |
| Delegitimization | 4,363 | 5.4% |
| Mixed/Monitoring | 863 | 1.1% |
| Escalation | 299 | 0.4% |
| Mixed | 2 | <0.1% |

---

## Column Reference (149 columns)

### Core Identifiers & Metadata (11 columns)

| Column | Type | Fill% | Description |
|--------|------|-------|-------------|
| `country` | string | 100% | Target country: `Kenya`, `Somalia`, or `South Sudan` |
| `gather_topic` | string | 100% | Phoenix gather topic used to collect this record (see Topic Distribution above) |
| `platform` | string | 100% | Source platform: `facebook`, `x`, or `tiktok` |
| `content_topic` | float | 49% | Phoenix-assigned content topic (where available) |
| `primary_topic` | float | 49% | Primary topic classification from Phoenix |
| `phoenix_processed_at` | datetime | 100% | Timestamp when Phoenix processed this record |
| `phoenix_job_run_id` | int | 100% | Phoenix job run identifier (-1 = manually processed) |
| `facebook_video_views` | float | <1% | Video view count (Facebook video posts only) |
| `tiktok_post_plays` | float | 4% | Play count (TikTok posts only) |
| `platform_post` | float | <1% | Platform-specific post identifier (sparse) |
| `x_post_retweeted_id` | float | <1% | Original tweet ID if this is a retweet (X only) |

### Post-Level Fields (17 columns)

These fields describe the original social media post. Filled for ~78% of records (the remaining 22% are standalone comments).

| Column | Type | Fill% | Description |
|--------|------|-------|-------------|
| `post_id` | string | 78% | Unique post identifier (UUID) |
| `post_author_id` | string | 78% | Anonymised author identifier (UUID) |
| `post_author_name_pi` | string | 78% | Author display name (PII-redacted) |
| `post_text_pi` | string | 77% | **Primary text field.** Post body text (PII-redacted). This is the main input for classification models. |
| `post_date` | date | 78% | Publication date (YYYY-MM-DD) |
| `post_datetime` | datetime | 78% | Full publication timestamp (UTC) |
| `post_link_pi` | string | 78% | URL to the original post (PII-redacted) |
| `post_gather_id` | float | 78% | Phoenix gather ID that collected this post |
| `post_like_count` | float | 78% | Number of likes/reactions |
| `post_comment_count` | float | 78% | Number of comments |
| `post_share_count` | float | 78% | Number of shares/reposts |
| `post_class` | string | 38% | Phoenix-assigned post classification (e.g., `high_prob_afxumo`) |
| `post_author_category` | float | 0% | Author category (not populated in current dataset) |
| `post_author_class` | float | 0% | Author classification (not populated) |
| `post_author_description_pi` | float | 0% | Author bio/description (not populated) |
| `post_author_followers_count` | float | 0% | Follower count (not populated) |
| `post_author_location` | float | 0% | Author location (not populated) |
| `post_author_link_pi` | float | 0% | Author profile URL (not populated) |

### Comment-Level Fields (12 columns)

These fields describe a comment/reply to a post. Filled for ~24% of records.

| Column | Type | Fill% | Description |
|--------|------|-------|-------------|
| `comment_id` | string | 24% | Unique comment identifier (UUID) |
| `comment_author_id` | string | 24% | Anonymised commenter identifier (UUID) |
| `comment_author_name_pi` | string | 24% | Commenter display name (PII-redacted) |
| `comment_text_pi` | string | 24% | **Fallback text field.** Comment body text (PII-redacted). Used for classification when `post_text_pi` is empty. |
| `comment_date` | date | 24% | Comment date (YYYY-MM-DD) |
| `comment_datetime` | datetime | 24% | Full comment timestamp (UTC) |
| `comment_link_pi` | string | 24% | URL to the comment (PII-redacted) |
| `comment_gather_id` | float | 24% | Phoenix gather ID that collected this comment |
| `comment_like_count` | float | 24% | Number of likes on the comment |
| `comment_parent_post_id` | string | 21% | UUID of the parent post this comment belongs to |
| `comment_replied_to_id` | string | 24% | UUID of the post/comment being replied to |
| `comment_class` | string | 13% | Phoenix-assigned comment classification (e.g., `very_high_prob_afxumo`) |

### X (Twitter)-Specific Fields (2 columns)

| Column | Type | Fill% | Description |
|--------|------|-------|-------------|
| `x_comment_is_quote` | string | 24% | Whether the comment is a quote tweet (`True`/`False`) |
| `x_comment_is_reply` | string | 24% | Whether the comment is a reply (`True`/`False`) |

### Parent Post Fields (14 columns)

Context fields for the parent post when the record is a nested comment/reply. **Currently unpopulated (0% fill)** in this dataset — reserved for future Phoenix gathers that include threaded context.

| Column | Description |
|--------|-------------|
| `post_id_parent` | Parent post UUID |
| `post_author_id_parent` | Parent post author UUID |
| `post_author_name_pi_parent` | Parent post author name |
| `post_text_pi_parent` | Parent post text |
| `post_date_parent` | Parent post date |
| `post_datetime_parent` | Parent post datetime |
| `post_gather_id_parent` | Parent post gather ID |
| `post_link_pi_parent` | Parent post URL |
| `post_like_count_parent` | Parent post likes |
| `post_share_count_parent` | Parent post shares |
| `post_comment_count_parent` | Parent post comments |
| `post_author_category_parent` | Parent post author category |
| `post_author_class_parent` | Parent post author class |
| `post_class_parent` | Parent post classification |

### Phoenix Toxicity Scores (9 columns)

Pre-computed toxicity probabilities from Phoenix's built-in models. Sparsely populated (15–34% fill) — only available for records processed by specific Phoenix job runs.

| Column | Fill% | Description |
|--------|-------|-------------|
| `prob_toxicity` | 22% | Probability of toxic content |
| `prob_severe_toxicity` | 22% | Probability of severely toxic content |
| `prob_insult` | 22% | Probability of insult |
| `prob_identity_attack` | 22% | Probability of identity-based attack |
| `prob_threat` | 22% | Probability of threat |
| `prob_sexually_explicit` | 22% | Probability of sexually explicit content |
| `prob_flirtation` | 18% | Probability of flirtation |
| `prob_afxumo` | 15% | Afxumo (Somali toxicity) score from Phoenix |
| `prob_not_afxumo` | 34% | Inverse Afxumo score from Phoenix |

### Phoenix Topic Labels (65 columns)

Binary or probability labels assigned by Phoenix's topic classification system. Each `topic_*` column indicates whether a specific thematic tag applies to the record. Fill rates vary from 1% to 48% depending on topic coverage.

These are grouped into five families:

#### Hate Speech Topics (16 columns)
| Column | Fill% | Description |
|--------|-------|-------------|
| `topic_HS_ANTI_FOREIGN` | 32% | Anti-foreigner / xenophobic rhetoric |
| `topic_HS_CASTE_RACISM` | 27% | Caste-based or racial discrimination |
| `topic_HS_CLAN_HIERARCHY` | 29% | Clan hierarchy / superiority narratives |
| `topic_HS_CLAN_TARGETING` | 27% | Targeting based on clan identity |
| `topic_HS_DEHUMANISATION_TARGETING` | 48% | Dehumanising language directed at groups |
| `topic_HS_DEHUMANISE_MEDIA_TRUST` | 21% | Dehumanising media / trust erosion |
| `topic_HS_ETHNIC_SCAPEGOATING_JIENGE_CLUSTER` | 5% | Ethnic scapegoating (Jieng/Dinka cluster — South Sudan) |
| `topic_HS_FACTIONAL_ATTACKS_AND_BETRAYAL` | 26% | Inter-factional attack / betrayal narratives |
| `topic_HS_GBOV_GENDERED` | 21% | Gender-based violence / gendered hate |
| `topic_HS_MILITARISATION_STEREOTYPE_MATHIANG_ANYOR` | 6% | Militarisation stereotypes (Mathiang Anyoor — South Sudan) |
| `topic_HS_MTN_CODED_METAPHOR_REVIEW` | 12% | Coded metaphors requiring manual review |
| `topic_HS_NATIONAL_IDENTITY_ANTI_ARAB_FRAMING` | 5% | National identity / anti-Arab framing (South Sudan) |
| `topic_HS_REGIONALISM_KOKORA` | 5% | Regionalism / Kokora (separatism — South Sudan) |
| `topic_HS_RETURN_DIASPORA_STIGMA` | 5% | Stigmatisation of returning diaspora |
| `topic_coded_slurs_ethnic` | 6% | Coded ethnic slurs |
| `topic_hate_slurs_or_coded` | 6% | Hate slurs or coded language |

#### Violent Extremism Topics (17 columns)
| Column | Fill% | Description |
|--------|-------|-------------|
| `topic_VE_ATROCITY_AERIAL_AND_ATTACKS` | 42% | Atrocity / aerial bombardment / attack references |
| `topic_VE_CODED_YOUTH_REFERENCES` | 48% | Coded references to youth combatants |
| `topic_VE_MILITIA_MOBILISATION` | 48% | Militia mobilisation calls |
| `topic_VE_OPERATIONAL_ESCALATION` | 24% | Operational escalation signals |
| `topic_VE_RECRUITMENT_COERCION` | 42% | Recruitment and coercion |
| `topic_VE_RELIGIOUS_JUSTIFICATION` | 48% | Religious justification for violence |
| `topic_VE_SELF_REFERENCE_TERMS` | 38% | VE group self-reference terminology |
| `topic_VE_TAKFIR_DEHUMANISE` | 47% | Takfiri dehumanisation language |
| `topic_VE_SECURITY_DELEGITIMATION_SPY_CLAIMS` | 2% | Security force delegitimisation / spy accusations |
| `topic_VE_ARABIC_PEACE_OR_WAR_TERMS_REVIEW` | 27% | Arabic peace/war terms requiring review |
| `topic_VE_FINANCING_COORDINATION` | 21% | VE financing and coordination |
| `topic_COUNTER_VE_LABELS` | 29% | Counter-VE narrative labels |
| `topic_RM_ATROCITY_PLANNING_RUMOURS` | 42% | Rumours about atrocity planning |
| `topic_RM_FINANCING_REQUESTS` | 21% | Financing requests / fundraising |
| `topic_ve_attack_tactics` | 42% | Attack tactics discussion |
| `topic_ve_bayah_affiliation` | 11% | Bay'ah (allegiance pledge) / VE group affiliation |
| `topic_ve_crossborder_diaspora` | 48% | Cross-border / diaspora VE activity |
| `topic_ve_group_branding` | 48% | VE group branding / propaganda |
| `topic_ve_propaganda_recruitment` | 48% | Propaganda and recruitment content |
| `topic_ve_recruitment_or_hijrah` | 37% | Recruitment / hijrah (migration) calls |

#### Peace & Counter-Narrative Topics (11 columns)
| Column | Fill% | Description |
|--------|-------|-------------|
| `topic_PEACE_CALLS_FOR_PEACE` | 48% | Direct calls for peace |
| `topic_PEACE_INDIGENOUS_MECHANISMS` | 44% | Indigenous peace mechanisms |
| `topic_PEACE_MEDIA_LITERACY_COUNTER_RUMOUR` | 37% | Media literacy / counter-rumour |
| `topic_PEACE_RECONCILIATION_FORGIVENESS` | 48% | Reconciliation and forgiveness |
| `topic_PEACE_TRADITIONAL_MEDIATION` | 25% | Traditional mediation |
| `topic_PEACE_UNITY_HEALING` | 48% | Unity and healing |
| `topic_PEACE_WOMEN_VICTIM_SURVIVOR_VOICES` | 48% | Women's / victim / survivor voices |
| `topic_PEACE_HASHTAG_CAMPAIGNS` | 5% | Peace hashtag campaigns |
| `topic_PEACE_ORG_REFERENCES` | 6% | Peace organisation references |
| `topic_PEACE_SYMBOLIC_SLOGANS` | 1% | Symbolic peace slogans |
| `topic_nonviolence_deescalation` | 10% | Non-violence / de-escalation |

#### Cross-Cutting Narrative Topics (14 columns)
| Column | Fill% | Description |
|--------|-------|-------------|
| `topic_delegitimisation_anti_state` | 48% | Anti-state delegitimisation |
| `topic_counter_disinfo_correction` | 48% | Counter-disinformation / corrections |
| `topic_explicit_violence_or_attack` | 48% | Explicit violence or attack description |
| `topic_gendered_hate_or_humiliation` | 45% | Gendered hate or humiliation |
| `topic_grievance_victimhood` | 48% | Grievance / victimhood narratives |
| `topic_identity_incitement_dehumanisation` | 6% | Identity-based incitement / dehumanisation |
| `topic_interfaith_peace` | 47% | Interfaith peace initiatives |
| `topic_misdisinfo_rumour_conspiracy` | 48% | Misinformation / disinformation / rumour / conspiracy |
| `topic_peace_cohesion_counter` | 48% | Peace / cohesion counter-narratives |
| `topic_reconciliation_forgiveness` | 48% | Reconciliation / forgiveness |
| `topic_religious_justification_takfir` | 47% | Religious justification / takfir |
| `topic_retaliation_mobilisation` | 47% | Retaliation / mobilisation calls |
| `topic_sectarian_or_religious_incitement` | 45% | Sectarian or religious incitement |
| `topic_sexualised_harm_or_humiliation` | 48% | Sexualised harm or humiliation |
| `topic_unity_cohesion` | 45% | Unity / social cohesion |

#### Threat-Specific Topics (3 columns)
| Column | Fill% | Description |
|--------|-------|-------------|
| `topic_direct_threats_intimidation` | 7% | Direct threats and intimidation |
| `topic_doxxing_or_personal_data_cues` | 18% | Doxxing or personal data exposure cues |
| `topic_expulsion_or_ethnic_cleansing_cues` | 3% | Expulsion or ethnic cleansing cues |

---

## Classification Model Outputs (17 columns)

Four HuggingFace BERT models are applied to every record. Each model produces a predicted label, confidence score, and per-class probabilities.

### Model 1: EA-HS (East Africa Hate Speech) — COMPLETE

- **HuggingFace**: [KSvendsen/EA-HS](https://huggingface.co/KSvendsen/EA-HS)
- **Architecture**: `bert-base-multilingual-cased` fine-tuned on East African social media
- **Labels**: Normal, Abusive, Hate (3-class)
- **Fill**: 100% (80,714/80,714)

| Column | Type | Description |
|--------|------|-------------|
| `EA_HS_pred` | string | Predicted label: `Normal`, `Abusive`, or `Hate` |
| `EA_HS_conf` | float | Confidence score (probability of predicted class, 0–1) |
| `EA_HS_Normal` | float | Probability of Normal class |
| `EA_HS_Abusive` | float | Probability of Abusive class |
| `EA_HS_Hate` | float | Probability of Hate class |

**Distribution**: Normal: 65,429 (81.1%) · Abusive: 10,155 (12.6%) · Hate: 5,130 (6.4%)

### Model 2: Polarization-Kenya — IN PROGRESS

- **HuggingFace**: [datavaluepeople/Polarization-Kenya](https://huggingface.co/datavaluepeople/Polarization-Kenya)
- **Architecture**: BERT fine-tuned on Kenyan political discourse
- **Labels**: not_polarization, polarization (binary)
- **Fill**: ~48% (classification in progress)

| Column | Type | Description |
|--------|------|-------------|
| `Polarization_Kenya_pred` | string | Predicted label: `not_polarization` or `polarization` |
| `Polarization_Kenya_conf` | float | Confidence score (0–1) |
| `Polarization_Kenya_not_polarization` | float | Probability of not_polarization |
| `Polarization_Kenya_polarization` | float | Probability of polarization |

### Model 3: Afxumo Toxicity (Somaliland) — QUEUED

- **HuggingFace**: [datavaluepeople/Afxumo-toxicity-somaliland-SO](https://huggingface.co/datavaluepeople/Afxumo-toxicity-somaliland-SO)
- **Architecture**: BERT fine-tuned on Somali-language content
- **Labels**: not_afxumo, afxumo (binary — "afxumo" = toxic in Somali)
- **Fill**: ~7% (partial from previous runs)

| Column | Type | Description |
|--------|------|-------------|
| `Afxumo_Somali_pred` | string | Predicted label: `not_afxumo` or `afxumo` |
| `Afxumo_Somali_conf` | float | Confidence score (0–1) |
| `Afxumo_Somali_not_afxumo` | float | Probability of not_afxumo |
| `Afxumo_Somali_afxumo` | float | Probability of afxumo (toxic) |

### Model 4: Hate Speech Sudan v2 — QUEUED

- **HuggingFace**: [datavaluepeople/Hate-Speech-Sudan-v2](https://huggingface.co/datavaluepeople/Hate-Speech-Sudan-v2)
- **Architecture**: BERT fine-tuned on Sudan/South Sudan content
- **Labels**: not_hate_speech, hate_speech (binary)
- **Fill**: ~34% (partial from previous runs)

| Column | Type | Description |
|--------|------|-------------|
| `HateSpeech_Sudan_pred` | string | Predicted label: `not_hate_speech` or `hate_speech` |
| `HateSpeech_Sudan_conf` | float | Confidence score (0–1) |
| `HateSpeech_Sudan_not_hate_speech` | float | Probability of not_hate_speech |
| `HateSpeech_Sudan_hate_speech` | float | Probability of hate_speech |

---

## Text Field Logic

The classification script uses a fallback approach for text input:

1. **Primary**: `post_text_pi` — the post body text
2. **Fallback**: `comment_text_pi` — used only when `post_text_pi` is empty/null
3. Records with neither field populated (327 rows, 0.4%) receive no classification

This ensures both posts and comments are classified, with post text taking priority when a record contains both.

---

## Data Provenance

| Attribute | Detail |
|-----------|--------|
| Collection platform | [Phoenix](https://console.phoenix.howtobuildup.org) by How To Build Up |
| Project | BRACE4PEACE (UNDP Project 133) |
| Collection method | Keyword-based social media gathers |
| Platforms monitored | Facebook, X (Twitter), TikTok |
| Geographic scope | Kenya, Somalia, South Sudan |
| PII handling | All text and identifiers are PII-redacted (`_pi` suffix) |
| Processing pipeline | Phoenix gather → CSV export → HuggingFace model inference |

---

## Monitoring Data (Daily Scans)

In addition to the Phoenix social media datasets, this repository contains structured findings from the **BRACE4PEACE automated monitoring system** — a daily scan that monitors web sources, news outlets, and analysis platforms for new hate speech, disinformation, and violent extremism developments.

### Location

```
monitoring/
├── brace4peace_protocol.md        # Full 5-step monitoring protocol
├── baseline_feb26_2026.md         # Rolling threat baseline for alert decisions
└── findings/                      # Daily scan outputs
    ├── README.md                  # Schema documentation
    ├── state.json                 # System state (last run, notifications sent)
    ├── findings_2026-03-14.json   # Daily findings
    └── findings_2026-03-15.json
```

### What the Monitor Covers

| Dimension | Scope |
|-----------|-------|
| Countries | South Sudan (P1 CRITICAL), Kenya (P1 HIGH), Somalia (P1 HIGH) |
| Threat types | Hate speech, disinformation, violent extremism, Al-Shabaab media |
| Sources | 10+ news sites, 6+ analysis centres, Al-Shabaab media outlets |
| Frequency | Daily at 06:00 UTC |
| Protocol steps | X/Twitter searches (24 queries), web monitoring (27 searches), direct URL fetches (6 sites), narrative classification, alert decisions |

### Findings Schema

Each daily JSON file contains:

- **`notable_new_intel`** — Array of findings that represent genuinely new intelligence beyond the rolling baseline. Each entry includes:
  - `region`, `threat_level` (P1/P2/P3), `headline`
  - `why_new_vs_baseline` — explanation of why this crosses the alert threshold
  - `sources` — array of `{title, url}` references
  - `narrative_classification` — mapping to BRACE4PEACE narrative families (Ethnic Incitement, Victimhood/Grievance, Revenge/Retribution, Religious Distortion, Delegitimization, Misinformation/Disinformation, Existential Threat, Collective Blame, Peace/Counter-Narratives)
  - `ve_related`, `al_shabaab_related` — boolean flags
  - `confidence` — high / medium / low

- **`items_checked`** — Full audit trail of all sources queried, with per-source relevance assessment and analytical notes

See [`monitoring/findings/README.md`](../monitoring/findings/README.md) for the complete schema documentation.

### Collected Intelligence Summary

| Date | Alerts | Key Finding |
|------|--------|-------------|
| 2026-03-14 | 0 | Routine scan — no new intelligence beyond baseline |
| 2026-03-15 | 1 (P1 CRITICAL) | South Sudan: Akobo evacuation order, SSPDF–SPLA-IO fighting, aid agencies suspended, 280K+ displaced |

### Current Limitations

- X/Twitter social media searches (24 queries in protocol) cannot execute in the automated environment
- Eye Radio articles blocked by robots.txt
- System relies on web search + direct URL fetches; real-time social media monitoring requires additional tooling

---

## Missing Data

- **2 pending files**: `Somalia_Comments_Escalation.csv` and `Somalia_Other.csv` (~4,067 additional rows) were not included in the current upload
- **Parent post fields**: All 14 `*_parent` columns are unpopulated (0% fill) — reserved for future threaded context
- **Author metadata**: Fields like `post_author_followers_count`, `post_author_location`, `post_author_description_pi` are unpopulated
- **Phoenix topic labels**: Fill rates vary 1–48% depending on which Phoenix job runs processed each record
- **Phoenix toxicity scores**: 15–34% fill — only available for certain job runs
