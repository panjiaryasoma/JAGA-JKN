# JAGA-JKN Documentation Hub

## Current gate
- Phase A: `PASS_WITH_CONSTRAINTS`
- Phase B: `DRAFT + REVIEW AUTHORIZED`
- Phase B freeze: `HOLD`
- Product implementation: `NOT AUTHORIZED`

## Authority semantics

**Authority precedence is: `A0 > A1 > A2 > A3 > A4 > A5 > A6`. Lower numeric index means higher authority.**

A0 is reserved for **external official sources** such as applicable law/regulation and official Healthkathon/BPJS channels. A repository artifact MUST NOT become A0 merely because it transcribes an A0 source.

Project files therefore distinguish:

- `artifact_authority_level`: authority of the repository artifact itself;
- `source_authority`: authority of the source material it derives from;
- `artifact_role`: e.g. `A0_DERIVED_REGISTRY`.

Example: `HEALTHKATHON_REQUIREMENTS.md` is a project-maintained derived registry. Its source authority is A0, but the file itself is not official source truth.

## Conflict rule

1. A0 source overrides project interpretation.
2. A1 overrides A2..A6 when it does not conflict with A0.
3. A DRAFT artifact never overrides a REVIEWED/FROZEN artifact of equal or higher precedence.
4. A downstream contract that conflicts with an upstream frozen requirement is invalid until an approved Change Request changes the upstream authority.
5. Conflicting A0 sources are recorded in `10_COMPETITION_AND_SUBMISSION/A0_CONFLICT_REGISTER.md`; they are not silently reconciled.
6. UNKNOWN stays UNKNOWN. A downstream design need does not create evidence.

## Lifecycle

`DRAFT → REVIEWED → FROZEN → IMPLEMENTED → VERIFIED → ACCEPTED`

Additional terminal states: `SUPERSEDED`, `RETIRED`.

## Freeze gate

No first project artifact may become FROZEN until:
- contradiction audit passes;
- no unresolved HIGH finding affects it;
- provenance and ownership are complete;
- change-control process is reviewed and repository enforcement is active enough to prevent accidental bypass;
- any A0 conflicts relevant to the artifact are resolved or explicitly non-blocking.

## Repository enforcement state

This branch introduces:
- CODEOWNERS;
- governance CI validation;
- change-control semantics;
- frozen-artifact change detection.

**Branch protection / required status checks are still an external repository setting. Until that setting is verified active, Phase B freeze remains HOLD.**
