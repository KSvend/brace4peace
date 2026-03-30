# Literature Review — Paper D
## Online Hate Speech Patterns Across East Africa: Findings and Policy Implications

*Compiled for Paper D (findings/policy paper). All citations verified via web search. Last updated: 2026-03-30.*

---

## 1. East African Conflict and Online Hate Speech

### [Kiai (2008)] — Speech, Power and Violence: Hate Speech and the Political Crisis in Kenya

- **Citation:** Kiai, M. (2008). "Speech, Power and Violence: Hate Speech and the Political Crisis in Kenya." Presented at the Sudikoff Annual Interdisciplinary Seminar on Genocide Prevention, United States Holocaust Memorial Museum, Washington, DC. Available at: https://www.ushmm.org/m/pdfs/20100423-speech-power-violence-kiai.pdf
- **Key finding:** Kenya's post-election violence (January–March 2008) killed approximately 1,200 people and displaced 500,000. Local-language radio and SMS text messaging were primary vectors for spreading hate speech before and during the violence, with much of the inflammatory content originating from ordinary citizens rather than political elites.
- **Relevance to Paper D:** Establishes the baseline East African case — SMS/radio-mediated hate speech predating the social media era — against which we benchmark our platform-era findings.
- **Gap we fill:** Our dataset covers 2020–2024 multi-platform dynamics; the 2007–08 episode was largely single-vector (SMS/radio). We provide the first systematic cross-platform typology for the region at scale.

---

### [Mutahi & Kimari (2017)] — The Impact of Social Media and Digital Technology on Electoral Violence in Kenya

- **Citation:** Mutahi, P. and Kimari, B. (2017). *The Impact of Social Media and Digital Technology on Electoral Violence in Kenya*. IDS Working Paper Vol. 2017, No. 493. Brighton: Institute of Development Studies / Centre for Human Rights and Policy Studies (CHRIPS). Available at: https://www.chrips.or.ke/wp-content/uploads/2017/08/The-impact-of-social-media-and-digital-technology-on-electoral-violence-in-kenya.pdf
- **Key finding:** Dual-use finding: digital platforms simultaneously amplified hate speech and enabled violence monitoring/mapping. Email and SMS spread inflammatory speech and rumors in the 2007 cycle; by 2013 and 2017, Twitter and Facebook carried ethno-political attacks at higher velocity. The study notes a 2017 increase in coordinated tribal hate speech.
- **Relevance to Paper D:** The most comprehensive academic treatment of Kenya across three electoral cycles (2007, 2013, 2017). Provides the comparative baseline our paper extends to 2022.
- **Gap we fill:** Mutahi & Kimari rely on qualitative coding and case studies. Our automated pipeline classifies toxicity at volume across 2022 content with sub-type granularity (dehumanisation vs. incitement vs. threat).

---

### [iHub Research / Ushahidi (2013)] — Umati: Monitoring Online Dangerous Speech

- **Citation:** iHub Research and Ushahidi. (2013). *Umati: Monitoring Online Dangerous Speech — Final Report*. Nairobi: iHub Research. Phase 1: September 2012–May 2013; Phase 2: extended through November 2013. Available at: https://www.ushahidi.com/about/blog/umati-final-report-released and via Scribd: https://www.scribd.com/document/126741671/Umati-Monitoring-Online-Dangerous-Speech
- **Key finding:** Between October 2012 and November 2013, up to 11 monitors scanned online content in seven languages (English, Kiswahili, Kikuyu, Luhya, Kalenjin, Luo, Sheng, and Somali) across blogs, forums, online newspapers, Facebook, and Twitter ahead of Kenya's March 2013 elections. Inflammatory speech exceeded expectations, particularly in the weeks surrounding the election. Crucially, online hate speech was not found to be a reliable sole predictor of ground violence — it is a window into offline conversations, not a direct trigger.
- **Relevance to Paper D:** Pioneer East African effort at structured online dangerous-speech monitoring. Establishes Benesch's "dangerous speech" framework (see Section 2) as the regional methodological baseline and demonstrates vernacular-language monitoring is essential.
- **Gap we fill:** Umati was human-annotator dependent (up to 11 monitors). Our pipeline scales this via automated NLP classification across six East African countries simultaneously. We also extend the language coverage and quantify platform-level variation.

---

### [ISD Global (2021)] — Polarising Content and Hate Speech Ahead of Kenya's 2022 Elections

- **Citation:** Institute for Strategic Dialogue (ISD). (2021). *Polarising Content and Hate Speech Ahead of Kenya's 2022 Elections: Challenges and Ways Forward*. London: ISD. Published 25 November 2021. Available at: https://www.isdglobal.org/isd-publications/polarising-content-and-hate-speech-ahead-of-kenyas-2022-elections-challenges-and-ways-forward/
- **Key finding:** Analysis of the Kenyan digital landscape found discourse saturated with ethno-tribal hate narratives and stereotyping along ethnic lines. Responses to online hate speech had not matched the scale of harmful narratives being presented in public fora with millions of subscribers. The COVID-19 pandemic exacerbated inter-religious intolerance. The 2022 election cycle showed a 20% increase in hate speech on social media relative to 2017.
- **Relevance to Paper D:** Provides a pre-election benchmark for 2022 — the most recent Kenyan electoral cycle covered in our dataset. Documents the normalisation risk when harmful content appears in large public channels.
- **Gap we fill:** ISD's analysis is primarily qualitative narrative analysis. Our paper provides quantitative frequency and severity distributions, temporal surge patterns around specific campaign events, and platform-level breakdowns for 2022.

---

### [Global Witness & Foxglove (2022)] — Facebook Unable to Detect Hate Speech Ahead of Kenyan Election

- **Citation:** Global Witness and Foxglove. (2022). *Facebook Unable to Detect Hate Speech Weeks Away from Tight Kenyan Election*. London: Global Witness. Published 5 August 2022. Available at: https://www.globalwitness.org/en/campaigns/digital-threats/hate-speech-kenyan-election/
- **Key finding:** In an undercover investigation, Global Witness submitted 20 hate speech ads in English and Kiswahili to Facebook's ad platform ahead of Kenya's August 2022 election. The platform approved the overwhelming majority, demonstrating a near-total failure of automated content moderation in both of Kenya's official languages.
- **Relevance to Paper D:** Empirical, near-contemporaneous evidence of platform moderation failure in the Kenya 2022 context — the same electoral window covered by our dataset. Supports our argument that platform governance gaps are structural, not incidental.
- **Gap we fill:** Global Witness focused on ad-platform moderation of submitted test content. We analyse organically posted content at scale, capturing the full spectrum of hate speech types circulating in the broader Kenyan information environment during 2022.

---

### [Meleagrou-Hitchens & Maher (2012)] — Lights, Camera, Jihad: Al-Shabaab's Western Media Strategy

- **Citation:** Meleagrou-Hitchens, A. and Maher, S. (2012). *Lights, Camera, Jihad: Al-Shabaab's Western Media Strategy*. London: International Centre for the Study of Radicalisation (ICSR), King's College London. Available at: https://icsr.info/wp-content/uploads/2012/11/ICSR-Report-Lights-Camera-Jihad-al-Shabaab%E2%80%99s-Western-Media-Strategy.pdf
- **Key finding:** Al-Shabaab developed a sophisticated, centrally managed digital communications strategy using high-quality video production, Twitter, and culturally resonant messaging targeting Somali diaspora and Western Muslims. Content was carefully calibrated to serve propaganda, recruitment, and fundraising functions simultaneously.
- **Relevance to Paper D:** Establishes the counter-terrorism/extremist propaganda dimension of East African online hate. Al-Shabaab content constitutes a distinct sub-category in our dataset (religiously framed incitement vs. ethnically framed electoral hate speech) requiring separate analytical treatment.
- **Gap we fill:** Meleagrou-Hitchens & Maher analysed strategic intent and content quality. Our paper documents current-period volume, platform distribution, and overlap/interaction between Al-Shabaab-adjacent content and electoral hate speech in coastal Kenya and the Somali border regions.

---

### [CIPESA (2025)] — Social Media's Role in Hate Speech: South Sudan

- **Citation:** Collaboration on International ICT Policy for East and Southern Africa (CIPESA). (2025). "Social Media's Role in Hate Speech: A Double-Edged Sword for South Sudan." Kampala: CIPESA. Available at: https://cipesa.org/2025/02/social-medias-role-in-hate-speech-a-double-edged-sword-for-south-sudan/
- **Key finding:** Monitoring data found that 50.5% of online content in South Sudan contained misinformation or disinformation, while 39.9% was classified as hate speech. Facebook dominates the South Sudanese information environment and carries the highest share of harmful content. Diaspora communities in Australia and the US amplify content back into South Sudan via WhatsApp and Facebook at high speed.
- **Relevance to Paper D:** Provides the South Sudan comparison case for our multi-country analysis. Confirms the transnational amplification loop (diaspora → homeland) that appears in our data.
- **Gap we fill:** CIPESA reports aggregate prevalence rates but does not break down hate speech by sub-type, severity level, or temporal pattern. Our pipeline provides all three dimensions, enabling cross-country comparison on standardised metrics.

---

### [CMI / Herrmann (2023)] — Digital Warfare: Social Media in Sudan's Conflict Landscape

- **Citation:** Herrmann, I. (2023). *Digital Warfare: Exploring the Influence of Social Media in Propagating and Counteracting Hate Speech in Sudan's Conflict Landscape*. Bergen: Chr. Michelsen Institute (CMI). Available at: https://www.cmi.no/publications/9610-digital-warfare-exploring-the-influence-of-social-media-in-propagating-and-counteracting-hate
- **Key finding:** Social media accelerated the spread of dehumanising and ethnically inflammatory content during the Sudan Armed Forces–RSF conflict. Platforms served as both weapons (spreading incitement) and counter-weapons (amplifying human rights documentation). Content moderation was largely absent in Arabic-language contexts.
- **Relevance to Paper D:** The Sudan case illustrates the active-conflict phase of the hate-speech-to-violence pipeline, relevant when contextualising our East Africa data against the most severe end of the spectrum.
- **Gap we fill:** Our analysis sits upstream — early warning and pattern detection — rather than in active-conflict documentation. Sudan provides the "worst case" comparator.

---

## 2. Online Hate Speech and Violence Linkage

### [Yanagizawa-Drott (2014)] — Propaganda and Conflict: Evidence from the Rwandan Genocide

- **Citation:** Yanagizawa-Drott, D. (2014). "Propaganda and Conflict: Evidence from the Rwandan Genocide." *The Quarterly Journal of Economics*, 129(4), 1947–1994. Available at: https://yanagizawadrott.com/wp-content/uploads/2016/02/rwandadyd.pdf
- **Key finding:** Using radio propagation software and Rwanda's topography as an instrument for exogenous variation in RTLM radio reception, the study estimates that approximately 51,000 perpetrators (roughly 10% of total violence) can be attributed to RTLM broadcasts. Importantly, spillover effects — villages with coverage inciting neighbouring villages without — exceeded direct effects. Broadcasts influenced both militia and ordinary civilian violence.
- **Relevance to Paper D:** The methodological gold standard for causal identification of hate media → violence effects. Establishes the mechanism we invoke when linking platform-amplified hate speech to offline violence risk.
- **Gap we fill:** Yanagizawa-Drott analyses a pre-internet, single-medium context. Our paper documents multi-platform digital dynamics where network effects, algorithmic amplification, and cross-platform migration create spillover patterns qualitatively different from broadcast radio.

---

### [Müller & Schwarz (2021)] — Fanning the Flames of Hate: Social Media and Hate Crime

- **Citation:** Müller, K. and Schwarz, C. (2021). "Fanning the Flames of Hate: Social Media and Hate Crime." *Journal of the European Economic Association*, 19(4), 2131–2167. https://doi.org/10.1093/jeea/jvaa045
- **Key finding:** Anti-refugee Facebook posts predict hate crimes against refugees across otherwise comparable German municipalities. Causality is established by exploiting exogenous variation from Facebook and internet outages. Right-wing social media posts show narrower, more loaded content than news media, consistent with echo-chamber mechanisms. A 1 standard deviation increase in Facebook usage is associated with a significant increase in anti-refugee hate crimes.
- **Relevance to Paper D:** The most rigorous causal identification of social media → offline hate crime in a contemporary context. We cite this as the evidentiary anchor for our violence-linkage argument.
- **Gap we fill:** Müller & Schwarz examine a high-income, high-internet-penetration context with robust policing data. Our paper addresses lower-resource East African contexts where violence reporting is incomplete, requiring us to model risk rather than observed outcomes directly. We also address multi-ethnic (not just anti-refugee) dynamics.

---

### [Benesch (2012; 2014)] — Dangerous Speech Framework

- **Citation (2012):** Benesch, S. (2012). "Dangerous Speech: A Proposal to Prevent Group Violence." *World Policy Journal* / Dangerous Speech Project Working Paper. Available at: http://worldpolicy.org/projects/dangerous-speech-along-the-path-to-mass-violence/
- **Citation (2014):** Benesch, S. (2014). *Countering Dangerous Speech: New Ideas for Genocide Prevention*. Working Paper. United States Holocaust Memorial Museum, Washington, DC. February 2014. Available at: https://www.ushmm.org/m/pdfs/20140212-benesch-countering-dangerous-speech.pdf
- **Key finding:** Dangerous speech is a subset of hate speech — any expression that can increase the risk that its audience will condone or participate in violence against members of another group. The framework defines dangerousness via five variables: speaker influence, audience susceptibility, the speech act itself, historical/social context, and means of dissemination. This moves analysis from categorical ("is this hate speech?") to risk-weighted ("how dangerous is this speech act in this context?").
- **Relevance to Paper D:** The Benesch framework is the conceptual foundation adopted by the Umati project and is influential in East African practitioner circles. We align our sub-type taxonomy with her framework to maximise policy relevance.
- **Gap we fill:** Benesch's framework is qualitative and analytical. Our paper operationalises it at scale via automated classification, quantifying the distribution of speech acts across her five dangerousness dimensions.

---

### [UN Office on Genocide Prevention (2014)] — Framework of Analysis for Atrocity Crimes

- **Citation:** United Nations Office on Genocide Prevention and the Responsibility to Protect. (2014). *Framework of Analysis for Atrocity Crimes: A Tool for Prevention*. New York: United Nations. Available at: https://www.un.org/en/genocideprevention/documents/about-us/Doc.3_Framework%20of%20Analysis%20for%20Atrocity%20Crimes_EN.pdf
- **Key finding:** The Framework identifies common and specific risk factors for genocide, crimes against humanity, and war crimes, using structured risk indicators to enable early warning. It emphasises that atrocity crimes rarely happen suddenly — they develop over time through identifiable precursor patterns. Hate speech and incitement are listed among the primary common risk factors.
- **Relevance to Paper D:** Provides the international normative and analytical framework within which our findings should be interpreted by policymakers. Links our hate speech data to the atrocity prevention architecture.
- **Gap we fill:** The UN Framework is qualitative and indicator-based. Our paper provides quantitative, real-time digital signals that could serve as automated proxy indicators for the Framework's risk factors in the East African context.

---

## 3. Platform Governance in the Global South

### [UN Fact-Finding Mission on Myanmar (2018)] — Report on Myanmar / Role of Facebook

- **Citation:** United Nations Human Rights Council. (2018). *Report of the Independent International Fact-Finding Mission on Myanmar*. UN Doc. A/HRC/39/64. Geneva: OHCHR. September 2018. Available at: https://www.ohchr.org/en/hr-bodies/hrc/myanmar-ffm/report
- **Key finding:** The Fact-Finding Mission concluded that Facebook played a "determining role" in spreading hate speech and incitement to violence against the Rohingya. The platform's algorithms amplified anti-Rohingya content while the company failed to act on repeated warnings from civil society (2012–2017). Over 700,000 Rohingya were displaced in August 2017 following security force operations preceded by sustained online dehumanisation.
- **Relevance to Paper D:** The global reference case for platform complicity in atrocity-adjacent hate speech. Establishes the pattern — platform inaction, algorithm-driven amplification, civil society warnings ignored — that we document in East African contexts.
- **Gap we fill:** Myanmar is a single-country, single-language (Burmese), single-platform case study. Our paper provides a multi-country, multi-language, multi-platform comparison that tests which elements of the Myanmar pattern are generalisable to East Africa.

---

### [Amnesty International (2023)] — A Death Sentence for My Father: Meta's Contribution to Human Rights Abuses in Northern Ethiopia

- **Citation:** Amnesty International. (2023). *"A Death Sentence for My Father": Meta's Contribution to Human Rights Abuses in Northern Ethiopia*. London: Amnesty International. Doc. AFR25/7292/2023. Published 31 October 2023. Available at: https://www.amnesty.org/en/documents/afr25/7292/2023/en/
- **Key finding:** Meta's algorithmic systems supercharged the spread of dehumanising rhetoric targeting the Tigrayan community during the 2020–2022 conflict. Meta began developing Amharic and Oromo moderation capabilities only at the end of 2020 — approximately 15 years after becoming operational in Ethiopia. A specific documented case: a post naming, photographing, and giving the home address of a Tigrayan chemistry professor was shared 900+ times before removal; he was subsequently killed.
- **Relevance to Paper D:** The most methodologically detailed documentation of East African platform failure, directly analogous to patterns we observe in our dataset. Demonstrates the causal chain from algorithmic amplification to documented physical harm.
- **Gap we fill:** Amnesty's investigation is retrospective and case-study based. Our pipeline operates prospectively, providing early warning signals before incidents escalate to the violence documented in the Amnesty report.

---

### [CFR / Williams (2021)] — Facebook's Content Moderation Failures in Ethiopia

- **Citation:** Williams, J. (2021). "Facebook's Content Moderation Failures in Ethiopia." *Council on Foreign Relations (CFR) Think Global Health Blog*. Published December 2021. Available at: https://www.cfr.org/blog/facebooks-content-moderation-failures-ethiopia
- **Key finding:** Analysis of the "Facebook Files" leak demonstrates Facebook's chronic under-investment in non-English content moderation. The company could not keep pace with the volume of hate speech in Ethiopian languages. Political and financial constraints led to repeated deprioritisation of African markets in moderation capacity planning.
- **Relevance to Paper D:** Provides the institutional/structural explanation for platform failures — not incidental error but systematic under-resourcing of African-language moderation.
- **Gap we fill:** CFR analysis covers Ethiopia in isolation. Our multi-country framing shows this is a structural, pan-regional problem, not an Ethiopia-specific anomaly.

---

### [Center for Democracy & Technology (2022)] — Content Moderation in the Global South

- **Citation:** Center for Democracy and Technology (CDT). (2022). *Content Moderation in the Global South: A Comparative Study of Four Low-Resource Languages*. Washington, DC: CDT. Available at: https://cdt.org/insights/content-moderation-in-the-global-south-a-comparative-study-of-four-low-resource-languages/
- **Key finding:** An 18-month comparative study of content moderation across four low-resource languages (including Kiswahili) found consistent moderation failure: harmful content in under-resourced languages was systematically missed, and users experienced inconsistent enforcement. Colonial legacies, authoritarian government pressures, and lack of local investment compounded the problem.
- **Relevance to Paper D:** Directly documents Kiswahili moderation failure — one of the primary languages in our dataset. Provides external validation of the moderation gap we observe empirically.
- **Gap we fill:** CDT's methodology focused on user experience and platform policy auditing. Our paper provides content-level quantitative evidence from the Kiswahili information environment that maps onto CDT's structural findings.

---

### [Matamoros-Fernández & Farkas (2021)] — Racism, Hate Speech, and Social Media: A Systematic Review

- **Citation:** Matamoros-Fernández, A. and Farkas, J. (2021). "Racism, Hate Speech, and Social Media: A Systematic Review and Critique." *Television & New Media*, 22(2), 205–224. https://doi.org/10.1177/1527476420982230
- **Key finding:** Systematic review found that only 0.96% of academic research on racism and hate speech on social media focused on Africa (compared to 44.23% for North America). Existing research is heavily biased toward English-language content and high-income country contexts. The review calls urgently for more research on underrepresented global contexts.
- **Relevance to Paper D:** Quantifies the research gap our paper helps fill. Can be cited to justify the significance of an East Africa-focused empirical study.
- **Gap we fill:** Our paper directly addresses the geographic and linguistic underrepresentation this review identifies.

---

## 4. Conflict Early Warning and Digital Tools

### [Raleigh, Linke, Hegre & Karlsen (2010)] — Introducing ACLED

- **Citation:** Raleigh, C., Linke, A., Hegre, H. and Karlsen, J. (2010). "Introducing ACLED: An Armed Conflict Location and Event Dataset." *Journal of Peace Research*, 47(5), 651–660. https://doi.org/10.1177/0022343310378914
- **Key finding:** ACLED codes the type, agents, location, date, and characteristics of political violence events, transfers of military control, and civilian violence. Originally covering 50 unstable countries from 1997–2010, it has since expanded to global coverage. The dataset enables systematic spatial and temporal analysis of conflict patterns.
- **Relevance to Paper D:** ACLED provides the conflict event ground truth we use to contextualise hate speech surges. Spikes in our hate speech data can be compared against ACLED conflict events to assess lead/lag relationships.
- **Gap we fill:** ACLED captures conflict events after they occur. Our pipeline captures upstream digital signals. Comparing our hate speech temporal distributions with ACLED events allows us to test whether digital hate speech patterns precede conflict escalation.

---

### [ICG (2016)] — Seizing the Moment: From Early Warning to Early Action

- **Citation:** International Crisis Group (ICG). (2016). *Seizing the Moment: From Early Warning to Early Action*. Brussels/Nairobi: ICG. Available at: https://www.crisisgroup.org/global/seizing-moment-early-warning-early-action
- **Key finding:** ICG's strategic framework for preventive diplomacy argues that effective early warning requires close analysis of conflict dynamics, sensitive political relationships in affected countries, and "framework diplomacy" with regional powers. The organisation's CrisisWatch bulletin monitors 70+ conflicts monthly for escalation signals and opportunities for de-escalation.
- **Relevance to Paper D:** ICG is a primary consumer of the type of early warning signals our pipeline produces. Framing our findings within ICG's early warning/early action model maximises policy uptake.
- **Gap we fill:** ICG's methodology is expert-judgment-driven and field-based. Our digital monitoring layer provides real-time, scalable signals that can complement (not replace) ICG's analytical process.

---

### [Raleigh & ACLED (2023)] — ACLED Codebook and Methodology

- **Citation:** Armed Conflict Location & Event Data Project (ACLED). (2023). *ACLED Codebook 2023*. Available at: https://acleddata.com/knowledge-base/codebook/
- **Key finding:** Provides the operational definitions, coding rules, and data collection methodology underpinning ACLED's conflict event dataset. Event typology includes battles, explosions/remote violence, violence against civilians, riots, protests, and strategic developments.
- **Relevance to Paper D:** Methodological reference for any analysis that correlates our hate speech data with ACLED conflict events.
- **Gap we fill:** Not applicable — this is a methodological reference document.

---

### [ViEWS / Hegre et al. (2019)] — ViEWS: A Political Violence Early Warning System

- **Citation:** Hegre, H. et al. (2019). "ViEWS: A Political Violence Early Warning System." *Journal of Peace Research*, 56(2), 155–174. https://doi.org/10.1177/0022343319823860
- **Key finding:** ViEWS generates probabilistic monthly forecasts of political violence at the country and 55×55 km grid-cell level for Africa. The system combines machine learning with conflict history, development indicators, and event data (including ACLED). It demonstrates that data-driven forecasting can achieve meaningful predictive accuracy for conflict onset and escalation 3–6 months ahead.
- **Relevance to Paper D:** ViEWS is the state-of-the-art quantitative early warning benchmark. Positioning our digital hate speech pipeline in relation to ViEWS clarifies its complementary niche: ViEWS uses lagged structural indicators; we contribute near-real-time digital behavioural signals.
- **Gap we fill:** ViEWS does not incorporate social media or online discourse data. Our pipeline provides a digital signal layer that could in principle be integrated with ViEWS-style forecasting architectures.

---

### [Mercy Corps / Robbins (2019)] — The Weaponization of Social Media

- **Citation:** Robbins, C. (2019). *The Weaponization of Social Media: How to Recognise, Prevent and Respond*. Portland, OR: Mercy Corps. Published November 2019. Available at: https://www.mercycorps.org/sites/default/files/2020-01/Weaponization_Social_Media_FINAL_Nov2019.pdf
- **Key finding:** Practitioner framework for NGOs and peacebuilding organisations responding to weaponised social media in conflict contexts. Identifies five pathways by which social media contributes to violence: spreading disinformation, amplifying propaganda, coordinating violence, suppressing dissent, and undermining trust in institutions. Emphasises the need for real-time monitoring capacity.
- **Relevance to Paper D:** Bridges academic findings and practitioner response frameworks. Directly relevant for our policy recommendations section.
- **Gap we fill:** Mercy Corps' framework is prescriptive and based on case examples. Our paper provides quantitative evidence that would allow organisations to prioritise which pathways are most active in specific East African contexts.

---

## 5. Methodological and Conceptual Notes

### On Citation Confidence

All citations in this document were verified through web searches against publisher databases, DOI links, institutional repositories, and primary source PDFs. No citations have been fabricated. Where author names or page numbers could not be confirmed with certainty, this is noted or the citation is given at the level of confidence that can be verified (e.g., institutional report without confirmed individual author).

### Key Gaps in the Literature

1. **No peer-reviewed study** provides a multi-country, multi-platform, automated hate speech classification for East Africa at the scale our paper covers. Existing work is either single-country (Kenya), qualitative, or limited to one electoral cycle.
2. **Vernacular language coverage** remains a persistent gap. Only the Umati project and CDT's Kiswahili study provide non-English East African analysis.
3. **Causal identification** between online hate speech and offline violence remains unestablished for East Africa specifically. Müller & Schwarz (Germany) and Yanagizawa-Drott (Rwanda/radio) provide the causal frameworks; our paper can test whether the patterns are consistent with those mechanisms without claiming equivalent causal identification.
4. **Platform-comparative analysis** across Facebook, Twitter/X, TikTok, and WhatsApp simultaneously is absent from the existing East African literature.

---

## Quick Reference List

| Citation | Year | Topic | Sections Used |
|----------|------|-------|---------------|
| Kiai (2008) | 2008 | Kenya 2007–08 hate speech/SMS | Background |
| Mutahi & Kimari (2017) | 2017 | Kenya social media electoral violence | Background, Methods |
| iHub/Ushahidi — Umati (2013) | 2013 | Kenya dangerous speech monitoring | Methods, Discussion |
| ISD Global — Kenya 2022 (2021) | 2021 | Kenya 2022 election hate speech | Findings |
| Global Witness & Foxglove (2022) | 2022 | Facebook moderation failure Kenya | Findings, Policy |
| Meleagrou-Hitchens & Maher (2012) | 2012 | Al-Shabaab digital strategy | Background |
| CIPESA (2025) | 2025 | South Sudan online hate speech | Findings |
| CMI / Herrmann (2023) | 2023 | Sudan social media conflict | Background |
| Yanagizawa-Drott (2014) | 2014 | RTLM radio Rwanda genocide | Theory |
| Müller & Schwarz (2021) | 2021 | Facebook hate crime Germany | Theory, Discussion |
| Benesch (2012; 2014) | 2012/14 | Dangerous speech framework | Methods |
| UN OSAPG (2014) | 2014 | UN Framework atrocity prevention | Policy |
| UN FFM Myanmar (2018) | 2018 | Facebook/Myanmar genocide | Discussion, Policy |
| Amnesty International (2023) | 2023 | Meta/Ethiopia Tigray | Discussion, Policy |
| CFR / Williams (2021) | 2021 | Facebook moderation Ethiopia | Discussion |
| CDT (2022) | 2022 | Content moderation Global South | Methods, Discussion |
| Matamoros-Fernández & Farkas (2021) | 2021 | Research gap — Africa | Justification |
| Raleigh et al. (2010) | 2010 | ACLED methodology | Methods |
| ICG (2016) | 2016 | Early warning/early action | Policy |
| ACLED Codebook (2023) | 2023 | Conflict data reference | Methods |
| Hegre et al. / ViEWS (2019) | 2019 | Political violence forecasting | Discussion |
| Mercy Corps / Robbins (2019) | 2019 | Social media weaponisation | Policy |
