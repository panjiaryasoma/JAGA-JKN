"""End-to-end review workflow, persistence, authorization, and atomic write contracts."""

import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Barrier
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from apps.api.main import create_app
from packages.data.case_store import CaseStore

CASES = "/api/v1/cases"
REVIEWER = "test-reviewer-" + "r" * 32
SUPERVISOR = "test-supervisor-" + "s" * 32


@pytest.fixture
def workflow_settings(snapshot):
    return replace(
        snapshot,
        database_path=snapshot.data_root / "cases.sqlite3",
        reviewer_token=REVIEWER,
        supervisor_token=SUPERVISOR,
    )


@pytest.fixture
def workflow(workflow_settings):
    with TestClient(create_app(workflow_settings)) as client:
        yield client


def auth(token=REVIEWER):
    return {"Authorization": f"Bearer {token}"}


def write(client, path, payload, *, version=None, key=None, token=REVIEWER):
    headers = {**auth(token), "Idempotency-Key": key or uuid4().hex}
    if version is not None:
        headers["If-Match"] = f'"v{version}"'
    return client.post(path, json=payload, headers=headers)


def open_case(client, **kwargs):
    return write(
        client,
        CASES,
        {
            "id_badan_usaha": "BU-0001",
            "periode_bulan": "2025-01",
            "reason": "Tinjau bukti sintetis dan kualitas sumber.",
            **kwargs,
        },
    )


def transition(client, case_id, version, action, token=REVIEWER, key=None):
    return write(
        client,
        f"{CASES}/{case_id}/transitions",
        {
            "action": action,
            "reason": "Catatan keputusan manusia dalam prototipe.",
        },
        version=version,
        token=token,
        key=key,
    )


def test_case_intervention_resolution_recurrence_and_restart(workflow, workflow_settings):
    created = open_case(workflow)
    assert created.status_code == 201
    case_id = created.json()["data"]["case_id"]
    assert created.headers["etag"] == '"v1"'
    assert created.headers["location"] == f"{CASES}/{case_id}"
    assert transition(workflow, case_id, 1, "START_REVIEW").status_code == 200
    intervention = write(
        workflow,
        f"{CASES}/{case_id}/interventions",
        {
            "kind": "REQUEST_DOCUMENTS",
            "note": "Minta klarifikasi sumber.",
            "due_at": "2027-01-01T12:00:00+07:00",
        },
        version=2,
    )
    assert intervention.status_code == 201
    intervention_id = intervention.json()["data"]["intervention_id"]
    assert transition(workflow, case_id, 3, "REQUEST_EVIDENCE").status_code == 200
    result = write(
        workflow,
        f"{CASES}/{case_id}/interventions/{intervention_id}/outcomes",
        {
            "outcome": "COMPLETED",
            "note": "Klarifikasi diterima untuk pemeriksaan demo.",
        },
        version=4,
    )
    assert result.status_code == 200
    assert transition(workflow, case_id, 5, "RESUME_REVIEW").status_code == 200
    assert transition(workflow, case_id, 6, "RESOLVE", SUPERVISOR).status_code == 200
    detail = workflow.get(f"{CASES}/{case_id}", headers=auth()).json()["data"]
    assert detail["status"] == "RESOLVED" and detail["version"] == 7
    assert detail["interventions"][0]["due_at"] == "2027-01-01T05:00:00+00:00"
    assert detail["evidence_snapshot"]["registration"]["rule_result"] == "ABSTAIN"
    events = workflow.get(f"{CASES}/{case_id}/events", headers=auth()).json()["data"]
    assert [event["version"] for event in events] == list(range(1, 8))
    assert events[0]["actor_id"] == "demo-reviewer"
    assert events[-1]["actor_role"] == "SUPERVISOR"
    child = open_case(workflow, periode_bulan="2025-02", recurrence_of=case_id)
    assert child.status_code == 201
    child_id = child.json()["data"]["case_id"]
    with TestClient(create_app(workflow_settings)) as restarted:
        persisted = restarted.get(f"{CASES}/{case_id}", headers=auth()).json()["data"]
        assert persisted == detail
        assert (
            restarted.get(f"{CASES}/{child_id}", headers=auth()).json()["data"]["recurrence_of"]
            == case_id
        )


def test_authentication_and_role_boundary(workflow):
    assert workflow.get(CASES).status_code == 401
    bad = workflow.get(CASES, headers=auth("bad-token"))
    assert bad.status_code == 401 and bad.headers["www-authenticate"] == "Bearer"
    assert workflow.get("/api/v1/me", headers=auth()).json()["data"] == {
        "actor_id": "demo-reviewer",
        "role": "REVIEWER",
        "auth_mode": "DEMO_STATIC_TOKEN",
    }
    created = open_case(workflow).json()["data"]
    case_id = created["case_id"]
    assert transition(workflow, case_id, 1, "START_REVIEW").status_code == 200
    denied = transition(workflow, case_id, 2, "RESOLVE")
    assert denied.status_code == 403
    assert workflow.get(f"{CASES}/{case_id}", headers=auth()).json()["data"]["version"] == 2
    assert transition(workflow, case_id, 2, "RESOLVE", SUPERVISOR).status_code == 200


def test_unconfigured_auth_is_explicit(client):
    response = client.get(CASES)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "AUTH_NOT_CONFIGURED"
    assert client.get("/api/v1/badan-usaha").status_code == 200


def test_idempotency_replays_original_version_and_rejects_key_reuse(workflow):
    key = uuid4().hex
    payload = {"id_badan_usaha": "BU-0001", "periode_bulan": "2025-01", "reason": "Review demo."}
    first = write(workflow, CASES, payload, key=key)
    case_id = first.json()["data"]["case_id"]
    assert transition(workflow, case_id, 1, "START_REVIEW").status_code == 200
    replay = write(workflow, CASES, payload, key=key)
    assert replay.status_code == 201 and replay.json() == first.json()
    assert replay.headers["idempotent-replay"] == "true"
    assert replay.headers["etag"] == '"v1"'
    conflict = write(workflow, CASES, {**payload, "reason": "Changed"}, key=key)
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "IDEMPOTENCY_CONFLICT"
    assert workflow.get(CASES, headers=auth()).json()["pagination"]["total"] == 1


def test_active_duplicate_and_illegal_transition_do_not_change_state(workflow):
    case_id = open_case(workflow).json()["data"]["case_id"]
    assert open_case(workflow).status_code == 409
    invalid = transition(workflow, case_id, 1, "RESOLVE", SUPERVISOR)
    assert invalid.status_code == 409
    assert workflow.get(f"{CASES}/{case_id}", headers=auth()).headers["etag"] == '"v1"'


def test_if_match_required_and_stale_updates_rejected(workflow):
    case_id = open_case(workflow).json()["data"]["case_id"]
    path = f"{CASES}/{case_id}/notes"
    assert write(workflow, path, {"text": "A note"}).status_code == 428
    assert write(workflow, path, {"text": "A note"}, version=99).status_code == 412
    response = write(workflow, path, {"text": "A note"}, version=1)
    assert response.status_code == 200 and response.headers["etag"] == '"v2"'
    assert (
        workflow.post(
            path, json={"text": "Another"}, headers={**auth(), "If-Match": '"v2"'}
        ).status_code
        == 422
    )


def test_concurrent_updates_have_one_winner(workflow):
    case_id = open_case(workflow).json()["data"]["case_id"]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(lambda _: transition(workflow, case_id, 1, "START_REVIEW"), range(2))
        )
    assert sorted(result.status_code for result in results) == [200, 412]
    events = workflow.get(f"{CASES}/{case_id}/events", headers=auth()).json()["data"]
    assert len(events) == 2


def test_interventions_block_closure_until_outcome_recorded(workflow):
    case_id = open_case(workflow).json()["data"]["case_id"]
    transition(workflow, case_id, 1, "START_REVIEW")
    planned = write(
        workflow,
        f"{CASES}/{case_id}/interventions",
        {
            "kind": "FOLLOW_UP",
            "note": "Tunggu klarifikasi.",
        },
        version=2,
    )
    intervention_id = planned.json()["data"]["intervention_id"]
    blocked = transition(workflow, case_id, 3, "RESOLVE", SUPERVISOR)
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "OPEN_INTERVENTIONS"
    path = f"{CASES}/{case_id}/interventions/{intervention_id}/outcomes"
    assert (
        write(
            workflow, path, {"outcome": "CANCELLED", "note": "Tidak diperlukan."}, version=3
        ).status_code
        == 200
    )
    assert (
        write(
            workflow, path, {"outcome": "COMPLETED", "note": "Double outcome"}, version=4
        ).status_code
        == 409
    )
    assert transition(workflow, case_id, 4, "DISMISS", SUPERVISOR).status_code == 200
    assert transition(workflow, case_id, 5, "REOPEN", SUPERVISOR).status_code == 200


def test_recurrence_requires_resolved_same_company_earlier_period(workflow):
    case_id = open_case(workflow).json()["data"]["case_id"]
    assert open_case(workflow, periode_bulan="2025-02", recurrence_of=case_id).status_code == 409
    transition(workflow, case_id, 1, "START_REVIEW")
    transition(workflow, case_id, 2, "RESOLVE", SUPERVISOR)
    assert open_case(workflow, recurrence_of=case_id).status_code == 409
    assert (
        open_case(
            workflow, id_badan_usaha="BU-0002", periode_bulan="2025-02", recurrence_of=case_id
        ).status_code
        == 409
    )


def test_atomic_failure_rolls_back_event_version_and_receipt(workflow, workflow_settings):
    case_id = open_case(workflow).json()["data"]["case_id"]
    with sqlite3.connect(workflow_settings.database_path) as conn:
        conn.execute(
            "CREATE TRIGGER fail_note BEFORE INSERT ON case_events WHEN NEW.action='NOTE_ADDED' BEGIN SELECT RAISE(ABORT, 'injected failure'); END"
        )
    key = uuid4().hex
    path = f"{CASES}/{case_id}/notes"
    failed = write(workflow, path, {"text": "Atomic note"}, version=1, key=key)
    assert failed.status_code == 503
    assert workflow.get(f"{CASES}/{case_id}", headers=auth()).json()["data"]["version"] == 1
    with sqlite3.connect(workflow_settings.database_path) as conn:
        assert (
            conn.execute("SELECT count(*) FROM case_events WHERE case_id=?", (case_id,)).fetchone()[
                0
            ]
            == 1
        )
        assert (
            conn.execute(
                "SELECT count(*) FROM mutation_receipts WHERE idempotency_key=?", (key,)
            ).fetchone()[0]
            == 0
        )
        conn.execute("DROP TRIGGER fail_note")
    assert write(workflow, path, {"text": "Atomic note"}, version=1, key=key).status_code == 200


def test_case_keeps_evidence_when_current_snapshot_is_unavailable(workflow, workflow_settings):
    case_id = open_case(workflow).json()["data"]["case_id"]
    old = workflow.get(f"{CASES}/{case_id}", headers=auth()).json()["data"]
    (workflow_settings.data_root / "curated_kepatuhan_evidence.csv").unlink()
    with TestClient(create_app(workflow_settings)) as restarted:
        assert restarted.get("/health/ready").status_code == 503
        assert restarted.get(f"{CASES}/{case_id}", headers=auth()).json()["data"] == old
        assert open_case(restarted, periode_bulan="2025-02").status_code == 503


def test_database_failure_and_future_schema_are_explicit(workflow_settings):
    path = workflow_settings.database_path
    with sqlite3.connect(path) as conn:
        conn.execute("PRAGMA user_version=999")
    with TestClient(create_app(workflow_settings)) as client:
        assert client.get("/health/live").status_code == 200
        assert client.get("/health/ready").status_code == 503
        assert client.get(CASES, headers=auth()).status_code == 503
        assert client.get("/api/v1/badan-usaha").status_code == 200
    with sqlite3.connect(path) as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 999


@pytest.mark.parametrize(
    "extra",
    [{"actor_id": "spoof"}, {"role": "SUPERVISOR"}, {"status": "RESOLVED"}, {"reason": "   "}],
)
def test_write_input_cannot_spoof_actor_or_state(workflow, extra):
    response = open_case(workflow, **extra)
    assert response.status_code == 422
    assert workflow.get(CASES, headers=auth()).json()["pagination"]["total"] == 0


def test_dashboard_and_capabilities_are_honest(workflow):
    dashboard = workflow.get("/api/v1/dashboard", params={"periode_bulan": "2025-01"})
    assert dashboard.status_code == 200
    data = dashboard.json()["data"]
    assert data["company_count"] == 2
    for domain in ("registration", "wage", "contribution"):
        assert sum(data[domain]["discrepancy"].values()) == 2
        assert sum(data[domain]["quality"].values()) == 2
        assert data[domain]["abstain_count"] == 2
    status = workflow.get("/api/v1/ml/status").json()["data"]
    assert status["status"] == "NOT_CONFIGURED" and status["model_version"] is None
    caps = workflow.get("/api/v1/capabilities").json()["data"]
    assert caps["authentication"] == "DEMO_STATIC_TOKEN"
    assert caps["case_store"] == "AVAILABLE"
    assert "risk_score" not in json.dumps(dashboard.json())


def test_lost_database_degrades_readiness_without_recreating_empty_store(
    workflow, workflow_settings
):
    open_case(workflow)
    workflow_settings.database_path.unlink()
    response = workflow.get("/health/ready")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "PERSISTENCE_UNAVAILABLE"
    assert workflow.get(CASES, headers=auth()).status_code == 503
    assert not workflow_settings.database_path.exists()


def test_replay_create_survives_unavailable_current_snapshot(workflow, workflow_settings):
    key = uuid4().hex
    body = {"id_badan_usaha": "BU-0001", "periode_bulan": "2025-01", "reason": "Review demo."}
    original = write(workflow, CASES, body, key=key)
    (workflow_settings.data_root / "curated_kepatuhan_evidence.csv").unlink()
    with TestClient(create_app(workflow_settings)) as restarted:
        replay = write(restarted, CASES, body, key=key)
        assert replay.status_code == 201 and replay.json() == original.json()


def test_concurrent_create_has_one_active_case(workflow):
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: open_case(workflow), range(2)))
    assert sorted(result.status_code for result in results) == [201, 409]
    assert workflow.get(CASES, headers=auth()).json()["pagination"]["total"] == 1


def test_intervention_cannot_be_completed_through_another_case(workflow):
    first = open_case(workflow).json()["data"]["case_id"]
    second = open_case(workflow, id_badan_usaha="BU-0002").json()["data"]["case_id"]
    transition(workflow, first, 1, "START_REVIEW")
    planned = write(
        workflow,
        f"{CASES}/{first}/interventions",
        {"kind": "FOLLOW_UP", "note": "Review"},
        version=2,
    )
    intervention = planned.json()["data"]["intervention_id"]
    response = write(
        workflow,
        f"{CASES}/{second}/interventions/{intervention}/outcomes",
        {"outcome": "COMPLETED", "note": "Wrong case"},
        version=1,
    )
    assert response.status_code == 404


@pytest.mark.parametrize(
    "timestamp",
    [
        "2027-01-01T12:00:00",
        "2027-01-01",
        123,
        "bad-time",
        "0001-01-01T00:00:00+14:00",
        "9999-12-31T23:59:59-14:00",
    ],
)
def test_due_time_requires_explicit_timezone(workflow, timestamp):
    case_id = open_case(workflow).json()["data"]["case_id"]
    transition(workflow, case_id, 1, "START_REVIEW")
    response = write(
        workflow,
        f"{CASES}/{case_id}/interventions",
        {"kind": "FOLLOW_UP", "note": "Review", "due_at": timestamp},
        version=2,
    )
    assert response.status_code == 422


def test_credentials_and_actor_configuration_are_validated(workflow_settings):
    for change in (
        {"reviewer_token": "short"},
        {"supervisor_token": REVIEWER},
        {"supervisor_id": "demo-reviewer"},
        {"reviewer_id": "bad actor"},
    ):
        with pytest.raises(ValueError):
            replace(workflow_settings, **change)


def test_duplicate_security_headers_are_rejected(workflow):
    response = workflow.get(
        CASES,
        headers=[
            ("Authorization", f"Bearer {REVIEWER}"),
            ("Authorization", f"Bearer {SUPERVISOR}"),
        ],
    )
    assert response.status_code == 401
    response = workflow.post(
        CASES,
        json={"id_badan_usaha": "BU-0001", "periode_bulan": "2025-01", "reason": "Review"},
        headers=[
            ("Authorization", f"Bearer {REVIEWER}"),
            ("Idempotency-Key", uuid4().hex),
            ("Idempotency-Key", uuid4().hex),
        ],
    )
    assert response.status_code == 422


def test_concurrent_startup_initializes_one_complete_schema(tmp_path):
    path = tmp_path / "simultaneous.sqlite3"
    gate = Barrier(2)

    def initialize(_):
        gate.wait(timeout=5)
        store = CaseStore(path)
        store.initialize()
        store.check_ready()

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(initialize, range(2)))
    with sqlite3.connect(path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 1
        assert connection.execute("SELECT count(*) FROM case_events").fetchone()[0] == 0
