from __future__ import annotations

import csv
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs" / "DOCUMENT_MANIFEST.csv"
ALLOWED_LEVELS = {"A1", "A2", "A3", "A4", "A5", "A6"}
ALLOWED_STATUS = {
    "DRAFT", "REVIEWED", "FROZEN", "IMPLEMENTED", "VERIFIED",
    "ACCEPTED", "SUPERSEDED", "RETIRED",
}
PLACEHOLDER_TOKENS = ("TBD", "Scaffold;")

def fail(msg: str) -> None:
    raise SystemExit(f"GOVERNANCE_FAIL: {msg}")

def load_manifest() -> list[dict[str, str]]:
    with MANIFEST.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    required = {
        "path", "status", "artifact_authority_level", "source_authority",
        "artifact_role", "authority", "owner", "notes",
    }
    if not rows:
        fail("manifest is empty")
    if set(rows[0]) != required:
        fail(f"manifest columns mismatch: {set(rows[0])} != {required}")
    return rows

def validate_rows(rows: list[dict[str, str]]) -> None:
    seen: set[str] = set()
    for row in rows:
        path = row["path"]
        if path in seen:
            fail(f"duplicate manifest path: {path}")
        seen.add(path)

        if row["artifact_authority_level"] not in ALLOWED_LEVELS:
            fail(f"{path}: repo artifact cannot have authority {row['artifact_authority_level']}")
        if row["status"] not in ALLOWED_STATUS:
            fail(f"{path}: invalid status {row['status']}")
        if row["source_authority"] and row["source_authority"] != "A0":
            fail(f"{path}: unsupported source_authority {row['source_authority']}")
        if row["artifact_role"] == "A0_DERIVED_REGISTRY" and row["source_authority"] != "A0":
            fail(f"{path}: derived A0 registry must declare source_authority=A0")

        fs_path = ROOT / "docs" / path if path != "README.md" else ROOT / "docs" / "README.md"
        if not fs_path.exists():
            fail(f"manifest path does not exist: {path}")

        if row["status"] == "FROZEN":
            blob = " ".join(row.values())
            if any(tok in blob for tok in PLACEHOLDER_TOKENS):
                fail(f"{path}: FROZEN row still contains placeholder metadata")
            if not row["owner"] or not row["authority"]:
                fail(f"{path}: FROZEN row missing owner/authority")

def changed_files(base: str, head: str) -> set[str]:
    out = subprocess.check_output(
        ["git", "diff", "--name-only", f"{base}...{head}"],
        cwd=ROOT, text=True
    )
    return {x.strip() for x in out.splitlines() if x.strip()}

def validate_frozen_change_control(rows: list[dict[str, str]]) -> None:
    event_path = os.getenv("GITHUB_EVENT_PATH")
    if not event_path or not Path(event_path).exists():
        return
    event = json.loads(Path(event_path).read_text(encoding="utf-8"))
    base = None
    head = None
    if "pull_request" in event:
        base = event["pull_request"]["base"]["sha"]
        head = event["pull_request"]["head"]["sha"]
    elif event.get("before") and event.get("after"):
        base, head = event["before"], event["after"]
    if not base or not head or set(base) == {"0"}:
        return

    changed = changed_files(base, head)
    frozen_repo_paths = {
        f"docs/{row['path']}" for row in rows if row["status"] == "FROZEN"
    }
    touched = changed & frozen_repo_paths
    if not touched:
        return

    if "docs/00_PROJECT_GOVERNANCE/CHANGE_LOG.md" not in changed:
        fail(f"FROZEN artifacts changed without CHANGE_LOG.md: {sorted(touched)}")

    cr_changed = any(
        p.startswith("docs/00_PROJECT_GOVERNANCE/change_requests/CR-")
        and p.endswith(".md")
        for p in changed
    )
    if not cr_changed:
        fail(f"FROZEN artifacts changed without a CR record: {sorted(touched)}")

def main() -> None:
    rows = load_manifest()
    validate_rows(rows)
    validate_frozen_change_control(rows)
    print(f"governance ok: {len(rows)} manifest entries")

if __name__ == "__main__":
    main()
