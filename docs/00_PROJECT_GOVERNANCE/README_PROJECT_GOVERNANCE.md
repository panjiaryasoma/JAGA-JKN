# Project Governance

## Current state

Change control is `REVIEWED`, not FROZEN.

Phase B freeze remains blocked until repository-level prevention is verified, specifically required PR/status-check enforcement on `main`.

## Controls in repository

- `DOCUMENT_MANIFEST.csv` is the project artifact control plane.
- `CHANGE_CONTROL_PROCESS.md` defines semantic change classes.
- `CHANGE_REQUEST_TEMPLATE.md` defines CR semantics.
- `change_requests/` stores approved/rejected CR records when needed.
- `.github/CODEOWNERS` routes review ownership.
- `.github/workflows/governance.yml` validates manifest and frozen-change invariants.
- `scripts/validate_governance.py` is the executable validator.

## Important limitation

A workflow that fails after a direct push is not branch protection. Before first freeze, GitHub must be configured so protected changes require pull request + required governance status check.
