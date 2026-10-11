"""Validation-only macro-F1 threshold selection. No operational threshold is approved."""

import json

import numpy as np
import pandas as pd

from pipelines.configure.config import COL_TARGET, THRESHOLD_PATH, VAL_PATH


def select_threshold(y_true, scores, *, dataset_role):
    if dataset_role != "validation":
        raise ValueError("Threshold selection requires validation data")
    y = np.asarray(y_true)
    scores = np.asarray(scores, dtype=float)
    if (
        len(y) == 0
        or y.shape != scores.shape
        or not np.isin(y, [0, 1]).all()
        or not np.isfinite(scores).all()
        or ((scores < 0) | (scores > 1)).any()
    ):
        raise ValueError("Invalid validation labels or scores")
    if len(np.unique(y)) != 2:
        raise ValueError("Threshold selection requires both validation classes")
    order = np.argsort(scores, kind="stable")
    ordered_y = y[order]
    cumulative = np.r_[0, np.cumsum(ordered_y)]
    candidates = np.unique(np.r_[0.0, 0.5, 1.0, scores])
    starts = np.searchsorted(scores[order], candidates, side="left")
    fn = cumulative[starts]
    tp = y.sum() - fn
    tn = starts - fn
    fp = len(y) - starts - tp
    positive_f1 = np.divide(
        2 * tp, 2 * tp + fp + fn, out=np.zeros(len(tp)), where=(2 * tp + fp + fn) != 0
    )
    negative_f1 = np.divide(
        2 * tn, 2 * tn + fp + fn, out=np.zeros(len(tn)), where=(2 * tn + fp + fn) != 0
    )
    macro = (positive_f1 + negative_f1) / 2
    best = min(
        range(len(candidates)), key=lambda i: (-macro[i], abs(candidates[i] - 0.5), candidates[i])
    )
    return {
        "threshold": float(candidates[best]),
        "f1_macro": float(macro[best]),
        "selection_dataset": "validation",
        "selection_metric": "f1_macro",
        "candidate_count": len(candidates),
        "operational_threshold": None,
    }


def run():
    from packages.ml.inference import load_bundle, predict_scores

    bundle = load_bundle()
    validation = pd.read_csv(VAL_PATH, dtype={"kbli_code": str})
    result = select_threshold(
        validation[COL_TARGET],
        predict_scores(bundle, validation[bundle["feature_cols"]]),
        dataset_role="validation",
    )
    THRESHOLD_PATH.write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    print(run())
