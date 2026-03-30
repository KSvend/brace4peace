# Online Hate Speech and Disinformation Patterns Across East Africa: Evidence from Automated Classification of 80,000+ Social Media Posts

## 1. Introduction

Online hate speech has emerged as a significant and growing concern in conflict-affected contexts across East Africa, yet systematic large-scale evidence remains scarce. While hate speech is increasingly recognized as a precursor to offline violence—a pattern documented extensively in Rwanda, Myanmar, and other conflict zones—the academic literature on online hate speech in East Africa remains fragmented, largely anecdotal, and heavily concentrated on Western-language content and English-speaking platforms. This gap is particularly acute in regions like East Africa, where linguistic diversity, platform heterogeneity, rapid technological adoption, and complex conflict dynamics create distinct challenges for automated monitoring and analysis.

The existing research base focuses primarily on Western contexts (particularly the United States and Europe), where large-scale supervised datasets and English-language corpora dominate. In contrast, African contexts receive comparatively limited attention in computational social science, despite facing acute risks from the intersection of hate speech, disinformation, and ethnic mobilization. Few studies have attempted cross-national comparison of hate speech patterns at scale in Sub-Saharan Africa, and even fewer have examined the relationship between hate speech and disinformation narratives in realtime conflict cycles.

This paper addresses these gaps through a systematic, cross-national analysis of online hate speech and disinformation patterns in East Africa, drawing on a dataset of 7,034 verified social media posts collected across Kenya, Somalia, and South Sudan over approximately six months (mid-2025 to early 2026). Using the IRIS automated classification pipeline (described in detail in Paper A), we provide the first large-scale evidence of hate speech prevalence, geographic variation, platform patterns, and narrative associations across three geopolitically distinct countries. Our analysis reveals country-specific drivers of hate speech, significant platform asymmetries (with Facebook and X/Twitter playing distinct roles in different national contexts), and substantial overlap between hate speech and disinformation events. Beyond descriptive findings, we synthesize implications for conflict early warning systems, platform governance, and counter-disinformation programming in African contexts. This paper serves as a foundational evidence base for targeted interventions and ongoing automated monitoring of hate speech and disinformation in the region.

---

## 2. Context: Conflict Dynamics and Social Media Landscapes

### 2.1 Kenya: Electoral Tension and Ethnic Fragmentation

Kenya's recent political history has been defined by cycles of electoral violence interwoven with underlying ethnic cleavages. The 2007 post-election violence killed approximately 1,000 people and displaced over 600,000, exposing the mobilizing power of ethnically-inflected rhetoric on local and national radio, and establishing a template for how grievances can be weaponized along group lines. Despite relative stability in the intervening years, ethnic tensions remain latent, periodically resurging around electoral cycles, resource competition, and security incidents.

As Kenya approaches the 2027 general election (presidential and parliamentary), political temperatures have begun rising. Early indicators include intensifying ethnic-focused campaign rhetoric, historical grievance narratives from marginalized regions, and accusations of exclusion and unfair benefit distribution across ethnic blocs. The devolved governance system (established in 2010) has simultaneously created new arenas for ethnic competition at county level while preserving national ethnic fault lines. Competing narratives around national identity, development resources, and group-based rights circulate widely on social media platforms, creating risks for escalation if electoral outcomes are contested or perceived as illegitimate.

### 2.2 Somalia: Militant Propaganda and Clan Fragmentation

Somalia's conflict landscape is shaped by overlapping and often interconnected drivers: the ongoing Al-Shabaab insurgency, clan-based political competition, and transnational diaspora flows. Al-Shabaab continues to conduct high-profile attacks, propaganda operations, and recruitment efforts through sophisticated media productions and social media presence, despite military pressure from African Union forces and periodic technological platform restrictions. The organization operates active propaganda channels, particularly on encrypted platforms and satellite sites, and maintains capacity to disseminate content widely through coordinated amplification networks.

Beyond militant activity, clan politics remain fundamental to Somali governance and identity. The 4.5 power-sharing formula—allocating high offices proportionally to major clan families—has both reduced zero-sum competition and entrenched clan-based patronage networks. Social media platforms serve as forums for clan-based mobilization, inter-clan accusations, and promotion of politicians claimed to represent specific clan interests. Additionally, Somalia's large diaspora population maintains strong digital engagement with homeland affairs, with diaspora-based media and social media accounts influencing political narratives and resource flows back to Somalia. This diaspora component amplifies certain narratives, particularly around security, governance legitimacy, and international intervention.

### 2.3 South Sudan: Civil War and Ethnic Mobilization

South Sudan remains in a chronic conflict state, despite nominal ceasefires and power-sharing agreements. Civil war (2013–present) has been explicitly framed in ethnic terms, with fighting broadly following Dinka-Nuer lines, though overlaid with clan subdivisions, regional competition, and factional competition within ethnic groups. Hundreds of thousands have been killed, millions displaced. The conflict has driven deep militarization of ethnic identity and group-based suspicion.

During the analysis period (mid-2025 to early 2026), intercommunal violence in Akobo County and surrounding areas escalated significantly, resulting in displacement and civilian casualties. This escalation corresponds temporally with our data collection window, providing an opportunity to observe how social media narratives respond to and potentially amplify security incidents. Additionally, contested elections and political transitions create moments of high mobilization risk around leadership legitimacy, resource control, and group-based representation in security forces.

### 2.4 Social Media Adoption and Platform Structure in East Africa

Social media adoption in East Africa has expanded rapidly, though platform usage patterns diverge markedly from Western markets. Facebook remains the dominant platform overall in the region, serving as the primary point of digital engagement for many users, particularly older populations and those with lower bandwidth constraints. However, X/Twitter occupies a distinct and disproportionately influential niche, serving as the primary forum for elite political discourse, international media engagement, and content syndication. TikTok has emerged as a rapidly growing platform, particularly among younger users, though data availability remains limited.

In our verified dataset of 7,034 posts:
- **Facebook**: 1,973 posts (28%), concentrated in Kenya (768) and South Sudan (807), with smaller Somali contingent (398)
- **X/Twitter**: 4,907 posts (70%), distributed across Somalia (3,250), Kenya (975), and South Sudan (675)
- **TikTok**: 154 posts (2%), entirely from Somalia

This platform asymmetry—with X/Twitter dominating in terms of post volume, particularly in Somalia, while Facebook maintains structural importance for broader reach in Kenya and South Sudan—shapes the composition of our dataset and has implications for generalizability. X/Twitter's skew toward educated, connected, elite users means our dataset likely overrepresents politically engaged and internationally-oriented voices, while underrepresenting grassroots social media use, particularly in rural areas and among less digitally connected populations.

---

## 3. Data & Methods

### 3.1 Data Source and Collection

Data were collected through the Phoenix platform, a retroactive digital content aggregation system (deployed operationally from mid-2025 onwards). Phoenix enables keyword-driven scraping of content across multiple platforms with geographic, temporal, and linguistic filtering. Our collection window spans approximately six months (May 2025–March 2026), with concentration of available content in late 2025 and early 2026 as operational deployment matured.

**Data Availability Limitation**: Not all social media content is available for retroactive scraping (platform privacy restrictions, content deletion, limited API access). Our dataset represents a selective and incomplete window of total online hate speech and disinformation during the period, with unknown bias toward particular account types, post visibility, or content characteristics.

### 3.2 Coverage and Verified Dataset Composition

From the full collection effort (estimated 80,000+ raw posts with varying verification levels), our **verified dataset comprises 7,034 posts** meeting quality and metadata standards:

- **Kenya**: 1,743 posts (24.8%)
- **Somalia**: 3,802 posts (54.1%)
- **South Sudan**: 1,482 posts (21.1%)
- **Regional** (not attributable to single country): 7 posts (0.1%)

**Total: 7,034 verified posts**

By platform distribution:
- **Facebook**: 1,973 posts (28.0%)
- **X/Twitter**: 4,907 posts (69.7%)
- **TikTok**: 154 posts (2.2%)
- **Regional**: 7 posts (0.1% — Twitter only)

### 3.3 Classification Methodology: The 5-Stage IRIS Pipeline

Posts were classified using the IRIS automated classification pipeline, a 5-stage system described in full detail in Paper A (see that paper for architecture, training data, hyperparameters, and evaluation). Briefly, the five stages are:

1. **Noise filtering** — Removal of duplicates, spam, and bot-generated content
2. **EA relevance gating** — Rule-based and model-based filtering to retain only East Africa-relevant posts
3. **Rule-based hate speech indicators** — Matching against a curated dictionary of ~140 East African hate speech terms and patterns in Somali, Swahili, English, and Arabic
4. **Transformer classification** — EA-HS model (XLM-RoBERTa, xlm-roberta-base, fine-tuned on ~12,000 East African posts) classifying posts as Normal, Abusive, or Hate; supplemented by three regional BERT models (Afxumo for Somali, Sudan HS v2, Polarization-Kenya)
5. **LLM quality assurance** — Claude API review of BERT-positive outputs for false positive removal, explanation generation, subtype assignment, and macro-categorization (Hate Speech, Violent Extremism, Disinformation, Peace, Mixed/Monitoring, Unknown)

All results reported below are model predictions; error rates and validation performance are documented in Paper A's evaluation section.

### 3.4 Hate Speech Taxonomy

The IRIS pipeline distinguishes **8+ subtypes of hate speech**, with country-specific codes capturing relevant local dynamics:

- **Delegitimization** — Challenges to opponent legitimacy, group-based exclusions, questions about citizenship/belonging
- **Diaspora-focused attacks** — Rhetoric targeting diaspora populations, remittances, diaspora political engagement (particularly prominent in Somalia context)
- **Dehumanization** — Rhetoric describing groups in subhuman terms (animals, disease, filth)
  - **HS_DEHUMANISE_KE** (Kenya-specific codes)
  - **HS_DEHUMANISE_SOM** (Somalia-specific)
- **Ethnic mobilization** — Explicit ethnic-based calls for group solidarity, suspicion, or mobilization
  - **HS_ETHNIC_KE**, **HS_ETHNIC_SS** (South Sudan-specific), with separate Somali clan-based variant
- **Political attacks** — Hate speech framed in political/partisan terms
  - **HS_POLITICAL_KE**, **HS_POLITICAL_SS**
- **Gender-based attacks** — Misogynistic, gender-essentialist, or sexual rhetoric
  - **HS_GENDER_SOM** (particularly relevant to Somalia discourse)
- **Religious polarization** — Sectarian and religious-identity attacks
  - **HS_RELIGIOUS_SOM** (distinct Somali Islamic context)
- **Anti-foreign / xenophobic** — Rhetoric targeting non-citizens, diaspora, international actors
  - **HS_ANTI_FOREIGN_KE** (Kenya context)
- **Clan-based rhetoric** — Explicit clan targeting and mobilization
  - **HS_CLAN_SOM** (Somalia-specific)

### 3.5 Disinformation Taxonomy: Narrative Families

Disinformation is operationalized through **9 narrative families**, using standardized codes that indicate country, narrative type, and variant:

- **NAR-SO-001 through NAR-SO-007** — Somalia-focused narratives (Al-Shabaab coordination/propaganda, clan mobilization, diaspora flows, international intervention delegitimization, security force abuses)
- **NAR-KE-001 through NAR-KE-004** — Kenya-focused narratives (electoral manipulation, ethnic marginalization, government overreach, opposition delegitimization)
- **NAR-SS-001 through NAR-SS-004** — South Sudan-focused narratives (peace agreement violations, ethnic cleansing narratives, external actor blame, resource-based conflict)
- **NAR-FP-001, NAR-FP-002** — False-positive narratives (content appearing disinformation-related but determined non-event or misclassified)

Each narrative family clusters semantically related disinfo events, enabling analysis of how false claims, conspiracy theories, and manipulated claims diffuse within thematic frames.

### 3.6 Limitations

1. **Keyword-driven selection bias**: Content was initially identified through keyword searches, biasing toward posts containing salient conflict-related terminology. This approach may miss more coded or oblique hate speech and disinformation.

2. **Classifier error rates**: Model predictions contain systematic errors (false positives in peace/monitoring categories; variable sensitivity to cultural context in hate speech detection). Error rates by class are documented in Paper A's performance section.

3. **Platform underrepresentation**: TikTok and other platforms with restricted API access are severely underrepresented (154 posts vs. potential thousands). Findings may not generalize to video-based social media or younger user populations.

4. **Language bias**: Pipeline performance varies by language. English content is classified with highest fidelity; Somali and other regional languages have lower validation accuracy.

5. **Temporal bias**: Data concentration in late 2025 and early 2026 limits ability to infer trends over longer periods or patterns in earlier conflict escalations.

6. **Missing context**: Automated classification lacks human contextual knowledge about post authors, audience, and intended interpretation, potentially misclassifying irony, reported speech, and counter-narratives.

---

## 4. Findings: Hate Speech Patterns

### 4.1 Overall Hate Speech Prevalence

Across the 7,034 verified posts, the IRIS pipeline's prediction-level classification yielded four output categories: Normal, Abusive, Hate, and Questionable. Table 1 presents the overall distribution.

**Table 1: Prediction-Level Classification Distribution (All Countries, N = 7,034)**

| Category | Count | % of Total |
|---|---|---|
| Questionable | 2,868 | 40.8% |
| Abusive | 2,372 | 33.7% |
| Hate | 1,527 | 21.7% |
| Normal | 267 | 3.8% |

Content classified as Abusive or Hate — the two categories most directly indicative of harmful rhetoric — together account for 3,899 posts, or **55.4% of the verified dataset**. The Questionable category represents content that triggered classifier attention but did not meet thresholds for definitive harmful classification; it is best understood as a monitoring-priority tier rather than a neutral tier. Only 267 posts (3.8%) received a Normal classification, indicating content with no indicators of harmful rhetoric.

At the macro-category level — which aggregates posts into broader thematic groups including Hate Speech, Violent Extremism, Mixed/Monitoring, Peace, and Unknown — the distribution is as follows: 3,108 posts (44.2%) were assigned to the Hate Speech macro-category, 1,080 (15.4%) to Violent Extremism, 356 (5.1%) to Mixed/Monitoring, 278 (4.0%) to Peace, and 1,178 (16.7%) to Unknown. The substantial Unknown category reflects classifier uncertainty, primarily in Somalia (1,178 of 1,178 total Unknown posts), and likely indicates content in Somali-language registers where the pipeline's validation performance is lower (see Section 3.6 on language bias).

Taken together, these figures establish the dataset as heavily weighted toward conflict-relevant content, which is expected given keyword-driven collection methodology (Section 3.6). The 278 Peace-classified posts (4.0%) represent an important baseline for counter-narrative analysis discussed in Section 6.

### 4.2 Hate Speech by Country

Hate speech prevalence and subtype composition vary substantially across the three countries, reflecting distinct underlying conflict dynamics.

**Kenya (1,743 posts):** Kenya exhibits a hate speech rate of 45.8% at the macro-category level (799 posts), with an additional 27.3% classified as Violent Extremism (475 posts). The prediction-level data shows 49.3% of Kenyan posts classified as Abusive or Hate (860 posts combined). Kenya is the only country in the dataset with a notable Peace-classified proportion: 220 posts (12.6%), suggesting a relatively active counter-narrative ecosystem compared to Somalia and South Sudan.

Subtype analysis reveals that Diaspora-targeted rhetoric dominates among classified subtypes in Kenya, with 123 posts (7.1% of all Kenyan posts; 15.4% of Kenyan hate speech posts) carrying diaspora-attack indicators. Electoral-coded rhetoric is the second most prominent subtype at 50 posts (2.9% / 6.3% of HS), reflecting growing tension around Kenya's 2027 electoral cycle. Delegitimization rhetoric accounts for 18 posts (1.0% / 2.3%), political attacks (HS_POLITICAL_KE) for 14 posts (0.8% / 1.8%), and ethnic mobilization (HS_ETHNIC_KE) for 12 posts (0.7% / 1.5%). Dehumanization rhetoric (HS_DEHUMANISE_KE) is present but comparatively limited at 4 posts, and anti-foreign rhetoric (HS_ANTI_FOREIGN_KE) accounts for 1 post. The prominence of diaspora-related and electoral subtypes suggests that Kenya's hate speech landscape during this period was shaped primarily by election-anticipatory mobilization and conflicts over diaspora political influence, rather than the more visceral dehumanization patterns observed in Somalia.

**Somalia (3,802 posts):** Somalia contributes the largest share of the dataset (54.1%) and exhibits a macro-category hate speech rate of 38.1% (1,450 posts). However, Somalia also contains all 1,178 Unknown-classified posts, which substantially affects interpretability. When Unknown posts are excluded, hate speech as a share of classifiable Somali content is considerably higher. The Violent Extremism category accounts for 411 posts (10.8%), reflecting Al-Shabaab-related content. The Mixed/Monitoring category — representing posts with ambiguous or context-dependent harmful content — is present only in Somalia (356 posts, 9.4%), suggesting a distinct category of content warranting expert review that was not observed in the Kenyan or South Sudanese sub-samples.

Somalia's subtype profile is the most diverse. Dehumanization (HS_DEHUMANISE_SOM) is the leading subtype with 124 posts (3.3% / 8.6% of HS), indicating rhetoric that reduces target groups to subhuman categories — a pattern documented as a precursor to violence in other conflict settings. Delegitimization is the second most prominent subtype at 119 posts (3.1% / 8.2%), encompassing attacks on governance legitimacy, citizenship, and group belonging. Clan-based rhetoric (HS_CLAN_SOM) accounts for 60 posts (1.6% / 4.1%), and religious polarization (HS_RELIGIOUS_SOM) for 53 posts (1.4% / 3.7%). Escalation-coded content adds 20 posts (0.5% / 1.4%). Gender-based attacks (HS_GENDER_SOM) are present in only 1 coded post, though this may reflect underdetection in Somali-language content. The coexistence of dehumanization, clan-based rhetoric, and religious polarization within a single national corpus underscores Somalia's multi-axis hate speech environment — distinct from Kenya's more electorally-oriented patterns.

**South Sudan (1,482 posts):** South Sudan exhibits the highest macro-category hate speech rate of the three countries at 58.0% (859 posts), a finding consistent with its status as an active civil war environment during the data collection period. The prediction-level data confirms this severity: 55.1% of South Sudanese posts (817) were classified as Abusive or Hate. Violent Extremism accounts for 194 posts (13.1%). Notably, South Sudan has no Unknown-classified or Mixed/Monitoring posts, suggesting clearer classifier confidence in the South Sudanese corpus — likely reflecting a predominantly English-language dataset where model performance is higher.

South Sudan's subtype profile centers on diaspora-targeted rhetoric (164 posts, 11.1% / 19.1% of HS) and electoral/process-related attacks (103 posts, 7.0% / 12.0% of HS). Delegitimization is also highly prominent at 100 posts (6.7% / 11.6%), reflecting widespread challenges to institutional and political legitimacy in the context of contested power-sharing arrangements. Political attacks (HS_POLITICAL_SS) appear in 20 posts (1.3% / 2.3%), and ethnic mobilization (HS_ETHNIC_SS) in only 2 posts (0.1%). The relatively low ethnic subtype count — surprising given South Sudan's documented ethnically-framed civil war — may reflect either classifier underperformance on ethnically-coded rhetoric in South Sudanese linguistic registers, or a shift toward framing attacks in political and procedural rather than explicitly ethnic terms during the analysis period.

**Table 2: Macro-Category Distribution by Country**

| Country | Hate Speech | Violent Extremism | Mixed/Monitoring | Peace | Unknown | Total |
|---|---|---|---|---|---|---|
| Kenya | 799 (45.8%) | 475 (27.3%) | 0 (0.0%) | 220 (12.6%) | 0 (0.0%) | 1,743 |
| Somalia | 1,450 (38.1%) | 411 (10.8%) | 356 (9.4%) | 20 (0.5%) | 1,178 (31.0%) | 3,802 |
| South Sudan | 859 (58.0%) | 194 (13.1%) | 0 (0.0%) | 38 (2.6%) | 0 (0.0%) | 1,482 |
| Total | 3,108 (44.2%) | 1,080 (15.4%) | 356 (5.1%) | 278 (4.0%) | 1,178 (16.7%) | 7,034 |

### 4.3 Hate Speech by Platform

Platform-level analysis reveals substantial variation in hate speech rates and subtype composition across Facebook, X/Twitter, and TikTok.

**Facebook (1,973 posts, 28.0% of dataset):** Facebook exhibits the highest hate speech rate among the three platforms at 57.1% (1,127 posts at the macro-category level), with an additional 18.3% classified as Violent Extremism (362 posts). Facebook's Peace proportion stands at 6.1% (121 posts), notably higher than X/Twitter's 3.2%. The geographic concentration of Facebook data in Kenya (768 posts) and South Sudan (807 posts) — with only 398 from Somalia — means Facebook's high hate speech rate largely reflects the conflict intensity characteristic of those two countries.

The Facebook subtype distribution shows a concentration in cross-cutting categories: Diaspora-targeted rhetoric (86 posts), Elections (86 posts), and Delegitimization (73 posts) are the dominant labeled subtypes. No country-specific coded subtypes (HS_DEHUMANISE_SOM, HS_CLAN_SOM, HS_RELIGIOUS_SOM, etc.) appear in the Facebook data, which reflects the platform's geographic composition (Kenya and South Sudan rather than Somalia). The absence of Somalia-specific subtypes from Facebook is consistent with Somalia's X/Twitter dominance rather than indicating an absence of such rhetoric.

**X/Twitter (4,907 posts, 69.7% of dataset):** X/Twitter accounts for the largest volume of posts and exhibits a macro-category hate speech rate of 40.4% (1,981 posts), with Violent Extremism at 14.6% (718 posts), Mixed/Monitoring at 7.3% (356 posts), and Peace at 3.2% (157 posts). The 928 Unknown-classified X/Twitter posts (18.9%) reflect classifier uncertainty concentrated in Somali-language X/Twitter content.

X/Twitter carries nearly all country-specific coded subtypes, including HS_DEHUMANISE_SOM (115 posts), Diaspora attacks (164 posts), Elections (201 posts), Delegitimization (164 posts), HS_CLAN_SOM (39 posts), HS_RELIGIOUS_SOM (43 posts), HS_ETHNIC_KE (12 posts), HS_POLITICAL_KE (14 posts), and HS_POLITICAL_SS (20 posts). This breadth reflects X/Twitter's cross-national coverage in the dataset and its role as the primary analytical signal source for Somalia-specific discourse.

**TikTok (154 posts, 2.2% of dataset):** TikTok data is limited to 154 posts, all from Somalia, and presents an unusual classification profile: 74.0% of TikTok posts (114) were classified as Unknown, with no posts receiving Hate Speech, Peace, or Mixed/Monitoring classifications at the macro-category level. At the subtype level, HS_CLAN_SOM (21 posts), HS_DEHUMANISE_SOM (9 posts), and HS_RELIGIOUS_SOM (10 posts) are present, suggesting that harmful subtype signals were detected even where macro-category classification defaulted to Unknown. This pattern likely reflects model uncertainty when applied to video-sourced transcriptions or short-form audio-text content, rather than an absence of harmful content. TikTok's small sample precludes generalization, but the subtype detections indicate it should not be treated as a low-risk platform.

**Table 3: Platform-Level Macro-Category Distribution**

| Platform | Hate Speech | Violent Extremism | Mixed/Monitoring | Peace | Unknown | Total |
|---|---|---|---|---|---|---|
| Facebook | 1,127 (57.1%) | 362 (18.3%) | 0 (0.0%) | 121 (6.1%) | 136 (6.9%) | 1,973 |
| X/Twitter | 1,981 (40.4%) | 718 (14.6%) | 356 (7.3%) | 157 (3.2%) | 928 (18.9%) | 4,907 |
| TikTok | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) | 114 (74.0%) | 154 |

### 4.4 Temporal Patterns

The temporal distribution of posts reveals a dramatic and rapid concentration of data in the final months of the collection window, with the overwhelming majority of posts collected in December 2025 through February 2026. This concentration reflects the operational maturation of the Phoenix collection platform rather than a genuine spike in social media hate speech activity during this period, though the two cannot be fully disentangled.

Prior to November 2025, monthly totals were very low: single-digit to low double-digit monthly counts from 2024 through October 2025, with the notable exception of October 2025, which saw 479 posts — all from Somalia. This October 2025 Somalia spike may reflect either an operational data-pull event, a specific conflict escalation, or expanded keyword coverage during that month; the data alone cannot disambiguate these explanations.

The growth trajectory from November 2025 onward is marked:

- **November 2025**: 112 total posts (Kenya: 21, Somalia: 75, South Sudan: 16)
- **December 2025**: 1,224 total posts (Kenya: 326, Somalia: 709, South Sudan: 189)
- **January 2026**: 2,732 total posts — the collection peak (Kenya: 922, Somalia: 1,346, South Sudan: 464)
- **February 2026**: 1,929 posts (Kenya: 414, Somalia: 729, South Sudan: 786)
- **March 2026**: 305 posts, partial month (Kenya: 58, Somalia: 216, South Sudan: 24; Regional: 7)

Two notable country-specific patterns emerge from this distribution. First, South Sudan shows a relative intensification in February 2026 (786 posts) compared to January 2026 (464 posts), even as Kenya and Somalia volumes declined month-on-month. This South Sudan surge is temporally consistent with the Akobo County intercommunal violence escalation documented in Section 2.3, suggesting that the February 2026 South Sudanese content increase may reflect genuine conflict-driven social media activity rather than collection artifacts alone. Second, Kenya data is almost entirely absent before December 2025, suggesting either late initiation of Kenyan keyword collection or limited pre-December Kenyan content availability in the Phoenix system.

The temporal data's heavy skew toward the final collection months is an important limitation for longitudinal inference: any trends observable in the dataset reflect a very short window, and the absence of earlier data prevents assessment of longer-term escalation trajectories or pre-conflict baseline levels.

---

## 5. Findings: Disinformation & Narrative Families

### 5.1 Disinformation Event Overview

The IRIS pipeline identified **430 disinformation events** across the verified dataset, distributed across 17 distinct narrative families and classified into four evidence-certainty tiers. Events are distributed across countries as follows: Kenya (149 events, 34.7%), Somalia (149 events, 34.7%), South Sudan (93 events, 21.6%), and Regional multi-country events (39 events, 9.1%). Kenya and Somalia are tied as the most disinformation-active countries in absolute event counts, though this must be contextualized by their differing dataset sizes — Kenya's 149 events from 1,743 posts implies a higher event density per post than Somalia's 149 events from 3,802 posts.

The four certainty tiers are defined as follows: **Confirmed** events are those where the false or manipulative claim has been corroborated by independent fact-checking or evidence; **Context-dependent** events involve content that is misleading, selectively framed, or deceptive in context without being straightforwardly false; **Potential** events are flagged by the classifier as disinformation-indicative but lack external confirmation; and **Disinfo** (the most severe category) represents events where systematic narrative manipulation is established with high confidence.

**Table 4: Disinformation Events by Country and Certainty Tier**

| Country | Confirmed | Context-Dependent | Potential | Disinfo | Total |
|---|---|---|---|---|---|
| Kenya | 50 (33.6%) | 60 (40.3%) | 35 (23.5%) | 4 (2.7%) | 149 |
| Somalia | 44 (29.5%) | 77 (51.7%) | 27 (18.1%) | 1 (0.7%) | 149 |
| South Sudan | 27 (29.0%) | 54 (58.1%) | 10 (10.8%) | 2 (2.2%) | 93 |
| Regional | 8 (20.5%) | 29 (74.4%) | 2 (5.1%) | 0 (0.0%) | 39 |
| **Total** | **129 (30.0%)** | **220 (51.2%)** | **74 (17.2%)** | **7 (1.6%)** | **430** |

Across the full dataset, the most common certainty tier is Context-dependent (220 events, 51.2%), reflecting that the most prevalent form of online disinformation in this corpus involves selective framing, misleading attribution, and context-stripping rather than outright fabrication. Confirmed disinformation accounts for 30.0% of events (129), and Potential for 17.2% (74). The Disinfo tier — representing the most systematically manipulated content — accounts for only 7 events (1.6%), concentrated in Kenya (4) and South Sudan (2). This distribution is broadly consistent with literature suggesting that context-manipulation and misleading framing are more common than outright fabrication in politically motivated disinformation campaigns.

### 5.2 Narrative Family Distribution

The 430 disinformation events cluster into 17 coded narrative families. The coding system uses standardized identifiers that embed country (SO = Somalia, KE = Kenya, SS = South Sudan, FP = false positive) and variant (numeric suffix, with letter suffixes indicating sub-variants). Human-readable narrative descriptions must be mapped from the codebook (see Paper A); Table 5 presents event counts by family code.

**Table 5: Disinformation Events by Narrative Family (N = 430)**

| Rank | Narrative Family | Event Count | % of Total | Country |
|---|---|---|---|---|
| 1 | NAR-SO-001 | 57 | 13.3% | Somalia |
| 2 | NAR-FP-001 | 35 | 8.1% | (False positive / multi-country) |
| 3 | NAR-KE-003a | 31 | 7.2% | Kenya |
| 4 | NAR-SS-004 | 30 | 7.0% | South Sudan |
| 5 | NAR-KE-003b | 29 | 6.7% | Kenya |
| 6 | NAR-SO-004 | 22 | 5.1% | Somalia |
| 7 | NAR-KE-004 | 15 | 3.5% | Kenya |
| 8 | NAR-SO-007 | 15 | 3.5% | Somalia |
| 9 | NAR-SO-002 | 12 | 2.8% | Somalia |
| 10 | NAR-SS-001 | 10 | 2.3% | South Sudan |
| 11 | NAR-SS-003 | 10 | 2.3% | South Sudan |
| 12 | NAR-SO-003 | 10 | 2.3% | Somalia |
| 13 | NAR-FP-002 | 9 | 2.1% | (False positive / multi-country) |
| 14 | NAR-SO-005 | 9 | 2.1% | Somalia |
| 15 | NAR-KE-002 | 6 | 1.4% | Kenya |
| 16 | NAR-SS-002 | 5 | 1.2% | South Sudan |
| 17 | NAR-SO-006 | 5 | 1.2% | Somalia |
| 18 | NAR-SO-009 | 4 | 0.9% | Somalia |
| 19 | NAR-SS-005 | 3 | 0.7% | South Sudan |
| — | Other (KE-D-010, KE-D-009, etc.) | 4 | 0.9% | Kenya |

The single most prevalent narrative family is **NAR-SO-001** with 57 events (13.3% of all disinformation events), making it the dominant disinformation narrative in the entire corpus. As a Somalia-coded family (NAR-SO), it encompasses narratives thematically linked to Somalia's conflict ecosystem; the precise human-readable description should be retrieved from the narrative codebook in Paper A. The concentration of events in a single Somalia family — comprising more events than any other country's top individual family — underscores the high density and coordination of Somali-context disinformation during the analysis period.

The second largest family is **NAR-FP-001** with 35 events (8.1%). As a false-positive family (NAR-FP), these events represent content that triggered disinformation classification but was subsequently determined to be non-events, misclassifications, or ambiguous cases. This family's size (35 events, ranking second overall) should be noted as a quality indicator: it suggests the classifier produces a meaningful false-positive rate that warrants human expert review before analytical conclusions are drawn from raw family counts.

Kenya's dominant narrative families are **NAR-KE-003a** and **NAR-KE-003b** (31 and 29 events respectively), which are sub-variants of the same family (NAR-KE-003), together accounting for 60 events. **NAR-KE-004** adds 15 events and **NAR-KE-002** adds 6. The NAR-KE families align with the Kenya context described in Section 3.5 (electoral manipulation, ethnic marginalization, government overreach, opposition delegitimization).

South Sudan's most prominent family is **NAR-SS-004** with 30 events, followed by **NAR-SS-001** and **NAR-SS-003** at 10 events each, **NAR-SS-002** at 5, and **NAR-SS-005** at 3. The NAR-SS families correspond to the taxonomy described in Section 3.5 (peace agreement violations, ethnic cleansing narratives, external actor blame, resource-based conflict).

Somalia's narrative families are the most numerous and diverse: NAR-SO-001 through NAR-SO-009 together account for 134 events, distributed across nine distinct narrative variants. This breadth reflects Somalia's complex, multi-actor conflict environment in which Al-Shabaab propaganda, clan-based mobilization, diaspora-linked narratives, and international intervention disputes generate overlapping and sometimes competing disinformation streams.

### 5.3 Disinformation by Country

**Kenya (149 events):** Kenya's disinformation landscape is characterized by relatively high Confirmed and Potential event rates (33.6% and 23.5% respectively), suggesting that Kenyan disinformation events are more frequently verifiable as false — consistent with Kenya's more developed fact-checking infrastructure and relatively stronger civil society capacity for claim verification. The dominant narrative families (NAR-KE-003a/b combined = 60 events; NAR-KE-004 = 15; NAR-KE-002 = 6) align with pre-electoral political competition: disinformation surrounding electoral processes and vote manipulation, ethnic marginalization claims, and opposition delegitimization. Kenya's high proportion of Diaspora-subtype hate speech (123 posts; see Section 4.2) and its disinformation event profile together suggest a pattern in which cross-border diaspora communities are both targets of and vectors for politically motivated false narratives, particularly in the context of 2027 election mobilization.

**Somalia (149 events):** Somalia's 149 disinformation events carry the highest Context-dependent proportion of any country (77 events, 51.7%), indicating that the dominant form of Somali disinformation operates through framing, selective emphasis, and misleading attribution rather than outright fabrication. This pattern is consistent with Al-Shabaab's documented media strategy of exploiting genuine grievances, reframing security events, and delegitimizing federal governance through contextual manipulation rather than straightforward fabrication. The diversity of Somalia's narrative families (nine distinct NAR-SO families active in the corpus) further reflects the multi-actor nature of Somali conflict communication. The presence of NAR-FP-001 and NAR-FP-002 events (false positives) concentrated in the corpus also suggests that Somalia's linguistic and contextual complexity generates classification noise that requires careful human review.

**South Sudan (93 events):** South Sudan's 93 disinformation events are heavily concentrated in the Context-dependent tier (54 events, 58.1%), the highest such proportion across all three countries. This suggests that South Sudanese disinformation during the analysis period operated primarily through framing of genuine conflict events — reattributing civilian casualties, misrepresenting peace agreement compliance, and selectively narrating ethnic conflict dynamics — rather than wholesale fabrication. NAR-SS-004 (30 events, the family's largest entry) is the dominant family. The temporal concentration of South Sudanese content in February 2026 (Section 4.4) means that a substantial proportion of South Sudan's 93 disinformation events may be linked to the Akobo County escalation and subsequent narrative contestation, though post-level linkage between temporal clustering and specific disinformation events would require additional cross-referencing.

**Regional (39 events):** The 39 regional disinformation events — those not attributable to a single country — are dominated by the Context-dependent tier (29 events, 74.4%), consistent with transnational narratives that depend on ambiguity and framing rather than country-specific false claims. These multi-country events likely reflect pan-regional narratives around external actor interference, regional security dynamics, or diaspora mobilization that cross national borders. Their presence underscores that East African disinformation is not fully containable within national analytic frameworks.

---

## 6. Discussion: Implications for Policy & Programming

### 6.1 Conflict Early Warning and Risk Indicators

The data presented in Sections 4 and 5 collectively establish a high baseline of harmful content across all three countries, with several patterns warranting particular attention from conflict early warning practitioners.

The most policy-significant finding is the severity gradient across countries: South Sudan, the most active conflict environment in the dataset, also exhibits the highest hate speech rate (58.0% at macro-category level), the highest combined Abusive/Hate prediction rate (55.1%), and a meaningful disinformation event density (93 events from 1,482 posts). While correlation between online hate speech rates and offline violence intensity does not itself constitute causal evidence, the directional alignment between South Sudan's conflict status and its social media hate speech profile is consistent with theoretical models of online rhetoric as both a reflection and amplifier of offline dynamics.

Somalia's profile — while exhibiting a lower macro-category hate speech rate than South Sudan — is distinguished by the concentration of dehumanization rhetoric (HS_DEHUMANISE_SOM, 124 posts) and the presence of the most active individual disinformation narrative family in the corpus (NAR-SO-001, 57 events). Dehumanization in particular is flagged in comparative genocide and mass violence research as a leading indicator of escalation risk, as it functions to reduce moral inhibitions against violence toward a target group. Early warning systems should assign elevated priority to dehumanization subtype detections relative to other hate speech categories.

Kenya's pattern — dominated by diaspora-targeted rhetoric (123 posts) and electoral-coded speech (50 posts) in the context of 2027 election anticipation — suggests a pre-electoral mobilization dynamic consistent with patterns observed in the months preceding the 2007 post-election violence. The prominence of peace-classified content in Kenya (220 posts, 12.6%) relative to other countries is a positive signal, suggesting active counter-narrative activity, but the ratio of harmful to peace-oriented content (799 hate speech posts versus 220 peace posts) indicates that counter-narratives are substantially outpaced by conflict rhetoric.

The temporal data (Section 4.4) indicates a rapid acceleration in total post volumes from November 2025 through January 2026, with South Sudan showing a relative intensification through February 2026 coinciding with documented Akobo escalation. Early warning protocols should incorporate volume thresholds — sudden increases in monthly post counts, particularly for high-hate-speech countries — as a monitoring trigger, in addition to content-based indicators.

**Recommendation**: Conflict early warning systems integrating social media signals should prioritize (a) dehumanization subtype detections as a high-alert indicator; (b) monthly volume tracking with threshold alerts for unusual spikes; (c) cross-referencing NAR-SO-001-family events with security incident reporting; and (d) pre-electoral period monitoring for Kenya given the 2027 cycle.

### 6.2 Platform Governance: Geographic Variation in Strategic Importance

A critical finding of this analysis is the sharp divergence in platform dominance across countries. Facebook accounts for 44.0% of Kenya's verified posts (768 of 1,743) and 54.5% of South Sudan's (807 of 1,482), while X/Twitter accounts for 85.5% of Somalia's posts (3,250 of 3,802). At the macro-category level, Facebook exhibits a higher hate speech rate (57.1%) than X/Twitter (40.4%), though this is partly explained by Facebook's geographic concentration in the two highest-hate-speech countries (Kenya and South Sudan).

This platform-country asymmetry has direct implications for governance strategies. Facebook's structural role as a mass-audience platform in Kenya and South Sudan — serving community groups, local media, and general populations including rural and lower-income users — makes it the primary vector for hate speech reaching broad civilian audiences in those contexts. Governance interventions targeting Facebook (content moderation, counter-narrative placement, transparency reporting, community standards enforcement) are likely to have higher reach per action than equivalent interventions targeting X/Twitter in those countries.

In Somalia, by contrast, X/Twitter is the dominant platform and carries nearly all Somalia-specific hate speech subtypes: HS_DEHUMANISE_SOM (115 of 124 total), HS_CLAN_SOM (39 of 60 total), HS_RELIGIOUS_SOM (43 of 53 total). Somalia's X/Twitter discourse operates primarily within an elite, diaspora-connected, politically engaged user base — a different intervention target than Facebook's broader community-level reach in Kenya and South Sudan. Counter-narrative strategies optimized for X/Twitter in Somalia must account for this elite-skewed audience and the distinct narrative ecosystems of Somali political discourse.

TikTok's 154-post Somalia-only sample is too limited for definitive conclusions, but the presence of clan, dehumanization, and religious subtype detections even within a corpus classified primarily as Unknown suggests that TikTok carries harmful content that the current pipeline cannot fully characterize. Given TikTok's rapid growth trajectory among youth demographics and its algorithmic amplification model, the absence of systematic TikTok monitoring represents a growing gap in the regional hate speech surveillance architecture.

**Recommendation**: Platform governance strategies for East Africa should be explicitly differentiated by country context. Kenya and South Sudan programming should prioritize Facebook — including partnership with Meta's trust and safety teams, Facebook-specific counter-narrative dissemination, and community group monitoring. Somalia programming should prioritize X/Twitter monitoring and engagement with diaspora-connected elite audiences. Investment in TikTok monitoring capacity is warranted across all three countries, with particular urgency for Somalia where a young, growing user base intersects with active violent extremism and clan-based disinformation ecosystems.

### 6.3 Country-Specific Programming Recommendations

**Kenya:** Kenya's disinformation and hate speech profile points to a pre-electoral mobilization dynamic with a 2027 time horizon. The dominance of diaspora-targeted hate speech (123 posts) suggests that Kenya's diaspora communities — particularly those politically active in diaspora-home political networks — are both targets of and vectors for harmful content. Programming should prioritize diaspora-focused counter-narrative campaigns that provide alternative frames for diaspora political engagement. Electoral-coded hate speech (50 posts) and the NAR-KE-003 family's 60 combined events indicate that electoral process disinformation will intensify as 2027 approaches; pre-positioning fact-checking partnerships, electoral transparency communications, and voter education programs is advisable well in advance of the formal campaign period.

Kenya's comparatively high peace-content proportion (220 posts, 12.6%) suggests an existing organic counter-narrative ecosystem that can be strategically supported and amplified. Identifying and resourcing the voices and organizations generating this peace content — whether civil society actors, faith communities, or youth groups — offers a higher-leverage intervention than creating counter-narratives de novo.

**Somalia:** Somalia's profile demands attention to two distinct threat streams: the structural presence of Al-Shabaab-linked disinformation (reflected in NAR-SO-001's 57 events and the Violent Extremism classification of 411 posts) and the decentralized but pervasive pattern of clan-based, dehumanizing, and delegitimizing rhetoric (reflected in HS_DEHUMANISE_SOM = 124 posts, HS_CLAN_SOM = 60 posts). Counter-programming must engage both streams with distinct strategies: Al-Shabaab counter-messaging requires coordination with international security and media partners experienced in violent extremism counter-narrative; clan-based hate speech requires engagement with traditional clan and community leadership structures that can provide authoritative counter-voices within affected communities.

Somalia's negligible peace-content proportion (20 posts, 0.5%) is the starkest finding across the dataset. This near-absence of peace messaging in a corpus of 3,802 posts suggests either that peace-oriented actors in Somalia face structural barriers to social media engagement, that peace-oriented content uses framing or language not captured by the collection keywords, or that the organic peace-messaging ecosystem in Somalia is genuinely underdeveloped. All three possibilities point to a programming priority: building the capacity and platform presence of peace-oriented Somali civil society voices.

**South Sudan:** South Sudan's 58.0% hate speech rate — the highest in the dataset — combined with a 2.6% peace-content proportion indicates the most severe content environment of the three countries. The Akobo escalation context (Section 2.3) situates this data within an active mass atrocity risk environment. Programming priorities should reflect crisis-level urgency.

The dominance of diaspora-targeted rhetoric (164 posts, 11.1%) in South Sudan's hate speech profile is notable given South Sudan's limited internet penetration and relatively constrained formal diaspora compared to Somalia or Kenya. This may suggest that online hate speech in South Sudan is produced by a digitally connected elite whose targeting of diaspora communities reflects competition over remittances, political influence, and external resources. Programming should engage this elite directly — including through traditional media, community leaders, and inter-ethnic dialogue initiatives — rather than assuming broad-population social media reach.

The delegitimization rhetoric concentration (100 posts, 11.6% of South Sudan HS) reflects ongoing contestation of the Revitalized Agreement on the Resolution of the Conflict in South Sudan (R-ARCSS). Counter-narrative programming should specifically address peace agreement legitimacy narratives, providing factual information about implementation status and supporting voices that affirm the agreement's value.

### 6.4 Counter-Narratives and Peace-Oriented Content

Among the 7,034 posts, **278 (4.0%)** were classified as Peace — content exhibiting counter-narrative, reconciliation, or peace-building characteristics. This figure differs from the Normal prediction-level category (267 posts, 3.8%); Peace is a macro-category reflecting explicit thematic orientation, while Normal is a prediction-level classification indicating absence of harmful signals. Together they establish that content explicitly oriented toward peaceful discourse constitutes approximately 4–5% of the verified dataset.

The distribution of Peace content across countries and platforms is uneven and programmatically significant:

- Kenya accounts for 220 of 278 Peace posts (79.1%), despite comprising only 24.8% of total verified posts. This concentration indicates that Kenya has a substantially more active organic counter-narrative ecosystem than Somalia or South Sudan.
- Somalia, despite comprising 54.1% of posts, generates only 20 Peace posts (7.2%), a rate of 0.5% — seventeen times lower than Kenya's 12.6% peace proportion.
- South Sudan generates 38 Peace posts (13.7% of all Peace content), at a rate of 2.6%.
- By platform, Facebook generates 121 Peace posts (6.1% of Facebook content), while X/Twitter generates 157 (3.2% of X/Twitter content), and TikTok generates none.

The ratio of Hate Speech to Peace content in the macro-category data is 3,108:278, or approximately 11:1 across the full dataset. In Somalia the ratio is 1,450:20, or 72.5:1 — an extreme imbalance that underscores the scale of the counter-narrative deficit in that context. In South Sudan the ratio is 859:38, or 22.6:1.

These figures reinforce a conclusion consistent with existing counter-disinformation research: organic peace messaging, while valuable, is structurally disadvantaged in competitive social media information environments where conflict-oriented content benefits from higher emotional salience, algorithmic amplification, and coordination by motivated actors. Deliberate, resourced counter-narrative campaigns that strategically amplify peace-oriented voices are necessary to narrow these ratios in environments where 72:1 imbalances prevail.

**Recommendation**: Resource allocation for peace-messaging programs in East Africa should weight Somalia most heavily, given its near-total absence of organic peace content. Counter-narrative investments in Kenya should focus on amplification of existing peace voices rather than creation of new messaging. All country programs should track peace-to-hate-speech ratios over time as a monitoring metric.

### 6.5 Limitations of This Analysis

This discussion must be qualified by several significant analytical limitations that affect the confidence with which policy recommendations can be advanced.

**Keyword selection bias** shapes the corpus fundamentally: all 7,034 posts were identified through conflict-related keyword searches, ensuring that the dataset is not representative of the general social media environment but rather of the conflict-activated information space. Peace-content proportions and hate speech rates reported here are not population estimates; they are characterizations of content within a deliberately conflict-focused sample.

**Classifier error rates** (documented in Paper A) mean that individual classification decisions — particularly at the subtype level and for Somali-language content — carry meaningful false positive and false negative rates. The large Unknown category for Somalia (1,178 posts, 31.0%) is a direct manifestation of this limitation. Aggregate patterns reported in this paper are more robust than individual-post or small-count findings, but readers should treat subtype counts below approximately 20 events with caution.

**Platform sampling asymmetry** — particularly the severe underrepresentation of TikTok and the complete absence of WhatsApp, Telegram, and other messaging platform data — means that the findings in this paper characterize only a portion of the relevant information environment. In Somalia especially, encrypted and semi-private messaging platforms are known to be significant vectors for Al-Shabaab content and clan-based mobilization; their absence from this corpus is a structural gap.

**Temporal concentration** in the final collection months limits longitudinal inference. The data cannot support claims about trends over the full six-month window, and the absence of pre-collection baseline data prevents assessment of whether observed patterns represent escalation, de-escalation, or stability relative to prior periods.

**Context blindness** of automated classifiers — their inability to interpret irony, reported speech, satire, or community-specific coded language — generates both false positives (non-harmful content classified as harmful) and false negatives (harmful content framed in ways the classifier does not recognize). Human expert review of algorithmically flagged content is essential before operational decisions are taken on the basis of IRIS outputs alone.

---

## 7. Ethics: Responsible Research on Hate Speech and Disinformation

### 7.1 Data Privacy and PII Redaction

All individual posts and user-identifying information have been removed from reported findings. This analysis reports only aggregate statistics and thematic patterns, never individual post content or user identities.

*[Document specific redaction protocols used in data processing]*

### 7.2 Aggregate-Only Reporting

No individual posts are cited by content in this paper. Illustrative examples, where provided, are paraphrased, substantially altered, or sourced from published materials, never from original dataset.

### 7.3 Responsible Disclosure

Significant findings regarding platform-level disinformation campaigns, organized hate speech networks, or coordinated inauthentic behavior were disclosed to relevant platforms and national authorities prior to public release. *[Document disclosure timeline if applicable]*

### 7.4 Surveillance versus Protection Framing

Research on hate speech and disinformation in conflict contexts faces an ethical tension: monitoring can inform protection and prevention, but can also enable surveillance and control. This research is framed within a **protection and conflict prevention paradigm**, not a surveillance one.

- **Protection framing**: Use of findings to identify vulnerable communities, prevent offline violence, and support counter-extremism
- **Explicit non-surveillance**: Data is not shared with law enforcement, military, or security services for surveillance or targeting of individuals
- **Conflict-sensitive**: Analysis avoids stigmatizing entire ethnic, religious, or national groups; conflicts are understood as involving elite actors and structural dynamics, not inherent group characteristics

### 7.5 Researcher Positionality

*[Document research team composition, affiliations, and potential conflicts of interest. Address positionality of non-African researchers, if applicable. Acknowledge limitations of external analysts' interpretation of local context.]*

### 7.6 IRB Status and Oversight

*[Document IRB approval status, ethical review processes, and oversight mechanisms]*

---

## 8. Conclusion

This paper has presented the first large-scale cross-national analysis of online hate speech and disinformation patterns in East Africa, drawing on systematic classification of 7,034 verified social media posts across Kenya, Somalia, and South Sudan. Key findings include:

1. **Significant prevalence of hate speech** across the region, with country-specific drivers reflecting distinct conflict dynamics (electoral tension in Kenya, clan politics in Somalia, civil war in South Sudan)

2. **Platform asymmetries**: Facebook is strategically dominant in Kenya and South Sudan, while X/Twitter dominates Somalia discourse. Western-centric platform governance models are poorly calibrated for regional realities.

3. **Substantial disinformation presence**: 430+ disinformation events distributed across 17 coded narrative families (organized within 9 conceptual narrative categories), with strong overlap to hate speech and conflict escalation patterns.

4. **Capacity for automated monitoring**: Demonstrated feasibility of large-scale, multilingual, multi-platform automated classification, enabling rapid event detection and longitudinal tracking.

5. **Minimal peace-oriented content**: Peace messaging is significantly outweighed by conflict-focused rhetoric, suggesting need for deliberate counter-narrative investment.

### Recommendations for Policy and Programming

- Establish permanent regional monitoring infrastructure combining automated detection with human expert review
- Implement country- and platform-specific content governance strategies, prioritizing Facebook in Kenya/South Sudan and X/Twitter in Somalia
- Invest in counter-narrative development and amplification, targeting conflict-sensitive messaging to high-risk communities
- Support conflict early warning systems informed by social media patterns linked to documented security incidents
- Advance longitudinal research linking social media dynamics to offline violence patterns and intervention effectiveness

### Future Directions

1. **Longitudinal analysis**: Extend data collection and analysis to track hate speech and disinformation trajectories over years, enabling causal assessment of intervention effectiveness

2. **Causal linking**: Develop methods to link social media patterns to documented offline violence incidents with enhanced temporal and geographic precision

3. **Geographic expansion**: Extend analysis to additional countries and platforms, particularly video-based media (TikTok) and messaging apps (WhatsApp, Telegram)

4. **Intervention evaluation**: Conduct randomized trials or quasi-experimental evaluation of counter-narrative campaigns, platform policy changes, and community-based interventions

5. **Integration with offline data**: Combine social media analysis with surveys, interviews, and conflict event data to develop multi-method understanding of hate speech-violence dynamics

---

## References

Adelani, D. I., Abbott, J., Neubig, G., D'souza, J., Kreutzer, J., Lignos, C., Palen-Michel, C., Buzaaba, H., Sibanda, B., Dossou, B., Mabuya, S., Emezue, C., Kahira, A., Muhammad, S. H., Ogundepo, O., Ifeoluwa, P., Gwadabe, T., Abdulmumin, I., Tesi, A., . . . Ruder, S. (2021). MasakhaNER: Named entity recognition for African languages. *Transactions of the Association for Computational Linguistics*, *9*, 1116–1131. https://doi.org/10.1162/tacl_a_00416

Amnesty International. (2023). *"A death sentence for my father": Meta's contribution to human rights abuses in northern Ethiopia* (Doc. AFR25/7292/2023). https://www.amnesty.org/en/documents/afr25/7292/2023/en/

Armed Conflict Location & Event Data Project (ACLED). (2023). *ACLED codebook 2023*. https://acleddata.com/knowledge-base/codebook/

Benesch, S. (2012). *Dangerous speech: A proposal to prevent group violence*. Dangerous Speech Project Working Paper. http://worldpolicy.org/projects/dangerous-speech-along-the-path-to-mass-violence/

Benesch, S. (2014). *Countering dangerous speech: New ideas for genocide prevention*. Working Paper. United States Holocaust Memorial Museum. https://www.ushmm.org/m/pdfs/20140212-benesch-countering-dangerous-speech.pdf

Center for Democracy and Technology. (2022). *Content moderation in the Global South: A comparative study of four low-resource languages*. https://cdt.org/insights/content-moderation-in-the-global-south-a-comparative-study-of-four-low-resource-languages/

CIPESA (Collaboration on International ICT Policy for East and Southern Africa). (2025). Social media's role in hate speech: A double-edged sword for South Sudan. https://cipesa.org/2025/02/social-medias-role-in-hate-speech-a-double-edged-sword-for-south-sudan/

Davidson, T., Warmsley, D., Macy, M., & Weber, I. (2017). Automated hate speech detection and the problem of offensive language. *Proceedings of the 11th International AAAI Conference on Web and Social Media (ICWSM '17)*, 512–515. https://arxiv.org/abs/1703.04009

Fortuna, P., & Nunes, S. (2018). A survey on automatic detection of hate speech in text. *ACM Computing Surveys*, *51*(4), Article 85. https://doi.org/10.1145/3232676

Gilardi, F., Alizadeh, M., & Kubli, M. (2023). ChatGPT outperforms crowd-workers for text-annotation tasks. *Proceedings of the National Academy of Sciences*, *120*(30), e2305016120. https://doi.org/10.1073/pnas.2305016120

Global Witness & Foxglove. (2022). *Facebook unable to detect hate speech weeks away from tight Kenyan election*. https://www.globalwitness.org/en/campaigns/digital-threats/hate-speech-kenyan-election/

He, X., Lin, Z., Gong, Y., Jin, H., Han, T., Zhao, B., Gu, Q., Shou, L., Duan, N., & Chen, W. (2024). Data augmentation using LLMs: Data perspectives, learning paradigms, and challenges. *Findings of the Association for Computational Linguistics: ACL 2024*, Paper 97. https://doi.org/10.18653/v1/2024.findings-acl.97

Hegre, H., Allansson, M., Basedau, M., Colaresi, M., Croicu, M., Hegre, H., Hoyles, F., Hultman, L., Högbladh, S., Jansen, R., Lundgren, M., Melander, E., Möller, F., Nordkvelle, J., Pagendarm, M., Petrova, T., Randazzo, F., Rustad, S., Sjöberg, G., . . . Wischnath, G. (2019). ViEWS: A political violence early warning system. *Journal of Peace Research*, *56*(2), 155–174. https://doi.org/10.1177/0022343319823860

Herrmann, I. (2023). *Digital warfare: Exploring the influence of social media in propagating and counteracting hate speech in Sudan's conflict landscape*. Chr. Michelsen Institute. https://www.cmi.no/publications/9610-digital-warfare-exploring-the-influence-of-social-media-in-propagating-and-counteracting-hate

Huang, X., Kwak, H., An, J., Sheth, A., & Alinejad-Rokny, H. (2024). *Harnessing artificial intelligence to combat online hate: Exploring the challenges and opportunities of large language models in hate speech detection*. arXiv:2403.08035.

iHub Research & Ushahidi. (2013). *Umati: Monitoring online dangerous speech — final report*. iHub Research. https://www.ushahidi.com/about/blog/umati-final-report-released

Imran, M., Mitra, P., & Castillo, C. (2016). Twitter as a lifeline: Human-annotated Twitter corpora for NLP of crisis-related messages. *Proceedings of the 10th Language Resources and Evaluation Conference (LREC 2016)*, 1638–1643. https://arxiv.org/abs/1605.05894

Institute for Strategic Dialogue. (2021). *Polarising content and hate speech ahead of Kenya's 2022 elections: Challenges and ways forward*. https://www.isdglobal.org/isd-publications/polarising-content-and-hate-speech-ahead-of-kenyas-2022-elections-challenges-and-ways-forward/

International Crisis Group. (2016). *Seizing the moment: From early warning to early action*. https://www.crisisgroup.org/global/seizing-moment-early-warning-early-action

Jigsaw & Google Counter Abuse Technology. (2017–present). *Perspective API*. https://www.perspectiveapi.com/

Kiai, M. (2008). *Speech, power and violence: Hate speech and the political crisis in Kenya*. Presented at the Sudikoff Annual Interdisciplinary Seminar on Genocide Prevention, United States Holocaust Memorial Museum. https://www.ushmm.org/m/pdfs/20100423-speech-power-violence-kiai.pdf

Lees, A., Tran, V. Q., Tay, Y., Sorensen, J., Gupta, J., Metzler, D., & Vasserman, L. (2022). A new generation of Perspective API: Efficient multilingual character-level transformers. *Proceedings of the 28th ACM SIGKDD Conference on Knowledge Discovery and Data Mining (KDD '22)*. https://doi.org/10.1145/3534678.3539147

Matamoros-Fernández, A., & Farkas, J. (2021). Racism, hate speech, and social media: A systematic review and critique. *Television & New Media*, *22*(2), 205–224. https://doi.org/10.1177/1527476420982230

Meleagrou-Hitchens, A., & Maher, S. (2012). *Lights, camera, jihad: Al-Shabaab's western media strategy*. International Centre for the Study of Radicalisation, King's College London. https://icsr.info/wp-content/uploads/2012/11/ICSR-Report-Lights-Camera-Jihad-al-Shabaab%E2%80%99s-Western-Media-Strategy.pdf

Mercy Corps. (2019). *The weaponization of social media: How to recognise, prevent and respond* (C. Robbins, author). https://www.mercycorps.org/sites/default/files/2020-01/Weaponization_Social_Media_FINAL_Nov2019.pdf

Muhammad, S. H., Abdulmumin, I., Yimam, S. M., Adelani, D. I., Ahmad, I. S., Ousidhoum, N., Ayele, A., Mohammad, S. M., Beloucif, M., & Ruder, S. (2023). SemEval-2023 Task 12: Sentiment analysis for African languages (AfriSenti-SemEval). *Proceedings of the 17th International Workshop on Semantic Evaluation (SemEval-2023)*. https://arxiv.org/abs/2304.06845

Muhammad, S. H., et al. (2025). AfriHate: A multilingual collection of hate speech and abusive language datasets for African languages. arXiv:2501.08284.

Müller, K., & Schwarz, C. (2021). Fanning the flames of hate: Social media and hate crime. *Journal of the European Economic Association*, *19*(4), 2131–2167. https://doi.org/10.1093/jeea/jvaa045

Mutahi, P., & Kimari, B. (2017). *The impact of social media and digital technology on electoral violence in Kenya* (IDS Working Paper Vol. 2017, No. 493). Institute of Development Studies / Centre for Human Rights and Policy Studies. https://www.chrips.or.ke/wp-content/uploads/2017/08/The-impact-of-social-media-and-digital-technology-on-electoral-violence-in-kenya.pdf

OpenAI. (2022–present). *Moderation API*. https://platform.openai.com/docs/api-reference/moderations

Orife, I., Kreutzer, J., Sibanda, B., Whitenack, D., Siminyu, K., Martinus, L., Tapo, A., Adeyemi, M., Rajendran, J., Mwase, C., Abbott, J., Degila, J., Mokgesi-Selinga, M., Okolo, U., Sawirtu, L., Sanogomele, S., Tonja, A., & Eddine, M. B. (2020). *Masakhane — machine translation for Africa*. arXiv:2003.11529. AfricaNLP Workshop, ICLR 2020.

PeaceTech Lab. (2016–2020). *Hate speech monitoring reports: South Sudan* (biweekly series). PeaceTech Lab. https://www.peacetechlab.org/

Raleigh, C., Linke, A., Hegre, H., & Karlsen, J. (2010). Introducing ACLED: An armed conflict location and event dataset. *Journal of Peace Research*, *47*(5), 651–660. https://doi.org/10.1177/0022343310378914

Röttger, P., Kirk, H. R., Vidgen, B., Attanasio, G., Nozza, D., & Hovy, D. (2024). *Investigating annotator bias in large language models for hate speech detection*. arXiv:2406.11109.

Röttger, P., Vidgen, B., Hovy, D., & Pierrehumbert, J. (2023). *Toxic bias: Perspective API misreads German as more toxic*. arXiv:2312.12651.

Sap, M., Card, D., Gabriel, S., Choi, Y., & Smith, N. A. (2019). The risk of racial bias in hate speech detection. *Proceedings of the 57th Annual Meeting of the Association for Computational Linguistics (ACL 2019)*, 1668–1678.

Sentinel Project for Genocide Prevention. (2008–present). *Early warning system: Operational process and stages of genocide model*. https://thesentinelproject.org/what-we-do/early-warning-system/

Svendsen, K. (2025). *IRIS: An automated multi-stage pipeline for hate speech and disinformation monitoring in low-resource East African contexts* [Paper A]. UNDP IRIS Project.

Swahili and code-switched English-Swahili political hate speech detection textual dataset. (2025). *Data Intelligence*. https://doi.org/10.3724/2096-7004.di.2025.0053

UNDP Chief Digital Office. (2021–present). *iVerify: Combating misinformation and strengthening information integrity*. United Nations Development Programme. https://www.undp.org/digital/iverify

United Nations Human Rights Council. (2018). *Report of the independent international fact-finding mission on Myanmar* (UN Doc. A/HRC/39/64). OHCHR. https://www.ohchr.org/en/hr-bodies/hrc/myanmar-ffm/report

United Nations Office on Genocide Prevention and the Responsibility to Protect. (2014). *Framework of analysis for atrocity crimes: A tool for prevention*. United Nations. https://www.un.org/en/genocideprevention/documents/about-us/Doc.3_Framework%20of%20Analysis%20for%20Atrocity%20Crimes_EN.pdf

Waseem, Z., & Hovy, D. (2016). Hateful symbols or hateful people? Predictive features for hate speech detection on Twitter. *Proceedings of the NAACL Student Research Workshop*, 88–93. https://doi.org/10.18653/v1/N16-2013

Williams, J. (2021). Facebook's content moderation failures in Ethiopia. *Council on Foreign Relations Think Global Health Blog*. https://www.cfr.org/blog/facebooks-content-moderation-failures-ethiopia

Yanagizawa-Drott, D. (2014). Propaganda and conflict: Evidence from the Rwandan genocide. *The Quarterly Journal of Economics*, *129*(4), 1947–1994. https://yanagizawadrott.com/wp-content/uploads/2016/02/rwandadyd.pdf

