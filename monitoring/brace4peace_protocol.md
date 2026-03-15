# BRACE4PEACE Monitoring Protocol

## Overview
Daily automated monitoring for hate speech, disinformation, and violent extremism (VE) narratives across East Africa — covering South Sudan, Kenya, and Somalia, with dedicated Al-Shabaab media tracking.

## Schedule
- **Frequency**: Daily at 06:00 UTC
- **Sources**: Web search, direct URL fetches (X/Twitter social search when available)
- **Alert threshold**: Only genuinely NEW intelligence beyond the rolling baseline

---

## Step 1: X/Twitter Social Media Searches

### South Sudan (P1 - CRITICAL)
1. `"South Sudan" hate speech OR ethnic cleansing OR genocide`
2. `Jonglei violence OR displacement OR SSPDF`
3. `"Johnson Olony" OR "spare no lives"`
4. `Machar trial OR treason OR "political prisoner" South Sudan`
5. `"Dinka" "Nuer" kill OR attack OR revenge`
6. `from:EyeRadioJuba`

### Kenya (P1)
7. `Kenya hate speech OR ethnic incitement OR NCIC`
8. `"Linda Mwananchi" violence OR protest`
9. `Kenya 2027 election OR tribal rhetoric`
10. `Al-Shabaab Kenya OR Nairobi attack OR plot`
11. `from:CapitalFMKenya`

### Somalia (P1)
12. `Al-Shabaab attack OR execute OR kill civilians`
13. `Somalia clan hate OR "Abgaalistan" OR tribal`
14. `NISA raid OR operation OR Al-Shabaab killed`
15. `from:GaroweOnline`
16. `from:DalsanTv`
17. `from:MowliidHaji`

### Al-Shabaab Media & Propaganda (P1)
18. `"Shahada News" OR shahadanews OR "Al-Kataib" al-Shabaab`
19. `"Radio Andalus" OR "Radio al-Andalus" OR "Radio Furqaan" Somalia`
20. `Calamada OR Somalimemo al-Shabaab propaganda`
21. `Al-Shabaab Telegram OR recruitment OR "pledge allegiance"`
22. `Al-Shabaab video OR execution OR claim attack 2026`

### Cross-Cutting (P2)
23. `East Africa hate speech OR disinformation`
24. `ISIS Africa deepfake OR AI recruitment`

---

## Step 2: Web Source Monitoring

### Institutional & News Sources
| Source | Query |
|--------|-------|
| ACLED | `"ACLED" East Africa conflict analysis 2026` |
| HRW | `site:hrw.org South Sudan OR Kenya OR Somalia` |
| UNMISS | `site:unmiss.unmissions.org hate speech OR violence OR displacement` |
| Eye Radio | `site:eyeradio.org violence OR hate speech OR Jonglei OR Machar` |
| Garowe Online | `site:garoweonline.com Al-Shabaab OR clan OR hate speech` |
| Capital FM Kenya | `site:capitalfm.co.ke hate speech OR NCIC OR protest OR election` |
| Radio Tamazuj | `site:radiotamazuj.org South Sudan violence OR displacement` |
| defyhatenow | `site:defyhatenow.org South Sudan OR hate speech` |
| ReliefWeb | `site:reliefweb.int South Sudan OR Kenya OR Somalia hate speech OR violence` |
| Al Jazeera | `site:aljazeera.com South Sudan OR Somalia OR Kenya violence OR conflict 2026` |

### Al-Shabaab Media Monitoring
| Source | Query |
|--------|-------|
| Shahada News | `"Shahada News Agency" Al-Shabaab claim attack 2026` |
| Al-Kataib | `"Al-Kataib" media Al-Shabaab video propaganda 2026` |
| Radio Andalus | `"Radio Andalus" Somalia broadcast Al-Shabaab 2026` |
| Calamada/Somalimemo | `Calamada.com OR Somalimemo Somalia Al-Shabaab 2026` |
| Telegram | `"Al-Shabaab" propaganda Telegram recruitment 2026` |
| Tech Against Terrorism | `"Tech Against Terrorism" Al-Shabaab content removal 2026` |

### Dedicated Analysis Sources
| Source | Query |
|--------|-------|
| CTC West Point | `site:ctc.westpoint.edu Al-Shabaab Somalia 2026` |
| Terrorism Info | `site:terrorism-info.org.il Al-Shabaab Somalia` |
| ADF Magazine | `site:adf-magazine.com Al-Shabaab Somalia 2026` |
| Long War Journal | `"Long War Journal" Al-Shabaab Somalia attack` |
| CFR | `site:cfr.org Al-Shabaab Somalia conflict tracker` |
| Critical Threats | `"Critical Threats" Al-Shabaab Somalia` |

---

## Step 3: Direct URL Fetches
- https://www.eyeradio.org — South Sudan headlines
- https://www.garoweonline.com/en/news — Somalia headlines
- https://acleddata.com/ — ACLED homepage
- https://ctc.westpoint.edu — CTC Sentinel
- https://www.longwarjournal.org/ — Long War Journal
- https://www.criticalthreats.org/ — Critical Threats

---

## Step 4: Narrative Classification

### BRACE4PEACE Narrative Families
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

### Al-Shabaab-Specific Categories
- Attack Claim
- Recruitment
- Anti-Government Narrative
- Religious Justification
- Counter-Narrative Response
- Social Media Expansion

---

## Step 5: Alert Decision

### Escalation Criteria
| Priority | Description | Action |
|----------|-------------|--------|
| P1 CRITICAL | Genocidal rhetoric, imminent mass violence, direct incitement, major Al-Shabaab attack claim | ALWAYS notify |
| P2 HIGH | Systematic HS campaigns, VE recruitment, large-scale disinfo | Notify if new/escalating |
| P3 MODERATE | Escalating rhetoric, delegitimization trends | Only notify if notable shift |

### Notification Format
- **Title**: `[COUNTRY] [THREAT LEVEL] — [Brief description]`
- **Body**: Source URLs, detecting source, narrative classification
- **Schedule label**: "Checking daily at 06:00 UTC"
