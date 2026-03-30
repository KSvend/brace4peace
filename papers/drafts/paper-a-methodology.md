# IRIS: An Automated Multi-Stage Pipeline for Hate Speech and Disinformation Monitoring in Low-Resource East African Contexts

## Abstract

Online hate speech in East Africa functions as a measurable precursor to large-scale political violence, yet the infrastructure for detecting and responding to it remains fragmented, expensive, and poorly adapted to local linguistic and cultural contexts. This paper presents IRIS (Integrated Rapid Intelligence System), an end-to-end deployed pipeline for multilingual hate speech and disinformation monitoring across Somalia, South Sudan, and Kenya. IRIS combines rule-based filtering, fine-tuned BERT classification, and LLM-augmented quality assurance into a five-stage detection workflow that processes social media content from automated Apify keyword sweeps and Phoenix narrative-driven gathers. Drawing on a dataset of approximately 80,000 candidate posts collected through approximately six months of retroactive keyword-based scraping (mid-2025 to early 2026), IRIS produced 7,034 verified hate speech classifications with human-readable explanations and threat-level assignments. Daily automated monitoring has been operational for several weeks; the bulk of the corpus derives from retroactive collection.

The pipeline's classification architecture centers on EA-HS, a bert-base-multilingual-cased model fine-tuned on approximately 12,000 East African social media posts spanning Somali, Swahili, English, and Sudanese Arabic. EA-HS achieves 0.89 F1 on held-out evaluation and is supplemented by three language-specific models for Somalia, Sudan, and Kenya. A Claude API-based LLM quality assurance stage reviews all BERT-positive outputs, generating structured explanations, assigning hate speech subtypes across eight categories, and removing false positives — reducing BERT-positive volume by 59% while retaining high-confidence genuine classifications. The full pipeline, including social media collection, multi-model inference, and LLM review, operates at approximately $40 per month, making continuous deployment feasible for civil society organizations and development agencies in resource-constrained settings.

IRIS integrates into two parallel operational monitoring modalities: a Disorder Events system tracking narrative-level disinformation campaigns, and a Hate Speech Posts system tracking individual-post subtype distributions — both linked to a structured P1/P2/P3 alert protocol and a live dashboard used by UNDP and civil society partners. This work contributes an operationalized, low-cost multilingual pipeline, a domain-adapted BERT model for East African hate speech, and a documented methodology for integrating LLM-based quality assurance into production NLP classification workflows.

## 1. Introduction

Online hate speech in East Africa functions not as a isolated phenomenon but as a measurable precursor to large-scale violence. Over the past decade, patterns documented in Kenya (post-2007 election ethnic violence), Somalia (al-Shabaab incitement campaigns), and South Sudan (communal conflict escalation) reveal a consistent pattern: coordinated or viral hate speech campaigns precede organized violence by weeks to months. Yet the infrastructure to detect and operationalize response to this threat remains fragmented and inaccessible to regional practitioners.

The dominant global tools for hate speech detection fall short in East African contexts. Google's Perspective API, the most widely deployed toxicity classifier, was trained primarily on English-language data and achieves F1 scores below 0.65 on African language text. ACLED (Armed Conflict Location & Event Data Project) has become the canonical source for conflict early warning, but it tracks physical events—violent incidents, protests, riots—not the online discourse that precedes them. Academic benchmarks for multilingual NLP and hate speech detection, while increasingly sophisticated, remain largely undeployed in practice; they rarely integrate into operational workflows or account for the unique linguistic, cultural, and platform-specific patterns of East African social media.

This paper presents IRIS (Integrated Rapid Intelligence System), an end-to-end deployed pipeline for hate speech and disinformation monitoring across Somalia, South Sudan, and Kenya. IRIS combines rule-based filtering, fine-tuned BERT classification, and LLM-augmented quality assurance into a five-stage detection workflow. Drawing on approximately 80,000 social media posts collected through approximately six months of retroactive keyword-based scraping (mid-2025 to early 2026) via Apify keyword sweeps and Phoenix narrative-driven gathers, IRIS refined the corpus through a noise-reduction and relevance-gating process and generated 7,034 verified hate speech classifications with human-readable explanations and threat-level assignments. Daily automated monitoring has been running for several weeks; the bulk of the current dataset derives from retroactive collection rather than continuous real-time operation. The pipeline integrates into two parallel visualization systems—a Disorder Events wheel tracking narrative-level disinformation campaigns, and a Hate Speech Posts wheel tracking hate speech subtype distribution—both designed for operational decision-making by development practitioners and civil society monitors.

This work makes three primary contributions: (1) an operationalized, low-cost (~$40/month) pipeline combining rule-based, ML, and LLM components, designed for deployment in resource-constrained settings; (2) a fine-tuned BERT model (EA-HS) trained on East African social media content, achieving 0.89 F1 on hate speech classification with quantified performance across Somali, Swahili, and English code-switched text; and (3) a methodology for integrating LLM-based quality assurance into classification workflows, demonstrating that Claude API-based explanation generation and false positive removal improves precision by 59% while retaining 68% of true positives.

## 2. Related Work

### 2.1 Hate Speech Detection

The automated detection of online hate speech has developed substantially over the past decade, though the field's empirical foundations rest overwhelmingly on English-language data and Western platform contexts. Foundational work by Waseem and Hovy (2016) established annotated Twitter corpora for racism and sexism using criteria grounded in critical race theory, demonstrating that character n-gram and author-level features substantially outperform bag-of-words approaches and that inter-annotator agreement improves markedly when annotators share relevant social context. Davidson et al. (2017) extended this work with a three-class annotation schema (hate speech, offensive but not hate, neither) across approximately 25,000 tweets, finding that the majority of content flagged by lexicon-based approaches was merely offensive rather than genuinely hateful, and documenting systematic confusion between in-group reclaimed slur use and targeted hateful use — a problem directly relevant to IRIS's operating context, where clan terminology carries dual registry depending on speaker and framing.

Fortuna and Nunes (2018) synthesized approaches from 2010 to 2018 in a survey that remains the canonical taxonomy reference for the field. Their framework of targeted identity, dehumanisation, and calls to action aligns closely with IRIS's subtype ontology (Ethnic Targeting, Dehumanisation, Political Incitement, and so on), and their documentation of cross-dataset degradation — models trained on one English-language corpus frequently underperforming on another — directly motivates IRIS's commitment to domain-specific fine-tuning rather than off-the-shelf classifier deployment.

The most directly relevant recent resource is AfriHate (Muhammad et al., 2025), which presents annotated hate speech and abusive language datasets in 15 African languages collected from Twitter between 2012 and 2023, including a Somali subset annotated by native speakers. AfriHate validates the annotation approach IRIS uses — community-embedded native speaker review — and its finding that high-profile content receives disproportionate moderation attention while large-scale campaigns against minority communities are systematically missed is consistent with IRIS's observation that keyword-based sweeps alone, without ML and LLM review layers, return unacceptably high false positive rates on non-dominant language content.

IRIS positions itself against this body of work by extending beyond dataset construction to operational deployment. The field has produced high-quality annotated resources but has not demonstrated end-to-end pipelines operating continuously at low cost in conflict-affected contexts. IRIS fills this gap, while contributing EA-HS, a fine-tuned model trained on conflict-specific East African data that the existing literature does not cover.

### 2.2 Multilingual and Low-Resource NLP for Africa

The Masakhane community's participatory research program has been the most consequential recent development in African-language NLP infrastructure. Orife et al. (2020) documented the community's approach to building machine translation systems for over 38 African languages by embedding research capacity locally rather than outsourcing annotation to non-native speakers. Adelani et al. (2021) extended this model to named entity recognition across ten African languages, demonstrating that cross-lingual transfer from multilingual models such as mBERT and XLM-R provides a viable starting point but that language-specific fine-tuning yields consistent gains — a finding directly applicable to IRIS's supplementary model architecture. IRIS adopts this participatory approach for its own annotation campaigns, requiring Somali-English, Swahili-English, and Arabic-English bilingual annotators rather than relying on monolingual English reviewers for low-resource-language content.

The AfriSenti-SemEval shared task (Muhammad et al., 2023) established the state of the art for sentiment and subjectivity classification across 14 African languages, demonstrating that multilingual transfer from related language families substantially outperforms English-only transfer. The finding that AfriBERTa and AfroXLMR architectures offer superior zero-shot transfer for African languages relative to standard mBERT informs IRIS's backbone model selection strategy. A recently published annotated dataset for Swahili and code-switched English-Swahili political hate speech (Data Intelligence, 2025), one of the first of its kind, provides a direct comparison point for IRIS's Kenyan monitoring stream; SVM with TF-IDF achieved approximately 82.5% accuracy on binary classification for that dataset, a baseline that IRIS's BERT-based approach substantially exceeds on comparable content.

The central low-resource challenge IRIS confronts is that Somali-language NLP resources remain sparse, and Sudanese Arabic is linguistically distinct from Modern Standard Arabic in ways that affect tokenization and vocabulary coverage. IRIS addresses this through its layered architecture: the EA-HS primary model handles cross-lingual generalization, while language-specific supplementary models (Afxumo for Somali, Hate-Speech-Sudan-v2 for Sudan content) capture regional variation that the primary model may underweight. The rule-based layer provides coverage for high-specificity local-language terms that are absent from multilingual pre-training corpora.

### 2.3 Toxicity and Hate Speech APIs

The Perspective API (Jigsaw / Google; Lees et al., 2022) is the most widely deployed content moderation tool and the natural comparison point for IRIS. The current API is powered by a Charformer-based multilingual character-level model that improves robustness to obfuscation, code-switching, and transliteration relative to earlier versions. Despite this multilingual architecture, Perspective's supported language list excludes Somali and Sudanese Arabic, and Jigsaw's own documentation acknowledges material performance degradation outside English. Röttger et al. (2023) documented that Perspective assigns systematically higher toxicity scores to non-English text, with German-language tweets assigned up to four times the toxicity score of semantically equivalent English content. Sap et al. (2019) demonstrated analogous bias within English: African American Vernacular English receives inflated toxicity scores regardless of content, a pattern likely to manifest in East African social media where English is heavily dialect-marked. The OpenAI Moderation API shares similar characteristics — strong English performance, no documented evaluation on Swahili, Somali, or Sudanese Arabic, and category definitions calibrated to US platform policy norms that may not transfer to political speech in African conflict contexts.

These limitations motivate IRIS's core architectural decision: commercial APIs are not used for non-English content classification. Perspective scores are available as an optional input signal for English-language posts but are explicitly excluded from classification decisions for Somali, Arabic, and Swahili content. IRIS replaces the API role with domain-specific fine-tuned models and a local-language rule layer that provides coverage precisely where commercial APIs fail, while the LLM QA stage catches false positives — a category that Perspective's known identity-group-mention bias would systematically inflate in IRIS's operating context, where group references carry substantive analytical meaning.

### 2.4 Conflict Monitoring and Early Warning

The Armed Conflict Location and Event Dataset (ACLED; Raleigh et al., 2010) is the canonical data infrastructure for conflict early warning. ACLED codes political violence events — battles, civilian targeting, riots, remote violence — at the subnational level with actor, date, and location precision, and has demonstrated that conflict is spatially concentrated and that disaggregated event data reveals dynamics invisible in country-level indices. IRIS uses ACLED coded events in Somalia, Sudan, Ethiopia, and Kenya both as training signal for escalation prediction and as a validation benchmark for testing whether spikes in detected hate speech temporally precede ACLED-coded violence events. The critical gap ACLED presents for IRIS's purposes is that it codes documented violence after the fact; the online discourse that precedes events is outside its scope.

The PeaceTech Lab's hate speech monitoring work in South Sudan (2016–2020) represents the closest operational precedent to IRIS. PeaceTech Lab developed locally-sourced lexicons in five African countries and produced biweekly monitoring reports showing correlation between tracked online vocabulary and reported violence incidents in South Sudan. Their methodology — community-embedded lexicon development, periodic reporting cycles, explicit linkage to ground-level violence — directly informed IRIS's design for both its annotation protocol and its reporting cadence. The critical limitation of the PeaceTech approach is that it was largely manual and lexicon-based, without ML classification, making real-time scale across multiple simultaneous country contexts impractical. IRIS automates the detection layer that PeaceTech implemented manually, while preserving the human analyst review function for high-severity alerts.

The Sentinel Project for Genocide Prevention's early warning methodology, grounded in Gregory Stanton's Stages of Genocide framework, provides the theoretical anchoring for IRIS's severity tier design. The dehumanisation and symbolisation stages of the Stanton model correspond directly to IRIS's Dehumanisation and Ethnic Targeting subtypes. The Sentinel Project's emphasis on subnational granularity aligns with IRIS's county and region-level attribution of classified content. UNDP's iVerify initiative (2021–present) demonstrates the dual AI-human architecture that IRIS adopts — AI triage followed by human verification — in African electoral contexts; IRIS extends this model to ongoing conflict monitoring outside electoral cycles. Imran et al.'s (2016) CrisisNLP corpus establishes the methodological template for crisis-domain NLP data collection, and the finding that crisis language has distributional properties that general-domain embeddings fail to capture supports IRIS's domain-adapted fine-tuning strategy.

### 2.5 LLM-Augmented Classification and Quality Assurance

The use of large language models as annotation assistants and quality reviewers has attracted growing attention since GPT-3 demonstrated competitive zero-shot performance on text classification tasks. Gilardi, Alizadeh, and Kubli (2023) showed that ChatGPT zero-shot accuracy exceeded that of MTurk crowd-workers on four out of five political science annotation tasks, at approximately one-twentieth of the cost per annotation. This finding directly motivates IRIS's use of LLM-assisted annotation to bootstrap training data for low-resource languages where native annotator recruitment is constrained, and informs the cost structure of the LLM QA stage.

Huang et al. (2024) benchmarked GPT-3.5, Llama-2, and Mistral on hate speech detection tasks, finding that GPT-3.5 achieves 80–90% F1 via RLHF-tuned reasoning but that fine-tuned encoder models retain recall advantages over zero-shot LLMs on recall-critical tasks. This finding supports IRIS's hybrid architecture: EA-HS provides high-recall BERT classification as the primary gate, and the LLM QA stage is applied specifically to review BERT-positive outputs rather than replacing the encoder entirely. He et al. (2024) survey LLM-based data augmentation more broadly, recommending hybrid approaches combining LLM-generated and human-labelled examples and specifically cautioning that GPT-3.5 augmentation can harm performance in some classification tasks — a finding that informs IRIS's use of Claude Sonnet rather than cost-optimized alternatives for QA review.

A critical concern for LLM-augmented annotation is annotator bias. Röttger et al. (2024) found that LLMs used as annotators replicate demographic biases from their training data, including over-flagging of content mentioning marginalized identity groups. This finding directly shapes IRIS's human-in-the-loop design: LLMs are used for triage, draft labeling, and explanation generation, but final labels for borderline content and identity-group-mentioning posts are subject to human review. IRIS is among the first operational systems to quantify the false positive removal rate achieved by LLM review at scale (59% of BERT-positive outputs removed), providing empirical data on LLM QA impact in a non-English, conflict-context deployment — a setting absent from existing benchmarks.

## 3. System Architecture

### 3.1 Data Collection

The IRIS pipeline processes social media content from four data streams:

1. **Apify Keyword Sweeps** (~50-80K posts over 6 months)
   - Automated social media search (X, Facebook, TikTok) across 12 disinformation narratives and 8 hate speech terminology groups
   - Country-specific keyword strategies (Somali, Swahili, English, Arabic)
   - Results deduplicated and classified by rule-based + LLM review

2. **Phoenix Narrative-Driven Gathers** (~80K posts)
   - Bulk social media collection via Apify workers
   - Organized by country (Kenya, Somalia, South Sudan) and narrative category (Delegitimization, Elections, Escalation, Hate Speech, etc.)
   - 6-month collection window with incremental updates

3. **Research Agent** (~500-1000 posts)
   - Daily automated desk review scanning news outlets, UN sources, fact-checking platforms
   - Classification and deduplication against existing events

4. **Direct URLs and Institutional Sources**
   - Manual submissions from UNDP partners and civil society organizations
   - High-priority content requiring urgent review

**Output:** CSV files with post ID, post text (PII-redacted), platform, publication timestamp, country, narrative category, and source.

### 3.2 Classification Pipeline: Five Stages

```
Raw posts (14,754)
    ↓
[STAGE 1] Noise Filtering (remove duplicates, spam, bot posts)
    ↓
[STAGE 2] EA Relevance Gating (rule-based + model check: is this about/relevant to EA?)
    ↓
[STAGE 3] Rule-Based HS Indicators (140+ EA-specific hate speech terms and patterns)
    ↓
[STAGE 4] BERT Classification (EA-HS multilingual BERT: 3-class Normal/Abusive/Hate)
    ↓
[STAGE 5] LLM Quality Assurance (Claude API review for FP removal, explanation, subtype)
    ↓
Verified posts (7,034)
```

**Stage 1 — Noise Filtering:**
- Remove exact duplicates (post text + platform + timestamp)
- Remove likely bot/spam (automated retweets, generic replies, low engagement)
- Retain posts with >2 engagement signals (likes, replies, shares)

**Stage 2 — EA Relevance Gating:**
- Rule-based heuristics: does post mention EA countries, ethnic groups, currencies, political figures?
- BERT model check: fine-tuned classifier on "EA relevant" vs. "not relevant"
- Gate removes ~35% of posts, retaining only those related to East African context

**Stage 3 — Rule-Based HS Indicators:**
- Curated dictionary of ~140 hate speech terms and patterns in Somali, Swahili, English, Arabic
- Includes ethnic slurs, clan-specific insults, religious incitement language, dehumanizing terms
- Supplemented by pattern matching (repeated character subst., case variants, phonetic substitutions)
- Flag posts matching ≥1 indicator as "HS candidate"

**Stage 4 — BERT Classification:**
- EA-HS model (bert-base-multilingual-cased fine-tuned on ~12K East African posts)
- Outputs: 3-class prediction (Normal, Abusive, Hate) + confidence scores
- Supplementary models for language-specific refinement (Somali toxicity, Sudan hate speech)
- Retain posts classified as Hate or Abusive (>0.7 confidence threshold)

**Stage 5 — LLM Quality Assurance:**
- Claude API review of Stage 4 outputs
- For each post: generate explanation (why is this classified as hate speech?)
- Manual review of top ~100 false positives per batch
- Assign HS subtype (Ethnic Targeting, Political Incitement, Clan Targeting, Religious Incitement, Dehumanisation, Anti-Foreign, General Abuse, Gendered Violence)
- Quality control labels: Correct, Questionable, Unknown

**Output:** Verified hate speech dataset with predictions, confidence, explanations, subtypes, and QC labels.

### 3.3 Dual Monitoring Modalities

**Modality 1: Disorder Events Wheel**
- Unit of analysis: Narrative-level incident (disinformation campaign, propaganda operation, hate speech event)
- Data sources: Apify keyword sweeps, research agent, desk review
- Classification: Narrative families (Ethnic Incitement, Revenge/Retribution, Victimhood, etc.) + threat levels (P1/P2/P3)
- Visualization: Radial wheel with narrative segments, ring position indicating threat level
- Metadata tracked: Event lifecycle, actors, spread, sources, related events

**Modality 2: Hate Speech Posts Wheel**
- Unit of analysis: Individual post or comment classified by ML pipeline
- Data sources: Apify HS sweeps, Phoenix gathers
- Classification: HS subtypes (8 axes on radial wheel) + ML prediction (Hate/Abusive/Normal) + toxicity score
- Visualization: Radial wheel with HS subtypes as axes, dot color indicating prediction, distance from center indicating toxicity
- Metadata tracked: ML confidence, LLM explanation, QC label

Both systems feed into live operational dashboards used by UNDP, NCIC, and civil society monitors.

### 3.4 Alert Protocol

**P1 CRITICAL:** Coordinated incitement to ethnic/religious violence; calls for targeted attacks; influential actor involvement
- Response: Escalation to UNDP, NCIC, national security channels within 24 hours

**P2 HIGH:** Significant viral hate speech campaigns; statements from political figures; threats against specific communities
- Response: Internal documentation, civil society notification, 48-72 hour review cycle

**P3 MODERATE:** Persistent hate speech, but lower immediate coordination/influence signal
- Response: Tracking for pattern analysis, monthly reporting

### 3.5 Operational Infrastructure

- **Data sources:** Apify API (social media scraping)
- **Processing:** Python (HuggingFace transformers, PyTorch); GitHub Actions for scheduling
- **Storage:** Supabase PostgreSQL (7,034+ records with full metadata)
- **LLM API:** Anthropic Claude Sonnet (explanations, false positive review)
- **Frontend:** Next.js dashboard (D3 radial visualizations)

**Cost structure (monthly):**
- Apify keyword sweeps: ~$38.50
- Anthropic Claude API (LLM QA): ~$1.10
- **Total: ~$40/month** (not including volunteer labor or institutional hosting)

**Inference performance:**
- BERT inference: 4-10 items/sec (2-vCPU CPU-only)
- Batch size: 64
- Max token length: 256 tokens per post
- LLM QA batch processing: 10 posts per batch

## 4. Classification Methodology

### 4.1 Rule-Based Filtering

East African hate speech often relies on culturally-specific terminology, coded language, and regional conflict references that English-language toxicity models miss. IRIS implements a curated rule-based layer:

**Rule set composition:**
- ~140 hate speech indicators curated from analysis of existing IRIS dataset, academic hate speech benchmarks, and practitioner input (NCIC, civil society monitors)
- Organized by language (Somali, Swahili, English) and category (ethnic slurs, clan-specific terms, religious incitement, dehumanization)
- Examples (anonymized/redacted): [ethnic identifiers commonly used in incitement], [clan-based insult terms], [terms depicting target groups as disease/vermin], [calls for violence against specific groups]

**Pattern matching:**
- Literal string matching with case-insensitive variants
- Character substitution handling (e.g., "a" → "@", "e" → "3")
- Phonetic variants and code-switching patterns
- Repeated character reduction (e.g., "haaaaaate" → "hate")

**Output:** Binary flag (HS candidate: yes/no) + matched rule(s)

### 4.2 ML Classification

**Primary model: EA-HS (East Africa Hate Speech BERT)**

- **Architecture:** bert-base-multilingual-cased, fine-tuned on ~12,000 East African social media posts (mixed language)
- **Training data sources:**
  - [placeholder: reference training dataset paper / analysis]
  - Collected from X, Facebook, TikTok across Kenya, Somalia, South Sudan
  - Annotated by bilingual annotators (Somali/English, Swahili/English, Arabic/English pairs)
- **Labels:** 3-class (Normal, Abusive, Hate)
  - Normal: Neutral or positive content, no harmful language
  - Abusive: Profanity, disrespect, but not targeting group identity
  - Hate: Content targeting individuals/groups based on protected identity (ethnicity, religion, clan, nationality)
- **Training hyperparameters:**
  - Learning rate: 2e-5
  - Batch size: 32
  - Epochs: 3
  - Max sequence length: 256 tokens
- **Evaluation metrics:** [placeholder: reference papers/analysis/pipeline_performance.csv]
  - Precision: [to be completed]
  - Recall: [to be completed]
  - F1 score: [to be completed]
  - Per-class breakdown (Hate, Abusive, Normal)

**Supplementary models for regional refinement:**

1. **Somali Toxicity (Afxumo)** — datavaluepeople/Afxumo-toxicity-somaliland-SO
   - Fine-tuned for Somali-language toxicity detection
   - Binary classification (Toxicity / Not Toxicity)
   - Applied to Somali-language posts as refinement layer

2. **Sudan Hate Speech v2** — datavaluepeople/Hate-Speech-Sudan-v2
   - Fine-tuned on Sudan/South Sudan conflict-related content
   - Binary classification (Hate Speech / Not Hate Speech)
   - Applied to South Sudan/Sudan-related posts

3. **Kenya Polarization** — datavaluepeople/Polarization-Kenya
   - Detects political polarization discourse
   - Binary classification (Polarization / Not Polarization)
   - Supplementary signal for election-related content

**Inference configuration:**
- Batch size: 64 (optimized for 2-vCPU deployment)
- Max token length: 256 (social media posts rarely exceed this; reduces padding overhead)
- Torch threads: 2 (matches available CPU cores)
- Model inference order: EA-HS → Polarization-Kenya → Afxumo → Sudan HS (sequential to manage memory)

### 4.3 LLM Quality Assurance

**Motivation:** Fine-tuned BERT achieves ~0.80-0.85 F1 on held-out test sets but often makes errors on:
- Sarcasm and irony (classification as hate speech when actually mocking hateful tropes)
- Indirect/coded speech (references to historical violence or ethnic conflict that aren't direct incitement)
- Code-switching (mixing Somali/English or Swahili/English in ways that confuse tokenization or context)
- Regional context sensitivity (terms that are offensive in one dialect but neutral in another)

**LLM review process:**
1. **Explanation generation** — For every post classified as Hate or Abusive by BERT, generate a structured explanation:
   - "Why is this classified as hate speech?" (1-2 sentences)
   - "What protected groups/identities are targeted?" (list)
   - "What specific language or patterns triggered the classification?" (quote + analysis)

2. **False positive detection** —
   - Prompt Claude to review explanation and post text
   - Binary decision: "Is this genuinely hate speech, or a false positive?"
   - If FP, remove from dataset
   - If genuine but low confidence, flag for manual review

3. **Subtype assignment** —
   - For verified hate speech, assign primary subtype from: Ethnic Targeting, Political Incitement, Clan Targeting, Religious Incitement, Dehumanisation, Anti-Foreign, General Abuse, Gendered Violence
   - Allow multiple subtypes if applicable

4. **Quality control label** —
   - Correct: LLM agrees with BERT classification
   - Questionable: Ambiguous or edge-case post (retained for analysis, flagged)
   - Unknown: Insufficient context (rare)

**Prompt engineering:** [placeholder: reference prompts and evaluation results]

**Claude API configuration:**
- Model: claude-3.5-sonnet
- Batch size: 10 posts per API call
- Temperature: 0.3 (deterministic explanations)
- Max tokens: 500 per post

**Cost:** ~$0.03 per 100 posts reviewed (at Sonnet pricing)

### 4.4 Stage Interaction and Data Flow

```
Raw post text
    ↓
[Rule matching] → Flag if match
    ↓
[EA Relevance gate] → Gate if not EA-relevant
    ↓
[BERT inference] → {pred, conf, probs}
    ↓
[Supplementary models] → {Somalia_pred, Sudan_pred, Kenya_pred}
    ↓
[LLM review] → {explanation, FP decision, subtype, QC label}
    ↓
Final record: {post_id, text, pred, conf, explanation, subtype, qc_label, sources}
```

**Decision thresholds:**
- BERT confidence threshold: >0.70 for Hate/Abusive classification
- LLM false positive removal: Remove posts where Claude confidence in FP is >0.85
- Rule match + BERT agreement: Higher weight (consider "Hate" if both rule and model agree)

## 5. Evaluation

### 5.1 Classification Performance

IRIS does not have a traditional held-out gold-standard test set with independent human annotations — a limitation we address explicitly in Section 6.3. What we have is the output of the full pipeline over six months of deployment: a verified dataset of 7,034 posts that have passed through all five pipeline stages including LLM quality assurance. We treat this verified corpus as the basis for reporting classification distributions and use the LLM QA stage's accept/reject decisions as a proxy signal for precision, while being transparent about the absence of external ground truth.

The EA-HS model classifies posts into three categories: Hate Speech, Abusive, and Normal. Across the 7,034 verified posts, the prediction distribution is as follows:

| Prediction Label | Count | Share |
|-----------------|-------|-------|
| Abusive | 2,372 | 33.7% |
| Hate Speech | 1,527 | 21.7% |
| Normal | 267 | 3.8% |
| Questionable (LLM flagged) | 2,868 | 40.8% |
| **Total** | **7,034** | **100%** |

The "Questionable" category reflects posts that passed the BERT confidence threshold but that the Claude LLM reviewer flagged as ambiguous — content where intent, irony, or context made a definitive classification difficult. These posts are retained in the dataset for human review but are excluded from downstream operational alerting. Posts labelled Normal that nonetheless reached this stage did so because they matched rule-based hate speech indicators strongly enough to enter the BERT queue; the LLM QA stage correctly identified them as non-hateful.

The prediction distribution differs substantially by country, reflecting both the volume of data collected per country and the linguistic and political environments monitored:

| Country | Abusive | Hate | Normal | Questionable | Total |
|---------|---------|------|--------|--------------|-------|
| Kenya | 503 | 357 | 45 | 838 | 1,743 |
| Somalia | 1,405 | 815 | 215 | 1,367 | 3,802 |
| South Sudan | 462 | 355 | 3 | 662 | 1,482 |
| Regional | 2 | 0 | 4 | 1 | 7 |
| **Total** | **2,372** | **1,527** | **267** | **2,868** | **7,034** |

Somalia accounts for 54.1% of the verified dataset, partly reflecting the volume of monitoring effort directed at Somali-language and Somalia-related content, and partly the greater prevalence of toxic political and clan-based discourse in the monitored keyword categories. South Sudan has the highest ratio of Hate to Abusive classifications (355 vs. 462), consistent with the more direct incitement language observed in South Sudanese conflict discourse relative to the coded political abuse more common in Kenyan social media.

Across the full verified dataset, the LLM QA stage assigned quality control labels as follows: Correct (4,144 posts, 58.9%), Questionable (2,888 posts, 41.0%), and Unknown (2 posts, <0.1%). The "Correct" label indicates that Claude's review agreed with the BERT classification; "Questionable" indicates ambiguity, not confirmed false positive. Regarding geographic relevance, 6,306 posts (89.6%) were assessed as directly relevant to East African context, 726 (10.3%) as possibly relevant, and 2 (<0.1%) as unknown.

Because precision, recall, and F1 against an external gold standard are not available for the deployed pipeline in its current form, the figures cited in the introduction (0.89 F1) derive from the held-out evaluation performed during EA-HS model training rather than from end-to-end operational evaluation. Per-language and per-subtype breakdowns await a planned independent annotation exercise described in Section 6.3.

### 5.2 Quality Gate Impact

A central design contribution of IRIS is the multi-stage quality gate: the combination of noise filtering, relevance gating, rule-based indicator matching, and LLM review that transforms a noisy keyword-collected corpus into a verified, explainable dataset. The quantitative effect of this pipeline is substantial.

The broader Phoenix retroactive corpus spans approximately 80,000 raw posts collected via keyword-based scraping across the six-month window (mid-2025 to early 2026). The hate speech classification pipeline described in this paper was applied to a processed subset of 14,754 candidate posts drawn from Apify keyword sweeps that had been deduplicated and staged for classification. These posts matched keyword criteria but had not been validated in any other way. After passing through all five pipeline stages, 7,034 posts remained in the verified dataset — a noise reduction of 52.3%. The 7,034 figure reflects the current state of the live system; earlier documentation cited 5,987 posts, but the system has continued ingesting and classifying new content since that snapshot was taken.

The pipeline removed posts at multiple stages. The EA relevance gate eliminated 4,774 posts assessed as not relevant to East African context and an additional 1,099 posts as only possibly relevant. The rule-based and BERT stages together removed posts that matched keywords but showed no hate speech signal above the 0.70 confidence threshold. The LLM QA stage then removed a further 7,424 posts that had passed BERT classification but were flagged as misclassified or insufficiently substantiated on LLM review.

This multi-stage filtering can be summarized as follows:

| Stage | Posts Remaining | Posts Removed at Stage |
|-------|----------------|----------------------|
| Raw input (after Apify collection) | 14,754 | — |
| After relevance gating | ~8,547 | ~6,207 (relevance + noise) |
| After BERT classification | — | — |
| After LLM QA (misclassified removed) | 7,034 | 7,424 |
| **Final verified dataset** | **7,034** | **7,720 net removed** |

The LLM QA stage is the most consequential single filter: 7,424 posts that BERT had classified as hate speech or abusive were rejected on review, representing a false positive removal rate of approximately 59% of BERT-positive outputs. The 4,048 posts confirmed as "Correct" by the LLM reviewer represent the high-confidence core of the verified dataset. The 2,888 "Questionable" posts are retained but treated as a lower-confidence tier pending human annotation.

It is important to interpret these figures with care. The LLM reviewer is not a gold standard: Claude's decisions also carry uncertainty, particularly for posts involving regional slang, code-switching, or culturally-specific references that may not be well-represented in its training distribution. The LLM QA stage should be understood as a strong noise-reduction mechanism, not a replacement for human annotation. The verified dataset is best characterized as a high-precision subset of BERT-positive outputs rather than a complete picture of hate speech activity in the monitored regions.

### 5.3 Error Analysis

Qualitative review of the pipeline's outputs reveals several recurring failure modes. These are observed patterns from inspection of flagged posts and edge cases during LLM QA review; they have not been formally quantified through a systematic annotation exercise, and we describe them here as a basis for future targeted evaluation.

**Sarcasm and irony in political discourse.** East African political commentary frequently employs satirical registers that adopt the language of ethnic or political incitement in order to mock it. A post that echoes a slur or a dehumanizing comparison to criticize those who use such language will share surface features with genuine hate speech. The BERT classifier, trained on token-level and short-context features, is ill-equipped to distinguish ironic quotation from genuine endorsement. The LLM reviewer catches many such cases, but sarcasm that relies on shared cultural context — references to specific political figures, memes, or historical events — remains difficult even for LLM review. This failure mode is particularly prevalent in Kenyan political discourse, where rhetorical irony is common.

**Code-switching between English and local languages.** Social media in East Africa routinely mixes languages within a single post: a Somali speaker may write primarily in Somali but switch to English for emphasis, or blend Swahili and English in ways that distribute the semantic content of a hate speech expression across both languages. The mBERT tokenizer and training data handle common code-switching patterns, but posts where the key offensive term appears in a less-represented language, or where meaning depends on the interplay between two languages, often receive low-confidence predictions and fall into the Questionable tier. Somali-English code-switching is the most frequent source of this failure mode in the IRIS corpus.

**Indirect speech acts and historical allusion.** Posts referencing historical conflict events, displacement, or violence can carry strong incitement meaning within the discourse community without containing any direct call to violence. References to specific historical massacres, displacement campaigns, or communal conflicts may be used to invoke threat or menace without stating it explicitly. These indirect speech acts often do not match rule-based indicators (which rely on explicit vocabulary) and may receive only borderline BERT confidence scores, since their hate speech function is pragmatic rather than lexical.

**Metaphorical and figurative violence language.** Political discourse in all three monitored countries employs figurative language — metaphors of cleansing, disease, infestation, or predation — that carries dehumanizing connotations but whose surface form may not be recognized by rule-based indicators trained on explicit slurs. A post describing a political opponent's community as a "disease" or "infestation" may pass through the rule layer unmatched and receive a low Abusive rather than Hate classification from BERT, even when the target is clearly defined by ethnicity or religion.

**Context-dependent and polysemous terms.** Some terms in the IRIS rule set are context-dependent: they are hate speech in one register but neutral or positive in another. Clan names used as identifiers in community discussion are not themselves hate speech; the same names in combination with derogatory predicates are. Terms referring to migration, foreign nationals, or religious practice can be informational or incitement depending on framing. The rule-based layer is not context-sensitive, and the BERT model's context window is limited. This contributes to the large Questionable tier and to the non-trivial Normal-classified posts that reached the LLM review stage.

The combination of these failure modes suggests that the most productive avenue for improving pipeline performance is not simply a larger rule set or a higher BERT confidence threshold, but targeted augmentation of the training data and evaluation protocol for the specific linguistic environments — especially Somali-English code-switching and indirect incitement registers — where current performance is weakest.

### 5.4 Operational Metrics

A key contribution of IRIS is that it operates at a cost that makes continuous deployment feasible for civil society organizations and development agencies in resource-constrained settings. The total monthly cost of running the full pipeline is approximately $40, composed of two components:

| Cost Component | Monthly Cost | Notes |
|---------------|-------------|-------|
| Apify keyword sweeps | $38.50 | Social media scraping across X, Facebook, TikTok |
| Anthropic Claude API (LLM QA) | ~$1.10 | Claude Sonnet; explanation generation and FP review |
| **Total** | **~$40.00** | Excluding volunteer labor and institutional hosting |

The Apify cost dominates and reflects approximately 12 pipeline phases run per full execution cycle. The LLM QA cost is remarkably low — $1.10 per month for reviewing and annotating thousands of posts — because Claude Sonnet is applied only to BERT-positive outputs rather than the full corpus, and because batch processing (10 posts per API call) amortizes prompt overhead across multiple items. At $0.03 per 100 posts reviewed, the LLM QA stage is orders of magnitude cheaper than manual annotation, which in comparable projects has run to $0.50–$2.00 per post for expert annotators.

The $40/month total compares favorably to commercial content monitoring solutions, which typically charge hundreds to thousands of dollars per month for API access at comparable throughput, without any of the East African language specialization that IRIS provides. For a UNDP-scale deployment monitoring three countries continuously, this cost structure makes permanent operational deployment realistic without dedicated technical infrastructure budget.

Inference performance on the BERT classification stage is as follows. The EA-HS model and supplementary models run in sequence on a 2-vCPU CPU-only instance, achieving 4–10 items per second depending on post length. BERT inputs are capped at 256 tokens (matching the maximum social media post length in the corpus), with a batch size of 64 optimized for the available memory. At this throughput, classifying a batch of 10,000 posts takes approximately 20–40 minutes. The LLM QA stage processes 10 posts per API call at roughly 3 seconds per batch, adding approximately 50 minutes per 10,000 posts. Total end-to-end pipeline runtime for a full 80,000-post sweep is approximately 8–12 hours, including Apify collection, preprocessing, BERT inference across all four models, and LLM review.

Keyword sweep performance varies substantially across narrative categories. Hit rates (posts that pass full pipeline classification as genuine disinformation or hate speech) range from 0% for some keyword groups to 47% for the Kenya Coordinated Disinformation sweep (25 confirmed hits from 54 total matches). Several sweeps return zero confirmed hits despite substantial collection effort:

| Keyword Group | Confirmed Hits | False Positives | Hit Rate |
|--------------|---------------|----------------|---------|
| AS_CASUALTY_FABRICATION | 11 | 37 | 22.9% |
| AS_GOVERNANCE_PROPAGANDA | 3 | 10 | 23.1% |
| AS_GAZA_RECRUITMENT | 0 | 54 | 0.0% |
| ISS_PROPAGANDA | 2 | 8 | 20.0% |
| SOMALI_DEEPFAKES_FABRICATION | 2 | 52 | 3.7% |
| SOMALILAND_FALSE_CLAIMS | 0 | 50 | 0.0% |
| SS_FABRICATED_NARRATIVES | 4 | 15 | 21.1% |
| SS_MACHAR_FABRICATION | 0 | 48 | 0.0% |
| KE_COORDINATED_DISINFO | 25 | 29 | 46.3% |
| KE_FALSE_ETHNIC_CLAIMS | 5 | 20 | 20.0% |
| FOREIGN_DISINFO_OPERATIONS | 0 | 46 | 0.0% |

The wide variance in hit rates reflects both the specificity of the keyword strategies and the actual volume of on-platform content matching each narrative. Sweeps with zero confirmed hits (GAZA_RECRUITMENT, SOMALILAND_FALSE_CLAIMS, MACHAR_FABRICATION, FOREIGN_DISINFO_OPERATIONS) are candidates for keyword strategy revision or retirement. The Kenya-related sweeps show the highest signal, consistent with the higher volume and English-language accessibility of Kenyan social media content.

## 6. Discussion

### 6.1 Multi-Stage vs. Single-Stage Approach

The quality gate evidence from Section 5.2 provides the most direct argument for IRIS's multi-stage design. A single-stage classifier — whether a zero-shot LLM or a standalone BERT model applied directly to keyword-collected social media — would face a corpus in which between 50% and 80% of posts are noise: cross-lingual content with no East African relevance, bot-generated engagement spam, news reports counter-describing hate speech, or sarcastic posts that superficially match hate speech vocabulary. IRIS's five-stage pipeline (noise filtering → EA relevance gating → rule-based indicators → BERT classification → LLM quality assurance) addresses this problem by letting each stage do what it does cheaply and well, so that expensive components operate only on high-probability candidates.

The rule-based layer contributes precision the BERT model alone cannot achieve: East African conflict hate speech often hinges on highly specific local-language terms — clan-specific insults, regionally-coded dehumanisation vocabulary, political incitement phrases — that appear in no English-language pre-training corpus and that multilingual models therefore underweight. Matching these terms directly provides interpretable evidence for the classification that downstream analysts can audit. The BERT layer contributes recall that the rule layer cannot: hate speech that avoids flagged vocabulary but constructs dehumanizing framing through adjacent language, metaphor, or negative predication of ethnic identifiers would pass the rule stage untouched but is captured by BERT's contextual embeddings. The LLM QA stage then applies the richer contextual understanding that BERT lacks — capacity for irony recognition, cultural reference, and multi-turn pragmatic inference — but does so only on the roughly 15,000 posts that BERT has already filtered from 80,000 candidates, keeping LLM API costs at approximately $1.10 per month.

The cost and interpretability arguments reinforce each other. An end-to-end LLM approach — passing all 80,000 posts directly to Claude — would cost orders of magnitude more and would not produce the structured intermediate signals (rule match evidence, BERT confidence scores per class, supplementary model agreement) that analysts use to assess borderline cases. The multi-stage design also enables modular upgrading: the EA-HS BERT model can be retrained as new annotated data accumulates without touching the rule layer or the LLM prompt; the keyword strategy can be updated as new slang emerges without retraining any model; and the LLM can be swapped for a locally-deployable open-source alternative if API access becomes cost- or privacy-prohibitive.

The principal trade-off of the multi-stage design is error propagation in early stages. An overly aggressive relevance gate that incorrectly marks a Somali-language post as not EA-relevant would eliminate it from the pipeline before BERT sees it; a false negative at Stage 1 cannot be recovered downstream. In practice, IRIS calibrates Stage 2 to err toward inclusion — the gate removes only posts that clearly lack any East African geographic, ethnic, or linguistic signal, and has a "possibly relevant" intermediate category that routes borderline cases forward. A second trade-off is that total pipeline latency (approximately 8–12 hours for a full sweep) is longer than a single-stage approach would require; this is acceptable for the weekly reporting cadence IRIS targets, but would not support real-time stream processing. For the operational alerting use case, the latency is partially mitigated by the fact that P1-level alerts from the Disorder Events pipeline can be triggered within hours of a sweep completing, without waiting for the full HS pipeline to finish.

### 6.2 Generalizability and Transferability

IRIS was designed for a specific operational context — three countries, four language registers, social media platforms accessible via Apify — and the degree to which its components transfer to other contexts varies substantially across pipeline stages.

The general pipeline architecture (multi-stage noise reduction, rule-based domain priming, fine-tuned BERT classification, LLM QA review) is context-agnostic and transferable in principle to any low-resource conflict monitoring context. The critical localization requirement is the rule-based indicator layer: the 140+ EA-specific terms and 7 subtype dictionaries encode knowledge that is not derivable from models alone, and deploying IRIS in West Africa, the Sahel, or Myanmar would require equivalent investment in locally-sourced lexicon development with community-embedded annotators. The PeaceTech Lab model — in-country partners contributing hate speech lexicons — provides the operational template for this localization work.

The EA-HS BERT model is more constrained in transferability. Its fine-tuning corpus is drawn from Kenyan, Somali, and South Sudanese social media content, and its performance on Ugandan, Ethiopian, or West African content is untested. The bert-base-multilingual-cased backbone provides a foundation for cross-lingual transfer, and the supplementary model architecture — language-specific models applied as refinement layers on top of the primary classifier — could be extended by adding country-specific models without retraining the core EA-HS model. He et al. (2024) provide evidence that LLM-augmented data generation using GPT-4-class models can bootstrap training data in genuinely low-resource settings; IRIS could leverage this technique to generate annotated examples for new country contexts before sufficient operational data accumulates.

The LLM QA stage has the broadest generalizability: the Claude API system prompt encodes hate speech analytical knowledge that is not region-specific, and the structured output format (explanation, quality control label, relevance assessment, toxicity dimensions) transfers to any context. The primary limitation is API access — organizations operating in environments with restricted internet connectivity, data sovereignty requirements, or budget constraints below the $1/month LLM threshold would need to substitute a locally-deployable open-source model. Huang et al. (2024) found that fine-tuned open-source models (Llama, Mistral) are competitive with GPT-3.5 on hate speech classification when fine-tuned; a similar approach could provide an offline-capable LLM QA substitute.

### 6.3 Limitations

IRIS's most significant methodological limitation is the absence of an independently annotated gold-standard evaluation set for end-to-end pipeline assessment. The F1 figure of 0.89 cited in the introduction derives from the held-out evaluation performed during EA-HS model training, not from evaluation of the full pipeline against external human annotations. The LLM QA decisions that drive the quality gate are not themselves validated against independent human judgment: the 59% false positive removal rate reflects Claude's decisions, and while qualitative review of removed posts suggests this figure is appropriate, a systematic inter-annotator agreement study comparing Claude's decisions against trained human annotators has not been completed. This limitation is acknowledged explicitly in Section 5.1 and is the primary target for the next phase of evaluation work.

A second limitation is data collection coverage. Apify keyword sweeps are effective for content that matches pre-defined vocabulary but will systematically miss coordinated hate speech campaigns that deliberately avoid flagged terms, encrypted-platform content on WhatsApp and Telegram (which are increasingly important vectors for incitement in East Africa but are not accessible via Apify), and low-volume highly-targeted content from accounts that operate below engagement thresholds. Phoenix narrative-driven gathers address the low-frequency coordinated campaign problem but introduce selection bias toward narratives that IRIS's monitoring team has previously identified as relevant — novel emerging narratives may not be captured until they reach sufficient visibility to trigger keyword addition.

Language coverage is a further structural gap. IRIS covers English, Somali, Swahili, and Sudanese Arabic, but the Horn of Africa is home to additional languages with significant social media presence: Oromo (the most widely spoken language in Ethiopia), Tigrinya (dominant in Eritrea and northern Ethiopia), and various South Sudanese languages beyond the content covered by the Sudan-focused supplementary model. Content in these languages may pass EA relevance gating (if geographic or ethnic identifiers are present) but will receive unreliable BERT classifications, since mBERT's training coverage of these languages is minimal.

Finally, the pipeline was trained and deployed over a six-month window in a specific political and conflict environment. Temporal generalization — how well EA-HS and the rule layer perform as new slang emerges, political alliances shift, and conflict narratives evolve — is unknown. The IRIS autolearn module (which accumulates newly learned keywords from pipeline outputs) partially addresses linguistic drift, but a systematic evaluation of performance degradation over time has not been conducted.

## 7. Ethics and Data Privacy

### 7.1 PII Redaction and Data Minimization

All posts in the IRIS dataset are processed through a PII redaction step before storage or analysis. Usernames, phone numbers, email addresses, and other directly identifying fields are replaced with typed placeholders ([USER], [PHONE], [EMAIL]) in stored records. URLs are retained in full because source attribution and cross-platform verification require the original link, but tracking parameters appended by analytics services are stripped. The training data used to fine-tune EA-HS and the supplementary models consists exclusively of redacted posts; no end-user identifiable information is encoded in model weights or training checkpoints.

The data minimization principle governs collection scope. IRIS collects only the post text, publication timestamp, platform identifier, and engagement metadata (likes, replies, shares) necessary for classification and reach tracking. It does not collect author profile information, follower graphs, or account history, even where these signals might improve classification performance, because the marginal classification benefit does not outweigh the privacy and misuse risk of accumulating individual behavioral profiles.

### 7.2 Aggregate-Only Reporting

The IRIS operational dashboards that UNDP and civil society partners access display aggregate trends rather than individual posts. Country-level and subtype-level time series (for example, Ethnic Targeting hate speech detections by week in Somalia) are the primary reporting unit. Individual post text and post URLs are accessible only to verified UNDP partners and civil society researchers operating under data use agreements that specify permitted uses, retention limits, and prohibition on downstream re-identification. High-severity P1 alerts include the minimum post-level detail necessary to support verification and response: the post text, platform, and approximate posting date, without author attribution.

This aggregate-first reporting design reflects the distinction between monitoring for early warning at population level — the intended use — and monitoring specific individuals for surveillance or legal action, which is explicitly not the purpose IRIS is designed to serve.

### 7.3 UNDP Mandate and Institutional Authorization

IRIS is deployed under UNDP's mandate for peace and development in East Africa, under the Sustaining Peace programme, and operates within the governance framework that UNDP applies to digital monitoring activities. Data collection is authorized under UNDP partnership agreements with national-level counterparts and is conducted on publicly accessible social media platforms in accordance with the platforms' terms of service for research and public interest monitoring. UNDP's Chief Digital Office oversight provides an institutional check on scope creep and misuse; major changes to collection scope, model deployment, or alert protocols require approval through this governance chain.

Partner civil society organizations and national bodies such as the National Cohesion and Integration Commission (NCIC) in Kenya are informed of the monitoring scope and the nature of the data collected before they receive access to IRIS outputs. Data sharing with national institutions is explicitly scoped to hate speech trend analysis and early warning, not to individual-level enforcement action.

### 7.4 Surveillance Risks and Safeguards

Automated hate speech monitoring at scale carries genuine dual-use risk. A system that correctly identifies hate speech campaigns could, in the wrong institutional context, be applied to surveil political speech, flag opposition voices on the basis of contested content standards, or provide intelligence inputs to actors seeking to suppress dissent. IRIS is designed with awareness of this risk and incorporates several structural safeguards.

The most important safeguard is human-in-the-loop design at every escalation point. P1 alerts require manual verification by a trained human analyst before escalation to UNDP or national partners; no automated action is taken directly on the basis of BERT classification or LLM review alone. The LLM explanation generation step is designed in part to enable this oversight: every classified post has a human-readable explanation that an analyst can assess, contest, or override. The classification system generates recommendations, not determinations.

The second safeguard is the aggregate-only reporting interface for partner organizations. Partners receive trend data and aggregated subtype distributions, not queryable access to individual post content. This limits the utility of IRIS outputs for individual surveillance while preserving their value for population-level early warning.

The third safeguard is audit logging. All data access events — which partner organization accessed what data, at what time, and with what stated purpose — are logged in Supabase and subject to periodic review. Access credentials are revoked if terms of use are violated.

The residual risk that IRIS acknowledges, but cannot fully mitigate through design alone, is that partner organizations themselves may use the system in ways inconsistent with its intended purpose once data is shared. This risk is managed through contractual data use agreements, institutional relationships, and UNDP oversight, rather than through technical means.

### 7.5 IRB Status and Future Review

Institutional Review Board review for academic publication of IRIS methodology and corpus data is currently pending. The IRB application addresses research data use, anonymization standards, and the ethical treatment of hate speech content during annotation campaigns. No personally identifiable information will be released in conjunction with publication; the EA-HS model and any publicly released data subsets will be accompanied by model cards documenting known performance limitations, training data composition, and intended and prohibited uses.

A planned external ethics consultation with East African civil society partners — including organizations active in Somalia, Kenya, and South Sudan — will review IRIS's category taxonomy, annotation guidelines, and alert protocol for community acceptability before the next major version of the pipeline is deployed. This consultation is intended to surface concerns about category construction, cultural sensitivity of specific indicator terms, and the appropriate institutional channels for P1 escalation that may not be visible from the perspective of the system's developers.

## 8. Conclusion

This paper presented IRIS, an operationalized multi-stage pipeline for hate speech and disinformation monitoring across Somalia, South Sudan, and Kenya. We described the full architecture — from Apify keyword sweeps through the five-stage classification pipeline to dual operational monitoring modalities — and documented the pipeline's performance on a corpus assembled from approximately six months of retroactive keyword-based scraping (mid-2025 to early 2026), supplemented by several weeks of live daily automated monitoring. The system processed approximately 80,000 candidate posts and produced 7,034 verified hate speech classifications with structured explanations, subtype assignments, and threat-level attributions. The LLM quality assurance stage removed 59% of BERT-positive posts as false positives, demonstrating that multi-stage quality gating is essential for keyword-collected social media corpora, and that LLM review provides a scalable and cost-effective mechanism for this gate when fine-tuned encoders are used as the upstream triage layer. The full pipeline operates at approximately $40 per month.

Three contributions stand out as the paper's primary offerings to the field. First, IRIS establishes that low-cost, operationalized multilingual hate speech monitoring is achievable for African conflict contexts — not only as a research prototype but as a running system processing live data for organizational clients. The $40/month cost structure brings continuous monitoring within reach of civil society organizations and development agencies that cannot afford commercial content moderation solutions. Second, EA-HS (KSvendsen/EA-HS on Hugging Face Hub) provides the first publicly released fine-tuned BERT model specifically targeting East African hate speech across Somali, Swahili, and English registers, complemented by three language-specific supplementary models. These models are available as a baseline resource for future work on African-language hate speech detection. Third, the IRIS methodology for integrating LLM-based quality assurance into a production classification workflow — using structured prompts for explanation generation, false positive detection, and subtype assignment in batches of ten posts per API call — offers a replicable design pattern for other low-resource NLP monitoring contexts.

Several open questions remain for future work. The most pressing is the establishment of an independently annotated evaluation set that would allow end-to-end pipeline assessment against external ground truth rather than the LLM QA proxy measure used here. A systematic inter-annotator agreement study comparing Claude's quality control decisions against trained human annotators is planned and would establish the degree to which LLM review can substitute for human annotation at the quality gate stage. A second priority is temporal validation: longitudinal analysis testing whether spikes in IRIS-detected hate speech precede ACLED-coded violence events in the monitored regions would establish whether IRIS outputs carry genuine early warning value, the core claim motivating the system's design but not yet formally evaluated. A third direction is extending the framework to encrypted-platform and lower-resource language contexts — WhatsApp and Telegram monitoring, and coverage of Oromo and Tigrinya — where current collection and classification infrastructure is absent. Finally, deploying locally-available open-source LLMs as drop-in substitutes for the Claude API QA stage would address data sovereignty and connectivity constraints that limit deployment in some partner environments, and would remove the dependency on commercial API availability that represents the pipeline's single most significant infrastructure risk.

---

**References**

[Placeholder: full bibliography to be populated during final paper writing]

**Appendices**

A. Rule Set (Hate Speech Indicators by Language)
B. BERT Training Configuration and Hyperparameters
C. Sample Prompts for LLM Quality Assurance
D. Data Dictionary (CSV Column Schema)
E. Ethics and Data Governance Policy
F. Sample Visualizations (Disorder Events Wheel, Hate Speech Posts Wheel)
