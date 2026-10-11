"""Behavioral tests for selection isolation, train/serve parity, and artifact integrity."""

import copy
import importlib
import json

import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import LogisticRegression

from packages.ml.inference import load_bundle, predict_record, predict_scores
from packages.ml.preprocessing import transform_features
from pipelines.configure.config import ALL_FEATURES, COL_TARGET, PROJECT_ROOT
from pipelines.features.data_split import make_partitions
from pipelines.features.feature_engineering import build_full_dataset
from pipelines.training.train import fit_and_select


@pytest.fixture(scope="module")
def training_fixture():
    partitions, _ = make_partitions(build_full_dataset())
    train = partitions["group_time"]["train"].iloc[:560]
    val = partitions["group_time"]["val"].iloc[:90]
    bundle, selection = fit_and_select(
        train, val, {"logistic-test": LogisticRegression(max_iter=1000)}
    )
    return train, val, bundle, selection


def test_preprocessor_fit_does_not_use_validation(training_fixture):
    train, val, bundle, _ = training_fixture
    prep = bundle["preprocessor"]
    observed = "observed_wage_signal_rp"
    i = prep["num_cols"].index(observed)
    assert prep["num_imputer"].statistics_[i] == train[observed].median()
    before = copy.deepcopy(prep["num_imputer"].statistics_)
    changed = val[ALL_FEATURES].copy()
    changed[observed] = 9e15
    changed["province"] = "UNSEEN"
    transformed = transform_features(changed, prep)
    assert (transformed["province"] == -1).all()
    np.testing.assert_array_equal(before, prep["num_imputer"].statistics_)


def test_future_labels_do_not_change_past_features():
    from pipelines.configure.config import DATA_CURATED_EVIDENCE, DATA_MASTER_BU
    from pipelines.features.feature_engineering import prepare_dataset

    evidence, master = pd.read_csv(DATA_CURATED_EVIDENCE), pd.read_csv(DATA_MASTER_BU)
    original = prepare_dataset(evidence, master)
    evidence.loc[evidence.periode_bulan >= "2026-04", "synthetic_risk_mode_ground_truth"] = (
        "MULTI_SIGNAL"
    )
    changed = prepare_dataset(evidence, master)
    pd.testing.assert_frame_equal(original[ALL_FEATURES], changed[ALL_FEATURES])
    mask = original.target_period <= "2026-03"
    pd.testing.assert_series_equal(original.loc[mask, COL_TARGET], changed.loc[mask, COL_TARGET])


def test_selection_api_has_no_test_input(training_fixture):
    import inspect

    assert list(inspect.signature(fit_and_select).parameters) == ["train", "validation", "models"]
    _, val, bundle, results = training_fixture
    selected = results["logistic-test"]["threshold_selection"]
    assert selected["selection_dataset"] == "validation"
    from sklearn.metrics import f1_score

    predictions = predict_scores(bundle, val[ALL_FEATURES]) >= bundle["threshold"]
    assert selected["f1_macro"] == f1_score(val[COL_TARGET], predictions, average="macro")


def test_reload_and_corruption_checks(tmp_path, training_fixture):
    from pipelines.training.artifacts import export_bundle

    _, val, bundle, selection = training_fixture
    path = tmp_path / "best_model.pkl"
    export_bundle(bundle, path, {"selection": selection})
    loaded = load_bundle(path)
    np.testing.assert_array_equal(
        predict_scores(bundle, val[ALL_FEATURES]), predict_scores(loaded, val[ALL_FEATURES])
    )
    metadata_path = path.with_name("metadata.json")
    original = metadata_path.read_text()
    for key, replacement in [
        ("runtime_versions", {}),
        ("features_admitted", list(reversed(ALL_FEATURES))),
        ("threshold_used", -1),
        ("model_version", "wrong"),
    ]:
        metadata = json.loads(original)
        metadata[key] = replacement
        metadata_path.write_text(json.dumps(metadata))
        with pytest.raises(ValueError):
            load_bundle(path)
    metadata_path.write_text(original)
    path.write_bytes(path.read_bytes() + b"corrupted")
    with pytest.raises(ValueError, match="SHA-256"):
        load_bundle(path)


def test_strict_inference_and_order(training_fixture):
    from packages.ml.features import RAW_COLUMNS, build_features
    from pipelines.configure.config import COLUMN_RENAME_MAP, DATA_CURATED_EVIDENCE, DATA_MASTER_BU

    _, val, bundle, _ = training_fixture
    evidence = pd.read_csv(DATA_CURATED_EVIDENCE).rename(columns=COLUMN_RENAME_MAP)
    master = pd.read_csv(DATA_MASTER_BU, dtype={"kode_kbli": str}).rename(columns=COLUMN_RENAME_MAP)
    row = evidence.merge(master, on="company_id", suffixes=("", "_master")).iloc[0]
    record = {
        key: row[key].item() if hasattr(row[key], "item") else row[key] for key in RAW_COLUMNS
    }
    record["is_synthetic"] = True
    bundle["model_version"] = "test"
    output = predict_record(bundle, record)
    assert output["target_period"] == str(pd.Period(record["period_month"], freq="M") + 1)
    assert output["score"] == predict_scores(bundle, build_features(pd.DataFrame([record])))[0]
    for bad in [
        dict(record, is_synthetic=False),
        dict(record, observed_wage_signal_rp=None),
        dict(record, registration_evidence_quality="UNKNOWN"),
    ]:
        with pytest.raises(ValueError):
            predict_record(bundle, bad)
    with pytest.raises(ValueError, match="order"):
        predict_scores(bundle, val[list(reversed(ALL_FEATURES))])


@pytest.mark.parametrize(
    "path",
    sorted(
        p
        for p in (PROJECT_ROOT / "pipelines").glob("*/*.py")
        if p.parent.name != "synthetic" and p.name != "__main__.py"
    ),
)
def test_all_ml_modules_import(path):
    importlib.import_module(".".join(path.relative_to(PROJECT_ROOT).with_suffix("").parts))


def test_actual_backend_response_adapter_matches_training_features():
    from packages.ml.features import build_features
    from packages.ml.inference import record_from_api

    fixture = json.loads((PROJECT_ROOT / "tests/ml/fixtures/backend_pair.json").read_text())
    raw = record_from_api(**fixture)
    features = build_features(pd.DataFrame([raw])).reset_index(drop=True)
    dataset = build_full_dataset()
    expected = dataset[(dataset.company_id == "BU-0001") & (dataset.period_month == "2025-01")]
    pd.testing.assert_frame_equal(features, expected[ALL_FEATURES].reset_index(drop=True))
    for changed in ["dataset_id", "source_commit", "is_synthetic"]:
        invalid = copy.deepcopy(fixture)
        invalid["evidence_response"]["meta"][changed] = (
            False if changed == "is_synthetic" else "mismatched"
        )
        with pytest.raises(ValueError):
            record_from_api(**invalid)
    invalid = copy.deepcopy(fixture)
    invalid["evidence_response"]["data"]["id_badan_usaha"] = "BU-0002"
    with pytest.raises(ValueError):
        record_from_api(**invalid)
