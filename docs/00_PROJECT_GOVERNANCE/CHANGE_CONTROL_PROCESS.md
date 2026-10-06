---
project: JAGA-JKN
status: REVIEWED
version: 0.3.0
owner: Panji
artifact_authority_level: A1
authority: Project Governance
last_updated: 2026-10-07
---

# Change Control Process

## Purpose

Control semantic changes to project truth, scope, requirements, policy, evaluation, contracts, and acceptance evidence.

## Canonical state

`DOCUMENT_MANIFEST.csv` is the control plane for lifecycle state. Frontmatter in REVIEWED/FROZEN Markdown artifacts must agree with manifest metadata; CI validates the overlap.

## Change classes

### Class 0 — editorial
No semantic meaning changes.

### Class 1 — non-frozen semantic
Semantic change to DRAFT/REVIEWED artifacts. Normal review.

### Class 2 — protected semantic
Any semantic change to:
- an artifact that is `FROZEN` in the **base revision**;
- the lifecycle/authority metadata of an artifact that is `FROZEN` in base;
- trusted governance controls after governance bootstrap is established.

Class 2 requires a pre-approved CR.

## Anti-downgrade invariant

A base artifact with `status=FROZEN` remains protected for the entire PR even if the head:
- changes it to REVIEWED/DRAFT;
- marks it SUPERSEDED/RETIRED;
- removes its manifest row;
- deletes the file.

The validator compares **base manifest + head manifest**. Head cannot erase base protection.

## CR sequencing

A CR authorizing a Class 2 change MUST exist and be APPROVED in the **base branch before** the semantic-change PR begins.

A CR added or edited in the same PR as the protected semantic change cannot authorize that change.

Required flow:

```text
CR PR
→ review/approval
→ CR merged to protected base
→ semantic-change PR
→ trusted validator verifies base CR
```

## Machine-readable CR block

Approved CR records contain a JSON governance block:

```text
<!-- GOVERNANCE-CR
{
  "cr_id": "CR-YYYY-NNN",
  "decision": "APPROVE",
  "approver": "github-login",
  "approved_at": "YYYY-MM-DD",
  "affected_paths": ["docs/..."],
  "affected_ids": ["BR-001"],
  "validation_plan": "non-empty text"
}
GOVERNANCE-CR -->
```

The human-readable body remains required for reasoning and impact analysis.

## Approval authority

Authorized approvers are defined in `APPROVAL_AUTHORITY.csv`.

The validator resolves each affected path to the most specific registered path prefix and verifies the CR approver against that registry.

Cross-workstream human review requirements remain explicitly recorded in the registry. Where reviewer identities are not yet machine-bound, this is a known enforcement limitation and cannot be represented as automatically verified.

## CR validity requirements

For a protected change the validator requires, from a CR already present in base:
- decision exactly `APPROVE`;
- non-empty approval date;
- approver authorized for every affected path;
- changed protected artifact included in `affected_paths`;
- requirement/rule IDs visible in the diff included in `affected_ids`;
- non-empty validation plan.

Merely adding `CHANGE_LOG.md` or a dummy/pending CR does not authorize a protected change.

## Trusted-control protection

Once the trusted governance workflow exists in the base branch, changes to:
- trusted workflow;
- CODEOWNERS;
- validator;
- manifest;
- Change Control Process;
- Approval Authority registry

are treated as protected-control changes and require a pre-approved base CR.

## Freeze prerequisites

Before first FROZEN artifact:
1. artifact is REVIEWED;
2. contradiction audit has no unresolved HIGH affecting it;
3. provenance complete;
4. owner/authority non-TBD;
5. downstream impact known;
6. manifest/frontmatter consistent;
7. branch/ruleset enforcement requires PR + trusted Governance check;
8. force-push/deletion bypass is constrained appropriately.

## Repository enforcement reality

CI without branch protection detects violations but cannot prevent direct push. Therefore successful CI is not equivalent to repository enforcement.

As of the latest audit, `main` is unprotected and required checks are off. First freeze remains blocked until that external repository setting is changed and verified.
