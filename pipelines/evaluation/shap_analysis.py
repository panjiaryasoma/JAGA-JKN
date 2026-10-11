"""
SHAP model interpretability.
Calculates feature-level attribution values and generates bar and beeswarm plots.
"""

import sys
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from pipelines.ml.config import FIGURES_DIR

FIGURES_DIR.mkdir(parents=True, exist_ok=True)

DARK_BG  = "#0f1117"
PANEL_BG = "#1a1d27"


def _style_axes(ax):
    ax.set_facecolor(PANEL_BG)
    ax.tick_params(colors="white", labelsize=8)
    ax.spines[["top", "right"]].set_visible(False)
    for s in ["left", "bottom"]:
        ax.spines[s].set_color("#444")


def compute_shap_values(model, X_arr: np.ndarray, max_samples: int = 500) -> tuple:
    """
    Calculate SHAP attribution values using appropriate explainer:
    - TreeExplainer for Random Forest and LightGBM
    - LinearExplainer for Logistic Regression
    Returns: (shap_values, sampled_features).
    """
    try:
        import shap
    except ImportError:
        raise ImportError("Missing package.")

    rng = np.random.default_rng(42)
    sample_size = min(max_samples, X_arr.shape[0])
    sample_indices = rng.choice(X_arr.shape[0], sample_size, replace=False)
    X_sample = X_arr[sample_indices]

    model_type = type(model).__name__.lower()
    if any(k in model_type for k in ("lgbm", "forest", "tree", "gradient")):
        explainer = shap.TreeExplainer(model)
    else:
        explainer = shap.LinearExplainer(model, X_sample)

    shap_vals = explainer.shap_values(X_sample)

    # For binary classification: isolate positive class attribution (index 1)
    if isinstance(shap_vals, list) and len(shap_vals) == 2:
        shap_vals = shap_vals[1]
    elif isinstance(shap_vals, np.ndarray) and shap_vals.ndim == 3:
        shap_vals = shap_vals[:, :, 1]

    return shap_vals, X_sample


def plot_shap_bar(shap_values: np.ndarray, feature_names: list,
                  model_name: str, top_n: int = 20) -> Path:
    """Generate horizontal bar chart of mean absolute SHAP value per feature."""
    mean_abs_shap = np.abs(shap_values).mean(axis=0)
    fi_df = (
        pd.DataFrame({"feature": feature_names, "mean_abs_shap": mean_abs_shap})
        .sort_values("mean_abs_shap", ascending=True)
        .tail(top_n)
    )

    fig, ax = plt.subplots(figsize=(10, max(6, top_n * 0.38)))
    fig.patch.set_facecolor(DARK_BG)
    _style_axes(ax)

    ax.barh(fi_df["feature"], fi_df["mean_abs_shap"], color="#9b59b6", alpha=0.85)
    ax.set_title(f"SHAP — Mean |SHAP Value| (Top {top_n})\n{model_name} | Early Warning",
                 color="white", fontsize=12, fontweight="bold")
    ax.set_xlabel("Mean |SHAP Value|", color="#aaa")

    plt.tight_layout()
    output_path = FIGURES_DIR / f"eval_shap_{model_name.replace(' ', '_').lower()}.png"
    plt.savefig(output_path, dpi=150, bbox_inches="tight", facecolor=DARK_BG)
    plt.close()
    return output_path


def plot_shap_beeswarm(shap_values: np.ndarray, X_sample: np.ndarray,
                       feature_names: list, model_name: str, top_n: int = 15) -> Path:
    """Generate feature effect scatter plots (simplified beeswarm layout)."""
    mean_abs_shap = np.abs(shap_values).mean(axis=0)
    top_indices   = np.argsort(mean_abs_shap)[-top_n:]

    fig, axes = plt.subplots(3, 5, figsize=(18, 10)) if top_n == 15 else \
                plt.subplots(2, 5, figsize=(18, 7))
    fig.patch.set_facecolor(DARK_BG)
    axes_flat = axes.flatten()

    for i, feat_idx in enumerate(top_indices[:len(axes_flat)]):
        ax = axes_flat[i]
        _style_axes(ax)
        feat_vals = X_sample[:, feat_idx]
        s_vals    = shap_values[:, feat_idx]
        ax.scatter(feat_vals, s_vals, c=feat_vals, cmap="coolwarm", alpha=0.5, s=8)
        ax.axhline(0, color="#666", lw=0.8)
        ax.set_title(feature_names[feat_idx], color="white", fontsize=7)
        ax.set_xlabel("Feature value", color="#aaa", fontsize=6)
        ax.set_ylabel("SHAP value",    color="#aaa", fontsize=6)

    for j in range(i + 1, len(axes_flat)):
        axes_flat[j].set_visible(False)

    plt.suptitle(f"SHAP Beeswarm — {model_name} | Early Warning",
                 color="white", fontsize=13, fontweight="bold", y=1.01)
    plt.tight_layout()
    output_path = FIGURES_DIR / f"eval_shap_beeswarm_{model_name.replace(' ', '_').lower()}.png"
    plt.savefig(output_path, dpi=130, bbox_inches="tight", facecolor=DARK_BG)
    plt.close()
    return output_path


def run(model, X_arr: np.ndarray, feature_names: list, model_name: str) -> dict:
    """Execute complete SHAP interpretability suite."""
    print(f"[SHAP] Calculating SHAP attribution values for [{model_name}]...")
    try:
        sv, X_sample = compute_shap_values(model, X_arr)

        print("[SHAP] Generating SHAP bar chart...")
        bar_path = plot_shap_bar(sv, feature_names, model_name)

        print("[SHAP] Generating SHAP beeswarm plot...")
        bee_path = plot_shap_beeswarm(sv, X_sample, feature_names, model_name)

        print(f"   SHAP Bar Chart: {bar_path}")
        print(f"   SHAP Beeswarm Plot: {bee_path}")
        return {"shap_bar": str(bar_path), "shap_beeswarm": str(bee_path)}

    except Exception as exc:
        print(f"   SHAP computation failed (non-fatal): {exc}")
        return {}


if __name__ == "__main__":
    import pickle
    from pipelines.ml.config import BEST_MODEL_PATH, COL_TARGET, TEST_PATH
    bundle  = pickle.loads(BEST_MODEL_PATH.read_bytes())
    test_df = pd.read_csv(TEST_PATH)
    mask    = test_df[COL_TARGET].notna()
    prep    = bundle["preprocessor"]
    X_test  = test_df.loc[mask, [c for c in bundle["feature_cols"] if c in test_df.columns]]
    cat = prep["cat_encoder"].transform(X_test[prep["cat_cols"]].astype(str).fillna("MISSING"))
    num = prep["num_scaler"].transform(prep["num_imputer"].transform(X_test[prep["num_cols"]]))
    X_arr = np.hstack([num, cat])
    run(bundle["model"], X_arr, bundle["feature_names_transformed"], bundle["model_name"])
