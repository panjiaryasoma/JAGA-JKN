---
project: JAGA-JKN
status: REVIEWED
version: 0.6.0
owner: Panji
artifact_authority_level: A6
authority: Verification & Governance Evidence
last_updated: 2026-10-07
---

# Phase B Contradiction Audit

## Latest independent result

Independent Pass 4 against head `fdc32aaeab6d28d77e1b25e66ac35a8ae356ff9e` concluded:

- H-B03: **CLOSED**
- H-B06: **CLOSED**
- M-B06: **CLOSED**
- M-B01: **OPEN**
- M-B02: **OPEN — B2 ONLY**
- M-B03: **CLOSED**
- M-B04: **CLOSED**
- M-B05: **PARTIAL**
- M-B07: **OPEN — approver identity binding**
- M-B08: **OPEN — CR evidence immutability / ingest validation**

No new HIGH was found.

## M-B07 — authenticated approval identity

### Independent finding

The previous validator proved that the CR *claimed* an authorized login, but did not prove that GitHub authenticated that user as the approval actor.

### Remediation

CR schema v3 adds `approval_pr_number`.

When a protected semantic PR consumes an approved CR, Governance Trusted now queries the GitHub Pull Request API using read-only `pull-requests: read` permission and requires:

```text
approval PR merged == true
approval PR merge_commit_sha == semantic PR base
approval PR merged_by.login == CR.approver
CR.approver authorized for all targets
```

Therefore `approver=panjiaryasoma` is no longer accepted merely because those bytes exist in a Markdown file.

This deliberately binds approval to the authenticated account that merges the isolated CR approval PR. It avoids the self-review deadlock created by a sole CODEOWNER being unable to approve their own PR.

**M-B07 status: `REMEDIATED / PENDING INDEPENDENT PASS 5`.**

## M-B08 — append-only CR evidence + ingest validation

### Independent finding

Historical CR files could be edited/deleted after use, and malformed CRs could enter base before being parsed.

### Remediation

The validator now treats `change_requests/CR-*.md` as an append-only evidence ledger.

New CR ingest requires:
- exactly one new CR file;
- no unrelated changed path;
- schema v3 parses immediately;
- filename equals `cr_id`;
- `decision=APPROVE`;
- valid approval date;
- approval PR number matches current CR-only PR;
- authorized approver;
- authorized base equals current PR base;
- source hashes match the current base.

Existing CR:
- modify → REJECT;
- delete → REJECT;
- rename/copy rewrite → REJECT.

Corrections require a new evidence record.

**M-B08 status: `REMEDIATED / PENDING INDEPENDENT PASS 5`.**

## Regression additions

Added adversarial coverage for:
- valid isolated new CR ingest → ACCEPT;
- malformed new CR → REJECT;
- unauthorized approver → REJECT;
- existing approved CR edited → REJECT;
- existing approved CR deleted → REJECT;
- self-asserted approver != authenticated GitHub merge actor → REJECT;
- authenticated authorized merge actor → ACCEPT;
- approval PR merge SHA mismatch → REJECT;
- CR approval PR-number mismatch → REJECT.

Existing downgrade, replay, target/base mismatch, DELETE, ID-context, snapshot-isolation, and trusted-control regressions remain.

## M-B01 — repository enforcement

**OPEN / B1 BLOCKER, not bootstrap-merge blocker once M-B07/M-B08 pass independent review.**

Required final configuration after governance bootstrap reaches main:

```text
PR required
Governance Trusted required
strict / branch up-to-date required
force push blocked
branch deletion blocked
bypass constrained
```

Then run an adversarial canary PR against the trusted-base controls. Only verified enforcement closes M-B01 and permits B1 freeze.

## M-B02

**OPEN — B2 ONLY.**

Executable policy consolidation remains separate from B1.

## Bootstrap gate

```text
PHASE B CONTENT
CONDITIONALLY PASS
        ↓
H-B03 / H-B06 / M-B06
CLOSED
        ↓
M-B07 + M-B08
REMEDIATED
PENDING INDEPENDENT PASS 5
        ↓
PR #1
HOLD pending Pass 5
        ↓
if Pass 5 clears correctness blockers:
BOOTSTRAP MERGE READY
SUBJECT TO EXPLICIT ACC
        ↓
merge governance to main
        ↓
configure strict repository enforcement
        ↓
adversarial canary PR
        ↓
M-B01 CLOSED
        ↓
B1 FREEZE READY
```

A4 / PRD / SRS and implementation remain NOT AUTHORIZED.
