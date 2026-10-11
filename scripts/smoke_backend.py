"""Exercise a real loopback server with an isolated DB and ephemeral credentials."""

import json
import os
import secrets
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]


def run():
    with tempfile.TemporaryDirectory(prefix="jaga-http-") as directory:
        reviewer, supervisor = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        environment = {
            **os.environ,
            "JAGA_REVIEWER_TOKEN": reviewer,
            "JAGA_SUPERVISOR_TOKEN": supervisor,
            "JAGA_REVIEWER_ID": "smoke-reviewer",
            "JAGA_SUPERVISOR_ID": "smoke-supervisor",
            "JAGA_DB_PATH": str(Path(directory) / "cases.sqlite3"),
            "JAGA_DATA_ROOT": str(ROOT / "data/synthetic/curated"),
            "JAGA_DATASET_MANIFEST": str(ROOT / "config/backend_dataset_manifest.json"),
        }
        checks = 0

        def request(path, expected=200, *, body=None, token=None, version=None, key=None):
            nonlocal checks
            headers = {"Content-Type": "application/json"}
            if token:
                headers["Authorization"] = f"Bearer {token}"
            if body is not None:
                headers["Idempotency-Key"] = key or uuid4().hex
            if version is not None:
                headers["If-Match"] = f'"v{version}"'
            query = urllib.request.Request(
                f"http://127.0.0.1:{port}{path}",
                data=json.dumps(body).encode() if body is not None else None,
                headers=headers,
            )
            try:
                response = urllib.request.urlopen(query, timeout=5)
            except urllib.error.HTTPError as exc:
                response = exc
            with response:
                assert response.status == expected, (
                    f"{path}: expected {expected}, got {response.status}"
                )
                assert response.headers["X-Request-ID"]
                assert response.headers["Cache-Control"] == "no-store"
                checks += 1
                return json.load(response), dict(response.headers)

        with (Path(directory) / "server.log").open("w+") as log:
            process = subprocess.Popen(
                [sys.executable, "-m", "apps.api", "--port", str(port)],
                cwd=ROOT,
                env=environment,
                stdout=log,
                stderr=subprocess.STDOUT,
            )
            try:
                deadline = time.monotonic() + 30
                while True:
                    if process.poll() is not None:
                        raise RuntimeError("Loopback server exited before readiness")
                    try:
                        request("/health/ready")
                        break
                    except (urllib.error.URLError, TimeoutError):
                        if time.monotonic() >= deadline:
                            raise RuntimeError("Loopback server did not become ready") from None
                        time.sleep(0.1)
                metadata, _ = request("/api/v1/dataset")
                assert metadata["data"]["company_count"] == 500
                assert metadata["data"]["evidence_record_count"] == 12000
                request("/api/v1/badan-usaha?q=BU-0001")
                record, _ = request("/api/v1/badan-usaha/BU-0001/evidence/2025-01")
                assert record["data"]["overall_review_state"] == "ABSTAIN"
                request("/api/v1/dashboard?periode_bulan=2025-01")
                request("/api/v1/cases", 401)
                request("/api/v1/me", token=reviewer)
                key = uuid4().hex
                body = {
                    "id_badan_usaha": "BU-0001",
                    "periode_bulan": "2025-01",
                    "reason": "HTTP smoke review",
                }
                opened, _ = request("/api/v1/cases", 201, body=body, token=reviewer, key=key)
                replay, _ = request("/api/v1/cases", 201, body=body, token=reviewer, key=key)
                assert replay == opened
                case_path = f"/api/v1/cases/{opened['data']['case_id']}"
                request(
                    case_path + "/transitions",
                    body={"action": "START_REVIEW", "reason": "Review started"},
                    token=reviewer,
                    version=1,
                )
                planned, _ = request(
                    case_path + "/interventions",
                    201,
                    token=reviewer,
                    version=2,
                    body={"kind": "FOLLOW_UP", "note": "Verify synthetic source"},
                )
                intervention = planned["data"]["intervention_id"]
                request(
                    case_path + f"/interventions/{intervention}/outcomes",
                    token=reviewer,
                    version=3,
                    body={"outcome": "COMPLETED", "note": "Source reviewed"},
                )
                resolution = {"action": "RESOLVE", "reason": "Human review complete"}
                request(case_path + "/transitions", 403, body=resolution, token=reviewer, version=4)
                request(case_path + "/transitions", body=resolution, token=supervisor, version=4)
                detail, _ = request(case_path, token=reviewer)
                assert detail["data"]["status"] == "RESOLVED"
                assert detail["data"]["evidence_snapshot"] == record["data"]
                events, _ = request(case_path + "/events", token=supervisor)
                assert [event["version"] for event in events["data"]] == [1, 2, 3, 4, 5]
                request("/openapi.json")
                print(
                    json.dumps(
                        {
                            "result": "PASS",
                            "transport": "HTTP/loopback",
                            "checks": checks,
                            "companies": 500,
                            "monthly_records": 12000,
                            "case_status": "RESOLVED",
                        }
                    )
                )
            finally:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)


if __name__ == "__main__":
    run()
