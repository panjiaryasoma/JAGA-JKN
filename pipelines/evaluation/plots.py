"""
Evaluation plots — Confusion Matrix and Feature Importance.
"""

import sys
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix

warnings.filterwarnings("ignore")

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from pipelines.ml.config import FEAT_IMP_PATH, FIGURES_DIR

FIGURES_DIR.mkdir(parents=True, exist_ok=True)

DARK_BG  = "#0f1117"
PANEL_BG = "#1a1d27"


def _style_axes(ax):
    ax.set_facecolor(PANEL_BG)
    ax.tick_params(colors="white")
    ax.spines[["top", "right"]].set_visible(False)
    for s in ["left", "bottom"]:
        ax.spines[s].set_color("#444")


def plot_confusion_matrix(y_true, y_pred, model_name: str, threshold: float) -> Path:
    """Generate confusion matrix visual with NORMAL and NON-NORMAL categories."""
    cm = confusion_matrix(y_true, y_pred)

    fig, ax = plt.subplots(figsize=(7, 6))
    fig.patch.set_facecolor(DARK_BG)
    ax.set_facecolor(PANEL_BG)

    ax.imshow(cm, cmap="Blues", aspect="auto")
    ax.set_xticks([0, 1])
    ax.set_yticks([0, 1])
    ax.set_xticklabels(["NORMAL", "NON-NORMAL"], color="white", fontsize=11)
    ax.set_yticklabels(["NORMAL", "NON-NORMAL"], color="white", fontsize=11)
    ax.set_xlabel("Predicted Class", color="#aaa", fontsize=12)
    ax.set_ylabel("Actual Class",    color="#aaa", fontsize=12)
    ax.set_title(
        f"Confusion Matrix — {model_name}\nEarly Warning | threshold={threshold}",
        color="white", fontsize=12, fontweight="bold",
    )

    total_samples = cm.sum()
    for i in range(2):
        for j in range(2):
            pct = cm[i, j] / total_samples * 100
            ax.text(j, i, f"{cm[i, j]:,}\n({pct:.1f}%)",
                    ha="center", va="center", color="white",
                    fontsize=13, fontweight="bold")

    plt.tight_layout()
    output_path = FIGURES_DIR / f"eval_cm_{model_name.replace(' ', '_').lower()}.png"
    plt.savefig(output_path, dpi=150, bbox_inches="tight", facecolor=DARK_BG)
    plt.close()
    return output_path


def plot_feature_importance(model, feature_names: list,
                            model_name: str, top_n: int = 20) -> tuple:
    """
    Extract and visualize top feature importances from tree-based or linear models.
    Exports results to CSV and generates a horizontal bar chart.
    """
    if hasattr(model, "feature_importances_"):
        importance_values = model.feature_importances_
    elif hasattr(model, "coef_"):
        importance_values = np.abs(model.coef_[0])
    else:
        print(f"   [{model_name}] does not expose feature importances — skipping.")
        return None, None

    fi_df = (
        pd.DataFrame({"feature": feature_names, "importance": importance_values})
        .sort_values("importance", ascending=False)
        .reset_index(drop=True)
    )

    # Persist complete feature importance table
    fi_df.to_csv(FEAT_IMP_PATH, index=False)

    top_subset = fi_df.head(top_n).sort_values("importance")
    fig, ax = plt.subplots(figsize=(10, max(6, top_n * 0.38)))
    fig.patch.set_facecolor(DARK_BG)
    _style_axes(ax)

    ax.barh(top_subset["feature"], top_subset["importance"], color="#9b59b6", alpha=0.85)
    ax.set_title(f"Top-{top_n} Feature Importance\n{model_name} | Early Warning",
                 color="white", fontsize=12, fontweight="bold")
    ax.set_xlabel("Relative Importance Score", color="#aaa")
    ax.tick_params(colors="white", labelsize=8)

    plt.tight_layout()
    output_path = FIGURES_DIR / f"eval_fi_{model_name.replace(' ', '_').lower()}.png"
    plt.savefig(output_path, dpi=150, bbox_inches="tight", facecolor=DARK_BG)
    plt.close()
    return fi_df, output_path


def run(model, feature_names: list, model_name: str,
        y_true, y_pred, threshold: float) -> dict:
    """Execute complete evaluation plotting suite."""
    print("[Plots] Generating Confusion Matrix visual...")
    cm_path = plot_confusion_matrix(y_true, y_pred, model_name, threshold)

    print("[Plots] Computing and plotting Feature Importance...")
    fi_df, fi_path = plot_feature_importance(model, feature_names, model_name)

    print(f"   Confusion Matrix: {cm_path}")
    if fi_path:
        print(f"   Feature Importance Plot: {fi_path}")
        print(f"   Feature Importance CSV: {FEAT_IMP_PATH}")

    return {
        "confusion_matrix": str(cm_path),
        "feature_importance": str(fi_path) if fi_path else None,
    }


if __name__ == "__main__":
    import pickle
    from pipelines.ml.config import BEST_MODEL_PATH, COL_TARGET, TEST_PATH
    bundle  = pickle.loads(BEST_MODEL_PATH.read_bytes())
    test_df = pd.read_csv(TEST_PATH)
    mask    = test_df[COL_TARGET].notna()
    prep    = bundle["preprocessor"]
    X_test  = test_df.loc[mask, [c for c in bundle["feature_cols"] if c in test_df.columns]]
    y_test  = test_df.loc[mask, COL_TARGET].astype(int)
    cat = prep["cat_encoder"].transform(X_test[prep["cat_cols"]].astype(str).fillna("MISSING"))
    num = prep["num_scaler"].transform(prep["num_imputer"].transform(X_test[prep["num_cols"]]))
    X_arr   = np.hstack([num, cat])
    y_pred  = (bundle["model"].predict_proba(X_arr)[:, 1] >= bundle["threshold"]).astype(int)
    run(bundle["model"], bundle["feature_names_transformed"],
        bundle["model_name"], y_test, y_pred, bundle["threshold"])
