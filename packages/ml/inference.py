"""Trusted synthetic artifact loading and fail-closed offline inference.

Pickle is executable Python: use only the bundle produced by this pipeline or a trusted
CI run. A checksum detects accidental corruption, not a malicious publisher.
"""

import hashlib
import importlib.metadata
import json
import pickle
import platform
from pathlib import Path

import numpy as np
import pandas as pd

from packages.ml.features import RAW_COLUMNS, build_features
from packages.ml.preprocessing import transform_features
from pipelines.configure.config import ALL_FEATURES, BEST_MODEL_PATH, COLUMN_RENAME_MAP

ARTIFACT_SCHEMA_VERSION = 1


def runtime_versions():
    return {
        "python": ".".join(platform.python_version_tuple()[:2]),
        **{
            name: importlib.metadata.version(name)
            for name in ["numpy", "pandas", "scikit-learn", "lightgbm"]
        },
    }


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_bundle(path=BEST_MODEL_PATH, metadata_path=None):
    path = Path(path)
    metadata_path = Path(metadata_path) if metadata_path else path.with_name("metadata.json")
    if not path.is_file() or not metadata_path.is_file():
        raise FileNotFoundError(
            "Model/metadata missing. Run: uv run --locked --group ml python -m pipelines.training"
        )
    metadata = json.loads(metadata_path.read_text())
    if metadata.get("artifact_schema_version") != ARTIFACT_SCHEMA_VERSION:
        raise ValueError("Unsupported artifact schema version")
    payload = path.read_bytes()
    if metadata.get("artifact_sha256") != hashlib.sha256(payload).hexdigest():
        raise ValueError("Artifact SHA-256 mismatch; refusing to load")
    if metadata.get("runtime_versions") != runtime_versions():
        raise ValueError(
            "Runtime version mismatch; install the supplied uv.lock and Python version"
        )
    if metadata.get("features_admitted") != ALL_FEATURES:
        raise ValueError("Metadata feature schema/order mismatch")
    bundle = pickle.loads(payload)
    expected = {
        "artifact_schema_version": ARTIFACT_SCHEMA_VERSION,
        "feature_cols": ALL_FEATURES,
        "model_version": metadata.get("model_version"),
        "model_name": metadata.get("best_model"),
        "threshold": metadata.get("threshold_used"),
    }
    if any(bundle.get(key) != value for key, value in expected.items()):
        raise ValueError("Model bundle/metadata mismatch")
    threshold = bundle["threshold"]
    if (
        not isinstance(threshold, (int, float))
        or not np.isfinite(threshold)
        or not 0 <= threshold <= 1
    ):
        raise ValueError("Invalid artifact threshold")
    if (
        bundle["preprocessor"]["num_cols"] + bundle["preprocessor"]["cat_cols"]
        != bundle["feature_names_transformed"]
    ):
        raise ValueError("Preprocessor feature schema mismatch")
    if list(bundle["model"].classes_) != [0, 1]:
        raise ValueError("Unexpected model classes")
    return bundle


def predict_scores(bundle, features):
    scores = bundle["model"].predict_proba(transform_features(features, bundle["preprocessor"]))[
        :, 1
    ]
    if not np.isfinite(scores).all() or ((scores < 0) | (scores > 1)).any():
        raise ValueError("Invalid model scores")
    return scores


def predict_record(bundle, record):
    if record.get("is_synthetic") is not True:
        raise ValueError("Only explicitly synthetic input is accepted")
    if any(pd.isna(record.get(key)) for key in RAW_COLUMNS):
        raise ValueError("Incomplete inference input; abstain instead of filling missing evidence")
    features = build_features(pd.DataFrame([record]))
    score = float(predict_scores(bundle, features)[0])
    return {
        "model_version": bundle["model_version"],
        "model_name": bundle["model_name"],
        "status": "EXPERIMENTAL_SYNTHETIC",
        "period_month": record["period_month"],
        "target_period": str(pd.Period(record["period_month"], freq="M") + 1),
        "score": score,
        "score_semantics": "uncalibrated_synthetic_non_normal_score",
        "threshold": bundle["threshold"],
        "experimental_prediction": int(score >= bundle["threshold"]),
        "is_synthetic": True,
        "policy_status": "UNRESOLVED",
    }


def record_from_api(company_response, evidence_response):
    """Adapt the backend's existing company + one-month evidence response envelopes."""
    company, evidence = company_response["data"], evidence_response["data"]
    cm, em = company_response["meta"], evidence_response["meta"]
    if cm.get("is_synthetic") is not True or em.get("is_synthetic") is not True:
        raise ValueError("Only synthetic API datasets are supported")
    for key in ["dataset_id", "source_commit"]:
        if not cm.get(key) or cm[key] != em.get(key):
            raise ValueError("API dataset identity mismatch")
    if not company.get("id_badan_usaha") or company["id_badan_usaha"] != evidence.get(
        "id_badan_usaha"
    ):
        raise ValueError("API company identity mismatch")
    raw = {COLUMN_RENAME_MAP.get(k, k): v for k, v in company.items()}
    raw.update(period_month=evidence["periode_bulan"], is_synthetic=True)
    for domain in ["registration", "wage", "contribution"]:
        group = evidence[domain]
        for name in [
            "evidence_valid",
            "evidence_quality",
            "source_metadata_valid",
            "period_binding_valid",
        ]:
            raw[f"{domain}_{name}"] = group[name]
    reg, wage, contribution = [evidence[x] for x in ["registration", "wage", "contribution"]]
    for name in ["worker_set_valid", "explanation_metadata_valid"]:
        raw[f"registration_{name}"] = reg[name]
    for name in ["observed_registered_worker_count", "unexpected_worker_count"]:
        raw[name] = reg[name]
    raw["observed_wage_signal_rp"] = wage["observed_wage_signal_rp"]
    raw["wage_semantic_consistency_valid"] = wage["semantic_consistency_valid"]
    raw["payment_semantic_consistency_valid"] = contribution["semantic_consistency_valid"]
    return raw


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Offline synthetic-only inference")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--model", type=Path, default=BEST_MODEL_PATH)
    args = parser.parse_args()
    print(
        json.dumps(
            predict_record(load_bundle(args.model), json.loads(args.input.read_text())), indent=2
        )
    )


if __name__ == "__main__":
    main()
