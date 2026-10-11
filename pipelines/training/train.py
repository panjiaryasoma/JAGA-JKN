"""Train-only preprocessing and validation-only model/threshold selection."""

import pandas as pd

from packages.ml.preprocessing import build_preprocessor, transform_features
from pipelines.configure.config import ALL_FEATURES, COL_TARGET, DEFAULT_THRESHOLD
from pipelines.evaluation.metrics import evaluate_scores
from pipelines.evaluation.threshold_analysis import select_threshold
from pipelines.training.build_models import get_models


def _load_xy(path, target_col=COL_TARGET):
    df = pd.read_csv(path, dtype={"kbli_code": str})
    if df[target_col].isna().any() or not df[target_col].isin([0, 1]).all():
        raise ValueError("Invalid partition target")
    return df[ALL_FEATURES], df[target_col].astype(int), list(ALL_FEATURES)


def compute_metrics(model, X_arr, y, threshold=DEFAULT_THRESHOLD):
    return evaluate_scores(y, model.predict_proba(X_arr)[:, 1], threshold)


def fit_and_select(train, validation, models=None):
    """No test parameter: threshold/model selection cannot inspect the held-out test."""
    models = get_models() if models is None else models
    preprocessor = build_preprocessor(train[ALL_FEATURES])
    X_train = transform_features(train[ALL_FEATURES], preprocessor)
    X_val = transform_features(validation[ALL_FEATURES], preprocessor)
    y_train, y_val = train[COL_TARGET].astype(int), validation[COL_TARGET].astype(int)
    if set(y_train) != {0, 1}:
        raise ValueError("Both training classes are required")
    best, results = None, {}
    for name, model in models.items():
        print(f"  Fitting {name}", flush=True)
        model.fit(X_train, y_train)
        scores = model.predict_proba(X_val)[:, 1]
        selected = select_threshold(y_val, scores, dataset_role="validation")
        results[name] = {
            "threshold_selection": selected,
            "val_metrics": evaluate_scores(y_val, scores, selected["threshold"]),
        }
        if best is None or selected["f1_macro"] > best["val_f1_macro"]:
            best = {
                "model_name": name,
                "model": model,
                "preprocessor": preprocessor,
                "feature_cols": list(ALL_FEATURES),
                "feature_names_transformed": preprocessor["num_cols"] + preprocessor["cat_cols"],
                "threshold": selected["threshold"],
                "val_f1_macro": selected["f1_macro"],
            }
    if best is None:
        raise ValueError("No candidate models")
    return best, results


def run():
    from pipelines.training.run_pipeline import run as run_pipeline

    return run_pipeline()


if __name__ == "__main__":
    run()
