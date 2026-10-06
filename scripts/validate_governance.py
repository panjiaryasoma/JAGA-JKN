from __future__ import annotations

import csv
import json
import os
import re
import subprocess
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

def git_exists(ref: str, path: str) -> bool:
    return subprocess.run(
        ["git", "cat-file", "-e", f"{ref}:{path}"],
        cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    ).returncode == 0

def git_text(ref: str, path: str) -> str:
    return git("show", f"{ref}:{path}")

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
        normalized = []
        for row in rows:
            normalized.append({
                "path": row["path"],
                "status": row["status"],
                "artifact_authority_level": row["authority_level"],
                "source_authority": "",
                "artifact_role": "LEGACY_UNCLASSIFIED",
                "authority": row["authority"],
                "owner": row["owner"],
                "notes": row["notes"],
            })
        return normalized
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
            fail(f"{path}: repo artifact cannot have authority {row['artifact_authority_level']}")
        if row["status"] not in ALLOWED_STATUS:
            fail(f"{path}: invalid status {row['status']}")
        if row["source_authority"] and row["source_authority"] != "A0":
            fail(f"{path}: unsupported source_authority {row['source_authority']}")
        if row["artifact_role"] == "A0_DERIVED_REGISTRY" and row["source_authority"] != "A0":
            fail(f"{path}: derived A0 registry must declare source_authority=A0")

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
            if any(tok in blob for tok in PLACEHOLDER_TOKENS):
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

def diff_ids(base: str, head: str, path: str) -> set[str]:
    try:
        diff = git("diff", "--unified=0", f"{base}...{head}", "--", path)
    except subprocess.CalledProcessError:
        return set()
    changed_lines = "\n".join(
        line[1:] for line in diff.splitlines()
        if (line.startswith("+") or line.startswith("-")) and not line.startswith(("+++", "---"))
    )
    return set(ID_RE.findall(changed_lines))

def load_approval_registry(ref: str) -> list[dict[str, str]]:
    if not git_exists(ref, APPROVAL_REL):
        fail(f"{ref}: approval authority registry missing")
    rows = list(csv.DictReader(git_text(ref, APPROVAL_REL).splitlines()))
    if not rows:
        fail(f"{ref}: approval authority registry empty")
    return rows

def authorized_for(path: str, approver: str, registry: list[dict[str, str]]) -> bool:
    candidates = [r for r in registry if path.startswith(r["path_prefix"])]
    if not candidates:
        return False
    row = max(candidates, key=lambda r: len(r["path_prefix"]))
    allowed = {x.strip() for x in row["authorized_approver_login"].split("|") if x.strip()}
    return approver in allowed

def parse_cr(text: str, path: str) -> dict:
    m = CR_RE.search(text)
    if not m:
        fail(f"{path}: missing GOVERNANCE-CR JSON block")
    try:
        data = json.loads(m.group(1))
    except json.JSONDecodeError as e:
        fail(f"{path}: invalid CR JSON: {e}")
    required = {"cr_id", "decision", "approver", "approved_at", "affected_paths", "affected_ids", "validation_plan"}
    if not required.issubset(data):
        fail(f"{path}: CR block missing fields {sorted(required - set(data))}")
    return data

def approved_base_crs(base: str, registry: list[dict[str, str]]) -> list[tuple[str, dict]]:
    try:
        names = git("ls-tree", "-r", "--name-only", base, "docs/00_PROJECT_GOVERNANCE/change_requests").splitlines()
    except subprocess.CalledProcessError:
        return []
    out = []
    for path in names:
        if not re.fullmatch(r"docs/00_PROJECT_GOVERNANCE/change_requests/CR-[A-Za-z0-9_-]+\.md", path):
            continue
        data = parse_cr(git_text(base, path), path)
        if data["decision"] != "APPROVE":
            continue
        if not str(data["approved_at"]).strip() or not str(data["validation_plan"]).strip():
            fail(f"{path}: approved CR lacks approval date or validation plan")
        affected = data["affected_paths"]
        ids = data["affected_ids"]
        if not isinstance(affected, list) or not affected:
            fail(f"{path}: approved CR must contain affected_paths")
        if not isinstance(ids, list):
            fail(f"{path}: affected_ids must be a list")
        for p in affected:
            if not authorized_for(p, data["approver"], registry):
                fail(f"{path}: approver {data['approver']} not authorized for {p}")
        out.append((path, data))
    return out

def require_authorization(
    protected_paths: set[str],
    base: str,
    head: str,
    crs: list[tuple[str, dict]],
) -> None:
    for path in sorted(protected_paths):
        changed_ids = diff_ids(base, head, path)
        valid = []
        for cr_path, cr in crs:
            if path not in set(cr["affected_paths"]):
                continue
            cr_ids = set(cr["affected_ids"])
            if changed_ids and not changed_ids.issubset(cr_ids):
                continue
            valid.append(cr_path)
        if not valid:
            fail(
                f"{path}: protected change lacks pre-approved base CR "
                f"covering path and changed IDs {sorted(changed_ids)}"
            )

def validate_protected_changes(head_rows: list[dict[str, str]], base: str, head: str) -> None:
    base_rows = load_base_manifest(base)
    if not base_rows:
        return
    bmap = manifest_map(base_rows)
    hmap = manifest_map(head_rows)
    changed = changed_files(base, head)

    base_frozen_manifest_paths = {p for p, r in bmap.items() if r["status"] == "FROZEN"}
    protected: set[str] = set()

    for mpath in base_frozen_manifest_paths:
        rpath = repo_path(mpath)
        head_row = hmap.get(mpath)
        row_downgraded_or_removed = head_row is None or head_row["status"] != "FROZEN"
        authority_changed = bool(head_row) and any(
            head_row.get(k) != bmap[mpath].get(k)
            for k in ("artifact_authority_level", "source_authority", "artifact_role", "authority", "owner")
        )
        if rpath in changed or row_downgraded_or_removed or authority_changed:
            protected.add(rpath)

    trusted_bootstrapped = git_exists(base, "scripts/validate_governance.py") and git_exists(
        base, ".github/workflows/governance-trusted.yml"
    )
    if trusted_bootstrapped:
        protected |= changed & TRUSTED_CONTROL_PATHS

    if not protected:
        return

    registry = load_approval_registry(base)
    crs = approved_base_crs(base, registry)
    require_authorization(protected, base, head, crs)

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
