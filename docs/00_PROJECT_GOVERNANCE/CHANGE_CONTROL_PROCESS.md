---
project: JAGA-JKN
status: REVIEWED
version: 0.2.0
owner: Panji
authority_level: A1
authority: Project Governance
last_updated: 2026-10-07
---

# Change Control Process

## Purpose

Control changes to artifacts whose semantics affect project truth, scope, requirements, policy, evaluation, contracts, or acceptance.

## Principle

A file path does not grant authority. The manifest status does.

A `FROZEN` artifact may not be changed through an ordinary feature edit. It requires an approved Change Request (CR) and explicit traceability of impact.

## Change classes

### Class 0 — editorial
Typos, formatting, links, or wording that provably does not change semantics.

### Class 1 — non-frozen semantic
Semantic change to a DRAFT/REVIEWED artifact. Normal review applies.

### Class 2 — frozen semantic
Any semantic modification to a FROZEN artifact, including:
- scope or requirement meaning;
- requirement IDs;
- domain/policy semantics;
- thresholds or effective dates;
- evaluation oracle or acceptance thresholds;
- API/data/model/inference contract;
- traceability relation that changes authority or acceptance.

Class 2 requires CR.

## CR minimum contents

- CR ID;
- initiator;
- date;
- problem/reason;
- source/evidence;
- exact artifacts and IDs affected;
- impact on scope/data/ML/backend/frontend/test/proposal;
- backward-compatibility impact;
- risk;
- validation plan;
- decision: APPROVE / REJECT / DEFER;
- approver and date.

## Approval semantics

A CR is not approved by existence. It is approved only when its decision field is `APPROVE` and the authorized approver is recorded.

Cross-workstream changes require the affected workstream owner to review the impact.

## Freeze prerequisites

Before an artifact is first marked `FROZEN`:
1. artifact is REVIEWED;
2. contradiction audit has no unresolved HIGH finding affecting it;
3. source provenance is complete;
4. owner and authority are non-TBD;
5. downstream impact is known;
6. repository enforcement is verified active;
7. manifest and file metadata agree.

## Repository enforcement

CI validates manifest invariants and detects changes to FROZEN artifacts. CODEOWNERS provides ownership routing.

Required branch protection/status checks are a GitHub repository setting and must be verified before first freeze. CI failure after a direct push is detection, not prevention; therefore CI alone does not satisfy the freeze gate.

## No silent supersession

When a new frozen artifact replaces another:
- new artifact records `supersedes`;
- old artifact becomes `SUPERSEDED`;
- manifest is updated in the same change;
- traceability is migrated or explicitly terminated.
