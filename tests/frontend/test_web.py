"""Exercise the frontend origin with the existing real API and persistent store."""

import json
import re
import subprocess
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from apps.api.config import Settings
from apps.web.app import STATIC, create_app

REVIEWER = "test-reviewer-token-" + "r" * 32
SUPERVISOR = "test-supervisor-token-" + "s" * 32


@pytest.fixture(scope="module")
def web(tmp_path_factory):
    settings = Settings(
        database_path=tmp_path_factory.mktemp("web") / "cases.sqlite3",
        reviewer_token=REVIEWER,
        supervisor_token=SUPERVISOR,
    )
    with TestClient(create_app(settings)) as client:
        yield client, settings


def auth(token=REVIEWER):
    return {"Authorization": f"Bearer {token}"}


def test_frontend_and_assets_use_one_origin_without_exposing_repository(web):
    client, _ = web
    page = client.get("/")
    assert page.status_code == 200
    assert '<html lang="id">' in page.text
    assert "script-src 'self'" in page.headers["Content-Security-Policy"]
    assert page.headers["X-Content-Type-Options"] == "nosniff"
    for path in ["styles.css", "app.mjs", "api.mjs", "domain.mjs", "views.mjs", "sample.mjs"]:
        asset = client.get(f"/assets/{path}")
        assert asset.status_code == 200
        assert REVIEWER not in asset.text and SUPERVISOR not in asset.text
        if path.endswith(".mjs"):
            assert "javascript" in asset.headers["content-type"]
    for path in [
        "/assets/%2e%2e/pyproject.toml",
        "/assets/../../config/backend_dataset_manifest.json",
    ]:
        assert client.get(path).status_code == 404
    assert client.get("/api/v1/not-found").json()["error"]["code"] == "NOT_FOUND"
    assert "Content-Security-Policy" not in client.get("/docs").headers


def test_public_journey_matches_one_snapshot(web):
    client, _ = web
    dataset = client.get("/api/v1/dataset").json()
    companies = client.get("/api/v1/badan-usaha?q=BU-0001").json()
    company = client.get("/api/v1/badan-usaha/BU-0001").json()
    evidence = client.get("/api/v1/badan-usaha/BU-0001/evidence/2025-12").json()
    history = client.get("/api/v1/badan-usaha/BU-0001/evidence?page_size=100").json()
    dashboard = client.get("/api/v1/dashboard?periode_bulan=2025-12").json()
    assert {
        r["meta"]["dataset_id"] for r in [dataset, companies, company, evidence, history, dashboard]
    } == {dataset["meta"]["dataset_id"]}
    assert len(history["data"]) == 24
    assert dashboard["data"]["company_count"] == 500
    for domain in ["registration", "wage", "contribution"]:
        assert sum(dashboard["data"][domain]["discrepancy"].values()) == 500


def test_preview_sample_is_exact_public_projection_and_contains_no_worker_ids(web):
    client, _ = web
    raw = (STATIC / "sample.mjs").read_text()
    sample = json.loads(raw.removeprefix("export const SAMPLE = ").removesuffix(";\n"))
    assert sample["scope"] == "READ_ONLY_SAMPLE"
    assert len(sample["companies"]) == 8
    assert len(sample["evidence"]) == 192
    actual = client.get("/api/v1/badan-usaha/BU-0001/evidence?page_size=100").json()
    assert [r for r in sample["evidence"] if r["id_badan_usaha"] == "BU-0001"] == actual["data"]
    assert sample["meta"] == actual["meta"]
    assert not re.search(r'"(?:worker_ids|npwp|phone|ground_truth|label_next_month)"', raw)


def test_persistent_case_journey_retry_conflict_and_roles(web):
    client, _ = web
    assert client.get("/api/v1/cases").status_code == 401
    assert client.get("/api/v1/me", headers=auth()).json()["data"]["role"] == "REVIEWER"
    key = str(uuid4())
    headers = {**auth(), "Idempotency-Key": key}
    body = {
        "id_badan_usaha": "BU-0001",
        "periode_bulan": "2025-12",
        "reason": "Telaah bukti frontend",
    }
    opened = client.post("/api/v1/cases", headers=headers, json=body)
    assert opened.status_code == 201
    replay = client.post("/api/v1/cases", headers=headers, json=body)
    assert replay.headers["Idempotent-Replay"] == "true"
    assert replay.json() == opened.json()
    case_id = opened.json()["data"]["case_id"]

    def post(suffix, payload, etag, token=REVIEWER):
        return client.post(
            f"/api/v1/cases/{case_id}/{suffix}",
            headers={**auth(token), "Idempotency-Key": str(uuid4()), "If-Match": etag},
            json=payload,
        )

    started = post(
        "transitions",
        {"action": "START_REVIEW", "reason": "Periksa sumber"},
        opened.headers["ETag"],
    )
    assert started.status_code == 200
    stale = post("notes", {"text": "Catatan dari versi lama"}, opened.headers["ETag"])
    assert stale.status_code == 412
    detail = client.get(f"/api/v1/cases/{case_id}", headers=auth())
    assert detail.headers["ETag"] == started.headers["ETag"]
    planned = post(
        "interventions",
        {"kind": "REQUEST_DOCUMENTS", "note": "Rencana verifikasi"},
        detail.headers["ETag"],
    )
    assert planned.status_code == 201
    intervention = planned.json()["data"]["intervention_id"]
    done = post(
        f"interventions/{intervention}/outcomes",
        {"outcome": "COMPLETED", "note": "Bukti ditelaah"},
        planned.headers["ETag"],
    )
    assert done.status_code == 200
    assert (
        post(
            "transitions", {"action": "RESOLVE", "reason": "Selesai"}, done.headers["ETag"]
        ).status_code
        == 403
    )
    resolved = post(
        "transitions",
        {"action": "RESOLVE", "reason": "Review selesai"},
        done.headers["ETag"],
        SUPERVISOR,
    )
    assert resolved.status_code == 200
    events = client.get(f"/api/v1/cases/{case_id}/events", headers=auth()).json()["data"]
    assert [e["version"] for e in events] == list(range(1, 6))
    assert events[-1]["actor_role"] == "SUPERVISOR"


def test_cases_and_frontend_survive_active_dataset_failure(web, tmp_path):
    client, settings = web
    opened = client.post(
        "/api/v1/cases",
        headers={**auth(), "Idempotency-Key": str(uuid4())},
        json={
            "id_badan_usaha": "BU-0002",
            "periode_bulan": "2025-12",
            "reason": "Persisted context",
        },
    )
    case_id = opened.json()["data"]["case_id"]
    with TestClient(create_app(replace(settings, data_root=tmp_path / "missing"))) as unavailable:
        assert unavailable.get("/").status_code == 200
        assert unavailable.get("/api/v1/dataset").status_code == 503
        result = unavailable.get(f"/api/v1/cases/{case_id}", headers=auth())
        assert result.status_code == 200
        assert result.json()["data"]["evidence_snapshot"]["id_badan_usaha"] == "BU-0002"
        assert unavailable.get("/api/v1/cases", headers=auth()).status_code == 200


def test_preview_build_is_self_contained_and_uses_the_same_sources(tmp_path):
    from scripts.build_web_preview import bundle

    bundle()
    path = Path(__file__).resolve().parents[2] / "apps/web/dist/JAGA_JKN_frontend_preview.html"
    html = path.read_text()
    assert "window.JAGA_PREVIEW = true;" in html
    assert 'src="/assets/' not in html
    assert 'href="/assets/' not in html
    assert not re.search(r"^import .+ from ", html, re.MULTILINE)
    assert (STATIC / "styles.css").read_text() in html
    script = re.search(r'<script type="module">\n(.*?)\n</script>', html, re.DOTALL).group(1)
    entrypoint = tmp_path / "preview.mjs"
    entrypoint.write_text(script)
    subprocess.run(["node", "--check", str(entrypoint)], check=True, capture_output=True)
