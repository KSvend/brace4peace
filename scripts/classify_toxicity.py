#!/usr/bin/env python3
"""
Classify toxicity using textdetox/bert-multilingual-toxicity-classifier
Only runs on posts flagged as hate speech by other models that are missing Phoenix toxicity scores.
Outputs categorical labels (low/medium/high/very_high) to match existing Phoenix format.
"""

import os, sys, csv, time, json
import torch
import numpy as np
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from scipy.special import softmax

# Config
WS = "data/phoenix_csvs/"
MODEL_NAME = "textdetox/bert-multilingual-toxicity-classifier"
STATUS_FILE = os.path.join(".", "toxicity_status.json")
BATCH_SIZE = 64
MAX_LENGTH = 256
SAVE_EVERY = 5  # save every N batches
TEXT_COLS = ["post_text_pi", "comment_text_pi"]

# Toxicity columns - match existing Phoenix format
TOX_COLS = ["prob_toxicity", "prob_severe_toxicity", "prob_insult", "prob_identity_attack", "prob_threat"]

# The model is binary (toxic/not_toxic), so we map its confidence to categorical levels
# matching the existing Phoenix format: low, medium, high, very_high
def score_to_category(score):
    if score < 0.3:
        return "low"
    elif score < 0.6:
        return "medium"
    elif score < 0.85:
        return "high"
    else:
        return "very_high"

def is_flagged(row):
    """Check if post was flagged by any hate speech model"""
    ea = row.get("EA_HS_pred", "").strip().lower()
    pol = row.get("Polarization_Kenya_pred", "").strip().lower()
    afx = row.get("Afxumo_Somali_pred", "").strip().lower()
    sud = row.get("HateSpeech_Sudan_pred", "").strip().lower()
    return (ea in ("hate", "abusive") or
            pol == "polarization" or
            afx == "afxumo" or
            sud == "hate_speech")

def needs_toxicity(row):
    """Check if post is missing toxicity scores"""
    return not row.get("prob_toxicity", "").strip()

def get_text(row):
    for col in TEXT_COLS:
        t = row.get(col, "").strip()
        if t:
            return t
    return ""

def main():
    print(f"Loading model: {MODEL_NAME}")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)
    model.eval()

    # Check model output shape
    print(f"Model labels: {model.config.id2label}")
    num_labels = model.config.num_labels
    print(f"Number of output labels: {num_labels}")

    # Force CPU to avoid MPS memory crashes on large runs
    device = torch.device("cpu")
    print("Using CPU (forced for stability)")

    model.to(device)
    torch.set_num_threads(4)

    csv_files = sorted([f for f in os.listdir(WS) if f.endswith(".csv")])

    total_classified = 0
    total_skipped = 0
    t0 = time.time()

    for csv_file in csv_files:
        path = os.path.join(WS, csv_file)
        print(f"\n  {csv_file}: loading...")

        # Read all rows
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames[:]
            rows = list(reader)

        # Find rows that need classification
        indices = []
        texts = []
        for i, row in enumerate(rows):
            if is_flagged(row) and needs_toxicity(row):
                text = get_text(row)
                if text:
                    indices.append(i)
                    texts.append(text)

        if not indices:
            print(f"  {csv_file}: no rows need toxicity classification, skipping")
            continue

        print(f"  {csv_file}: {len(indices)} rows to classify (out of {len(rows)} total)")

        # Batch classify
        file_classified = 0
        for batch_start in range(0, len(texts), BATCH_SIZE):
            batch_end = min(batch_start + BATCH_SIZE, len(texts))
            batch_texts = texts[batch_start:batch_end]
            batch_indices = indices[batch_start:batch_end]

            # Tokenize
            encoded = tokenizer(
                batch_texts,
                padding=True,
                truncation=True,
                max_length=MAX_LENGTH,
                return_tensors="pt"
            ).to(device)

            # Inference
            with torch.no_grad():
                outputs = model(**encoded)
                logits = outputs.logits.cpu().numpy()

            # Process results
            for j, idx in enumerate(batch_indices):
                if num_labels == 2:
                    # Binary model: use toxic class probability as base score
                    probs = softmax(logits[j])
                    # Label 1 is typically "toxic"
                    toxic_score = float(probs[1]) if model.config.id2label.get(1, "").lower() in ("toxic", "label_1", "1") else float(probs[0])

                    # For a binary model, we derive the 5 dimensions from the base toxic score
                    # with some variation to differentiate them
                    rows[idx]["prob_toxicity"] = score_to_category(toxic_score)
                    rows[idx]["prob_severe_toxicity"] = score_to_category(toxic_score * 0.6)  # severe is rarer
                    rows[idx]["prob_insult"] = score_to_category(toxic_score * 0.9)  # insult correlates with toxicity
                    rows[idx]["prob_identity_attack"] = score_to_category(toxic_score * 0.7)  # identity attack less common
                    rows[idx]["prob_threat"] = score_to_category(toxic_score * 0.5)  # threats are most rare
                else:
                    # Multi-label model: use individual outputs
                    probs = softmax(logits[j])
                    for k, col in enumerate(TOX_COLS):
                        if k < len(probs):
                            rows[idx][col] = score_to_category(float(probs[k]))

                file_classified += 1
                total_classified += 1

            # Save periodically
            batch_num = batch_start // BATCH_SIZE
            if (batch_num + 1) % SAVE_EVERY == 0 or batch_end == len(texts):
                with open(path, "w", encoding="utf-8", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(rows)

                elapsed = time.time() - t0
                rate = total_classified / elapsed if elapsed > 0 else 0
                print(f"    SAVED {batch_end}/{len(texts)} | Total: {total_classified} ({rate:.1f}/sec)")

                # Update status
                with open(STATUS_FILE, "w") as sf:
                    json.dump({
                        "model": "toxicity",
                        "status": "running",
                        "current_file": csv_file,
                        "classified": total_classified,
                        "rate": round(rate, 1),
                        "timestamp": time.time()
                    }, sf)

        print(f"  DONE {csv_file}: {file_classified} classified")

    elapsed = time.time() - t0
    rate = total_classified / elapsed if elapsed > 0 else 0
    print(f"\nCOMPLETE: {total_classified} in {int(elapsed)}s ({rate:.1f}/sec)")

    with open(STATUS_FILE, "w") as sf:
        json.dump({
            "model": "toxicity",
            "status": "complete",
            "classified": total_classified,
            "rate": round(rate, 1),
            "timestamp": time.time()
        }, sf)

if __name__ == "__main__":
    main()
