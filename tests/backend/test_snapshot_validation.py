"""Malformed snapshots must never look like empty or safe company data."""

import json

import pytest
from conftest import EVIDENCE, MASTER, read_rows, refresh_manifest, write_rows
from fastapi.testclient import TestClient

from apps.api.main import create_app


def assert_unready(settings, code):
    with TestClient(create_app(settings)) as client:
        assert client.get("/health/live").json() == {"status": "alive"}
        for path in (
            "/health/ready",
            "/api/v1/dataset",
            "/api/v1/badan-usaha",
            "/api/v1/badan-usaha/BU-0001/evidence",
        ):
            response = client.get(path)
            assert response.status_code == 503
            assert response.json()["error"]["code"] == code
            assert str(settings.data_root) not in response.text
        invalid = client.get("/api/v1/badan-usaha?page=0")
        assert invalid.status_code == 422


def test_missing_file_degrades_readiness(snapshot):
    (snapshot.data_root / EVIDENCE).unlink()
    assert_unready(snapshot, "DATASET_UNAVAILABLE")


def test_hash_mismatch_is_not_ignored(snapshot):
    path = snapshot.data_root / EVIDENCE
    path.write_bytes(path.read_bytes() + b"\n")
    assert_unready(snapshot, "DATASET_INVALID")


@pytest.mark.parametrize(
    "column,value",
    [
        ("registration_discrepancy_detected", "yes"),
        ("registration_evidence_valid", ""),
        ("registration_evidence_quality", "SUPER_HIGH"),
        ("missing_worker_count", "-1"),
        ("missing_worker_count", "1.5"),
        ("wage_discrepancy_signal_rp", "NaN"),
        ("wage_discrepancy_signal_rp", "Infinity"),
        ("reference_wage_signal_rp", "9007199254740992"),
        ("registration_source_ids_json", "[1]"),
        ("registration_source_ids_json", "not-json"),
        ("registration_source_periods_json", '["2025-13"]'),
        ("id_badan_usaha", "BU-9999"),
        ("periode_bulan", "2025-13"),
        ("is_synthetic", "False"),
        ("is_synthetic", "1"),
        ("registration_rule_result", "CONSISTENT"),
        ("wage_authority_authorized", "True"),
        ("registration_review_state", "NORMAL"),
        ("overall_review_state", "NORMAL"),
        ("registration_applicable_period_verified", "True"),
    ],
)
def test_invalid_typed_evidence_closes_snapshot(snapshot, column, value):
    rows = read_rows(snapshot.data_root / EVIDENCE)
    rows[0][column] = value
    write_rows(snapshot.data_root / EVIDENCE, rows)
    refresh_manifest(snapshot)
    assert_unready(snapshot, "DATASET_INVALID")


@pytest.mark.parametrize(
    "kind",
    [
        "company_duplicate",
        "evidence_duplicate",
        "source_duplicate",
        "grid_missing",
        "required_column_missing",
        "duplicate_header",
    ],
)
def test_relational_and_shape_integrity(snapshot, kind):
    name = MASTER if kind == "company_duplicate" else EVIDENCE
    path = snapshot.data_root / name
    rows = read_rows(path)
    if kind in {"company_duplicate", "evidence_duplicate"}:
        rows.append(rows[0].copy())
    elif kind == "source_duplicate":
        rows[1]["source_record_id"] = rows[0]["source_record_id"]
    elif kind == "grid_missing":
        rows.pop()
    elif kind == "required_column_missing":
        for row in rows:
            row.pop("wage_evidence_quality")
    write_rows(path, rows)
    if kind == "duplicate_header":
        content = path.read_text().replace(
            "id_badan_usaha,periode_bulan", "id_badan_usaha,id_badan_usaha", 1
        )
        path.write_text(content)
    refresh_manifest(snapshot)
    assert_unready(snapshot, "DATASET_INVALID")


@pytest.mark.parametrize(
    "kind",
    [
        "malformed",
        "false_synthetic",
        "wrong_count",
        "unexpected_file",
        "unknown_field",
        "duplicate_key",
    ],
)
def test_invalid_manifest(snapshot, kind):
    path = snapshot.manifest_path
    data = json.loads(path.read_text())
    if kind == "malformed":
        path.write_text("{")
    elif kind == "duplicate_key":
        path.write_text(
            path.read_text().replace(
                '"is_synthetic": true', '"is_synthetic": false, "is_synthetic": true'
            )
        )
    else:
        if kind == "false_synthetic":
            data["is_synthetic"] = False
        elif kind == "wrong_count":
            data["files"][MASTER]["rows"] = 3
        elif kind == "unexpected_file":
            data["files"]["../untrusted.csv"] = data["files"][MASTER]
        elif kind == "unknown_field":
            data["policy_authorized"] = True
        path.write_text(json.dumps(data))
    assert_unready(snapshot, "DATASET_INVALID")
