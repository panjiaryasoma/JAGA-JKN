---
project: JAGA-JKN
status: REVIEWED
version: 0.3.0
owner: Panji
artifact_authority_level: A6
authority: Verification & Governance Evidence
last_updated: 2026-10-07
---

# Phase B Contradiction Audit

## Governing verdict

The latest **independent** audit found H-B03, so the project does not self-promote that finding to CLOSED merely because its own regression tests pass.

Current state:

- Phase B content: `CONDITIONALLY PASS`
- PR #1 merge: `HOLD`
- B1 business/domain-boundary freeze: `HOLD`
- B2 executable-policy freeze: `HOLD`
- implementation: `NOT AUTHORIZED`

## H-B03 — change-control validator bypass

**Independent finding:** HIGH / BLOCKING.

### Remediation now implemented

1. **Base + head manifest**
   - protection derives from base state;
   - a base-FROZEN artifact remains protected if head downgrades, supersedes, removes, or deletes it.

2. **Pre-approved base CR**
   - protected change is authorized only by an APPROVED CR already present in base;
   - a CR created/edited in the same semantic-change PR cannot authorize that PR.

3. **CR content validation**
   - decision must equal APPROVE;
   - approval date required;
   - approver must be authorized by `APPROVAL_AUTHORITY.csv`;
   - affected path must cover changed protected artifact;
   - requirement/rule IDs found in changed lines must be covered;
   - validation plan required.

4. **Trusted-control self-protection**
   - after bootstrap, validator/workflow/CODEOWNERS/manifest/change-control/approval registry are protected controls;
   - changing them requires a pre-approved base CR.

5. **Trusted workflow design**
   - `governance-trusted.yml` uses `pull_request_target`;
   - workflow definition and validator are taken from trusted base;
   - PR head is materialized as data;
   - PR version of the validator is not executed by the trusted job.

### Regression evidence

`scripts/test_governance_security.py` covers:

- downgrade attack: **REJECTED**;
- same-PR dummy/pending CR attack: **REJECTED**;
- pre-approved base CR covering path/ID: **ACCEPTED**;
- validator self-change without base CR: **REJECTED**.

Latest `Governance Head Advisory` run on remediation head passed both:
- `validate_governance.py`;
- `test_governance_security.py`.

**H-B03 state: `REMEDIATED / PENDING INDEPENDENT PASS 2`.**

Reason for not self-closing: the trusted workflow does not yet exist on the base branch for PR #1 itself. It becomes independent of PR-controlled workflow content only after governance bootstrap lands on main. PR #1 therefore still requires independent review.

## M-B01 — repository enforcement

**VERIFIED OPEN / B1 FREEZE BLOCKER / PR MERGE CONTROL GAP**

Repository metadata on 2026-10-07 shows:

- `main.protected = false`;
- protection `enabled = false`;
- required status check enforcement `off`;
- repository rulesets = `[]`.

Therefore:
- Head Advisory success is not a required check;
- Trusted workflow is not yet enforceable as required;
- direct-push bypass remains possible.

No artifact may be marked FROZEN while this remains true.

## M-B02 — legal/domain consolidation

**OPEN / B2 EXECUTABLE-POLICY BLOCKER**

Legal provenance has been expanded:

- UU 24/2011 is recorded as amended through the Cipta Kerja chain, including UU 6/2023;
- PP 86/2013 Pasal 3(2)(b) is a direct normative anchor for reported wage matching wage received;
- contribution chain is explicit:
  `PerBPJS 5/2018 → PerBPJS 3/2020 → PerBPJS 2/2024`.

Remaining B2 work includes article-level consolidation, effective-date tables, exceptions, wage basis/caps, and arrears/timing semantics.

This does **not** invalidate B1 high-level safety semantics.

## M-B03 — manifest ↔ artifact metadata drift

**REMEDIATED / CI PASS**

- `A0_CONFLICT_REGISTER.md`: manifest and frontmatter now agree on REVIEWED, A6-derived registry, source A0.
- `CHANGE_REQUEST_TEMPLATE.md`: lifecycle is REVIEWED; template-ness is represented separately as `artifact_kind=TEMPLATE`.
- validator checks REVIEWED/FROZEN markdown frontmatter against canonical manifest for lifecycle/authority fields where duplicated.
- manifest v1 is accepted **only as read-only base migration input**; head must use manifest v2.

## M-B04 — acceptance/self-audit inconsistency

**REMEDIATED**

B1/B2 gates are separated:

- **B1** freezes business/domain safety boundaries.
- **B2** freezes executable consolidated policy.

BAC-009 now refers to the latest independent audit. Since the latest independent audit still contains H-B03, B1 remains HOLD until Pass 2.

## M-B05 — approval/ownership enforcement

**PARTIALLY CLOSED / residual tied to M-B01**

Implemented:
- reviewed RACI;
- machine-readable `APPROVAL_AUTHORITY.csv`;
- approver validation by most-specific path prefix;
- CODEOWNERS expanded across all documentation/control areas.

Known limitation:
- cross-workstream reviewer roles (Lintang/Haidir) are not machine-bound to GitHub identities;
- CODEOWNERS/review requirements are routing only until branch/ruleset enforcement is enabled.

## Additional remediation

### BRD scope link
Corrected to:
`../../00_PROJECT_GOVERNANCE/PROJECT_SCOPE_STATEMENT.md`

### Authority control
Official A0 sources remain distinct from project-derived registries.

## Gate after remediation

```text
PHASE A
PASS_WITH_CONSTRAINTS
        ↓
PHASE B CONTENT
CONDITIONALLY PASS
        ↓
H-B03
REMEDIATED
PENDING INDEPENDENT PASS 2
        ↓
B1 BUSINESS / DOMAIN BOUNDARY FREEZE
HOLD
├── latest independent audit must clear HIGH
└── M-B01 repository enforcement must be active
        ↓
B2 EXECUTABLE POLICY FREEZE
HOLD
└── M-B02 policy consolidation
        ↓
A4 / IMPLEMENTATION
NOT AUTHORIZED
```
