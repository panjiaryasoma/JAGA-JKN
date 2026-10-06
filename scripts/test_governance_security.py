from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

VALIDATOR = Path(__file__).with_name("validate_governance.py").resolve()

def run(cmd, cwd, check=True):
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=check)

def write(root: Path, path: str, text: str):
    p = root / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")

def manifest(status="FROZEN"):
    return (
        "path,status,artifact_authority_level,source_authority,artifact_role,authority,owner,notes\n"
        f"02_BUSINESS_AND_PRODUCT_REQUIREMENTS/01_BUSINESS/BRD.md,{status},A3,,BUSINESS_AUTHORITY,Business Requirements,Panji,protected fixture\n"
    )

BRD_FROZEN = """---
project: JAGA-JKN
status: FROZEN
owner: Panji
artifact_authority_level: A3
---
# BRD
BR-001 baseline
"""

BRD_REVIEWED = BRD_FROZEN.replace("status: FROZEN", "status: REVIEWED").replace("baseline", "changed")
BRD_CHANGED = BRD_FROZEN.replace("baseline", "changed")

APPROVAL = """path_prefix,authority_scope,authorized_approver_login,accountable_role,required_human_review_role,enforcement_note
docs/02_BUSINESS_AND_PRODUCT_REQUIREMENTS/01_BUSINESS/,A3,panjiaryasoma,Project/Product Accountable,,test
scripts/validate_governance.py,CONTROL,panjiaryasoma,Project/Product Accountable,,test
"""

APPROVED_CR = """# CR
<!-- GOVERNANCE-CR
{
  "cr_id": "CR-TEST-001",
  "decision": "APPROVE",
  "approver": "panjiaryasoma",
  "approved_at": "2026-10-07",
  "affected_paths": ["docs/02_BUSINESS_AND_PRODUCT_REQUIREMENTS/01_BUSINESS/BRD.md"],
  "affected_ids": ["BR-001"],
  "validation_plan": "Run governance regression tests."
}
GOVERNANCE-CR -->
"""

PENDING_CR = APPROVED_CR.replace('"APPROVE"', '"PENDING"')

class GovernanceSecurityTests(unittest.TestCase):
    def repo(self, approved_cr=False):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        run(["git", "init", "-b", "main"], root)
        run(["git", "config", "user.email", "test@example.com"], root)
        run(["git", "config", "user.name", "Governance Test"], root)
        write(root, "docs/DOCUMENT_MANIFEST.csv", manifest())
        write(root, "docs/02_BUSINESS_AND_PRODUCT_REQUIREMENTS/01_BUSINESS/BRD.md", BRD_FROZEN)
        write(root, "docs/00_PROJECT_GOVERNANCE/APPROVAL_AUTHORITY.csv", APPROVAL)
        write(root, "docs/00_PROJECT_GOVERNANCE/CHANGE_LOG.md", "# log\n")
        write(root, "scripts/validate_governance.py", "# trusted marker\n")
        write(root, ".github/workflows/governance-trusted.yml", "name: trusted\n")
        if approved_cr:
            write(root, "docs/00_PROJECT_GOVERNANCE/change_requests/CR-TEST-001.md", APPROVED_CR)
        run(["git", "add", "."], root)
        run(["git", "commit", "-m", "base"], root)
        base = run(["git", "rev-parse", "HEAD"], root).stdout.strip()
        return td, root, base

    def validator(self, root, base, head):
        env = os.environ.copy()
        env.update({"GOV_REPO_ROOT": str(root), "GOV_BASE_SHA": base, "GOV_HEAD_SHA": head})
        return subprocess.run(["python", str(VALIDATOR)], cwd=root, env=env, text=True, capture_output=True)

    def test_downgrade_attack_fails(self):
        td, root, base = self.repo()
        self.addCleanup(td.cleanup)
        write(root, "docs/DOCUMENT_MANIFEST.csv", manifest("REVIEWED"))
        write(root, "docs/02_BUSINESS_AND_PRODUCT_REQUIREMENTS/01_BUSINESS/BRD.md", BRD_REVIEWED)
        run(["git", "add", "."], root); run(["git", "commit", "-m", "attack"], root)
        head = run(["git", "rev-parse", "HEAD"], root).stdout.strip()
        p = self.validator(root, base, head)
        self.assertNotEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("pre-approved base CR", p.stdout + p.stderr)

    def test_dummy_pending_cr_in_same_pr_fails(self):
        td, root, base = self.repo()
        self.addCleanup(td.cleanup)
        write(root, "docs/02_BUSINESS_AND_PRODUCT_REQUIREMENTS/01_BUSINESS/BRD.md", BRD_CHANGED)
        write(root, "docs/00_PROJECT_GOVERNANCE/CHANGE_LOG.md", "# log\nchanged\n")
        write(root, "docs/00_PROJECT_GOVERNANCE/change_requests/CR-TEST-999.md", PENDING_CR)
        run(["git", "add", "."], root); run(["git", "commit", "-m", "dummy cr attack"], root)
        head = run(["git", "rev-parse", "HEAD"], root).stdout.strip()
        p = self.validator(root, base, head)
        self.assertNotEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("pre-approved base CR", p.stdout + p.stderr)

    def test_preapproved_base_cr_allows_covered_change(self):
        td, root, base = self.repo(approved_cr=True)
        self.addCleanup(td.cleanup)
        write(root, "docs/02_BUSINESS_AND_PRODUCT_REQUIREMENTS/01_BUSINESS/BRD.md", BRD_CHANGED)
        write(root, "docs/00_PROJECT_GOVERNANCE/CHANGE_LOG.md", "# log\nauthorized change\n")
        run(["git", "add", "."], root); run(["git", "commit", "-m", "authorized"], root)
        head = run(["git", "rev-parse", "HEAD"], root).stdout.strip()
        p = self.validator(root, base, head)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_trusted_control_self_change_fails_without_base_cr(self):
        td, root, base = self.repo()
        self.addCleanup(td.cleanup)
        write(root, "scripts/validate_governance.py", "# attacker replaces guard\n")
        write(root, "docs/00_PROJECT_GOVERNANCE/CHANGE_LOG.md", "# log\ntouched\n")
        run(["git", "add", "."], root); run(["git", "commit", "-m", "self bypass"], root)
        head = run(["git", "rev-parse", "HEAD"], root).stdout.strip()
        p = self.validator(root, base, head)
        self.assertNotEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("scripts/validate_governance.py", p.stdout + p.stderr)

if __name__ == "__main__":
    unittest.main()
