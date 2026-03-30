# IRIS Papers — Action Items

## Critical Blockers (Must Resolve Before Submission)

### Paper A (Methodology) — Technical Validation

- [ ] **Evaluation metrics completion**: Fill in empirical performance numbers
  - [ ] Precision: [currently marked "to be completed" on line 224]
  - [ ] Recall: [currently marked "to be completed" on line 225]
  - [ ] F1 score: [currently marked "to be completed" on line 226]
  - [ ] Per-class breakdown (Normal, Abusive, Hate)
  - [ ] Source file: `papers/analysis/pipeline_performance.csv` or equivalent metrics
  - [ ] Alternative: Run evaluation against a held-out test set if not yet done

- [ ] **Training dataset documentation**: Reference the EA-HS training data paper/analysis
  - [ ] Placeholder on line 211: `[placeholder: reference training dataset paper / analysis]`
  - [ ] Need to cite or document the ~12,000 East African posts dataset
  - [ ] Confirm bilingual annotator methodology is documented
  - [ ] Inter-annotator agreement (IAA) scores if available

- [ ] **Prompt engineering documentation**: Reference prompts and evaluation results
  - [ ] Placeholder on line 281: `[placeholder: reference prompts and evaluation results]`
  - [ ] Include sample prompts used in LLM QA stage (line 281, Appendix C)
  - [ ] Document how false positive decision was validated (59% FP removal rate)
  - [ ] Evaluation results for prompt consistency/reliability

- [ ] **Bibliography completion**: Populate references section
  - [ ] Line 502: `[Placeholder: full bibliography to be populated during final paper writing]`
  - [ ] Include citations for:
    - Foundational hate speech detection work
    - East African conflict literature
    - Multilingual NLP papers
    - Similar operational monitoring systems
    - Ethics in AI/NLP

### Paper D (Findings) — Ethical & Methodological Disclosure

- [ ] **Data privacy and redaction protocols**: Document specific procedures
  - [ ] Line 374: `*[Document specific redaction protocols used in data processing]*`
  - [ ] Specify PII redaction rules (usernames, phone, email, etc.)
  - [ ] Confirm URL handling and parameter stripping procedures
  - [ ] Reference data governance policy (Appendix E)

- [ ] **Responsible disclosure timeline**: If applicable, document and validate
  - [ ] Line 382: `*[Document disclosure timeline if applicable]*`
  - [ ] If disinformation/organized hate networks were disclosed: when, to whom, platforms, authorities
  - [ ] If not disclosed: clarify why and document decision
  - [ ] May need approval from UNDP/partner organizations before publication

- [ ] **Researcher positionality statement**: Complete composition & conflict of interest section
  - [ ] Line 394: `*[Document research team composition, affiliations, and potential conflicts of interest. Address positionality of non-African researchers, if applicable. Acknowledge limitations of external analysts' interpretation of local context.]*`
  - [ ] Names, roles, institutional affiliations of all authors
  - [ ] Any external (non-African) researchers — address their positionality
  - [ ] Potential conflicts of interest with platforms, governments, or organizations
  - [ ] Acknowledgment of limitations in interpreting local context

- [ ] **IRB approval and ethical oversight**: Document and verify status
  - [ ] Line 398: `*[Document IRB approval status, ethical review processes, and oversight mechanisms]*`
  - [ ] Check with UNDP whether project approval constitutes ethical clearance
  - [ ] If separate IRB review needed: timeline and approval status
  - [ ] Document any ethical review board (university IRB, institutional review, etc.)
  - [ ] Oversight mechanisms and approval conditions

- [ ] **Bibliography completion**: Populate references
  - [ ] Line 440: `*[To be completed during revision — references to Paper A (IRIS pipeline validation), existing literature on hate speech and conflict, platform governance research, conflict dynamics in East Africa, and methodological sources]*`
  - [ ] Cross-references to Paper A methodology validation
  - [ ] Hate speech and conflict literature (regional and global)
  - [ ] Platform governance and content moderation research
  - [ ] East African conflict dynamics and peacebuilding work
  - [ ] Methodological sources (BERT, multilingual NLP, qualitative synthesis)

---

## Venue Selection & Formatting

- [ ] **Choose primary venue for Paper A (Methodology & System Design)**
  - Target venues (with formatting requirements to verify):
    - ACM COMPASS (Conference on Computing and Sustainable Societies)
    - AAAI AI for Social Good
    - EMNLP Findings (Computational Linguistics)
    - AI & Society (Springer journal)
    - Other: NeurIPS/ICML workshop, ACL workshop, or domain-specific venue
  - [ ] Check formatting guidelines (page limits, LaTeX/Word requirements, citation style)
  - [ ] Verify deadlines and submission timeline
  - [ ] Check whether this venue prefers archival vs. non-archival track

- [ ] **Choose primary venue for Paper D (Findings & Analysis)**
  - Target venues (with formatting requirements to verify):
    - Journal of Peace Research (peer-reviewed, high impact)
    - Conflict Management & Peace Science
    - Stability: International Journal of Security & Development
    - Peace and Conflict: Journal of Peace Psychology
    - Other: African Studies Review, African Conflict and Peace Building Review
  - [ ] Check formatting guidelines and citation styles
  - [ ] Verify ethics approval requirements for each journal
  - [ ] Confirm whether findings-oriented papers are in scope

- [ ] **Format papers to target venue templates**: Use LaTeX or Word templates
  - [ ] Paper A: Prepare title, abstract, keywords in target format
  - [ ] Paper D: Prepare title, abstract, keywords in target format
  - [ ] Ensure figures and tables meet venue specifications

---

## Data & Analysis Validation

- [ ] **Narrative family mapping (Paper D)**: Map NAR-XX-NNN codes to human-readable names
  - [ ] Populate Table/Figure showing narrative taxonomy
  - [ ] Confirm codebook against original collected narratives
  - [ ] Validate frequency counts against dataset

- [ ] **Aggregate statistics review**: Validate all numbers in Paper D
  - [ ] 80,000 candidate posts processed ✓ (appears consistent)
  - [ ] 7,034 verified hate speech classifications ✓
  - [ ] 59% false positive removal rate — verify against LLM review logs
  - [ ] Regional breakdown (Somalia, South Sudan, Kenya) — confirm counts by country
  - [ ] Temporal patterns (6 months of deployment) — verify date ranges
  - [ ] Subtype distribution (Ethnic Targeting, Political Incitement, etc.) — validate percentages
  - [ ] Platform breakdown (X, Facebook, TikTok) — confirm split

- [ ] **Cost calculations**: Verify $40/month operating cost
  - [ ] Confirm Apify keyword sweep cost
  - [ ] Confirm LLM QA cost (~$0.03 per 100 posts)
  - [ ] Include infrastructure (storage, compute) if applicable
  - [ ] Document any in-kind contributions or unpaid labor

- [ ] **ACLED temporal validation**: If claiming early warning value
  - [ ] Obtain ACLED violence event data for monitored regions
  - [ ] Run Granger causality or spike correlation analysis (mentioned as future work on line 498)
  - [ ] Document whether hate speech detection _precedes_ documented violence
  - [ ] If not completed: be clear this is future work, not a current claim

---

## Model Artifacts & Reproducibility

- [ ] **Confirm EA-HS model availability on Hugging Face**
  - [ ] Verify KSvendsen/EA-HS is public and accessible
  - [ ] Include model card with training data, performance metrics, intended use, limitations
  - [ ] Add links in paper (Paper A, Line 504+)

- [ ] **Language-specific supplementary models**: Confirm availability
  - [ ] Somalia_pred, Sudan_pred, Kenya_pred models on Hugging Face or in appendix
  - [ ] Document training data and performance for each

- [ ] **Code and pipeline reproducibility**
  - [ ] Make IRIS codebase (Apify → BERT → LLM stages) available
  - [ ] Include data dictionary (Appendix D) in submission or supplementary materials
  - [ ] Document dependencies, versions, and setup instructions

---

## Authorship & Acknowledgments

- [ ] **Authorship and ordering**: Decide for each paper
  - [ ] Paper A: Who is first author? Order of remaining authors?
  - [ ] Paper D: Who is first author? Order of remaining authors?
  - [ ] Note: May differ between papers

- [ ] **UNDP attribution and approval**
  - [ ] Confirm UNDP is properly acknowledged
  - [ ] Verify whether UNDP needs to approve findings disclosure
  - [ ] Determine if UNDP should be listed as an author or funder
  - [ ] Resolve any publication restrictions or pre-approval requirements

- [ ] **Contributor and translator acknowledgments**
  - [ ] Bilingual annotators (Somali/English, Swahili/English, Arabic/English pairs)
  - [ ] Field partners in Somalia, South Sudan, Kenya
  - [ ] Any external reviewers or advisors

---

## Nice to Have (Not Blocking but Recommended)

- [ ] **Precision/recall/F1 against gold-standard subset**
  - [ ] Manually annotate 200–500 posts as ground truth
  - [ ] Run evaluation against this subset instead of (or in addition to) LLM proxy
  - [ ] Would strengthen claims about pipeline reliability

- [ ] **Ablation experiments**: Test each pipeline stage
  - [ ] Full pipeline vs. without Rule-Based HS Indicators
  - [ ] Full pipeline vs. without BERT classification
  - [ ] Full pipeline vs. without LLM QA stage
  - [ ] Demonstrates which stages contribute most to performance

- [ ] **System architecture diagram**: Figure 1 in Paper A
  - [ ] Visual flowchart of the 5-stage pipeline
  - [ ] Decision trees and threshold logic
  - [ ] Cost and latency characteristics

- [ ] **Inter-annotator agreement study**: As mentioned in conclusion
  - [ ] Compare Claude LLM QA decisions against trained human annotators (≥2)
  - [ ] Calculate Cohen's kappa or Krippendorff's alpha
  - [ ] Establishes degree to which LLM review can substitute for human annotation

- [ ] **Supplementary materials**: Prepare if needed by venue
  - [ ] Appendix A: Full rule set (Hate Speech Indicators by Language)
  - [ ] Appendix B: BERT Training Configuration and Hyperparameters
  - [ ] Appendix C: Sample Prompts for LLM Quality Assurance
  - [ ] Appendix D: Data Dictionary (CSV Column Schema)
  - [ ] Appendix E: Ethics and Data Governance Policy

- [ ] **Extension to encrypted platforms**: Document future work
  - [ ] WhatsApp and Telegram monitoring (mentioned line 502)
  - [ ] Oromo and Tigrinya language support (mentioned line 502)
  - [ ] Open-source LLM alternatives for data sovereignty (mentioned line 502)

---

## Legend

- **Critical Blockers**: Must be resolved before submitting to any venue
- **Venue Selection & Formatting**: Depends on which journals/conferences you choose
- **Data & Analysis Validation**: Ensure numerical claims in the papers are accurate
- **Model Artifacts & Reproducibility**: Needed for transparency and future work
- **Authorship & Acknowledgments**: Administrative but essential
- **Nice to Have**: Strengthen papers but not strictly necessary for initial submission

**Timeline Suggestion**: Complete Critical Blockers first (weeks 1–2), then Venue Selection (week 3), then prepare supplementary materials for submission (weeks 4–5).

**Last Updated**: 2026-03-30
