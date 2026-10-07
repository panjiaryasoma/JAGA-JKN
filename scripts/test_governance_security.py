from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

VALIDATOR = Path(__file__).with_name("validate_governance.py").resolve()
BRD_PATH = "docs/02_BUSINESS_AND_PRODUCT_REQUIREMENTS/01_BUSINESS/BRD.md"
CR_DIR = "docs/00_PROJECT_GOVERNANCE/change_requests"

def run(cmd, cwd, check=True):
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=check)

def write(root: Path, path: str, text: str):
    p = root / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")

def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()

def manifest(status="FROZEN", include_brd=True):
    rows = [
        "path,status,artifact_authority_level,source_authority,artifact_role,authority,owner,notes",
        "README.md,REVIEWED,A1,,PROJECT_GOVERNANCE,Project Governance,Panji,test fixture",
    ]
    if include_brd:
        rows.append(
            f"02_BUSINESS_AND_PRODUCT_REQUIREMENTS/01_BUSINESS/BRD.md,{status},"
            "A3,,BUSINESS_AUTHORITY,Business Requirements,Panji,protected fixture"
        )
    return "\n".join(rows) + "\n"

README = """---
project: JAGA-JKN
status: REVIEWED
owner: Panji
artifact_authority_level: A1
---
# Docs
"""

BRD_A = """---
project: JAGA-JKN
status: FROZEN
owner: Panji
artifact_authority_level: A3
---
# BRD

## BR-001
Automated signal may NEVER establish violation.
"""

BRD_B = BRD_A.replace("NEVER", "only NEVER")
BRD_C = BRD_A.replace("NEVER", "MAY")
BRD_NO_ID_CONTEXT = """---
project: JAGA-JKN
status: FROZEN
owner: Panji
artifact_authority_level: A3
---
# BRD

General policy statement.

## BR-001
Automated signal may NEVER establish violation.
"""
BRD_NO_ID_CONTEXT_CHANGED = BRD_NO_ID_CONTEXT.replace(
    "General policy statement.",
    "General policy statement changed.",
)

APPROVAL = """path_prefix,authority_scope,authorized_approver_login,accountable_role,required_human_review_role,enforcement_note
docs/02_BUSINESS_AND_PRODUCT_REQUIREMENTS/01_BUSINESS/,A3,panjiaryasoma,Project/Product Accountable,,test
scripts/validate_governance.py,CONTROL,panjiaryasoma,Project/Product Accountable,,test
"""

def cr_text(
    cr_id: str,
    authorized_base: str,
    source: str,
    target: str | None,
    *,
    affected_ids=None,
    decision="APPROVE",
    approved_at="2026-10-07",
    filename_id=None,
):
    if affected_ids is None:
        affected_ids = ["BR-001"]
    spec = {
        "source_sha256": sha256_text(source),
        "target_state": "DELETE" if target is None else "PRESENT",
        "affected_ids": affected_ids,
    }
    if target is not None:
        spec["target_sha256"] = sha256_text(target)
    data = {
        "schema_version": 3,
        "cr_id": filename_id or cr_id,
        "decision": decision,
        "approver": "panjiaryasoma" if decision == "APPROVE" else "",
        "approved_at": approved_at if decision == "APPROVE" else "",
        "approval_pr_number": 101,
        "authorized_base_sha": authorized_base,
        "targets": {BRD_PATH: spec},
        "validation_plan": "Run governance security regression tests.",
    }
    return "# CR\n<!-- GOVERNANCE-CR\n" + json.dumps(data, indent=2) + "\nGOVERNANCE-CR -->\n"

class GovernanceSecurityTests(unittest.TestCase):
    def repo(self, brd=BRD_A, trusted=False):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        run(["git", "init", "-b", "main"], root)
        run(["git", "config", "user.email", "test@example.com"], root)
        run(["git", "config", "user.name", "Governance Test"], root)
        write(root, "docs/DOCUMENT_MANIFEST.csv", manifest())
        write(root, "docs/README.md", README)
        write(root, BRD_PATH, brd)
        write(root, "docs/00_PROJECT_GOVERNANCE/APPROVAL_AUTHORITY.csv", APPROVAL)
        write(root, "docs/00_PROJECT_GOVERNANCE/CHANGE_LOG.md", "# log\n")
        if trusted:
            write(root, "scripts/validate_governance.py", "# trusted marker\n")
            write(root, ".github/workflows/governance-trusted.yml", "name: trusted\n")
        run(["git", "add", "."], root)
        run(["git", "commit", "-m", "base"], root)
        base = run(["git", "rev-parse", "HEAD"], root).stdout.strip()
        return td, root, base

    def commit(self, root, message):
        run(["git", "add", "-A"], root)
        run(["git", "commit", "-m", message], root)
        return run(["git", "rev-parse", "HEAD"], root).stdout.strip()

    def approve(self, root, authorized_base, source, target, *, cr_id="CR-TEST-001", affected_ids=None,
                authorized_base_override=None, approved_at="2026-10-07", filename_id=None):
        path = f"{CR_DIR}/{cr_id}.md"
        write(
            root, path,
            cr_text(
                cr_id,
                authorized_base_override or authorized_base,
                source,
                target,
                affected_ids=affected_ids,
                approved_at=approved_at,
                filename_id=filename_id,
            ),
        )
        return self.commit(root, "approve change request")

    def validator(self, root, base, head, *, merged_by="panjiaryasoma",
                  merge_commit_sha=None, current_pr_number=101):
        env = os.environ.copy()
        fixture = {
            "101": {
                "merged": True,
                "merge_commit_sha": merge_commit_sha or base,
                "merged_by": {"login": merged_by},
            }
        }
        env.update({
            "GOV_REPO_ROOT": str(root),
            "GOV_BASE_SHA": base,
            "GOV_HEAD_SHA": head,
            "GOV_PR_NUMBER": str(current_pr_number),
            "GOV_TEST_PR_FIXTURES_JSON": json.dumps(fixture),
        })
        return subprocess.run(
            ["python", str(VALIDATOR)], cwd=root, env=env, text=True, capture_output=True
        )

    def assert_rejected(self, process, needle=None):
        self.assertNotEqual(process.returncode, 0, process.stdout + process.stderr)
        if needle:
            self.assertIn(needle, process.stdout + process.stderr)

    def test_downgrade_attack_fails(self):
        td, root, base = self.repo()
        self.addCleanup(td.cleanup)
        write(root, "docs/DOCUMENT_MANIFEST.csv", manifest("REVIEWED"))
        write(root, BRD_PATH, BRD_B.replace("status: FROZEN", "status: REVIEWED"))
        head = self.commit(root, "downgrade attack")
        self.assert_rejected(self.validator(root, base, head), "one-shot approved CR")

    def test_same_pr_dummy_cr_fails(self):
        td, root, base = self.repo()
        self.addCleanup(td.cleanup)
        write(root, BRD_PATH, BRD_B)
        write(root, f"{CR_DIR}/CR-TEST-999.md", cr_text("CR-TEST-999", base, BRD_A, BRD_B))
        write(root, "docs/00_PROJECT_GOVERNANCE/CHANGE_LOG.md", "# log\nchanged\n")
        head = self.commit(root, "same pr cr attack")
        self.assert_rejected(self.validator(root, base, head), "one-shot approved CR")

    def test_exact_approved_target_accepts(self):
        td, root, pre = self.repo()
        self.addCleanup(td.cleanup)
        approval_base = self.approve(root, pre, BRD_A, BRD_B)
        write(root, BRD_PATH, BRD_B)
        write(root, "docs/00_PROJECT_GOVERNANCE/CHANGE_LOG.md", "# log\nauthorized\n")
        head = self.commit(root, "apply exact target")
        p = self.validator(root, approval_base, head)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_replay_second_different_change_rejected(self):
        td, root, pre = self.repo()
        self.addCleanup(td.cleanup)
        approval_base = self.approve(root, pre, BRD_A, BRD_B)
        write(root, BRD_PATH, BRD_B)
        write(root, "docs/00_PROJECT_GOVERNANCE/CHANGE_LOG.md", "# log\nfirst use\n")
        first = self.commit(root, "first authorized change")
        self.assertEqual(self.validator(root, approval_base, first).returncode, 0)

        write(root, BRD_PATH, BRD_C)
        write(root, "docs/00_PROJECT_GOVERNANCE/CHANGE_LOG.md", "# log\nsecond use\n")
        second = self.commit(root, "replay attempt")
        self.assert_rejected(self.validator(root, first, second), "one-shot approved CR")

    def test_target_hash_mismatch_rejected(self):
        td, root, pre = self.repo()
        self.addCleanup(td.cleanup)
        approval_base = self.approve(root, pre, BRD_A, BRD_B)
        write(root, BRD_PATH, BRD_C)
        write(root, "docs/00_PROJECT_GOVERNANCE/CHANGE_LOG.md", "# log\nmismatch\n")
        head = self.commit(root, "wrong target")
        self.assert_rejected(self.validator(root, approval_base, head), "one-shot approved CR")

    def test_authorized_base_sha_mismatch_rejected(self):
        td, root, pre = self.repo()
        self.addCleanup(td.cleanup)
        approval_base = self.approve(
            root, pre, BRD_A, BRD_B,
            authorized_base_override="0" * 40,
        )
        write(root, BRD_PATH, BRD_B)
        write(root, "docs/00_PROJECT_GOVERNANCE/CHANGE_LOG.md", "# log\nbase mismatch\n")
        head = self.commit(root, "base mismatch")
        self.assert_rejected(self.validator(root, approval_base, head), "one-shot approved CR")

    def test_id_scoped_cr_rejects_change_without_identifiable_id_context(self):
        td, root, pre = self.repo(brd=BRD_NO_ID_CONTEXT)
        self.addCleanup(td.cleanup)
        approval_base = self.approve(
            root, pre, BRD_NO_ID_CONTEXT, BRD_NO_ID_CONTEXT_CHANGED,
            affected_ids=["BR-001"],
        )
        # Change only the trailing unscoped line; exact target hash is approved,
        # but defense-in-depth refuses to pretend the change belongs to BR-001.
        write(root, BRD_PATH, BRD_NO_ID_CONTEXT_CHANGED)
        write(root, "docs/00_PROJECT_GOVERNANCE/CHANGE_LOG.md", "# log\nunscoped\n")
        head = self.commit(root, "unscoped semantic change")
        self.assert_rejected(self.validator(root, approval_base, head), "one-shot approved CR")

    def test_explicit_delete_target_accepts_only_deletion(self):
        td, root, pre = self.repo()
        self.addCleanup(td.cleanup)
        approval_base = self.approve(root, pre, BRD_A, None)

        # A replacement is not an approved deletion.
        write(root, BRD_PATH, BRD_B)
        write(root, "docs/00_PROJECT_GOVERNANCE/CHANGE_LOG.md", "# log\nnot delete\n")
        wrong = self.commit(root, "replace instead of delete")
        self.assert_rejected(self.validator(root, approval_base, wrong), "one-shot approved CR")

        # Reset to approval base, then perform the explicit deletion and remove manifest row.
        run(["git", "reset", "--hard", approval_base], root)
        (root / BRD_PATH).unlink()
        write(root, "docs/DOCUMENT_MANIFEST.csv", manifest(include_brd=False))
        write(root, "docs/00_PROJECT_GOVERNANCE/CHANGE_LOG.md", "# log\ndelete\n")
        deleted = self.commit(root, "approved delete")
        p = self.validator(root, approval_base, deleted)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_cr_filename_must_match_cr_id(self):
        td, root, pre = self.repo()
        self.addCleanup(td.cleanup)
        approval_base = self.approve(
            root, pre, BRD_A, BRD_B,
            filename_id="CR-WRONG-ID",
        )
        write(root, BRD_PATH, BRD_B)
        write(root, "docs/00_PROJECT_GOVERNANCE/CHANGE_LOG.md", "# log\nfilename mismatch\n")
        head = self.commit(root, "filename mismatch")
        self.assert_rejected(self.validator(root, approval_base, head), "does not match filename")

    def test_approved_at_must_be_iso_date(self):
        td, root, pre = self.repo()
        self.addCleanup(td.cleanup)
        approval_base = self.approve(
            root, pre, BRD_A, BRD_B,
            approved_at="sometime yesterday",
        )
        write(root, BRD_PATH, BRD_B)
        write(root, "docs/00_PROJECT_GOVERNANCE/CHANGE_LOG.md", "# log\nbad date\n")
        head = self.commit(root, "bad approval date")
        self.assert_rejected(self.validator(root, approval_base, head), "valid ISO date")

    def test_cr_approval_commit_with_unrelated_artifact_change_rejected(self):
        td, root, pre = self.repo()
        self.addCleanup(td.cleanup)
        path = f"{CR_DIR}/CR-TEST-001.md"
        write(root, path, cr_text("CR-TEST-001", pre, BRD_A, BRD_B))
        write(root, "docs/README.md", README + "\nUnrelated reviewed-context change.\n")
        approval_base = self.commit(root, "impure approval commit")

        write(root, BRD_PATH, BRD_B)
        write(root, "docs/00_PROJECT_GOVERNANCE/CHANGE_LOG.md", "# log\nsemantic change\n")
        head = self.commit(root, "apply target after impure approval")
        self.assert_rejected(
            self.validator(root, approval_base, head),
            "CR approval commit must be CR-only",
        )

    def test_cr_approval_commit_with_second_cr_rejected(self):
        td, root, pre = self.repo()
        self.addCleanup(td.cleanup)
        write(root, f"{CR_DIR}/CR-TEST-001.md", cr_text("CR-TEST-001", pre, BRD_A, BRD_B))
        write(
            root,
            f"{CR_DIR}/CR-TEST-002.md",
            cr_text("CR-TEST-002", pre, BRD_A, BRD_B, decision="PENDING"),
        )
        approval_base = self.commit(root, "two cr approval commit")

        write(root, BRD_PATH, BRD_B)
        write(root, "docs/00_PROJECT_GOVERNANCE/CHANGE_LOG.md", "# log\nsemantic change\n")
        head = self.commit(root, "apply target after multi-cr approval")
        self.assert_rejected(
            self.validator(root, approval_base, head),
            "CR approval commit must be CR-only",
        )

    def test_valid_isolated_new_cr_ingest_accepts(self):
        td, root, pre = self.repo()
        self.addCleanup(td.cleanup)
        write(root, f"{CR_DIR}/CR-TEST-001.md", cr_text("CR-TEST-001", pre, BRD_A, BRD_B))
        approval_head = self.commit(root, "valid isolated cr")
        p = self.validator(root, pre, approval_head)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_new_malformed_cr_ingest_rejected(self):
        td, root, pre = self.repo()
        self.addCleanup(td.cleanup)
        write(root, f"{CR_DIR}/CR-TEST-001.md", "# malformed CR without governance block\n")
        approval_head = self.commit(root, "malformed cr")
        self.assert_rejected(self.validator(root, pre, approval_head), "missing GOVERNANCE-CR")

    def test_new_cr_unauthorized_approver_rejected(self):
        td, root, pre = self.repo()
        self.addCleanup(td.cleanup)
        text = cr_text("CR-TEST-001", pre, BRD_A, BRD_B).replace(
            '"approver": "panjiaryasoma"',
            '"approver": "unauthorized-user"',
        )
        write(root, f"{CR_DIR}/CR-TEST-001.md", text)
        approval_head = self.commit(root, "unauthorized cr")
        self.assert_rejected(
            self.validator(root, pre, approval_head),
            "not authorized",
        )

    def test_existing_approved_cr_edit_rejected(self):
        td, root, pre = self.repo()
        self.addCleanup(td.cleanup)
        approval_base = self.approve(root, pre, BRD_A, BRD_B)
        path = f"{CR_DIR}/CR-TEST-001.md"
        original = (root / path).read_text(encoding="utf-8")
        write(root, path, original + "\nrewritten history\n")
        head = self.commit(root, "rewrite approved cr")
        self.assert_rejected(self.validator(root, approval_base, head), "append-only")

    def test_existing_approved_cr_delete_rejected(self):
        td, root, pre = self.repo()
        self.addCleanup(td.cleanup)
        approval_base = self.approve(root, pre, BRD_A, BRD_B)
        (root / f"{CR_DIR}/CR-TEST-001.md").unlink()
        head = self.commit(root, "delete approved cr")
        self.assert_rejected(self.validator(root, approval_base, head), "append-only")

    def test_self_asserted_approver_must_match_authenticated_merge_actor(self):
        td, root, pre = self.repo()
        self.addCleanup(td.cleanup)
        approval_base = self.approve(root, pre, BRD_A, BRD_B)
        write(root, BRD_PATH, BRD_B)
        write(root, "docs/00_PROJECT_GOVERNANCE/CHANGE_LOG.md", "# log\nactor mismatch\n")
        head = self.commit(root, "semantic change")
        self.assert_rejected(
            self.validator(root, approval_base, head, merged_by="someone-else"),
            "authenticated GitHub merged_by",
        )

    def test_authenticated_authorized_merge_actor_accepts(self):
        td, root, pre = self.repo()
        self.addCleanup(td.cleanup)
        approval_base = self.approve(root, pre, BRD_A, BRD_B)
        write(root, BRD_PATH, BRD_B)
        write(root, "docs/00_PROJECT_GOVERNANCE/CHANGE_LOG.md", "# log\nauthenticated actor\n")
        head = self.commit(root, "semantic change")
        p = self.validator(root, approval_base, head, merged_by="panjiaryasoma")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_approval_pr_merge_sha_must_equal_approval_base(self):
        td, root, pre = self.repo()
        self.addCleanup(td.cleanup)
        approval_base = self.approve(root, pre, BRD_A, BRD_B)
        write(root, BRD_PATH, BRD_B)
        write(root, "docs/00_PROJECT_GOVERNANCE/CHANGE_LOG.md", "# log\nwrong merge sha\n")
        head = self.commit(root, "semantic change")
        self.assert_rejected(
            self.validator(root, approval_base, head, merge_commit_sha="0" * 40),
            "merge_commit_sha",
        )

    def test_cr_approval_pr_number_must_match_current_ingest_pr(self):
        td, root, pre = self.repo()
        self.addCleanup(td.cleanup)
        write(root, f"{CR_DIR}/CR-TEST-001.md", cr_text("CR-TEST-001", pre, BRD_A, BRD_B))
        approval_head = self.commit(root, "wrong approval pr binding")
        self.assert_rejected(
            self.validator(root, pre, approval_head, current_pr_number=999),
            "approval_pr_number",
        )

    def test_trusted_control_self_change_fails_without_one_shot_cr(self):
        td, root, base = self.repo(trusted=True)
        self.addCleanup(td.cleanup)
        write(root, "scripts/validate_governance.py", "# attacker replaces guard\n")
        write(root, "docs/00_PROJECT_GOVERNANCE/CHANGE_LOG.md", "# log\nself change\n")
        head = self.commit(root, "self bypass")
        self.assert_rejected(self.validator(root, base, head), "scripts/validate_governance.py")

if __name__ == "__main__":
    unittest.main()
