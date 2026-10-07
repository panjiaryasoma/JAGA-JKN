# Project Governance

## Current state

- Phase B content: `CONDITIONALLY PASS`
- H-B03: `CLOSED`
- H-B06: `CLOSED`
- M-B06: `CLOSED`
- M-B07: `REMEDIATED / PENDING INDEPENDENT PASS 5`
- M-B08: `REMEDIATED / PENDING INDEPENDENT PASS 5`
- PR #1: `HOLD pending Independent Pass 5`; if cleared, it may become `BOOTSTRAP MERGE READY` subject to explicit ACC
- B1 freeze: `HOLD`
- B2 executable-policy freeze: `HOLD`
- implementation: `NOT AUTHORIZED`

## Controls

- `DOCUMENT_MANIFEST.csv`: canonical lifecycle/control-plane state.
- `CHANGE_CONTROL_PROCESS.md`: Class 0/1/2 semantics and anti-downgrade rule.
- `APPROVAL_AUTHORITY.csv`: machine-readable approver authorization.
- `RACI_MATRIX.csv`: reviewed workstream accountability.
- `CHANGE_REQUEST_TEMPLATE.md`: human + machine-readable CR format.
- `change_requests/`: CR records.
- `scripts/validate_governance.py`: base/head validator.
- `scripts/test_governance_security.py`: bypass regression suite.
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

PR #1 is the PR introducing the trusted mechanism. Because the trusted workflow is not yet present on its base, PR #1 cannot use that mechanism as independent proof of itself. It remains subject to independent Pass 2 before merge.
