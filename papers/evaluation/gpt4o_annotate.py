#!/usr/bin/env python3
"""
GPT-4o Blind Annotation Script

Loads posts from papers/evaluation/sample_blind.json and sends them to GPT-4o
for classification using the IRIS hate speech taxonomy.

Saves results to papers/evaluation/gpt4o_annotations.json with intermediate
checkpoints every 50 posts for crash recovery.
"""

import json
import os
import sys
from pathlib import Path
from typing import Optional
import time

from openai import OpenAI, APIError

# Configuration
BATCH_SIZE = 50
TEMPERATURE = 0
MODEL = "gpt-4o"

# System prompt defining the taxonomy and task
SYSTEM_PROMPT = """You are an expert hate speech classifier. Your task is to classify social media posts according to the IRIS hate speech taxonomy.

## Classification Task

For each post, provide:
1. **classification**: One of "Normal", "Abusive", or "Hate"
2. **subtype**: One of the 8 subtypes (or null if Normal)
3. **confidence**: "Low", "Medium", or "High"
4. **reasoning**: Brief explanation of your classification

## Definitions

### Classifications

**Normal** — Neutral, informational, or positive content. No harmful language targeting individuals or groups. Includes news reporting, factual statements, and peace-building content.

**Abusive** — Contains profanity, insults, disrespect, or aggressive language, but does NOT target individuals or groups based on their identity (ethnicity, religion, clan, nationality, gender). Example: general insults directed at a specific person's actions, not their group identity.

**Hate** — Content that attacks, dehumanizes, or incites violence against individuals or groups based on protected identity characteristics: ethnicity, religion, clan, nationality, or gender. Includes direct threats, dehumanizing language, calls for exclusion, and incitement to discrimination or violence.

### Subtypes (assign one if Abusive or Hate)

- **Ethnic Targeting**: Targets specific ethnic groups (e.g., Nuer, Dinka, Kikuyu, Luo, Bantu)
- **Clan Targeting**: Targets specific clans (e.g., Hawiye, Darod, Isaaq — primarily Somalia)
- **Political Incitement**: Attacks political figures/parties based on identity, calls for political violence
- **Religious Incitement**: Targets religious groups or uses religious justification for violence
- **Dehumanisation**: Compares people to animals, vermin, disease; denies humanity
- **Anti-Foreign**: Targets foreigners, refugees, diaspora, or specific nationalities
- **General Abuse**: Abusive language not fitting other categories
- **Gendered Violence**: Targets based on gender; includes threats of sexual violence

## Important Notes

- Posts may be in English, Swahili, Somali, Arabic, or mixed. Classify based on meaning, not language.
- Context matters: A word that is hateful in one context may be neutral in another.
- If sarcastic but the intent is clearly hateful, classify as Hate.
- Reporting about hate speech is Normal, not Hate. The post must itself contain hate speech.

## Output Format

You MUST respond with valid JSON in this exact format:
{
  "classification": "Normal|Abusive|Hate",
  "subtype": "Ethnic Targeting|Clan Targeting|Political Incitement|Religious Incitement|Dehumanisation|Anti-Foreign|General Abuse|Gendered Violence|null",
  "confidence": "Low|Medium|High",
  "reasoning": "Brief explanation"
}"""

# Few-shot examples
FEW_SHOT_EXAMPLES = [
    {
        "role": "user",
        "content": 'Classify this post:\n\n"We should all come together for the upcoming elections and vote for positive change in our community. Democracy is the future."'
    },
    {
        "role": "assistant",
        "content": json.dumps({
            "classification": "Normal",
            "subtype": None,
            "confidence": "High",
            "reasoning": "Positive content about democracy and civic participation. No hateful or abusive language."
        })
    },
    {
        "role": "user",
        "content": 'Classify this post:\n\n"Those Kikuyu traders are parasites stealing our money. They need to be driven out of this region."'
    },
    {
        "role": "assistant",
        "content": json.dumps({
            "classification": "Hate",
            "subtype": "Ethnic Targeting",
            "confidence": "High",
            "reasoning": "Dehumanizing language (parasites) targeting Kikuyu ethnic group, calls for exclusion and violence."
        })
    },
    {
        "role": "user",
        "content": 'Classify this post:\n\n"You are a complete idiot for supporting that policy. Your opinion is worthless."'
    },
    {
        "role": "assistant",
        "content": json.dumps({
            "classification": "Abusive",
            "subtype": "General Abuse",
            "confidence": "High",
            "reasoning": "Contains insults and disrespect, but targets individual actions/opinions, not identity-based group membership."
        })
    }
]


def load_posts(input_file: str) -> list[dict]:
    """Load posts from sample_blind.json"""
    with open(input_file, "r") as f:
        posts = json.load(f)
    return posts


def load_existing_annotations(output_file: str) -> dict:
    """Load existing annotations to avoid re-processing"""
    if os.path.exists(output_file):
        with open(output_file, "r") as f:
            return json.load(f)
    return {}


def annotate_post(client: OpenAI, post_text: str) -> dict:
    """
    Send a post to GPT-4o for annotation.

    Returns a dict with keys: classification, subtype, confidence, reasoning
    """
    messages = FEW_SHOT_EXAMPLES.copy()
    messages.append({
        "role": "user",
        "content": f'Classify this post:\n\n"{post_text}"'
    })

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            system=SYSTEM_PROMPT,
            temperature=TEMPERATURE,
            response_format={"type": "json_object"},
            timeout=30
        )

        result = json.loads(response.choices[0].message.content)
        return result
    except APIError as e:
        raise Exception(f"OpenAI API error: {str(e)}")
    except json.JSONDecodeError as e:
        raise Exception(f"Failed to parse GPT-4o response as JSON: {str(e)}")


def process_posts(
    input_file: str,
    output_file: str,
    checkpoint_interval: int = BATCH_SIZE
) -> None:
    """
    Process posts and save annotations with checkpointing.

    Args:
        input_file: Path to sample_blind.json
        output_file: Path to save gpt4o_annotations.json
        checkpoint_interval: Save checkpoint every N posts
    """
    # Check for API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY environment variable not set")
        sys.exit(1)

    # Initialize client
    client = OpenAI(api_key=api_key)

    # Load posts and existing annotations
    posts = load_posts(input_file)
    annotations = load_existing_annotations(output_file)

    total_posts = len(posts)
    processed_count = len(annotations)

    print(f"Loaded {total_posts} posts from {input_file}")
    print(f"Found {processed_count} existing annotations")
    print(f"Processing {total_posts - processed_count} remaining posts...")

    for i, post in enumerate(posts):
        post_id = post.get("i")
        post_text = post.get("t", "")

        # Skip if already annotated
        if post_id in annotations:
            continue

        try:
            print(f"[{i+1}/{total_posts}] Annotating post {post_id}...", end=" ", flush=True)

            # Get annotation from GPT-4o
            annotation = annotate_post(client, post_text)

            # Add metadata
            result = {
                "post_id": post_id,
                "classification": annotation.get("classification"),
                "subtype": annotation.get("subtype"),
                "confidence": annotation.get("confidence"),
                "reasoning": annotation.get("reasoning"),
                "model": MODEL
            }

            annotations[post_id] = result
            print("✓")

            # Save checkpoint every N posts
            if (i + 1) % checkpoint_interval == 0:
                with open(output_file, "w") as f:
                    json.dump(annotations, f, indent=2)
                print(f"Saved checkpoint: {len(annotations)} annotations")

            # Small delay to avoid rate limiting
            time.sleep(0.1)

        except Exception as e:
            print(f"ERROR")
            result = {
                "post_id": post_id,
                "classification": "ERROR",
                "subtype": None,
                "confidence": None,
                "reasoning": f"Error during annotation: {str(e)}",
                "model": MODEL
            }
            annotations[post_id] = result
            continue

    # Final save
    with open(output_file, "w") as f:
        json.dump(annotations, f, indent=2)

    print(f"\nCompleted! Saved {len(annotations)} annotations to {output_file}")


if __name__ == "__main__":
    # Get the script directory to compute relative paths
    script_dir = Path(__file__).parent

    input_file = script_dir / "sample_blind.json"
    output_file = script_dir / "gpt4o_annotations.json"

    if not input_file.exists():
        print(f"ERROR: Input file not found: {input_file}")
        sys.exit(1)

    process_posts(str(input_file), str(output_file))
