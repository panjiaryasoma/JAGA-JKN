---
project: JAGA-JKN
status: REVIEWED
version: 0.3.0
owner: Panji
artifact_authority_level: A3
authority: Business Requirements
last_updated: 2026-10-07
---

# Business Acceptance Criteria

## B1 — Business / Domain Boundary Freeze

B1 covers Charter, Scope, BRD, business safety rules, and non-executable expected-state semantics.

B1 is freeze-ready only if:

- BAC-001: every BR has provenance and epistemic state;
- BAC-002: no UNKNOWN is expressed as a BPJS operational fact;
- BAC-003: selected MVP modes are organizer-recognized employer risks;
- BAC-004: disputed A0 taxonomy item is excluded from current MVP;
- BAC-005: human-decision boundary is explicit;
- BAC-006: real-data restriction is explicit;
- BAC-007: policy-dependent semantics require source/version/effective period;
- BAC-008: no production threshold is invented;
- BAC-009: latest independent contradiction audit has zero unresolved HIGH affecting B1;
- BAC-010: repository enforcement requires PR + **Governance Trusted** as a required status check, **strict / branch-must-be-up-to-date before merge**, force-push blocked, branch deletion blocked, and bypass constrained.

**Current B1 result: HOLD.**

Independent Pass 4 closed H-B03, H-B06, and M-B06. M-B07/M-B08 remediation requires Independent Pass 5. BAC-010 remains false because `main` is unprotected and strict required-check enforcement is not active.

## B2 — Executable Policy Freeze

B2 additionally requires consolidated executable policy, including:
- article-level amendment impact;
- effective-date table;
- lawful exceptions;
- wage basis/caps where relevant;
- payment timing/grace/arrears semantics;
- consolidated PerBPJS 5/2018 → 3/2020 → 2/2024 chain.

**Current B2 result: HOLD.**

Incomplete B2 policy does not invalidate reviewed B1 safety semantics such as:
`signal != violation`, `missing authority => ABSTAIN`, and human final authority.

## A4 entry

PRD/SRS drafting remains NOT AUTHORIZED in the current project state. A later governance decision may permit A4 drafting after B1 freeze while keeping executable policy-dependent implementation blocked on B2.
