"""
compute_agreement.py
====================
Compute inter-annotator agreement and evaluation metrics for the IRIS paper.

Data sources
------------
- papers/evaluation/human_annotations.json  — human blind annotations
- papers/evaluation/gpt4o_annotations.json  — GPT-4o annotations
- papers/evaluation/sample_full.json        — pipeline predictions (field: pr)

Outputs
-------
- papers/evaluation/agreement_metrics.json
- papers/evaluation/agreement_report.md
- papers/figures/fig_confusion_pipeline.png
- papers/figures/fig_confusion_gpt4o.png

Labels: ["Normal", "Abusive", "Hate"]
"Questionable" pipeline predictions are excluded from agreement computation.
"""

import json
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[2]
EVAL_DIR = REPO_ROOT / "papers" / "evaluation"
FIG_DIR = REPO_ROOT / "papers" / "figures"

HUMAN_ANN_PATH = EVAL_DIR / "human_annotations.json"
GPT4O_ANN_PATH = EVAL_DIR / "gpt4o_annotations.json"
SAMPLE_FULL_PATH = EVAL_DIR / "sample_full.json"

METRICS_OUT = EVAL_DIR / "agreement_metrics.json"
REPORT_OUT = EVAL_DIR / "agreement_report.md"
FIG_PIPELINE = FIG_DIR / "fig_confusion_pipeline.png"
FIG_GPT4O = FIG_DIR / "fig_confusion_gpt4o.png"

LABELS = ["Normal", "Abusive", "Hate"]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_json(path: Path):
    """Load JSON; return None if file does not exist."""
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def build_id_map(records: list, label_field: str = "label") -> dict:
    """Return {post_id: label} from a list of annotation dicts."""
    return {r["id"]: r[label_field] for r in records}


def align(id_map_a: dict, id_map_b: dict, valid_labels=None) -> tuple[list, list]:
    """
    Return two aligned label lists for IDs present in both maps.
    Optionally filter to rows where BOTH labels are in valid_labels.
    """
    common = set(id_map_a) & set(id_map_b)
    pairs = [(id_map_a[k], id_map_b[k]) for k in sorted(common)]
    if valid_labels is not None:
        valid_set = set(valid_labels)
        pairs = [(a, b) for a, b in pairs if a in valid_set and b in valid_set]
    y_a = [p[0] for p in pairs]
    y_b = [p[1] for p in pairs]
    return y_a, y_b


def kappa(y_true, y_pred):
    from sklearn.metrics import cohen_kappa_score
    if len(y_true) < 2:
        return None
    return round(float(cohen_kappa_score(y_true, y_pred)), 4)


def prf(y_true, y_pred, labels):
    from sklearn.metrics import precision_recall_fscore_support
    p, r, f, s = precision_recall_fscore_support(
        y_true, y_pred, labels=labels, average=None, zero_division=0
    )
    per_class = {}
    for i, lbl in enumerate(labels):
        per_class[lbl] = {
            "precision": round(float(p[i]), 4),
            "recall": round(float(r[i]), 4),
            "f1": round(float(f[i]), 4),
            "support": int(s[i]),
        }
    pm, rm, fm, _ = precision_recall_fscore_support(
        y_true, y_pred, labels=labels, average="macro", zero_division=0
    )
    macro = {
        "precision": round(float(pm), 4),
        "recall": round(float(rm), 4),
        "f1": round(float(fm), 4),
    }
    return per_class, macro


def plot_confusion(y_true, y_pred, labels, title, out_path: Path):
    """Save a labelled confusion-matrix PNG."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from sklearn.metrics import confusion_matrix
    import numpy as np

    cm = confusion_matrix(y_true, y_pred, labels=labels)
    fig, ax = plt.subplots(figsize=(6, 5))
    im = ax.imshow(cm, interpolation="nearest", cmap="Blues")
    fig.colorbar(im, ax=ax)
    ax.set(
        xticks=np.arange(len(labels)),
        yticks=np.arange(len(labels)),
        xticklabels=labels,
        yticklabels=labels,
        xlabel="Predicted",
        ylabel="True",
        title=title,
    )
    thresh = cm.max() / 2.0
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(
                j, i, format(cm[i, j], "d"),
                ha="center", va="center",
                color="white" if cm[i, j] > thresh else "black",
                fontsize=12,
            )
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"  Saved: {out_path}")


def write_placeholder(reason: str):
    """Write a placeholder metrics file and exit gracefully."""
    payload = {"status": "placeholder", "reason": reason}
    METRICS_OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(METRICS_OUT, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"[compute_agreement] Placeholder written to {METRICS_OUT}")
    print(f"[compute_agreement] Reason: {reason}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    # -- Load pipeline predictions ------------------------------------------
    pipeline_raw = load_json(SAMPLE_FULL_PATH)
    if pipeline_raw is None:
        write_placeholder(f"{SAMPLE_FULL_PATH.name} not found")
        sys.exit(0)

    pipeline_map = {r["i"]: r["pr"] for r in pipeline_raw}

    # -- Load annotation files -----------------------------------------------
    human_raw = load_json(HUMAN_ANN_PATH)
    gpt4o_raw = load_json(GPT4O_ANN_PATH)

    missing = []
    if human_raw is None:
        missing.append(HUMAN_ANN_PATH.name)
    if gpt4o_raw is None:
        missing.append(GPT4O_ANN_PATH.name)

    if missing:
        write_placeholder(
            "Annotation files not yet available: " + ", ".join(missing)
        )
        sys.exit(0)

    # -- Build id maps -------------------------------------------------------
    human_map = build_id_map(human_raw)
    gpt4o_map = build_id_map(gpt4o_raw)

    # Pipeline predictions keyed by id, restricted to LABELS
    pipeline_label_map = {
        k: v for k, v in pipeline_map.items() if v in LABELS
    }

    # -- Overall Cohen's kappa -----------------------------------------------
    print("[compute_agreement] Computing Cohen's kappa ...")

    yh, yg = align(human_map, gpt4o_map, valid_labels=LABELS)
    yh_pipe, ypipe = align(human_map, pipeline_label_map, valid_labels=LABELS)
    yg_pipe, ypipe_g = align(gpt4o_map, pipeline_label_map, valid_labels=LABELS)

    kappa_results = {
        "human_vs_gpt4o": {
            "n": len(yh),
            "kappa": kappa(yh, yg),
        },
        "human_vs_pipeline": {
            "n": len(yh_pipe),
            "kappa": kappa(yh_pipe, ypipe),
        },
        "gpt4o_vs_pipeline": {
            "n": len(yg_pipe),
            "kappa": kappa(yg_pipe, ypipe_g),
        },
    }

    # -- Per-country kappa ---------------------------------------------------
    print("[compute_agreement] Computing per-country kappa ...")

    country_map = {r["i"]: r.get("c", "Unknown") for r in pipeline_raw}
    countries = sorted(set(country_map.values()))

    per_country_kappa = {}
    for country in countries:
        ids_country = {k for k, v in country_map.items() if v == country}

        hm_c = {k: v for k, v in human_map.items() if k in ids_country}
        gm_c = {k: v for k, v in gpt4o_map.items() if k in ids_country}
        pm_c = {k: v for k, v in pipeline_label_map.items() if k in ids_country}

        yh_c, yg_c = align(hm_c, gm_c, valid_labels=LABELS)
        yh_pc, yp_c = align(hm_c, pm_c, valid_labels=LABELS)
        yg_pc, ypg_c = align(gm_c, pm_c, valid_labels=LABELS)

        per_country_kappa[country] = {
            "human_vs_gpt4o": {"n": len(yh_c), "kappa": kappa(yh_c, yg_c)},
            "human_vs_pipeline": {"n": len(yh_pc), "kappa": kappa(yh_pc, yp_c)},
            "gpt4o_vs_pipeline": {"n": len(yg_pc), "kappa": kappa(yg_pc, ypg_c)},
        }

    # -- Precision / Recall / F1 ---------------------------------------------
    print("[compute_agreement] Computing P/R/F1 ...")

    prf_pipeline_pc, prf_pipeline_mac = prf(yh_pipe, ypipe, LABELS)
    prf_gpt4o_pc, prf_gpt4o_mac = prf(yh, yg, LABELS)

    prf_results = {
        "pipeline_vs_human": {
            "per_class": prf_pipeline_pc,
            "macro": prf_pipeline_mac,
        },
        "gpt4o_vs_human": {
            "per_class": prf_gpt4o_pc,
            "macro": prf_gpt4o_mac,
        },
    }

    # -- Confusion matrices --------------------------------------------------
    print("[compute_agreement] Plotting confusion matrices ...")
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    if len(yh_pipe) >= 2:
        plot_confusion(
            yh_pipe, ypipe, LABELS,
            "Pipeline vs. Human (gold)",
            FIG_PIPELINE,
        )
    else:
        print(f"  Skipped pipeline confusion matrix (n={len(yh_pipe)} < 2)")

    if len(yh) >= 2:
        plot_confusion(
            yh, yg, LABELS,
            "GPT-4o vs. Human (gold)",
            FIG_GPT4O,
        )
    else:
        print(f"  Skipped GPT-4o confusion matrix (n={len(yh)} < 2)")

    # -- Write metrics JSON --------------------------------------------------
    metrics = {
        "status": "complete",
        "labels": LABELS,
        "kappa": kappa_results,
        "kappa_per_country": per_country_kappa,
        "prf": prf_results,
    }
    METRICS_OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(METRICS_OUT, "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"[compute_agreement] Metrics written to {METRICS_OUT}")

    # -- Write markdown report -----------------------------------------------
    _write_report(metrics)
    print(f"[compute_agreement] Report written to {REPORT_OUT}")


# ---------------------------------------------------------------------------
# Report writer
# ---------------------------------------------------------------------------

def _kappa_row(label: str, d: dict) -> str:
    k = d.get("kappa")
    k_str = f"{k:.4f}" if k is not None else "N/A"
    return f"| {label} | {d['n']} | {k_str} |"


def _prf_table(prf_dict: dict, labels) -> str:
    lines = [
        "| Class | Precision | Recall | F1 | Support |",
        "|-------|-----------|--------|----|---------|",
    ]
    for lbl in labels:
        row = prf_dict["per_class"].get(lbl, {})
        lines.append(
            f"| {lbl} | {row.get('precision', 'N/A')} | {row.get('recall', 'N/A')} "
            f"| {row.get('f1', 'N/A')} | {row.get('support', 'N/A')} |"
        )
    m = prf_dict["macro"]
    lines.append(
        f"| **Macro avg** | {m['precision']} | {m['recall']} | {m['f1']} | — |"
    )
    return "\n".join(lines)


def _write_report(metrics: dict):
    k = metrics["kappa"]
    p = metrics["prf"]
    labels = metrics["labels"]

    lines = [
        "# Inter-Annotator Agreement Report",
        "",
        "Labels: " + ", ".join(f"`{l}`" for l in labels),
        "",
        "## 1. Overall Cohen's Kappa",
        "",
        "| Pair | N | κ |",
        "|------|---|---|",
        _kappa_row("Human vs. GPT-4o", k["human_vs_gpt4o"]),
        _kappa_row("Human vs. Pipeline", k["human_vs_pipeline"]),
        _kappa_row("GPT-4o vs. Pipeline", k["gpt4o_vs_pipeline"]),
        "",
        "## 2. Per-Country Cohen's Kappa",
        "",
    ]

    for country, ck in metrics["kappa_per_country"].items():
        lines += [
            f"### {country}",
            "",
            "| Pair | N | κ |",
            "|------|---|---|",
            _kappa_row("Human vs. GPT-4o", ck["human_vs_gpt4o"]),
            _kappa_row("Human vs. Pipeline", ck["human_vs_pipeline"]),
            _kappa_row("GPT-4o vs. Pipeline", ck["gpt4o_vs_pipeline"]),
            "",
        ]

    lines += [
        "## 3. Pipeline Precision / Recall / F1 (vs. Human gold standard)",
        "",
        _prf_table(p["pipeline_vs_human"], labels),
        "",
        "## 4. GPT-4o Precision / Recall / F1 (vs. Human gold standard)",
        "",
        _prf_table(p["gpt4o_vs_human"], labels),
        "",
        "## 5. Confusion Matrices",
        "",
        "![Pipeline confusion matrix](../figures/fig_confusion_pipeline.png)",
        "",
        "![GPT-4o confusion matrix](../figures/fig_confusion_gpt4o.png)",
        "",
    ]

    REPORT_OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_OUT, "w") as f:
        f.write("\n".join(lines) + "\n")


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    main()
