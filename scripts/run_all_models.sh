#!/bin/bash
# Runs all remaining models sequentially, clearing cache between each.
# Polarization -> Afxumo -> HateSpeech Sudan
# Each model saves incremental progress so it can resume if interrupted.

WS="/home/user/workspace"
CACHE="/home/user/.cache/huggingface/hub"
LOG="/tmp/classification_chain.log"

echo "=== Classification chain started at $(date) ===" >> $LOG

# Model 1: Polarization-Kenya (already running separately, skip if status=complete)
STATUS=$(python3 -c "import json; d=json.load(open('$WS/classify_status.json')); print(d.get('model',''), d.get('status',''))" 2>/dev/null)
echo "Current status: $STATUS" >> $LOG

# Wait for polarization to finish if it's currently running
while true; do
    STATUS=$(python3 -c "import json; d=json.load(open('$WS/classify_status.json')); print(d['status'])" 2>/dev/null)
    MODEL=$(python3 -c "import json; d=json.load(open('$WS/classify_status.json')); print(d['model'])" 2>/dev/null)
    if [ "$MODEL" = "polarization" ] && [ "$STATUS" = "complete" ]; then
        echo "Polarization complete!" >> $LOG
        break
    fi
    if [ "$STATUS" != "running" ] && [ "$STATUS" != "loading_model" ]; then
        echo "Polarization not running (status=$STATUS). Starting it..." >> $LOG
        python -u $WS/classify_fast.py polarization >> /tmp/polarization.log 2>&1
        break
    fi
    sleep 60
done

# Clear polarization model cache
echo "Clearing polarization cache..." >> $LOG
rm -rf $CACHE/models--datavaluepeople--Polarization-Kenya 2>/dev/null

# Model 2: Afxumo
echo "=== Starting Afxumo at $(date) ===" >> $LOG
python -u $WS/classify_fast.py afxumo >> /tmp/afxumo.log 2>&1
echo "Afxumo finished at $(date)" >> $LOG

# Clear afxumo model cache
rm -rf $CACHE/models--datavaluepeople--Afxumo-toxicity-somaliland-SO 2>/dev/null

# Model 3: HateSpeech Sudan
echo "=== Starting HateSpeech Sudan at $(date) ===" >> $LOG
python -u $WS/classify_fast.py hatespeech_sudan >> /tmp/hatespeech_sudan.log 2>&1
echo "HateSpeech Sudan finished at $(date)" >> $LOG

echo "=== ALL MODELS COMPLETE at $(date) ===" >> $LOG

# Write final summary
python3 -c "
import pandas as pd, glob, json
files = sorted(glob.glob('$WS/Kenya_*.csv') + glob.glob('$WS/Somalia_*.csv') + glob.glob('$WS/South_Sudan_*.csv'))
models = ['EA_HS_pred', 'Polarization_Kenya_pred', 'Afxumo_Somali_pred', 'HateSpeech_Sudan_pred']
summary = {}
for m in models:
    filled = 0; total = 0
    for f in files:
        df = pd.read_csv(f, low_memory=False)
        total += len(df)
        if m in df.columns: filled += int(df[m].notna().sum())
    summary[m] = {'filled': filled, 'total': total, 'pct': round(filled/total*100,1) if total else 0}
json.dump(summary, open('$WS/classification_summary.json', 'w'), indent=2)
print('Summary written to classification_summary.json')
for m, v in summary.items():
    print(f\"  {m}: {v['filled']}/{v['total']} ({v['pct']}%)\")
" >> $LOG 2>&1
