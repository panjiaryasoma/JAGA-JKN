"""
Compute full evaluation metrics on the test partition.

"""

import json
import pickle
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    classification_report,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

warnings.filterwarnings("ignore")

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from pipelines.ml.config import (
    BEST_MODEL_PATH,
    COL_TARGET,
    DEFAULT_THRESHOLD,
    METRICS_PATH,
    RESULTS_DIR,
    TEST_PATH,
)

RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def load_best_model() -> dict:
    """Load serialized model bundle from BEST_MODEL_PATH."""
    if not BEST_MODEL_PATH.exists():
        raise FileNotFoundError(f"Model artifact not found: {BEST_MODEL_PATH}. Run training first.")
    return pickle.loads(BEST_MODEL_PATH.read_bytes())


def predict_with_threshold(bundle: dict, X_arr: np.ndarray,
                           threshold: float = DEFAULT_THRESHOLD) -> tuple:
    """Generate predictions and probabilities using the model bundle and threshold."""
    model = bundle["model"]
    if hasattr(model, "predict_proba"):
        y_proba = model.predict_proba(X_arr)[:, 1]
        y_pred  = (y_proba >= threshold).astype(int)
    else:
        y_pred  = model.predict(X_arr)
        y_proba = None
    return y_pred, y_proba


def compute_full_metrics(y_true, y_pred, y_proba=None, threshold=DEFAULT_THRESHOLD) -> dict:
    """Calculate all standard classification metrics."""
    metrics = {
        "threshold":          threshold,
        "accuracy":           round(accuracy_score(y_true, y_pred), 4),
        "balanced_accuracy":  round(balanced_accuracy_score(y_true, y_pred), 4),
        "f1_macro":           round(f1_score(y_true, y_pred, average="macro", zero_division=0), 4),
        "f1_weighted":        round(f1_score(y_true, y_pred, average="weighted", zero_division=0), 4),
        "f1_binary":          round(f1_score(y_true, y_pred, average="binary", zero_division=0), 4),
        "precision_binary":   round(precision_score(y_true, y_pred, zero_division=0), 4),
        "recall_binary":      round(recall_score(y_true, y_pred, zero_division=0), 4),
    }
    if y_proba is not None:
        metrics["roc_auc"] = round(roc_auc_score(y_true, y_proba), 4)
        metrics["pr_auc"]  = round(average_precision_score(y_true, y_proba), 4)

    metrics["classification_report"] = classification_report(
        y_true, y_pred, target_names=["NORMAL", "NON-NORMAL"], zero_division=0
    )
    return metrics


def run(bundle: dict = None, X_test_arr: np.ndarray = None, y_test=None) -> tuple:
    """Compute and persist test set metrics. Returns (output_dict, y_pred, y_proba)."""
    if bundle is None:
        bundle = load_best_model()

    if X_test_arr is None or y_test is None:
        test_df = pd.read_csv(TEST_PATH)
        mask    = test_df[COL_TARGET].notna()
        feature_cols = bundle["feature_cols"]
        X_test  = test_df.loc[mask, [c for c in feature_cols if c in test_df.columns]]
        y_test  = test_df.loc[mask, COL_TARGET].astype(int)

        prep = bundle["preprocessor"]
        cat  = prep["cat_encoder"].transform(
            X_test[prep["cat_cols"]].astype(str).fillna("MISSING")
        )
        num  = prep["num_scaler"].transform(prep["num_imputer"].transform(X_test[prep["num_cols"]]))
        X_test_arr = np.hstack([num, cat])

    threshold = bundle.get("threshold", DEFAULT_THRESHOLD)
    y_pred, y_proba = predict_with_threshold(bundle, X_test_arr, threshold)
    metrics = compute_full_metrics(y_test, y_pred, y_proba, threshold)

    output = {
        "model_name": bundle["model_name"],
        "objective": "Early Warning Lead-1 Month (t+1)",
        "test_metrics": {k: v for k, v in metrics.items() if k != "classification_report"},
        "classification_report": metrics["classification_report"],
        "n_test": len(y_test),
        "n_positive_test": int(y_test.sum()),
    }

    def _clean_numbers(obj):
        if isinstance(obj, dict):          return {k: _clean_numbers(v) for k, v in obj.items()}
        if isinstance(obj, list):          return [_clean_numbers(i) for i in obj]
        if isinstance(obj, (np.integer,)): return int(obj)
        if isinstance(obj, (np.floating,)): return float(obj)
        return obj

    METRICS_PATH.write_text(
        json.dumps(_clean_numbers(output), indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"   Test evaluation metrics written to: {METRICS_PATH}")
    return output, y_pred, y_proba


if __name__ == "__main__":
    result, _, _ = run()
    print(result["classification_report"])
