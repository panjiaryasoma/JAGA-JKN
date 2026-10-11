"""Frozen-threshold evaluation, including class-imbalance baselines."""

import json

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from pipelines.configure.config import COL_TARGET, DEFAULT_THRESHOLD, METRICS_PATH, TEST_PATH


def load_best_model():
    from packages.ml.inference import load_bundle

    return load_bundle()


def predict_with_threshold(bundle, X_arr, threshold=None):
    threshold = bundle["threshold"] if threshold is None else threshold
    scores = bundle["model"].predict_proba(X_arr)[:, 1]
    return (scores >= threshold).astype(int), scores


def compute_full_metrics(y_true, y_pred, y_proba=None, threshold=DEFAULT_THRESHOLD):
    y = np.asarray(y_true)
    result = {
        "threshold": float(threshold),
        "n": len(y),
        "positive_count": int(y.sum()),
        "accuracy": float(accuracy_score(y, y_pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y, y_pred)),
        "f1_macro": float(f1_score(y, y_pred, labels=[0, 1], average="macro", zero_division=0)),
        "f1_binary": float(f1_score(y, y_pred, zero_division=0)),
        "precision_binary": float(precision_score(y, y_pred, zero_division=0)),
        "recall_binary": float(recall_score(y, y_pred, zero_division=0)),
        "confusion_matrix": confusion_matrix(y, y_pred, labels=[0, 1]).tolist(),
        "per_class": classification_report(
            y,
            y_pred,
            labels=[0, 1],
            target_names=["NORMAL", "NON-NORMAL"],
            zero_division=0,
            output_dict=True,
        ),
        "classification_report": classification_report(
            y, y_pred, labels=[0, 1], target_names=["NORMAL", "NON-NORMAL"], zero_division=0
        ),
    }
    if y_proba is not None:
        both = len(np.unique(y)) == 2
        result.update(
            roc_auc=float(roc_auc_score(y, y_proba)) if both else None,
            pr_auc=float(average_precision_score(y, y_proba)) if both else None,
            brier_score=float(brier_score_loss(y, y_proba)),
        )
    return result


def evaluate_scores(y, scores, threshold):
    return compute_full_metrics(y, (np.asarray(scores) >= threshold).astype(int), scores, threshold)


def baseline_metrics(y_train, y_test):
    return {
        name: evaluate_scores(y_test, np.full(len(y_test), score), 0.5)
        for name, score in [
            ("always_normal", 0.0),
            ("always_non_normal", 1.0),
            ("training_prior", float(np.mean(y_train))),
        ]
    }


def run(bundle=None, X_test_arr=None, y_test=None):
    from packages.ml.preprocessing import transform_features

    bundle = load_best_model() if bundle is None else bundle
    if X_test_arr is None or y_test is None:
        test = pd.read_csv(TEST_PATH, dtype={"kbli_code": str})
        y_test = test[COL_TARGET].astype(int)
        X_test_arr = transform_features(test[bundle["feature_cols"]], bundle["preprocessor"])
    predicted, scores = predict_with_threshold(bundle, X_test_arr)
    metrics = compute_full_metrics(y_test, predicted, scores, bundle["threshold"])
    output = {
        "model_name": bundle["model_name"],
        "test_metrics": metrics,
        "classification_report": metrics["classification_report"],
        "n_test": len(y_test),
    }
    METRICS_PATH.write_text(json.dumps(output, indent=2, allow_nan=False) + "\n")
    return output, predicted, scores


if __name__ == "__main__":
    print(run()[0]["classification_report"])
