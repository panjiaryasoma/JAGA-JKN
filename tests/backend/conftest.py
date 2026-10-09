"""Small, source-backed fixtures; no generated CSV changes in the repository."""

import csv
import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.api.config import Settings
from apps.api.main import create_app

ROOT = Path(__file__).resolve().parents[2]
MASTER = "curated_master_badan_usaha.csv"
EVIDENCE = "curated_kepatuhan_evidence.csv"


def read_rows(path):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_rows(path, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def refresh_manifest(settings):
    manifest = json.loads(settings.manifest_path.read_text())
    for name in (MASTER, EVIDENCE):
        path = settings.data_root / name
        manifest["files"][name] = {
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "rows": len(read_rows(path)),
        }
    settings.manifest_path.write_text(json.dumps(manifest))


@pytest.fixture
def snapshot(tmp_path):
    source = ROOT / "data/synthetic/curated"
    companies = read_rows(source / MASTER)[:2]
    ids = {row["id_badan_usaha"] for row in companies}
    evidence = [
        row
        for row in read_rows(source / EVIDENCE)
        if row["id_badan_usaha"] in ids and row["periode_bulan"] in {"2025-01", "2025-02"}
    ]
    write_rows(tmp_path / MASTER, companies)
    write_rows(tmp_path / EVIDENCE, evidence)
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "manifest_version": "1.0",
                "source_commit": "0" * 40,
                "assumption_version": "SYN-2026-10-08-v3",
                "is_synthetic": True,
                "generation_seed": 42,
                "raw_seed": 43,
                "period_from": "2025-01",
                "period_to": "2025-02",
                "files": {},
            }
        )
    )
    settings = Settings(
        data_root=tmp_path, manifest_path=manifest_path, database_path=tmp_path / "cases.sqlite3"
    )
    refresh_manifest(settings)
    return settings


@pytest.fixture
def client(snapshot):
    with TestClient(create_app(snapshot)) as connection:
        yield connection


@pytest.fixture(scope="session")
def baseline_client(tmp_path_factory):
    settings = Settings(database_path=tmp_path_factory.mktemp("baseline") / "cases.sqlite3")
    with TestClient(create_app(settings)) as connection:
        yield connection
