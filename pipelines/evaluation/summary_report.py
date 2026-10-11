"""
Final performance reporting — metrics summary table, calibration plot,
and summary dashboard graphic.
"""

import json
import sys
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve

warnings.filterwarnings("ignore")

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from pipelines.configure.config import FIGURES_DIR, METRICS_PATH, RESULTS_DIR, THRESHOLD_PATH

FIGURES_DIR.mkdir(parents=True, exist_ok=True)

DARK_BG  = "#0f1117"
PANEL_BG = "#1a1d27"


def _style_axes(ax):
    ax.set_facecolor(PANEL_BG)
    ax.tick_params(colors="white")
    ax.spines[["top", "right"]].set_visible(False)
    for s in ["left", "bottom"]:
        ax.spines[s].set_color("#444")


def plot_calibration(model, X_arr: np.ndarray, y_true,
                     model_name: str, n_bins: int = 10) -> Path:
    if not hasattr(model, "predict_proba"):
        return None

    y_proba = model.predict_proba(X_arr)[:, 1]
    try:
        frac_pos, mean_pred = calibration_curve(y_true, y_proba, n_bins=n_bins)
    except Exception:
        return None

    fig, ax = plt.subplots(figsize=(7, 6))
    fig.patch.set_facecolor(DARK_BG)
    _style_axes(ax)

    ax.plot([0, 1], [0, 1], "--", color="#666", label="Perfectly Calibrated")
    ax.plot(mean_pred, frac_pos, "o-", color="#3498db", lw=2, label=model_name)
    ax.set_title(f"Calibration Plot (Reliability Diagram)\n{model_name} | Early Warning",
                 color="white", fontsize=12, fontweight="bold")
    ax.set_xlabel("Mean Predicted Probability", color="#aaa")
    ax.set_ylabel("Fraction of Positives",      color="#aaa")
    ax.legend(facecolor="#2a2d37", labelcolor="white", fontsize=10)

    plt.tight_layout()
    output_path = FIGURES_DIR / f"eval_calibration_{model_name.replace(' ', '_').lower()}.png"
    plt.savefig(output_path, dpi=150, bbox_inches="tight", facecolor=DARK_BG)
    plt.close()
    return output_path


def print_summary_table() -> None:
    if not METRICS_PATH.exists():
        print("   metrics.json not found — skipping summary display.")
        return

    with open(METRICS_PATH, encoding="utf-8") as f:
        metrics_data = json.load(f)
    tm = metrics_data.get("test_metrics", {})

    print()
    print("-" * 70)
    print("  MODEL EVALUATION SUMMARY — EARLY WARNING (t+1)")
    print("-" * 70)
    print(f"  Model Name       : {metrics_data.get('model_name', '-')}")
    print(f"  F1-Macro         : {tm.get('f1_macro', '-')}")
    print(f"  F1-Binary        : {tm.get('f1_binary', '-')}")
    print(f"  Precision        : {tm.get('precision_binary', '-')}")
    print(f"  Recall           : {tm.get('recall_binary', '-')}")
    print(f"  Balanced Accuracy: {tm.get('balanced_accuracy', '-')}")
    print(f"  ROC-AUC          : {tm.get('roc_auc', '-')}")
    print(f"  PR-AUC           : {tm.get('pr_auc', '-')}")
    print(f"  Threshold Used   : {tm.get('threshold', '-')}")
    print(f"  Test Sample Count: {metrics_data.get('n_test', '-')}")
    print("-" * 70)

    if THRESHOLD_PATH.exists():
        with open(THRESHOLD_PATH, encoding="utf-8") as f:
            thresh_data = json.load(f)
        thresh_info = thresh_data.get("threshold_analysis", {})
        print("\n  [Threshold Analysis]")
        print(f"  Best Threshold (PR curve) : {thresh_info.get('best_threshold', '-')}")
        print(f"  F1 at Best Threshold      : {thresh_info.get('best_f1', '-')}")
        print(f"  Precision at Best         : {thresh_info.get('precision_at_best', '-')}")
        print(f"  Recall at Best            : {thresh_info.get('recall_at_best', '-')}")
    print()

    if "classification_report" in metrics_data:
        print("  [Classification Report — Test Set]")
        print(metrics_data["classification_report"])


def plot_summary_dashboard() -> Path:
    if not METRICS_PATH.exists():
        return None

    with open(METRICS_PATH, encoding="utf-8") as f:
        metrics_data = json.load(f)
    tm = metrics_data.get("test_metrics", {})

    rows = [
        ["Model",             metrics_data.get("model_name", "-")],
        ["F1-Macro",          tm.get("f1_macro", "-")],
        ["F1-Binary",         tm.get("f1_binary", "-")],
        ["Precision",         tm.get("precision_binary", "-")],
        ["Recall",            tm.get("recall_binary", "-")],
        ["Balanced Accuracy", tm.get("balanced_accuracy", "-")],
        ["ROC-AUC",           tm.get("roc_auc", "-")],
        ["PR-AUC",            tm.get("pr_auc", "-")],
        ["Threshold Used",    tm.get("threshold", "-")],
        ["Test Sample Count", metrics_data.get("n_test", "-")],
    ]

    fig, ax = plt.subplots(figsize=(8, 6))
    fig.patch.set_facecolor(DARK_BG)
    ax.set_facecolor(DARK_BG)
    ax.axis("off")

    table = ax.table(
        cellText=[[str(r[0]), str(r[1])] for r in rows],
        colLabels=["Metric", "Value"],
        cellLoc="center", loc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1.5, 2.0)

    for (row_idx, _), cell in table.get_celld().items():
        cell.set_facecolor("#2c3e50" if row_idx == 0 else PANEL_BG)
        cell.set_text_props(color="white")
        cell.set_edgecolor("#444")

    ax.set_title(
        "Model Summary Dashboard (Test Set)",
        color="white", fontsize=13, fontweight="bold", y=0.98,
    )
    plt.tight_layout()
    output_path = FIGURES_DIR / "eval_summary_dashboard.png"
    plt.savefig(output_path, dpi=150, bbox_inches="tight", facecolor=DARK_BG)
    plt.close()
    print(f"   Summary dashboard generated: {output_path}")
    return output_path


def run(model, X_arr: np.ndarray, y_true, model_name: str) -> None:
    """Execute complete reporting suite."""
    print("[Summary] Generating calibration plot")
    plot_calibration(model, X_arr, y_true, model_name)

    print("[Summary] Generating visual dashboard table")
    plot_summary_dashboard()

    print("[Summary] Printing evaluation summary table")
    print_summary_table()


if __name__ == "__main__":
    import pickle
    from pipelines.configure.config import BEST_MODEL_PATH, COL_TARGET, TEST_PATH
    bundle  = pickle.loads(BEST_MODEL_PATH.read_bytes())
    test_df = pd.read_csv(TEST_PATH)
    mask    = test_df[COL_TARGET].notna()
    prep    = bundle["preprocessor"]
    X_test  = test_df.loc[mask, [c for c in bundle["feature_cols"] if c in test_df.columns]]
    y_test  = test_df.loc[mask, COL_TARGET].astype(int)
    cat = prep["cat_encoder"].transform(X_test[prep["cat_cols"]].astype(str).fillna("MISSING"))
    num = prep["num_scaler"].transform(prep["num_imputer"].transform(X_test[prep["num_cols"]]))
    X_arr = np.hstack([num, cat])
    run(bundle["model"], X_arr, y_test, bundle["model_name"])
