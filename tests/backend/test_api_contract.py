"""Observable consumer contracts, including degraded operation and source isolation."""

import json
import logging
from uuid import UUID

import pytest
from conftest import EVIDENCE, MASTER, read_rows, refresh_manifest, write_rows
from fastapi.testclient import TestClient

from apps.api.main import create_app

BASE = "/api/v1/badan-usaha"


def assert_error(response, status, code):
    assert response.status_code == status
    error = response.json()["error"]
    assert error["code"] == code
    assert error["request_id"] == response.headers["x-request-id"]
    UUID(error["request_id"])
    assert "input" not in json.dumps(error)
    return error


def test_baseline_identity_and_complete_history(baseline_client):
    response = baseline_client.get("/api/v1/dataset")
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["company_count"] == 500
    assert body["data"]["evidence_record_count"] == 12000
    assert body["data"]["period_from"] == "2025-01"
    assert body["data"]["period_to"] == "2026-12"
    assert body["meta"]["source_commit"] == "9390d36a1adbef6f17aa6804dd6c56d290e06d04"
    assert body["meta"]["is_synthetic"] is True
    assert body["meta"]["ml_status"] == "NOT_CONFIGURED"
    assert body["meta"]["policy_status"] == "UNRESOLVED"
    assert set(body["data"]["files"]) == {MASTER, EVIDENCE}
    history = baseline_client.get(f"{BASE}/BU-0001/evidence").json()
    assert len(history["data"]) == 24
    assert history["pagination"]["total"] == 24
    assert history["meta"] == body["meta"]
    assert history["data"][-1]["periode_bulan"] == "2026-12"


def test_listing_filters_and_pagination(client):
    first = client.get(BASE, params={"page_size": 1}).json()
    second = client.get(BASE, params={"page_size": 1, "page": 2}).json()
    assert first["data"][0]["id_badan_usaha"] == "BU-0001"
    assert second["data"][0]["id_badan_usaha"] == "BU-0002"
    assert first["pagination"] == {"page": 1, "page_size": 1, "total": 2, "total_pages": 2}
    company = first["data"][0]
    response = client.get(
        BASE,
        params={
            "q": " bu-0001 ",
            "provinsi": company["provinsi"],
            "skala_usaha": company["skala_usaha"],
            "kode_kbli": company["kode_kbli"],
        },
    ).json()
    assert response["pagination"]["total"] == 1
    assert response["data"] == [company]
    named = client.get(BASE, params={"q": company["nama_badan_usaha"].upper()}).json()
    assert company in named["data"]
    assert client.get(BASE, params={"page": 100}).json()["data"] == []
    empty = client.get(BASE, params={"provinsi": "tidak tersedia"}).json()
    assert empty["data"] == []
    assert empty["pagination"]["total_pages"] == 0


def test_history_ranges_and_single_month(client):
    response = client.get(
        f"{BASE}/BU-0001/evidence",
        params={
            "period_from": "2025-02",
            "period_to": "2025-02",
        },
    ).json()
    assert response["pagination"]["total"] == 1
    assert response["data"][0]["periode_bulan"] == "2025-02"
    detail = client.get(f"{BASE}/BU-0001/evidence/2025-02").json()
    assert detail["data"] == response["data"][0]
    empty = client.get(f"{BASE}/BU-0001/evidence", params={"period_from": "2030-01"})
    assert empty.status_code == 200 and empty.json()["data"] == []
    paged = client.get(f"{BASE}/BU-0001/evidence", params={"page_size": 1, "page": 2})
    assert paged.json()["data"][0]["periode_bulan"] == "2025-02"


def test_evidence_preserves_source_and_authority(client, snapshot):
    source = read_rows(snapshot.data_root / EVIDENCE)[0]
    data = client.get(f"{BASE}/BU-0001/evidence/2025-01").json()["data"]
    assert data["source_record_id"] == source["source_record_id"]
    for domain in ("registration", "wage", "contribution"):
        group = data[domain]
        assert group["rule_result"] == "ABSTAIN"
        assert group["rule_reason"] == source[f"{domain}_rule_reason"]
        assert group["source_ids"] == json.loads(source[f"{domain}_source_ids_json"])
        assert group["source_periods"] == json.loads(source[f"{domain}_source_periods_json"])
        assert group["lineage"] == source[f"{domain}_lineage"]
        assert group["authority"]["authorized"] is False
        assert group["authority"]["rule_version"] == "UNVERIFIED"
    assert data["registration"]["missing_worker_count"] == 0
    assert data["registration"]["discrepancy_detected"] is False


def test_null_unknown_and_zero_are_distinct(snapshot):
    rows = read_rows(snapshot.data_root / EVIDENCE)
    for key in (
        "reference_worker_count",
        "observed_registered_worker_count",
        "missing_worker_count",
        "unexpected_worker_count",
        "registration_discrepancy_detected",
    ):
        rows[0][key] = ""
    rows[0]["registration_evidence_valid"] = "False"
    rows[0]["registration_worker_set_valid"] = "False"
    rows[0]["validated_payment_state"] = "UNKNOWN"
    rows[0]["contribution_payment_gap_observed"] = ""
    write_rows(snapshot.data_root / EVIDENCE, rows)
    refresh_manifest(snapshot)
    with TestClient(create_app(snapshot)) as client:
        data = client.get(f"{BASE}/BU-0001/evidence/2025-01").json()["data"]
        assert data["registration"]["missing_worker_count"] is None
        assert data["registration"]["discrepancy_detected"] is None
        assert data["wage"]["wage_discrepancy_signal_rp"] == 0
        assert data["contribution"]["validated_payment_state"] == "UNKNOWN"
        assert data["contribution"]["payment_gap_observed"] is None


def test_public_allowlist_hides_simulator_and_personal_fields(client):
    responses = [
        client.get(BASE),
        client.get(f"{BASE}/BU-0001"),
        client.get(f"{BASE}/BU-0001/evidence"),
        client.get("/openapi.json"),
    ]
    for response in responses:
        assert response.status_code == 200
        serialized = response.text
        for forbidden in (
            "synthetic_risk_mode_ground_truth",
            "scenario_profile_synthetic",
            "missing_worker_ids",
            "unexpected_worker_ids",
            "npwp",
            "nomor_telepon",
            "estimated_exposure",
            "baseline_upah",
            "baseline_tenaga",
        ):
            assert forbidden not in serialized


@pytest.mark.parametrize(
    "path",
    [
        f"{BASE}/BU-9999",
        f"{BASE}/BU-9999/evidence",
        f"{BASE}/BU-0001/evidence/2027-01",
        "/missing-route",
    ],
)
def test_not_found_is_consistent(client, path):
    assert_error(client.get(path), 404, "NOT_FOUND")


@pytest.mark.parametrize(
    "path,query",
    [
        (BASE, "page=0"),
        (BASE, "page=-1"),
        (BASE, "page=1.0"),
        (BASE, "page=abc"),
        (BASE, "page=100001"),
        (BASE, "page_size=101"),
        (BASE, "page_size=0"),
        (BASE, "q=%20%20"),
        (BASE, "unknown=x"),
        (BASE, "page=1&page=2"),
        (BASE, "q=a&q=b"),
        (f"{BASE}/bad-id", ""),
        (f"{BASE}/BU-0001/evidence/2025-13", ""),
        (f"{BASE}/BU-0001/evidence/0000-01", ""),
        (f"{BASE}/BU-0001/evidence", "period_from=2025-02&period_to=2025-01"),
        (f"{BASE}/BU-0001/evidence", "period_from=2025-00"),
        (f"{BASE}/BU-0001", "extra=x"),
        ("/api/v1/dataset", "source=untrusted"),
        ("/health/live", "extra=x"),
    ],
)
def test_invalid_request_rejected(client, path, query):
    assert_error(client.get(f"{path}?{query}"), 422, "VALIDATION_ERROR")


def test_read_only_method_preserves_allow_header(client):
    response = client.post(BASE, json={"authority_authorized": True})
    assert_error(response, 405, "METHOD_NOT_ALLOWED")
    assert "GET" in response.headers["allow"]


def test_safe_unexpected_failure_and_request_log(client, caplog):
    @client.app.get("/test-failure")
    def fail():
        raise RuntimeError("do-not-expose-this-value")

    with caplog.at_level(logging.INFO, logger="jaga.api"):
        response = client.get("/test-failure")
        company_response = client.get(BASE, params={"q": "private-search-marker"})
    assert_error(response, 500, "INTERNAL_ERROR")
    assert "do-not-expose-this-value" not in response.text
    assert "private-search-marker" not in " ".join(
        record.getMessage() for record in caplog.records if record.name == "jaga.api"
    )
    assert company_response.headers["cache-control"] == "no-store"


def test_request_ids_are_server_generated(client):
    first = client.get(BASE, headers={"X-Request-ID": "untrusted"})
    second = client.get(BASE)
    UUID(first.headers["x-request-id"])
    assert first.headers["x-request-id"] != second.headers["x-request-id"]


def test_snapshot_remains_consistent_until_restart(client, snapshot):
    before = client.get(BASE).json()
    (snapshot.data_root / MASTER).unlink()
    assert client.get(BASE).json() == before
    assert client.get("/health/ready").status_code == 200


def test_openapi_contains_error_contract(client):
    schema = client.get("/openapi.json").json()
    operation = schema["paths"][f"{BASE}/{{id_badan_usaha}}/evidence"]["get"]
    for code in ("404", "422", "503", "500"):
        ref = operation["responses"][code]["content"]["application/json"]["schema"]["$ref"]
        assert ref.endswith("/ErrorResponse")
