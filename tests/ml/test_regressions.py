"""Regression tests for observed ML failures and the repaired inference boundary."""

import importlib

import numpy as np
import pandas as pd
import pytest

from pipelines.configure.config import (
    ALL_EVIDENCE_VALID_COLS,
    ALL_FEATURES,
    FEATURES_EVIDENCE_QUALITY,
    FEATURES_MASTER,
    FEATURES_OBSERVATION,
    PROJECT_ROOT,
)
from pipelines.features.feature_engineering import (
    _cast_boolean_columns,
    _normalize_quality_columns,
    build_full_dataset,
)

QUALITY = [x for x in FEATURES_EVIDENCE_QUALITY if x.endswith("_evidence_quality")]


def test_quality_categories_remain_distinct():
    frame = pd.DataFrame({key: ["HIGH", "MEDIUM", "LOW"] for key in QUALITY})
    result = _normalize_quality_columns(frame)
    for key in QUALITY:
        assert result[key].tolist() == [1.0, 0.5, 0.0]


def test_unknown_quality_is_rejected():
    frame = pd.DataFrame({key: ["SUPER_HIGH"] for key in QUALITY})
    with pytest.raises(ValueError, match="quality"):
        _normalize_quality_columns(frame)


def test_invalid_boolean_is_not_silently_zero():
    frame = pd.DataFrame({key: ["broken"] for key in ALL_EVIDENCE_VALID_COLS})
    with pytest.raises(ValueError, match="boolean"):
        _cast_boolean_columns(frame)


@pytest.mark.parametrize("module", ["pipelines.evaluation.metrics", "pipelines.evaluation.plots"])
def test_evaluation_modules_import_from_actual_config_location(module):
    importlib.import_module(module)


def test_held_feature_is_excluded():
    assert "month_index" not in ALL_FEATURES


@pytest.fixture(scope="session")
def dataset():
    return build_full_dataset()


def test_lead_target_is_exact_next_month(dataset):
    assert "target_period" in dataset.columns
    valid = dataset.dropna(subset=["target_lead_1"])
    months = pd.PeriodIndex(valid.period_month, freq="M")
    assert valid.target_period.tolist() == (months + 1).astype(str).tolist()
    actual = dataset.set_index(["company_id", "period_month"]).label_binary
    for row in valid.itertuples():
        assert row.target_lead_1 == actual.loc[(row.company_id, row.target_period)]


def test_source_grid_and_labels_fail_closed():
    from pipelines.features.feature_engineering import prepare_dataset

    evidence = pd.read_csv(PROJECT_ROOT / "data/synthetic/curated/curated_kepatuhan_evidence.csv")
    master = pd.read_csv(PROJECT_ROOT / "data/synthetic/curated/curated_master_badan_usaha.csv")
    for kind in ("duplicate", "gap", "bad_label", "bad_period", "missing_feature"):
        bad = evidence.copy()
        if kind == "duplicate":
            bad = pd.concat([bad, bad.iloc[[0]]], ignore_index=True)
        elif kind == "gap":
            bad = bad.drop(index=1)
        elif kind == "bad_label":
            bad.loc[0, "synthetic_risk_mode_ground_truth"] = None
        elif kind == "bad_period":
            bad.loc[0, "periode_bulan"] = "2025-13"
        else:
            bad = bad.drop(columns=["observed_wage_signal_rp"])
        with pytest.raises(ValueError):
            prepare_dataset(bad, master)


def test_temporal_and_company_separation(dataset):
    from pipelines.features.data_split import make_partitions

    partitions, manifest = make_partitions(dataset)
    train, validation, test = [partitions["group_time"][x] for x in ("train", "val", "test")]
    assert set(train.company_id).isdisjoint(validation.company_id)
    assert set(train.company_id).isdisjoint(test.company_id)
    assert set(validation.company_id).isdisjoint(test.company_id)
    assert train.target_period.max() <= validation.period_month.min()
    assert validation.target_period.max() <= test.period_month.min()
    assert train.target_period.max() == "2026-03"
    assert validation.target_period.min() == "2026-04"
    assert test.target_period.min() == "2026-07"
    assert manifest["test_history"] == "PREVIOUSLY_INSPECTED_SYNTHETIC_BENCHMARK"


def test_threshold_selector_requires_validation_role():
    from pipelines.evaluation.threshold_analysis import select_threshold

    y, scores = np.array([0, 0, 1, 1]), np.array([0.1, 0.2, 0.3, 0.4])
    with pytest.raises(ValueError, match="validation"):
        select_threshold(y, scores, dataset_role="test")
    result = select_threshold(y, scores, dataset_role="validation")
    assert result["f1_macro"] == 1.0
    assert result["threshold"] <= 0.3


def test_inference_feature_builder_does_not_require_future_or_labels(dataset):
    from packages.ml.features import build_features

    raw_keys = ALL_EVIDENCE_VALID_COLS + QUALITY + FEATURES_MASTER + FEATURES_OBSERVATION
    raw = dataset.iloc[:1][list(dict.fromkeys(raw_keys + ["period_month"]))].copy()
    # Canonical online raw quality values, not already engineered training columns.
    for key in QUALITY:
        raw[key] = "HIGH"
    for key in ALL_EVIDENCE_VALID_COLS:
        raw[key] = True
    generated = build_features(raw)
    assert generated.columns.tolist() == ALL_FEATURES
    assert generated.shape == (1, len(ALL_FEATURES))
    with pytest.raises(ValueError):
        build_features(raw.drop(columns=[FEATURES_OBSERVATION[0]]))
