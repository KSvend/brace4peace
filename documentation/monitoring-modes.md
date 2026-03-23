# MERLx IRIS — Monitoring Modes

MERLx IRIS operates two parallel monitoring systems, each with its own data pipeline, classification workflow, and visualization. Both track harmful online content in East Africa (Somalia, South Sudan, Kenya), but they answer different questions.

---

## 1. Disorder Events Wheel

**Question:** What disinformation campaigns, propaganda operations, and hate speech events are actively circulating, and how are they evolving?

### What is a disorder event?

A disorder event is a **narrative-level incident** — a coordinated or significant claim, campaign, or event that creates societal disorder. Events can be:

| Type | Description |
|------|-------------|
| **Disinformation** | Deliberately false claims designed to deceive |
| **Misinformation** | False claims spread without deliberate intent |
| **Propaganda** | Coordinated messaging to shape opinion (may contain true/false elements) |
| **Hate Speech Event** | Significant hate speech incidents that constitute discrete events (e.g., a viral incitement post by a public figure, a coordinated harassment campaign) |
| **Incitement** | Calls to violence or action against specific groups |

### How events get on the wheel

Events enter the timeline via two automated pipelines:

1. **Apify keyword sweeps** — targeted social media searches on X, Facebook, TikTok using country-specific keyword strategies. Results are classified by rule-based pattern matching + LLM review.
2. **Research agent** — daily automated desk research scanning news outlets, analysis platforms, and watchlist sources. Classifies and deduplicates findings against existing events.

### Classification: Narrative families (wheel segments)

Each event is assigned to a **narrative family** — the high-level category that appears as a segment on the wheel:

| Family | Weight | Level |
|--------|--------|-------|
| Ethnic Incitement | 5 | CRITICAL |
| Revenge/Retribution | 5 | CRITICAL |
| Victimhood/Grievance | 4 | HIGH |
| Religious Distortion | 4 | HIGH |
| Misinformation/Disinformation | 4 | HIGH |
| Existential Threat | 4 | HIGH |
| Collective Blame | 4 | HIGH |
| Delegitimization | 3 | MODERATE |
| Foreign Influence | 3 | MODERATE |
| Peace/Counter-Narratives | -2 | PROTECTIVE |

Within each family, events may also be linked to **specific narratives** (e.g., `NAR-SO-001: Al-Shabaab False Victories`). These appear in the detail panel when clicking an event dot.

### What the wheel tracks per event

- **Lifecycle**: How long the event has been active (first seen → last seen)
- **Certainty**: Confirmed / Potential / Context
- **Threat level**: P1 Critical / P2 High / P3 Moderate (determines ring position)
- **Actors**: Instigators, influencers, amplifiers, counter-narrative voices
- **Spread**: How widely the event has been reproduced (1-5 scale)
- **Sources**: Direct URLs and publisher references
- **Related events**: Cross-links to other events in the same narrative cluster

### Dot appearance on the wheel

| Visual | Meaning |
|--------|---------|
| Bright dot with glow | Confirmed event |
| Medium opacity dot | Potential event |
| Faint dot | Context event |
| Inner ring | P1 CRITICAL threat |
| Middle ring | P2 HIGH threat |
| Outer ring | P3 MODERATE threat |
| Dot size | Spread + observation count |

---

## 2. Hate Speech Posts Wheel

**Question:** What types of hate speech are being used on social media right now, and at what volume?

### What is a hate speech post?

A hate speech post is a **single social media post or comment** classified by the ML pipeline. It is not necessarily part of a broader event — it's a data point showing what form of hate speech is being used online.

### How posts get on the wheel

1. **Apify HS keyword sweeps** — separate from the disorder pipeline, uses HS-specific keyword groups targeting known hate speech terms in Somali, Swahili, Arabic, and English.
2. **ML classification** — the EA-HS model (fine-tuned BERT) classifies each post as **Hate**, **Abusive**, or **Normal**.
3. **LLM quality assurance** — Anthropic Claude reviews ML-classified posts, assigns HS subtypes, generates human-readable explanations, and flags false positives.

### Classification: HS subtypes (wheel axes)

Each post is assigned an **HS subtype** that appears as an axis on the radial wheel:

- Ethnic Targeting
- Political Incitement
- Clan Targeting
- Religious Incitement
- Dehumanisation
- Anti-Foreign
- General Abuse
- Gendered Violence

### What the wheel shows per post

- **ML prediction**: Hate / Abusive / Normal (from EA-HS model)
- **Confidence score**: Model certainty (0-1)
- **Toxicity score**: Combined toxicity metric
- **HS subtype**: Specific form of hate speech
- **Explanation**: LLM-generated description of why the post is classified as hate speech
- **QC label**: Quality control assessment from LLM review

### Dot appearance on the wheel

| Visual | Meaning |
|--------|---------|
| Red dot | Classified as Hate |
| Orange dot | Classified as Abusive |
| Grey dot | Classified as Normal / Questionable |
| Distance from center | Toxicity score |

---

## Key Differences

| | Disorder Events | Hate Speech Posts |
|-|-----------------|-------------------|
| **Unit of analysis** | Narrative event / campaign | Individual post or comment |
| **Classification** | Narrative families + specific narratives | HS subtypes (Ethnic Targeting, etc.) |
| **ML model** | None (rule-based + LLM) | EA-HS BERT model + LLM QA |
| **Lifecycle tracking** | Yes — first seen, last seen, observations | No — point-in-time classification |
| **Actor tracking** | Yes — instigators, influencers, counter | No |
| **Wheel segments** | Narrative families (10 categories) | HS subtypes (8 axes) |
| **Threat levels** | P1/P2/P3 ring position | Toxicity score distance |
| **Volume** | ~430 tracked events | ~6,800 classified posts |
| **Data source** | Apify sweeps + research agent + desk review | Apify HS sweeps + Phoenix gathers |

---

## Data Flow

```
                    MERLx IRIS
                        │
          ┌─────────────┴──────────────┐
          │                            │
   Disorder Events               Hate Speech Posts
          │                            │
   ┌──────┴──────┐              ┌──────┴──────┐
   │             │              │             │
 Apify        Research        Apify HS      Phoenix
 Sweeps       Agent           Sweeps        Gathers
   │             │              │             │
 Rule-based    LLM            EA-HS         EA-HS
 + LLM        classify        BERT          BERT
   │             │              │             │
 Narrative     Dedup +        LLM QA +      LLM QA +
 matching      lifecycle      HS subtype    HS subtype
   │             │              │             │
   └──────┬──────┘              └──────┬──────┘
          │                            │
    events.json              hate_speech_posts.json
          │                            │
   Disorder Wheel              HS Posts Wheel
```
