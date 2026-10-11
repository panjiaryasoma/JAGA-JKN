"""
Model training and validation selection for Early Warning (t+1).
"""

import json
import pickle
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    classification_report,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.preprocessing import OrdinalEncoder, StandardScaler

warnings.filterwarnings("ignore")

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from pipelines.ml.config import (
    ALL_FEATURES,
    BEST_MODEL_PATH,
    CATEGORICAL_FEATURES,
    COL_TARGET,
    DEFAULT_THRESHOLD,
    MODEL_METADATA_PATH,
    MODEL_SEED,
    MODELS_DIR,
    OPERATIONAL_THRESHOLD,
    SPLIT_SEED,
    TEST_PATH,
    TRAIN_PATH,
    VAL_PATH,
)
from pipelines.training.build_models import get_models

MODELS_DIR.mkdir(parents=True, exist_ok=True)


def _load_xy(path: Path, target_col: str = COL_TARGET) -> tuple:
    """Load dataset partition and extract valid feature matrix and target series."""
    df = pd.read_csv(path)
    valid_mask = df[target_col].notna()
    feature_cols = [c for c in ALL_FEATURES if c in df.columns]
    X = df.loc[valid_mask, feature_cols].copy()
    y = df.loc[valid_mask, target_col].astype(int)
    return X, y, feature_cols


def build_preprocessor(X_train: pd.DataFrame) -> dict:
    """Fit feature scalers, imputers, and categorical encoders on training data only."""
    cat_cols = [c for c in CATEGORICAL_FEATURES if c in X_train.columns]
    num_cols = [c for c in X_train.columns if c not in cat_cols]

    cat_encoder = OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)
    cat_encoder.fit(X_train[cat_cols].astype(str).fillna("MISSING"))

    num_imputer = SimpleImputer(strategy="median")
    num_imputer.fit(X_train[num_cols])

    num_scaler = StandardScaler()
    num_scaler.fit(num_imputer.transform(X_train[num_cols]))

    return {
        "cat_cols": cat_cols,
        "num_cols": num_cols,
        "cat_encoder": cat_encoder,
        "num_imputer": num_imputer,
        "num_scaler": num_scaler,
    }


def transform_features(X: pd.DataFrame, preprocessor: dict) -> np.ndarray:
    """Transform feature dataframe using previously fitted preprocessor dictionary."""
    cat_encoded = preprocessor["cat_encoder"].transform(
        X[preprocessor["cat_cols"]].astype(str).fillna("MISSING")
    )
    num_scaled = preprocessor["num_scaler"].transform(
        preprocessor["num_imputer"].transform(X[preprocessor["num_cols"]])
    )
    return np.hstack([num_scaled, cat_encoded])


def compute_metrics(model, X_arr: np.ndarray, y: pd.Series,
                    threshold: float = DEFAULT_THRESHOLD) -> dict:
    """Calculate comprehensive evaluation metrics at a designated decision threshold."""
    has_proba = hasattr(model, "predict_proba")
    if has_proba:
        y_proba = model.predict_proba(X_arr)[:, 1]
        y_pred  = (y_proba >= threshold).astype(int)
    else:
        y_pred  = model.predict(X_arr)
        y_proba = None

    metrics = {
        "threshold": threshold,
        "f1_macro":          round(f1_score(y, y_pred, average="macro", zero_division=0), 4),
        "f1_binary":         round(f1_score(y, y_pred, average="binary", zero_division=0), 4),
        "precision_binary":  round(precision_score(y, y_pred, zero_division=0), 4),
        "recall_binary":     round(recall_score(y, y_pred, zero_division=0), 4),
        "balanced_accuracy": round(balanced_accuracy_score(y, y_pred), 4),
    }
    if y_proba is not None:
        metrics["roc_auc"] = round(roc_auc_score(y, y_proba), 4)
        metrics["pr_auc"]  = round(average_precision_score(y, y_proba), 4)

    metrics["classification_report"] = classification_report(
        y, y_pred, target_names=["NORMAL", "NON-NORMAL"], zero_division=0
    )
    return metrics


def run() -> dict:
    """Execute model training, validation selection, and export best model bundle."""
    print("[Training] Loading partitioned datasets...")
    X_train, y_train, feature_cols = _load_xy(TRAIN_PATH)
    X_val,   y_val,   _            = _load_xy(VAL_PATH)
    X_test,  y_test,  _            = _load_xy(TEST_PATH)

    print(f"   Sample sizes -> Train: {len(X_train):,} | Val: {len(X_val):,} | Test: {len(X_test):,}")
    print(f"   Feature Count: {len(feature_cols)} | Target Column: {COL_TARGET}")

    print("[Training] Fitting feature preprocessor on training data...")
    preprocessor = build_preprocessor(X_train)
    X_train_arr  = transform_features(X_train, preprocessor)
    X_val_arr    = transform_features(X_val,   preprocessor)
    X_test_arr   = transform_features(X_test,  preprocessor)
    feature_names = preprocessor["num_cols"] + preprocessor["cat_cols"]

    models = get_models()
    all_validation_results = {}
    best_name   = None
    best_val_f1 = -1.0
    best_model  = None

    for name, model in models.items():
        print(f"\n   [{name}] Fitting model...")
        model.fit(X_train_arr, y_train)

        # Validation evaluation to pick best model
        val_m = compute_metrics(model, X_val_arr, y_val, DEFAULT_THRESHOLD)
        print(f"   Val  -> F1-macro: {val_m['f1_macro']:.4f} | F1-binary: {val_m['f1_binary']:.4f} "
              f"| Precision: {val_m['precision_binary']:.4f} | Recall: {val_m['recall_binary']:.4f}")

        all_validation_results[name] = {
            "val_metrics": {k: v for k, v in val_m.items() if k != "classification_report"},
        }

        if val_m["f1_macro"] > best_val_f1:
            best_val_f1 = val_m["f1_macro"]
            best_name   = name
            best_model  = model

    # final evaluation on test partition for the best model only
    print(f"\n[Training] Optimal Model Selected: [{best_name}] (Validation F1-macro={best_val_f1:.4f})")
    print("[Training] Evaluating best model on test partition (one-time final test)...")
    test_m = compute_metrics(best_model, X_test_arr, y_test, DEFAULT_THRESHOLD)

    print(f"   Test -> F1-macro: {test_m['f1_macro']:.4f} | F1-binary: {test_m['f1_binary']:.4f} "
          f"| Precision: {test_m['precision_binary']:.4f} | Recall: {test_m['recall_binary']:.4f}")
    print()
    print(test_m["classification_report"])

    if test_m["f1_macro"] > 0.95:
        print("  !! WARNING: F1-macro > 0.95 — Possible hidden leakage detected! Re-audit required.")

    # Export best model bundle
    print(f"[Training] Persisting best model bundle to: {BEST_MODEL_PATH}...")
    bundle = {
        "model_name": best_name,
        "model": best_model,
        "preprocessor": preprocessor,
        "feature_cols": feature_cols,
        "feature_names_transformed": feature_names,
        "threshold": DEFAULT_THRESHOLD,
        "val_f1_macro": best_val_f1,
        "test_metrics": {k: v for k, v in test_m.items() if k != "classification_report"},
    }
    BEST_MODEL_PATH.write_bytes(pickle.dumps(bundle))

    # Export metadata manifest
    metadata = {
        "created_by": "Haidir",
        "objective": "Early Warning Lead-1 Month (t+1)",
        "dataset_commit": "9390d36a1adbef6f17aa6804dd6c56d290e06d04",
        "split_seed": SPLIT_SEED,
        "model_seed": MODEL_SEED,
        "algorithms_evaluated": list(models.keys()),
        "best_model": best_name,
        "best_val_f1_macro": best_val_f1,
        "test_f1_macro": test_m["f1_macro"],
        "test_f1_binary": test_m["f1_binary"],
        "test_precision": test_m["precision_binary"],
        "test_recall": test_m["recall_binary"],
        "threshold_used": DEFAULT_THRESHOLD,
        "threshold_operational_target": OPERATIONAL_THRESHOLD,
        "feature_count": len(feature_cols),
        "features_admitted": feature_cols,
        "disclaimer": "Synthetic benchmark dataset. Strictly forbidden for real JKN operational sanctions.",
        "all_validation_results": {
            name: res["val_metrics"] for name, res in all_validation_results.items()
        },
    }
    MODEL_METADATA_PATH.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"   Model metadata manifest written to: {MODEL_METADATA_PATH}")

    return {
        "best_name": best_name,
        "best_model": best_model,
        "preprocessor": preprocessor,
        "feat_names": feature_names,
        "test_metrics": test_m,
        "all_validation_results": all_validation_results,
        "X_test_arr": X_test_arr,
        "y_test": y_test,
    }


if __name__ == "__main__":
    run()
