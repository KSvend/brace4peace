"""papers/analysis/pipeline_metrics.py — Extract pipeline performance metrics for Paper A."""
import json
import csv
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
OUT = Path(__file__).resolve().parent

def load_hs_posts():
    with open(ROOT / "docs/data/hate_speech_posts.json") as f:
        return json.load(f)

def load_signal_metrics():
    with open(ROOT / "monitoring/config/signal_metrics.json") as f:
        return json.load(f)

def main():
    posts = load_hs_posts()

    # Quality gate metrics (from methodology.md — hardcoded as reference)
    quality_gate = {
        "original_dataset": 14754,
        "after_llm_qa": 5987,
        "noise_reduction_pct": 59,
        "correct_retained": 4048,
        "questionable_retained": 2948,
        "misclassified_removed": 7424,
        "relevant": 8547,
        "not_relevant_removed": 4774,
        "possibly_relevant": 1099,
    }

    with open(OUT / "pipeline_performance.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Metric", "Value"])
        for k, v in quality_gate.items():
            w.writerow([k, v])

        # LLM QA breakdown from actual data
        qc_counts = Counter(p.get("qc", "unknown") for p in posts)
        w.writerow([])
        w.writerow(["QC Label Distribution (verified dataset)", ""])
        for label, count in qc_counts.most_common():
            w.writerow([f"qc_{label}", count])

        rel_counts = Counter(p.get("rel", "unknown") for p in posts)
        w.writerow([])
        w.writerow(["Relevance Distribution (verified dataset)", ""])
        for label, count in rel_counts.most_common():
            w.writerow([f"rel_{label}", count])

    print("Wrote pipeline_performance.csv")

    # Operational metrics
    signal = load_signal_metrics()
    with open(OUT / "operational_metrics.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Metric", "Value", "Notes"])
        w.writerow(["Monthly cost (Apify)", "$38.50", "Social media scraping"])
        w.writerow(["Monthly cost (Anthropic)", "~$1.10", "Claude Sonnet QA"])
        w.writerow(["Total monthly cost", "~$40", "Full pipeline"])
        w.writerow(["Daily cost per run", "~$2", "Apify + API"])
        w.writerow(["Inference speed", "4-10 items/sec", "2-vCPU CPU-only"])
        w.writerow(["Batch size", "64", "BERT inference"])
        w.writerow(["Max token length", "256", "BERT input"])
        w.writerow(["LLM QA batch size", "10", "Claude Sonnet"])
        w.writerow(["Pipeline phases", "12", "Full run_pipeline.py"])

        # Signal quality from config - Apify keyword performance
        if isinstance(signal, dict) and "apify_keyword_performance" in signal:
            w.writerow([])
            w.writerow(["Apify Keyword Performance", "", ""])
            apify_perf = signal.get("apify_keyword_performance", {})
            for key, val in apify_perf.items():
                if isinstance(val, dict):
                    hits = val.get("hits", "")
                    fps = val.get("false_positives", "")
                    w.writerow([key, f"hits={hits}, fp={fps}", ""])

    print("Wrote operational_metrics.csv")

if __name__ == "__main__":
    main()
