"""
Precision-Recall curve and operational decision threshold analysis.
Identifies optimal decision threshold maximizing F1 and evaluates trade-offs
for operational risk screening.
"""

import json
import sys
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import average_precision_score, precision_recall_curve

warnings.filterwarnings("ignore")

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from pipelines.ml.config import (
    FIGURES_DIR,
    OPERATIONAL_THRESHOLD,
    RESULTS_DIR,
    THRESHOLD_PATH,
)

FIGURES_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

DARK_BG  = "#0f1117"
PANEL_BG = "#1a1d27"


def _style_axes(ax):
    ax.set_facecolor(PANEL_BG)
    ax.tick_params(colors="white")
    ax.spines[["top", "right"]].set_visible(False)
    for s in ["left", "bottom"]:
        ax.spines[s].set_color("#444")


def analyze_thresholds(y_true, y_proba, model_name: str) -> dict:
    """Analyze Precision-Recall trade-offs across probability thresholds."""
    precisions, recalls, thresholds = precision_recall_curve(y_true, y_proba)
    pr_auc = float(average_precision_score(y_true, y_proba))

    denom = precisions[:-1] + recalls[:-1]
    f1_scores = np.where(denom > 0, 2 * precisions[:-1] * recalls[:-1] / denom, 0.0)

    best_idx       = int(np.argmax(f1_scores))
    best_threshold = float(thresholds[best_idx])
    best_f1        = float(f1_scores[best_idx])
    best_precision = float(precisions[best_idx])
    best_recall    = float(recalls[best_idx])

    # Visualization
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.patch.set_facecolor(DARK_BG)

    # Subplot 1: PR curve
    ax1 = axes[0]
    _style_axes(ax1)
    ax1.plot(recalls, precisions, color="#3498db", lw=2, label=f"PR Curve (AUC={pr_auc:.3f})")
    ax1.scatter([best_recall], [best_precision], color="#e74c3c", s=80, zorder=5,
                label=f"Max F1 @ thr={best_threshold:.3f}")
    ax1.set_title(f"Precision-Recall Curve\n{model_name} | Early Warning",
                  color="white", fontsize=12, fontweight="bold")
    ax1.set_xlabel("Recall", color="#aaa")
    ax1.set_ylabel("Precision", color="#aaa")
    ax1.legend(facecolor="#2a2d37", labelcolor="white", fontsize=9)

    # Subplot 2: Metric curves vs Threshold
    ax2 = axes[1]
    _style_axes(ax2)
    ax2.plot(thresholds, precisions[:-1], color="#2ecc71", lw=1.5, label="Precision")
    ax2.plot(thresholds, recalls[:-1],    color="#e74c3c", lw=1.5, label="Recall")
    ax2.plot(thresholds, f1_scores,       color="#f39c12", lw=2,   label="F1-Score")
    ax2.axvline(best_threshold, color="white", ls="--", lw=1,
                label=f"Optimal Threshold={best_threshold:.3f}")
    ax2.axvline(OPERATIONAL_THRESHOLD, color="#9b59b6", ls=":", lw=1.5,
                label=f"Operational Target={OPERATIONAL_THRESHOLD:.2f}")
    ax2.set_title("Metrics vs Decision Threshold",
                  color="white", fontsize=12, fontweight="bold")
    ax2.set_xlabel("Decision Threshold", color="#aaa")
    ax2.set_ylabel("Metric Score", color="#aaa")
    ax2.legend(facecolor="#2a2d37", labelcolor="white", fontsize=8)

    plt.suptitle("JAGA-JKN — Operational Decision Threshold Calibration",
                 color="white", fontsize=14, fontweight="bold", y=1.02)
    plt.tight_layout()

    filename = f"eval_threshold_{model_name.replace(' ', '_').lower()}.png"
    plot_path = FIGURES_DIR / filename
    plt.savefig(plot_path, dpi=150, bbox_inches="tight", facecolor=DARK_BG)
    plt.close()

    result = {
        "model_name": model_name,
        "objective": "Early Warning Lead-1 Month (t+1)",
        "threshold_analysis": {
            "best_threshold":    round(best_threshold, 4),
            "best_f1":           round(best_f1, 4),
            "precision_at_best": round(best_precision, 4),
            "recall_at_best":    round(best_recall, 4),
            "pr_auc":            round(pr_auc, 4),
        },
        "plot_path": str(plot_path),
        "recommendation": (
            f"PR curve optimal threshold: {best_threshold:.3f}. Operational screening target: "
            f"{OPERATIONAL_THRESHOLD:.2f}. Higher thresholds minimize false inspections when investigation costs are high."
        ),
    }

    THRESHOLD_PATH.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"   Threshold analysis saved to: {THRESHOLD_PATH}")
    print(f"   Optimal threshold: {best_threshold:.4f} | F1: {best_f1:.4f} | PR-AUC: {pr_auc:.4f}")
    return result


def run(model_name: str, y_true, y_proba) -> dict:
    """Execute complete decision threshold analysis suite."""
    print(f"[Threshold] Analyzing Precision-Recall curve for [{model_name}]...")
    return analyze_thresholds(y_true, y_proba, model_name)


if __name__ == "__main__":
    import pickle
    from pipelines.ml.config import BEST_MODEL_PATH, COL_TARGET, TEST_PATH
    import pandas as pd
    bundle  = pickle.loads(BEST_MODEL_PATH.read_bytes())
    test_df = pd.read_csv(TEST_PATH)
    mask    = test_df[COL_TARGET].notna()
    prep    = bundle["preprocessor"]
    X_test  = test_df.loc[mask, [c for c in bundle["feature_cols"] if c in test_df.columns]]
    y_test  = test_df.loc[mask, COL_TARGET].astype(int)
    cat = prep["cat_encoder"].transform(X_test[prep["cat_cols"]].astype(str).fillna("MISSING"))
    num = prep["num_scaler"].transform(prep["num_imputer"].transform(X_test[prep["num_cols"]]))
    X_arr   = np.hstack([num, cat])
    y_proba = bundle["model"].predict_proba(X_arr)[:, 1]
    run(bundle["model_name"], y_test, y_proba)
