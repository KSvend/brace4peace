"""
Fast classification: loads model once, processes all CSV files incrementally.
Uses torch threading + larger batch + reduced max_len for speed on CPU.
Saves progress every 5 batches (320 items). Incremental — skips already-classified rows.
"""
import sys, os, time, gc, json
import pandas as pd
import numpy as np
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from scipy.special import softmax

# Enable multi-threading
torch.set_num_threads(2)
torch.set_num_interop_threads(2)

MODELS = {
    'ea_hs': {
        'hf_name': 'KSvendsen/EA-HS',
        'pred_col': 'EA_HS_pred', 'conf_col': 'EA_HS_conf',
        'score_cols': ['EA_HS_Normal', 'EA_HS_Abusive', 'EA_HS_Hate'],
        'labels': ['Normal', 'Abusive', 'Hate'],
    },
    'polarization': {
        'hf_name': 'datavaluepeople/Polarization-Kenya',
        'pred_col': 'Polarization_Kenya_pred', 'conf_col': 'Polarization_Kenya_conf',
        'score_cols': ['Polarization_Kenya_not_polarization', 'Polarization_Kenya_polarization'],
        'labels': ['not_polarization', 'polarization'],
    },
    'afxumo': {
        'hf_name': 'datavaluepeople/Afxumo-toxicity-somaliland-SO',
        'pred_col': 'Afxumo_Somali_pred', 'conf_col': 'Afxumo_Somali_conf',
        'score_cols': ['Afxumo_Somali_not_afxumo', 'Afxumo_Somali_afxumo'],
        'labels': ['not_afxumo', 'afxumo'],
    },
    'hatespeech_sudan': {
        'hf_name': 'datavaluepeople/Hate-Speech-Sudan-v2',
        'pred_col': 'HateSpeech_Sudan_pred', 'conf_col': 'HateSpeech_Sudan_conf',
        'score_cols': ['HateSpeech_Sudan_not_hate_speech', 'HateSpeech_Sudan_hate_speech'],
        'labels': ['not_hate_speech', 'hate_speech'],
    },
}

CSV_FILES = [
    "Kenya_Delegitimization.csv", "Kenya_Diaspora.csv", "Kenya_Elections.csv",
    "Kenya_Hate_Speech.csv", "Kenya_Peace.csv", "Kenya_Violent_Extremism.csv",
    "Somalia_Comments_Escalation.csv", "Somalia_Delegitimization.csv", "Somalia_Escalation.csv",
    "Somalia_Hate_Speech.csv", "Somalia_Mixed.csv", "Somalia_Mixed_Monitoring.csv",
    "Somalia_Other.csv", "Somalia_Peace.csv", "Somalia_Unknown.csv", "Somalia_Violent_Extremism.csv",
    "South_Sudan_Delegitimization.csv", "South_Sudan_Diaspora.csv", "South_Sudan_Elections.csv",
    "South_Sudan_Hate_Speech.csv", "South_Sudan_Peace.csv", "South_Sudan_Violent_Extremism.csv",
]

BATCH_SIZE = 64
MAX_LEN = 256
SAVE_EVERY = 5  # save every 5 batches = 320 items
WS = "/home/user/workspace/"
STATUS_FILE = os.path.join(WS, "classify_status.json")

model_key = sys.argv[1]
cfg = MODELS[model_key]

def write_status(msg, classified=0, remaining=0, rate=0):
    with open(STATUS_FILE, 'w') as f:
        json.dump({
            'model': model_key,
            'status': msg,
            'classified': classified,
            'remaining': remaining,
            'rate': rate,
            'timestamp': time.time()
        }, f)

write_status("loading_model")

print(f"Loading {cfg['hf_name']}...", flush=True)
t0 = time.time()
tokenizer = AutoTokenizer.from_pretrained(cfg['hf_name'])
model = AutoModelForSequenceClassification.from_pretrained(cfg['hf_name'])
model.eval()
load_time = time.time() - t0
print(f"Model loaded in {load_time:.0f}s (threads={torch.get_num_threads()})", flush=True)
write_status("running", 0, 0, 0)

grand_classified = 0
grand_start = time.time()

for csv_file in CSV_FILES:
    path = os.path.join(WS, csv_file)
    if not os.path.exists(path):
        continue

    df = pd.read_csv(path, low_memory=False)
    pred_col = cfg['pred_col']

    for col in cfg['score_cols'] + [pred_col, cfg['conf_col']]:
        if col not in df.columns:
            df[col] = np.nan

    texts = df['post_text_pi'].fillna('').astype(str)
    mask_empty = texts.str.strip() == ''
    if 'comment_text_pi' in df.columns:
        texts.loc[mask_empty] = df.loc[mask_empty, 'comment_text_pi'].fillna('').astype(str)

    has_text = texts.str.strip().str.len() > 0
    needs_pred = df[pred_col].isna()
    to_classify = needs_pred & has_text
    n_todo = int(to_classify.sum())

    if n_todo == 0:
        continue

    print(f"  {csv_file}: {n_todo} items", flush=True)
    indices = df.index[to_classify].tolist()
    all_texts = texts[to_classify].tolist()
    file_classified = 0
    dirty = False
    batch_count = 0

    for i in range(0, len(all_texts), BATCH_SIZE):
        bt = all_texts[i:i+BATCH_SIZE]
        bi = indices[i:i+BATCH_SIZE]
        valid = [(t, idx) for t, idx in zip(bt, bi) if t.strip()]
        if not valid:
            continue

        v_texts = [v[0] for v in valid]
        v_indices = [v[1] for v in valid]

        try:
            inputs = tokenizer(v_texts, padding=True, truncation=True, max_length=MAX_LEN, return_tensors='pt')
            with torch.no_grad():
                outputs = model(**inputs)
            probs = softmax(outputs.logits.cpu().numpy(), axis=1)

            for j, idx in enumerate(v_indices):
                for k, sc in enumerate(cfg['score_cols']):
                    df.at[idx, sc] = float(probs[j][k])
                pred_idx = int(np.argmax(probs[j]))
                df.at[idx, pred_col] = cfg['labels'][pred_idx]
                df.at[idx, cfg['conf_col']] = float(probs[j][pred_idx])
                file_classified += 1
                grand_classified += 1
                dirty = True
        except Exception as e:
            print(f"    ERR: {e}", flush=True)
            continue

        batch_count += 1
        if dirty and batch_count % SAVE_EVERY == 0:
            df.to_csv(path, index=False)
            dirty = False
            elapsed = time.time() - grand_start
            rate = grand_classified / elapsed
            write_status("running", grand_classified, 0, round(rate, 1))
            print(f"    SAVED {file_classified}/{n_todo} | Total: {grand_classified} ({rate:.1f}/sec)", flush=True)

    if dirty:
        df.to_csv(path, index=False)
    print(f"  DONE {csv_file}: {file_classified}", flush=True)
    gc.collect()

elapsed = time.time() - grand_start
rate = grand_classified / elapsed if elapsed > 0 else 0
print(f"\nCOMPLETE: {grand_classified} in {elapsed:.0f}s ({rate:.1f}/sec)", flush=True)
write_status("complete", grand_classified, 0, round(rate, 1))
