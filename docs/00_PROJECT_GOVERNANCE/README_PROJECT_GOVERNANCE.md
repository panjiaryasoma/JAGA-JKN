# Project Governance

## Current state

- Phase B content: `CONDITIONALLY PASS`
- H-B03: `CLOSED`
- H-B06: `CLOSED`
- M-B06: `CLOSED`
- M-B07: `CLOSED`
- M-B08: `CLOSED`
- M-B09: `REMEDIATED / PENDING INDEPENDENT PASS 6`
- M-B10: `REMEDIATED / PENDING INDEPENDENT PASS 6`
- PR #1: `HOLD pending Independent Pass 6`; if cleared, it may become `BOOTSTRAP MERGE READY` subject to explicit ACC
- B1 freeze: `HOLD on M-B01`
- B2 executable-policy freeze: `HOLD on M-B01 + M-B02`
- implementation: `NOT AUTHORIZED`

## Controls

- `DOCUMENT_MANIFEST.csv`: canonical lifecycle/control-plane state.
- `CHANGE_CONTROL_PROCESS.md`: Class 0/1/2 semantics and anti-downgrade rule.
- `APPROVAL_AUTHORITY.csv`: machine-readable approver authorization, including exact trusted-control coverage.
- `RACI_MATRIX.csv`: reviewed workstream accountability.
- `CHANGE_REQUEST_TEMPLATE.md`: human + machine-readable CR v3 format.
- `change_requests/`: immutable approved authorization ledger.
- `scripts/validate_governance.py`: base/head trusted-control validator.
- `scripts/test_governance_security.py`: adversarial regression suite.
- `governance-trusted.yml`: base-trusted PR validation after bootstrap.
- `CODEOWNERS`: review routing.

## Repository enforcement

Verified repository metadata currently says:
- main unprotected;
- required status checks off;
- no repository rulesets.

Therefore successful CI is evidence that checks ran, not proof they are mandatory.

Before first freeze, configure repository protection so changes to main require PR + successful **Governance Trusted** check in **strict / branch-up-to-date mode**, block force-push and branch deletion, and constrain bypass.

## Bootstrap caveat

PR #1 introduces the trusted mechanism, so it cannot use `Governance Trusted` from its own base as independent proof. It remains subject to **Independent Pass 6** after M-B09/M-B10 remediation. If that pass clears all bootstrap correctness blockers, PR #1 may be classified `BOOTSTRAP MERGE READY`, still requiring explicit ACC before merge.
