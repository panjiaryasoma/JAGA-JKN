from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import subprocess
from datetime import date
from pathlib import Path

ROOT = Path(os.environ.get("GOV_REPO_ROOT", Path(__file__).resolve().parents[1])).resolve()
MANIFEST_REL = "docs/DOCUMENT_MANIFEST.csv"
MANIFEST = ROOT / MANIFEST_REL
APPROVAL_REL = "docs/00_PROJECT_GOVERNANCE/APPROVAL_AUTHORITY.csv"

ALLOWED_LEVELS = {"A1", "A2", "A3", "A4", "A5", "A6"}
ALLOWED_STATUS = {
    "DRAFT", "REVIEWED", "FROZEN", "IMPLEMENTED", "VERIFIED",
    "ACCEPTED", "SUPERSEDED", "RETIRED",
}
PLACEHOLDER_TOKENS = ("TBD", "Scaffold;")
ID_RE = re.compile(r"\b(?:BR|BRULE|LAW|REG|WAGE|CONTRIB|BO|BAC|FR|NFR|ML|POL|EVAL|UAT|SIT)-[A-Z0-9-]+\b")
CR_RE = re.compile(r"<!--\s*GOVERNANCE-CR\s*(\{.*?\})\s*GOVERNANCE-CR\s*-->", re.S)
CR_PATH_RE = re.compile(r"docs/00_PROJECT_GOVERNANCE/change_requests/(CR-[A-Za-z0-9_-]+)\.md")
SHA_RE = re.compile(r"^[0-9a-f]{40,64}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")

TRUSTED_CONTROL_PATHS = {
    ".github/workflows/governance-trusted.yml",
    ".github/CODEOWNERS",
    "scripts/validate_governance.py",
    MANIFEST_REL,
    "docs/00_PROJECT_GOVERNANCE/CHANGE_CONTROL_PROCESS.md",
    APPROVAL_REL,
}

def fail(msg: str) -> None:
    raise SystemExit(f"GOVERNANCE_FAIL: {msg}")

def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True, stderr=subprocess.STDOUT)

def git_bytes(*args: str) -> bytes:
    return subprocess.check_output(["git", *args], cwd=ROOT, stderr=subprocess.STDOUT)

def git_exists(ref: str, path: str) -> bool:
    return subprocess.run(
        ["git", "cat-file", "-e", f"{ref}:{path}"],
        cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    ).returncode == 0

def git_text(ref: str, path: str) -> str:
    return git("show", f"{ref}:{path}")

def blob_sha256(ref: str, path: str) -> str | None:
    if not git_exists(ref, path):
        return None
    return hashlib.sha256(git_bytes("show", f"{ref}:{path}")).hexdigest()

def load_manifest_text(text: str, label: str, allow_legacy: bool = False) -> list[dict[str, str]]:
    rows = list(csv.DictReader(text.splitlines()))
    required = {
        "path", "status", "artifact_authority_level", "source_authority",
        "artifact_role", "authority", "owner", "notes",
    }
    legacy = {"path", "status", "authority_level", "authority", "owner", "notes"}
    if not rows:
        fail(f"{label}: manifest is empty")
    fields = set(rows[0])
    if fields == required:
        return rows
    if allow_legacy and fields == legacy:
        return [{
            "path": row["path"],
            "status": row["status"],
            "artifact_authority_level": row["authority_level"],
            "source_authority": "",
            "artifact_role": "LEGACY_UNCLASSIFIED",
            "authority": row["authority"],
            "owner": row["owner"],
            "notes": row["notes"],
        } for row in rows]
    fail(f"{label}: manifest columns mismatch: {fields} != {required}")

def load_head_manifest() -> list[dict[str, str]]:
    return load_manifest_text(MANIFEST.read_text(encoding="utf-8"), "head")

def load_base_manifest(base: str) -> list[dict[str, str]]:
    if not git_exists(base, MANIFEST_REL):
        return []
    return load_manifest_text(git_text(base, MANIFEST_REL), "base", allow_legacy=True)

def manifest_map(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {r["path"]: r for r in rows}

def repo_path(manifest_path: str) -> str:
    return f"docs/{manifest_path}"

def parse_frontmatter(path: Path) -> dict[str, str] | None:
    if path.suffix.lower() != ".md" or not path.exists():
        return None
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 4)
    if end < 0:
        fail(f"{path.relative_to(ROOT)}: malformed frontmatter")
    out: dict[str, str] = {}
    for raw in text[4:end].splitlines():
        if not raw.strip() or raw.lstrip().startswith("#") or ":" not in raw:
            continue
        key, value = raw.split(":", 1)
        out[key.strip()] = value.strip().strip('"').strip("'")
    return out

def validate_rows(rows: list[dict[str, str]]) -> None:
    seen: set[str] = set()
    for row in rows:
        path = row["path"]
        if path in seen:
            fail(f"duplicate manifest path: {path}")
        seen.add(path)
        if row["artifact_authority_level"] not in ALLOWED_LEVELS:
            fail(f"{path}: invalid repository authority {row['artifact_authority_level']}")
        if row["status"] not in ALLOWED_STATUS:
            fail(f"{path}: invalid status {row['status']}")
        if row["source_authority"] and row["source_authority"] != "A0":
            fail(f"{path}: unsupported source_authority {row['source_authority']}")
        if row["artifact_role"] == "A0_DERIVED_REGISTRY" and row["source_authority"] != "A0":
            fail(f"{path}: A0-derived registry must declare source_authority=A0")

        fs_path = ROOT / repo_path(path)
        if not fs_path.exists():
            fail(f"manifest path does not exist: {path}")

        if row["status"] in {"REVIEWED", "FROZEN"}:
            fm = parse_frontmatter(fs_path)
            if fm:
                if fm.get("status") and fm["status"] != row["status"]:
                    fail(f"{path}: frontmatter status={fm['status']} != manifest {row['status']}")
                level = fm.get("artifact_authority_level") or fm.get("authority_level")
                if level and level != row["artifact_authority_level"]:
                    fail(f"{path}: frontmatter authority level={level} != manifest {row['artifact_authority_level']}")
                for key in ("owner", "source_authority", "artifact_role"):
                    if fm.get(key) is not None and fm.get(key, "") != row.get(key, ""):
                        fail(f"{path}: frontmatter {key}={fm.get(key)!r} != manifest {row.get(key)!r}")

        if row["status"] == "FROZEN":
            blob = " ".join(row.values())
            if any(token in blob for token in PLACEHOLDER_TOKENS):
                fail(f"{path}: FROZEN row contains placeholder metadata")
            if not row["owner"] or not row["authority"]:
                fail(f"{path}: FROZEN row missing owner/authority")

def event_refs() -> tuple[str | None, str | None]:
    base = os.getenv("GOV_BASE_SHA")
    head = os.getenv("GOV_HEAD_SHA")
    if base and head:
        return base, head
    event_path = os.getenv("GITHUB_EVENT_PATH")
    if not event_path or not Path(event_path).exists():
        return None, None
    event = json.loads(Path(event_path).read_text(encoding="utf-8"))
    if "pull_request" in event:
        return event["pull_request"]["base"]["sha"], event["pull_request"]["head"]["sha"]
    if event.get("before") and event.get("after") and set(event["before"]) != {"0"}:
        return event["before"], event["after"]
    return None, None

def changed_files(base: str, head: str) -> set[str]:
    return {x.strip() for x in git("diff", "--name-only", f"{base}...{head}").splitlines() if x.strip()}

def context_ids(ref: str, path: str, line_no: int) -> set[str]:
    if not git_exists(ref, path):
        return set()
    lines = git_text(ref, path).splitlines()
    current: set[str] = set()
    stop = min(max(line_no, 1), len(lines))
    for line in lines[:stop]:
        found = set(ID_RE.findall(line))
        if found:
            current = found
    return current

def changed_ids(base: str, head: str, path: str) -> set[str]:
    try:
        diff = git("diff", "--unified=0", f"{base}...{head}", "--", path)
    except subprocess.CalledProcessError:
        return set()

    ids: set[str] = set()
    old_line = new_line = 0
    for line in diff.splitlines():
        h = HUNK_RE.match(line)
        if h:
            old_line = int(h.group(1))
            new_line = int(h.group(3))
            continue
        if line.startswith("---") or line.startswith("+++"):
            continue
        if line.startswith("-"):
            ids.update(ID_RE.findall(line[1:]))
            ids.update(context_ids(base, path, old_line))
            old_line += 1
        elif line.startswith("+"):
            ids.update(ID_RE.findall(line[1:]))
            ids.update(context_ids(head, path, new_line))
            new_line += 1
        elif line.startswith(" "):
            old_line += 1
            new_line += 1
    return ids

def load_approval_registry(ref: str) -> list[dict[str, str]]:
    if not git_exists(ref, APPROVAL_REL):
        fail(f"{ref}: approval authority registry missing")
    rows = list(csv.DictReader(git_text(ref, APPROVAL_REL).splitlines()))
    if not rows:
        fail(f"{ref}: approval authority registry empty")
    return rows

def authorized_for(path: str, approver: str, registry: list[dict[str, str]]) -> bool:
    candidates = [row for row in registry if path.startswith(row["path_prefix"])]
    if not candidates:
        return False
    row = max(candidates, key=lambda r: len(r["path_prefix"]))
    allowed = {x.strip() for x in row["authorized_approver_login"].split("|") if x.strip()}
    return approver in allowed

def valid_iso_date(value: object) -> bool:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True

def valid_repo_path(path: object) -> bool:
    if not isinstance(path, str) or not path or path.startswith("/") or "\\" in path:
        return False
    return ".." not in Path(path).parts

def parse_cr(text: str, path: str) -> dict:
    match = CR_RE.search(text)
    if not match:
        fail(f"{path}: missing GOVERNANCE-CR JSON block")
    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        fail(f"{path}: invalid CR JSON: {exc}")

    required = {
        "schema_version", "cr_id", "decision", "approver", "approved_at",
        "authorized_base_sha", "targets", "validation_plan",
    }
    missing = required - set(data)
    if missing:
        fail(f"{path}: CR block missing fields {sorted(missing)}")
    if data["schema_version"] != 2:
        fail(f"{path}: unsupported CR schema_version {data['schema_version']}")

    filename = CR_PATH_RE.fullmatch(path)
    if not filename:
        fail(f"{path}: invalid CR filename")
    if data["cr_id"] != filename.group(1):
        fail(f"{path}: cr_id {data['cr_id']} does not match filename {filename.group(1)}")

    if data["decision"] not in {"PENDING", "APPROVE", "REJECT", "DEFER"}:
        fail(f"{path}: invalid decision {data['decision']}")
    if data["decision"] == "APPROVE":
        if not valid_iso_date(data["approved_at"]):
            fail(f"{path}: approved_at must be a valid ISO date YYYY-MM-DD")
        if not isinstance(data["approver"], str) or not data["approver"].strip():
            fail(f"{path}: approved CR requires approver")
        if not isinstance(data["validation_plan"], str) or not data["validation_plan"].strip():
            fail(f"{path}: approved CR requires validation_plan")
        if not isinstance(data["authorized_base_sha"], str) or not SHA_RE.fullmatch(data["authorized_base_sha"]):
            fail(f"{path}: authorized_base_sha must be a Git SHA")

    targets = data["targets"]
    if not isinstance(targets, dict) or not targets:
        fail(f"{path}: targets must be a non-empty object")

    for target_path, spec in targets.items():
        if not valid_repo_path(target_path):
            fail(f"{path}: invalid target path {target_path!r}")
        if not isinstance(spec, dict):
            fail(f"{path}: target {target_path} must be an object")
        target_required = {"source_sha256", "target_state", "affected_ids"}
        if not target_required.issubset(spec):
            fail(f"{path}: target {target_path} missing {sorted(target_required - set(spec))}")
        if not isinstance(spec["source_sha256"], str) or not SHA256_RE.fullmatch(spec["source_sha256"]):
            fail(f"{path}: target {target_path} source_sha256 invalid")
        if spec["target_state"] not in {"PRESENT", "DELETE"}:
            fail(f"{path}: target {target_path} invalid target_state")
        if not isinstance(spec["affected_ids"], list) or not all(isinstance(x, str) for x in spec["affected_ids"]):
            fail(f"{path}: target {target_path} affected_ids must be string list")
        if spec["target_state"] == "PRESENT":
            if not isinstance(spec.get("target_sha256"), str) or not SHA256_RE.fullmatch(spec["target_sha256"]):
                fail(f"{path}: PRESENT target {target_path} requires target_sha256")
        elif spec.get("target_sha256") not in {None, ""}:
            fail(f"{path}: DELETE target {target_path} must not declare target_sha256")
    return data

def approved_base_crs(base: str, registry: list[dict[str, str]]) -> list[tuple[str, dict]]:
    try:
        names = git("ls-tree", "-r", "--name-only", base, "docs/00_PROJECT_GOVERNANCE/change_requests").splitlines()
    except subprocess.CalledProcessError:
        return []

    try:
        base_parent = git("rev-parse", f"{base}^1").strip()
    except subprocess.CalledProcessError:
        return []

    out: list[tuple[str, dict]] = []
    for path in names:
        if not CR_PATH_RE.fullmatch(path):
            continue
        data = parse_cr(git_text(base, path), path)
        if data["decision"] != "APPROVE":
            continue

        # One-shot authorization: the semantic PR base must be the commit that
        # introduced this approved CR directly on top of authorized_base_sha.
        if data["authorized_base_sha"] != base_parent:
            continue
        if git_exists(base_parent, path):
            continue

        # Snapshot isolation: the approval base commit has exactly one purpose:
        # introduce this approved CR and nothing else. No CHANGE_LOG, manifest,
        # unrelated REVIEWED docs, second CR, or target mutation may hitch a ride.
        approval_changed = {
            item.strip()
            for item in git("diff", "--name-only", base_parent, base).splitlines()
            if item.strip()
        }
        if approval_changed != {path}:
            fail(
                f"{path}: CR approval commit must be CR-only; "
                f"changed paths={sorted(approval_changed)}"
            )

        for target_path, spec in data["targets"].items():
            if not authorized_for(target_path, data["approver"], registry):
                fail(f"{path}: approver {data['approver']} not authorized for {target_path}")
            source_hash = blob_sha256(base_parent, target_path)
            if source_hash != spec["source_sha256"]:
                fail(f"{path}: source hash mismatch for {target_path} at authorized base")
            # CR approval commit itself may not mutate the target it authorizes.
            if blob_sha256(base, target_path) != spec["source_sha256"]:
                fail(f"{path}: approval commit changed authorized target {target_path}")
        out.append((path, data))
    return out

def target_matches(spec: dict, head: str, path: str) -> bool:
    if spec["target_state"] == "DELETE":
        return not git_exists(head, path)
    actual = blob_sha256(head, path)
    return actual == spec["target_sha256"]

def require_authorization(
    protected_paths: set[str],
    base: str,
    head: str,
    crs: list[tuple[str, dict]],
    changed: set[str],
) -> None:
    for path in sorted(protected_paths):
        ids = changed_ids(base, head, path)
        valid: list[str] = []
        for cr_path, cr in crs:
            if cr_path in changed:
                continue
            spec = cr["targets"].get(path)
            if not spec or not target_matches(spec, head, path):
                continue
            approved_ids = set(spec["affected_ids"])
            if ids and not ids.issubset(approved_ids):
                continue
            if approved_ids and not ids:
                # ID-scoped authorization cannot silently degrade to path-only.
                continue
            if ids and not approved_ids:
                continue
            valid.append(cr_path)

        if not valid:
            fail(
                f"{path}: protected change lacks one-shot approved CR bound to "
                f"source+target content; detected IDs={sorted(ids)}"
            )

def validate_protected_changes(head_rows: list[dict[str, str]], base: str, head: str) -> None:
    base_rows = load_base_manifest(base)
    if not base_rows:
        return

    bmap = manifest_map(base_rows)
    hmap = manifest_map(head_rows)
    changed = changed_files(base, head)
    protected: set[str] = set()

    for manifest_path, base_row in bmap.items():
        if base_row["status"] != "FROZEN":
            continue
        path = repo_path(manifest_path)
        head_row = hmap.get(manifest_path)
        downgraded_or_removed = head_row is None or head_row["status"] != "FROZEN"
        authority_changed = bool(head_row) and any(
            head_row.get(key) != base_row.get(key)
            for key in ("artifact_authority_level", "source_authority", "artifact_role", "authority", "owner")
        )
        if path in changed or downgraded_or_removed or authority_changed:
            protected.add(path)

    trusted_bootstrapped = git_exists(base, "scripts/validate_governance.py") and git_exists(
        base, ".github/workflows/governance-trusted.yml"
    )
    if trusted_bootstrapped:
        protected |= changed & TRUSTED_CONTROL_PATHS

    if not protected:
        return

    registry = load_approval_registry(base)
    crs = approved_base_crs(base, registry)
    require_authorization(protected, base, head, crs, changed)

    if "docs/00_PROJECT_GOVERNANCE/CHANGE_LOG.md" not in changed:
        fail(f"protected changes require CHANGE_LOG.md: {sorted(protected)}")

def main() -> None:
    rows = load_head_manifest()
    validate_rows(rows)
    base, head = event_refs()
    if base and head:
        validate_protected_changes(rows, base, head)
    print(f"governance ok: {len(rows)} manifest entries")

if __name__ == "__main__":
    main()
