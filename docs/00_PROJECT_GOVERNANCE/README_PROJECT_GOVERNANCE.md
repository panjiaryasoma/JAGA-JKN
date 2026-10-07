# Project Governance

## Current state

- Phase B content: `CONDITIONALLY PASS`
- H-B03: `CLOSED`
- H-B06: `CLOSED`
- M-B06: `CLOSED`
- M-B07: `CLOSED`
- M-B08: `CLOSED`
- M-B09: `CLOSED`
- M-B10: `CLOSED`
- PR #1: `BOOTSTRAP MERGE READY` — **subject to separate explicit ACC**
- M-B01: `OPEN` — post-bootstrap repository enforcement
- M-B02: `OPEN — B2 ONLY`
- M-B05: `PARTIAL`
- B1 freeze: `HOLD on M-B01`
- B2 executable-policy freeze: `HOLD on M-B01 + M-B02`
- A4 / PRD / SRS: `NOT AUTHORIZED`
- implementation: `NOT AUTHORIZED`

Independent Pass 6 found **0 new HIGH** and **0 new MEDIUM bootstrap blockers**.

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

This is tracked by **M-B01** and blocks B1 freeze, but no longer blocks the bootstrap merge itself.

After bootstrap reaches `main`, repository protection must require:

- pull request;
- successful **Governance Trusted** check;
- strict / branch-must-be-up-to-date mode;
- force-push blocked;
- branch deletion blocked;
- constrained bypass.

An adversarial canary PR must then prove the trusted-base controls are actually enforced before M-B01 can close.

## Bootstrap verdict

PR #1 introduces the trusted mechanism and has now completed Independent Pass 6 with no HIGH or MEDIUM bootstrap blocker.

```text
PR #1
BOOTSTRAP MERGE READY
SUBJECT TO SEPARATE EXPLICIT ACC
```

This classification does not authorize merge, freeze, A4 drafting, or implementation.
