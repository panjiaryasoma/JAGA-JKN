"""Experimental ML serving: failure modes, access control and serving isolation."""

import json
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from apps.api.config import Settings
from apps.api.experimental_ml import (
    ExperimentalResult,
    InferenceUnavailable,
    ModelService,
    open_trusted_model,
)
from apps.api.main import create_app

REVIEWER = "r" * 40
SUPERVISOR = "s" * 40
PREDICT = "/api/v1/ml/experimental/badan-usaha/BU-0001/2025-01"


def auth(token=REVIEWER):
    return {"Authorization": f"Bearer {token}"}


def enabled(snapshot):
    return replace(
        snapshot,
        reviewer_token=REVIEWER,
        supervisor_token=SUPERVISOR,
        experimental_ml_enabled=True,
        ml_model_path=snapshot.data_root / "best_model.pkl",
    )


def assert_safe_error(response, status, code):
    assert response.status_code == status
    payload = response.json()["error"]
    assert payload["code"] == code
    assert payload["request_id"] == response.headers["x-request-id"]
    assert "SECRET" not in response.text


def fake_model(snapshot, path):
    return ModelService(bundle={}, model_version="synthetic-test", model_name="TestModel")


def success_result(snapshot, service, company, evidence):
    return ExperimentalResult(
        status="EXPERIMENTAL_SYNTHETIC",
        id_badan_usaha=company.id_badan_usaha,
        period_month=evidence.periode_bulan,
        target_period="2025-02",
        model_version=service.model_version,
        model_name=service.model_name,
        score=0.25,
        score_semantics="uncalibrated_synthetic_non_normal_score",
        threshold=0.5,
        experimental_prediction=0,
    )


def test_opt_in_is_strict(monkeypatch):
    monkeypatch.setenv("JAGA_EXPERIMENTAL_ML_ENABLED", "true")
    with pytest.raises(ValueError, match="JAGA_EXPERIMENTAL_ML_ENABLED"):
        Settings.from_environment()
    monkeypatch.setenv("JAGA_EXPERIMENTAL_ML_ENABLED", "1")
    assert Settings.from_environment().experimental_ml_enabled is True
    monkeypatch.setenv("JAGA_EXPERIMENTAL_ML_ENABLED", "0")
    assert Settings.from_environment().experimental_ml_enabled is False
    with pytest.raises(ValueError, match="boolean"):
        Settings(experimental_ml_enabled="true")


def test_default_disabled_isolated_from_core_api(snapshot):
    settings = replace(snapshot, reviewer_token=REVIEWER)
    with TestClient(create_app(settings)) as client:
        ml = client.get("/api/v1/ml/status").json()["data"]
        assert ml["status"] == "NOT_CONFIGURED"
        assert ml["prediction_available"] is False
        assert ml["experimental_status"] == "DISABLED"
        assert client.get("/api/v1/capabilities").json()["data"]["experimental_ml"] == "DISABLED"
        assert_safe_error(client.get(PREDICT, headers=auth()), 503, "ML_EXPERIMENT_DISABLED")
        assert client.get("/health/ready").status_code == 200
        assert client.get("/api/v1/dataset").status_code == 200


def test_missing_model_does_not_break_evidence_or_cases(snapshot):
    with TestClient(create_app(enabled(snapshot))) as client:
        assert client.get("/api/v1/ml/status").json()["data"]["experimental_status"] == (
            "UNAVAILABLE"
        )
        assert_safe_error(client.get(PREDICT, headers=auth()), 503, "ML_ARTIFACT_UNAVAILABLE")
        assert client.get("/api/v1/dataset").status_code == 200
        assert client.get("/health/ready").status_code == 200
        assert client.get("/api/v1/cases", headers=auth()).status_code == 200


def test_serving_requires_auth_and_uses_existing_snapshot_only(snapshot, monkeypatch):
    monkeypatch.setattr("apps.api.main.open_trusted_model", fake_model)
    monkeypatch.setattr("apps.api.workflow.assess", success_result)
    with TestClient(create_app(enabled(snapshot))) as client:
        assert_safe_error(client.get(PREDICT), 401, "UNAUTHORIZED")
        assert_safe_error(client.get(PREDICT, headers=auth("bad")), 401, "UNAUTHORIZED")
        assert_safe_error(client.get(PREDICT + "?score=1", headers=auth()), 422, "VALIDATION_ERROR")
        assert_safe_error(
            client.get(PREDICT.replace("BU-0001", "BU-9999"), headers=auth()), 404, "NOT_FOUND"
        )
        assert_safe_error(
            client.get(PREDICT.replace("2025-01", "2025-13"), headers=auth()),
            422,
            "VALIDATION_ERROR",
        )
        for token in (REVIEWER, SUPERVISOR):
            prediction = client.get(PREDICT, headers=auth(token))
            assert prediction.status_code == 200
            data = prediction.json()["data"]
            assert data["status"] == "EXPERIMENTAL_SYNTHETIC"
            assert data["policy_status"] == "UNRESOLVED"
            assert data["score"] == 0.25 and data["experimental_prediction"] == 0
            assert prediction.json()["meta"]["ml_status"] == "NOT_CONFIGURED"
            assert "ground_truth" not in prediction.text
            assert "npwp" not in prediction.text
        assert client.get("/api/v1/cases", headers=auth()).json()["data"] == []
        assert client.get("/api/v1/capabilities").json()["data"]["policy"] == "UNRESOLVED"
        assert client.get("/api/v1/ml/status").json()["data"]["experimental_status"] == "READY"


def test_inference_fault_is_sanitized_and_not_mutating(snapshot, monkeypatch):
    monkeypatch.setattr("apps.api.main.open_trusted_model", fake_model)

    def fail(*args):
        raise InferenceUnavailable("SECRET cannot be printed")

    monkeypatch.setattr("apps.api.workflow.assess", fail)
    with TestClient(create_app(enabled(snapshot))) as client:
        assert_safe_error(client.get(PREDICT, headers=auth()), 503, "ML_INFERENCE_UNAVAILABLE")
        assert client.get("/api/v1/cases", headers=auth()).json()["data"] == []
        assert client.get("/health/ready").status_code == 200


def test_artifact_provenance_gate_precedes_any_unpickling(snapshot, monkeypatch, tmp_path):
    def forbidden(*args, **kwargs):
        raise AssertionError("unpickle must not run on unverified metadata")

    monkeypatch.setitem(
        sys.modules, "packages.ml.inference", SimpleNamespace(load_bundle=forbidden)
    )
    path = tmp_path / "best_model.pkl"
    path.write_bytes(b"untrusted")
    meta = {
        "status": "EXPERIMENTAL_SYNTHETIC",
        "calibration_status": "NOT_CALIBRATED",
        "operational_threshold": None,
        "dataset_commit": snapshot.manifest_path.read_text()[:4],
        "data_sha256": {"data/synthetic/curated/curated_master_badan_usaha.csv": "bad"},
    }
    path.with_name("metadata.json").write_text(json.dumps(meta))
    with pytest.raises(ValueError, match="Source commit mismatch"):
        open_trusted_model(
            SimpleNamespace(
                ref=SimpleNamespace(is_synthetic=True, source_commit="0" * 40),
                info=SimpleNamespace(files={}),
            ),
            path,
        )
    meta["dataset_commit"] = "0" * 40
    path.with_name("metadata.json").write_text(json.dumps(meta))
    with pytest.raises(ValueError, match="Curated dataset hashes"):
        open_trusted_model(
            SimpleNamespace(
                ref=SimpleNamespace(is_synthetic=True, source_commit="0" * 40),
                info=SimpleNamespace(files={"curated_master_badan_usaha.csv": "good"}),
            ),
            path,
        )


def test_real_trained_artifact_http_integration(snapshot):
    """Runs after ML CI training; backend-only CI deliberately has no pickle."""
    model_path = Path(__file__).resolve().parents[2] / "models/best_model.pkl"
    if not model_path.is_file():
        pytest.skip("ML bundle not installed; run the ML pipeline first")
    from apps.api.config import ROOT

    settings = Settings(
        database_path=snapshot.database_path,
        reviewer_token=REVIEWER,
        supervisor_token=SUPERVISOR,
        experimental_ml_enabled=True,
        ml_model_path=model_path,
        data_root=ROOT / "data/synthetic/curated",
        manifest_path=ROOT / "config/backend_dataset_manifest.json",
    )
    with TestClient(create_app(settings)) as client:
        status = client.get("/api/v1/ml/status").json()["data"]
        assert status["experimental_status"] == "READY", status
        response = client.get(PREDICT, headers=auth())
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["data"]["status"] in {"ABSTAIN", "EXPERIMENTAL_SYNTHETIC"}
        assert body["data"]["policy_status"] == "UNRESOLVED"
        assert body["meta"]["is_synthetic"] is True
        assert client.get("/api/v1/dataset").status_code == 200
        assert client.get("/api/v1/cases", headers=auth()).json()["data"] == []
