# IRIS Journal Papers — Design Spec

Two complementary papers drawing on the IRIS platform and BRACE4PEACE project data. Paper A targets the AI/CS community; Paper D targets the peace, conflict, and policy community.

## Constraints

- The BRACE4PEACE project report is confidential and cannot be referenced directly.
- Individual posts, sources, and actor identities must not be published — aggregate statistics only.
- All source data is PII-redacted (Phoenix `_pi` suffix fields).
- IRB/ethics approval status: **unresolved — must check with UNDP before submission.** No formal IRB, but PII-redacted data and aggregate-only publication is the baseline position.
- The Phoenix gathers dataset (80K+ posts) was collected via retroactive keyword-based scraping covering approximately 6 months (mid-2025 to early 2026). Dates outside this window (e.g., 2007) are outlier noise, not intentional collection.
- Daily automated monitoring has only been running for a few weeks. Do not overstate deployment duration.

---

## Paper A: Methodology / Systems Paper

### Title (working)

*IRIS: An Automated Multi-Stage Pipeline for Hate Speech and Disinformation Monitoring in Low-Resource East African Contexts*

### Target audience

Cross-disciplinary AI for social good — NLP researchers, computational social scientists, humanitarian tech practitioners.

### Target venues

- ACM COMPASS (Computing and Sustainable Societies)
- AAAI AI for Social Good workshop
- EMNLP Findings
- AI & Society (journal)

### Core contribution

The design and evaluation of a deployed end-to-end pipeline that combines rule-based linguistic filtering, fine-tuned multilingual BERT models, and LLM-based quality assurance for hate speech and disinformation monitoring in East Africa. No published system combines all three approaches in an operational conflict-monitoring context.

### Positioning against the landscape

| Existing approach | Gap IRIS fills |
|---|---|
| Perspective API / Jigsaw | English-centric, no local-language support for Somali/Swahili/Arabic dialects, no conflict-specific narrative taxonomy, no operational alerting |
| HateCheck / HatEval benchmarks | Academic datasets, rarely operationalized into deployed systems |
| ACLED / conflict monitoring | Tracks physical events from news reports, not online speech |
| CrisisNLP / social media crisis tools | Focus on natural disasters, not sustained hate speech monitoring |
| PeaceTech Lab / Sentinel Project | Closest peers — but typically manual or semi-automated, not end-to-end ML pipelines |
| AfriSenti / MasakhaNER | African NLP efforts — related but focused on sentiment/NER, not hate speech classification pipelines |

### Structure

#### 1. Introduction
- Online hate speech as a precursor to violence in East Africa.
- Why existing tools fail: English-centric classifiers, no conflict taxonomy, no operational alerting.
- IRIS's contribution: an end-to-end deployed system, not a benchmark exercise.

#### 2. Related Work
- General hate speech detection (Davidson et al., Waseem & Hovy, etc.).
- Multilingual / low-resource HS detection (AfriSenti, MasakhaNER — related African NLP efforts).
- Toxicity APIs (Perspective, OpenAI moderation) — limitations for non-English, local slang.
- Conflict monitoring systems (ACLED, CrisisNLP, PeaceTech Lab) — different modality.
- LLM-augmented classification pipelines (emerging area).

#### 3. System Architecture
- Data collection layer: Phoenix gathers (retroactive scraping, ~80K posts over 6 months), Apify sweeps (daily automated keyword searches), research agent (Tavily + Claude), direct URL monitoring (6 institutional sources).
- Five-stage classification pipeline: noise filtering -> EA relevance gating -> rule-based HS indicators -> BERT classification -> LLM QA.
- Alert and escalation protocol (P1 CRITICAL / P2 HIGH / P3 MODERATE thresholds).
- Operational infrastructure: GitHub Actions automation, Supabase vector store, daily commit cycle.
- Dual monitoring wheels: Disorder Events (campaign-level) and Hate Speech Posts (individual post-level).

#### 4. Classification Methodology
- Rule-based stage: 140+ East Africa indicators, local-language dictionaries (Somali, Swahili, Arabic dialect terms), noise rejection, non-EA fast reject.
- ML stage: EA-HS model (XLM-RoBERTa `xlm-roberta-base` fine-tuned, 278M params, 3-class: Normal/Abusive/Hate), plus 3 supplementary BERT models (Polarization-Kenya, Afxumo Toxicity, Hate Speech Sudan v2).
- LLM QA stage: Claude API for explanation generation, false positive removal, HS subtype assignment.
- How the stages interact — what each catches that the others miss.

#### 5. Evaluation
- Per-stage precision/recall/F1 on the 80K+ post dataset.
- Ablation study: pipeline with/without rule-based filtering, with/without LLM QA — demonstrating the value of each stage.
- Error analysis: common failure modes (sarcasm, code-switching, indirect speech, metaphorical violence).
- Operational metrics: throughput (4-10 items/sec on 2-vCPU), cost (~$2/day for Apify + API calls), batch size and crash recovery.
- **Note:** Ablation data may need to be generated — this is an analysis task, not a system-building task.

#### 6. Discussion
- Why a multi-stage pipeline outperforms any single approach in this context.
- Trade-offs: cost vs. accuracy, automation vs. human review, coverage vs. precision.
- Generalizability to other low-resource conflict monitoring contexts.
- Limitations: keyword-driven collection bias, classifier coverage gaps (Polarization-Kenya at 48%, Afxumo at 7%), X/Twitter search limitations in CI.

#### 7. Ethics & Data Privacy
- PII redaction protocol (all text fields redacted before classification).
- No individual post exposure — aggregate metrics only.
- Operational use strictly within UNDP mandate.
- Risks of automated conflict monitoring: false positives leading to misallocation of attention, surveillance concerns, potential for misuse.
- IRB status (to be resolved).

#### 8. Conclusion
- Summary: first published end-to-end hate speech monitoring pipeline deployed for East African conflict contexts.
- Open questions: model coverage completion, longitudinal performance, cross-context transfer.

### Key figures and tables needed
- System architecture diagram (pipeline stages with data flow).
- Classification performance table (precision/recall/F1 per model, per stage).
- Ablation results table.
- Error analysis examples (anonymized/synthesized, not real posts).
- Cost and throughput table.

### Analysis tasks required before writing
- [ ] Generate per-model precision/recall/F1 metrics.
- [ ] Run ablation experiments (pipeline with/without each stage).
- [ ] Compile error analysis categories with counts.
- [ ] Calculate operational metrics (throughput, cost per run).

---

## Paper D: Findings / Policy Paper

### Title (working)

*Online Hate Speech and Disinformation Patterns Across East Africa: Evidence from Automated Classification of 80,000+ Social Media Posts*

### Target audience

Peace & conflict researchers, policy makers, development practitioners, peacebuilding programme designers.

### Target venues

- Journal of Peace Research
- Conflict Management and Peace Science
- International Peacekeeping
- Stability: International Journal of Security and Development

### Core contribution

The largest published cross-national analysis of classified online hate speech in East Africa (to our knowledge). Empirical evidence on how hate speech subtypes, platforms, and disinformation narratives vary across Kenya, Somalia, and South Sudan.

### Structure

#### 1. Introduction
- Online hate speech as a growing concern in East African conflict contexts.
- The gap: most empirical research on online hate speech focuses on Western/English-language settings; limited large-scale evidence from East Africa.
- What this paper contributes: cross-national analysis of 80K+ classified posts across 3 countries and 3 platforms.
- Brief mention of IRIS as the classification tool (referencing Paper A for methodological details).

#### 2. Context
- Kenya: post-2007 election violence legacy, ongoing ethnic tensions, 2027 election cycle approaching, social media penetration patterns.
- Somalia: Al-Shabaab propaganda ecosystem, clan dynamics, diaspora information flows, Al-Shabaab-affiliated media outlets.
- South Sudan: civil war legacy, ethnic mobilization, recent escalations (e.g., Akobo), displacement dynamics.
- The role of social media platforms in East Africa: Facebook dominant, X/Twitter significant, TikTok emerging.

#### 3. Data & Methods
- Data source: Phoenix platform keyword-based gathers, retroactive scraping covering ~6 months (mid-2025 to early 2026).
- Coverage: 80,714 posts — Kenya (26,006), Somalia (27,006), South Sudan (27,702).
- Platforms: Facebook (44,821), X/Twitter (32,653), TikTok (3,240).
- Classification: automated five-stage pipeline (reference Paper A for details).
- Hate speech taxonomy: 8 subtypes — Ethnic Targeting, Political Incitement, Clan Targeting, Religious Incitement, Dehumanisation, Anti-Foreign, General Abuse, Gendered Violence.
- Disinformation taxonomy: 9 narrative families — Ethnic Incitement, Revenge/Retribution, Victimhood/Grievance, Religious Distortion, Misinformation, Existential Threat, Collective Blame, Delegitimization, Peace/Counter-Narratives.
- Limitations: keyword-driven collection introduces selection bias (posts without target keywords are missed); classifier error rates (report from Paper A); platform access constraints (TikTok underrepresented).

#### 4. Findings: Hate Speech Patterns
- Overall prevalence from Phoenix topic labels: 26.5% tagged as hate speech narratives. EA-HS BERT model classification: Normal (81.1%) / Abusive (12.6%) / Hate (6.4%). Note: these two measures use different definitions — Phoenix labels are broader narrative tags; EA-HS is a stricter ML classification. The paper must clearly define and reconcile these metrics.
- **By country:** which HS subtypes dominate where — e.g., ethnic targeting patterns in Kenya vs. clan-based targeting in Somalia vs. political incitement in South Sudan.
- **By platform:** how HS manifests differently on Facebook (largest volume) vs. X/Twitter vs. TikTok. Platform-specific dynamics.
- **Subtype distribution:** relative prevalence of each of the 8 HS subtypes, overall and by country.
- **Temporal patterns:** any trends visible within the ~6-month collection window.
- All presented as aggregate counts, proportions, cross-tabulations, and visualizations. No individual posts.

#### 5. Findings: Disinformation & Narrative Families
- The 9 narrative families and their relative prevalence across the dataset.
- ~430 tracked disinformation events: dominant themes and campaigns.
- Country-level variation in narrative types.
- Interaction between HS and disinformation: do they co-occur? Do disinformation narratives amplify hate speech or vice versa?
- Al-Shabaab-specific narratives: propaganda themes and platform distribution.

#### 6. Discussion: Implications for Policy & Programming
- What the patterns mean for conflict early warning: which signals matter most?
- Platform-specific recommendations: Facebook as the primary vector in East Africa vs. Western focus on X/Twitter. Implications for platform governance and counter-speech programming.
- Country-specific programming implications: tailoring interventions to the dominant HS subtypes in each context.
- The counter-narrative finding: 21% of content classified as "Peace." What does protective speech look like, and how can programming amplify it?
- The value of automated monitoring for programme design: moving from anecdotal evidence to systematic measurement.
- Limitations: selection bias from keyword-driven collection, classifier accuracy bounds, aggregate data masks individual dynamics, short temporal window limits trend analysis.

#### 7. Ethics
- PII redaction and aggregate-only reporting.
- Responsible disclosure: no individual actors, handles, or sources named.
- Risks of surveillance framing vs. protection framing — how monitoring systems can be misused.
- Researcher positionality: system built for UNDP programming, not independent academic research.
- IRB status (to be resolved before submission).

#### 8. Conclusion
- Summary of key empirical contributions: cross-national hate speech patterns, platform variation, narrative taxonomies.
- Call for more systematic monitoring infrastructure in conflict-affected regions.
- Future directions: longitudinal analysis as daily monitoring data accumulates, causal analysis linking online signals to offline events, expansion to additional countries.

### Key figures and tables needed
- Map visualization: HS prevalence by country.
- Cross-tabulation table: HS subtypes x country.
- Platform distribution chart: HS volume and subtypes by platform.
- Narrative family prevalence chart (9 families).
- Disinformation event themes table.
- Temporal trend line (if patterns exist within the 6-month window).

### Analysis tasks required before writing
- [ ] Generate cross-tabulations: HS subtype x country, HS subtype x platform.
- [ ] Calculate overall and per-country HS prevalence rates.
- [ ] Analyze disinformation event themes and country distribution.
- [ ] Test for HS-disinformation co-occurrence patterns.
- [ ] Check for temporal trends within the collection window.
- [ ] Produce aggregate visualizations (no individual post data).

---

## Shared Action Items

- [ ] **Resolve IRB/ethics status with UNDP** — required before submission of either paper. Determine whether UNDP project approval constitutes sufficient ethical clearance or whether separate IRB review is needed.
- [ ] **Literature review** — map the landscape for both papers. Key areas: African NLP hate speech detection, East African online hate speech studies, automated conflict monitoring systems.
- [ ] **Determine authorship** — who contributes to which paper, acknowledgments, UNDP attribution.
- [ ] **Select target venues** — decide primary venue for each paper, check formatting requirements and deadlines.
- [ ] **Generate evaluation data for Paper A** — ablation experiments, per-stage metrics.
- [ ] **Generate cross-tabulations for Paper D** — aggregate analysis of the 80K+ dataset.

## Relationship Between Papers

Paper A is referenced by Paper D for methodological details. Paper D can cite Paper A as "Author et al. (forthcoming)" or they can be submitted independently with Paper D containing a condensed methods section. Ideally Paper A is submitted first or simultaneously so the methods are peer-reviewed.

## Timeline Considerations

- Paper A can be written with existing system documentation + evaluation metrics generation.
- Paper D requires running aggregate analysis on the Phoenix dataset — this is the primary blocking task.
- Both papers benefit from the daily monitoring data accumulating — but neither should wait for a "complete" dataset. The 80K+ retroactive corpus is sufficient.
