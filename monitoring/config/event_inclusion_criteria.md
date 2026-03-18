# Event Inclusion Criteria

## What qualifies as a timeline event

An event enters the BRACE4PEACE timeline (events.json) when it meets ALL of:

1. **Content-based**: It describes specific disinformation CONTENT — false claims, propaganda, or coordinated campaigns
2. **Confidence**: HIGH or MEDIUM confidence classification (LOW never enters timeline)
3. **Verifiability**: The false claim can be identified and described
4. **Regional relevance**: Directly about Somalia, South Sudan, Kenya, or East Africa

## What does NOT qualify

- News reports ABOUT disinformation (these are CONTEXT events, separate track)
- Counter-speech or fact-checks (these are responses, not events)
- Generic hate speech without false claims (goes to HS pipeline instead)
- Low confidence findings (stay in daily findings for human review)

## Event Types

| Type | Description | Example |
|------|-------------|---------|
| DISINFO | False claims or coordinated campaigns | "#43Against1 claims Kikuyu leadership is tribalist" |
| CONTEXT | Background events that provide context | "Tech Against Terrorism issues report on al-Shabaab online" |

## The Bridge Test

Is the primary substance CONTENT or ACTION?
- CONTENT (false claims being spread) → PRIMARY event (DISINFO)
- ACTION (military operation, political event) → CONTEXT only
- ACTION that generates documented CONTENT → split into two entries

## Threat Levels

| Level | Criteria |
|-------|----------|
| P1 CRITICAL | Imminent physical threat, mass coordination, VE attack planning |
| P2 HIGH | Confirmed high-confidence disinfo/VE propaganda, active coordinated campaigns |
| P3 MODERATE | Medium confidence findings, emerging patterns |
