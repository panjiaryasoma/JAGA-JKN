---
project: JAGA-JKN
competition: BPJS Kesehatan Healthkathon 2026
status: REVIEWED
version: 0.2.0
owner: Panji
authority_level: A3
authority: Business Requirements
last_updated: 2026-10-07
---

# Business Requirements Document (BRD)

## 1. Context

JAGA-JKN is a Healthkathon prototype for the **Efisiensi Risiko pada Pemberi Kerja** category. It proposes decision support for three organizer-recognized risk slices: partial worker registration, under-reporting wage, and contribution irregularity.

This BRD does not claim visibility into BPJS internal workflows or production data access.

## 2. Business problem

Potential employer-compliance discrepancies must be identified and reviewed in a way that is useful for human decision-making without treating automated risk signals as authoritative findings.

## 3. Stakeholders

### Verified
- BPJS Kesehatan as competition organizer and JKN operator.
- Employers and workers as domain stakeholders affected by employer-side obligations.

### Candidate / not yet verified
- BPJS officer/team responsible for employer compliance, risk review, examination, or follow-up.

The candidate role remains intentionally generic.

## 4. Business objectives

See `BUSINESS_OBJECTIVES.md` (BO-001..BO-006).

## 5. Business requirements

See `BUSINESS_REQUIREMENTS.md` (BR-001..BR-012).

## 6. Business rules

See `BUSINESS_RULES.md`.

## 7. Scope

See `../../00_PROJECT_GOVERNANCE/PROJECT_SCOPE_STATEMENT.md`.

## 8. Data constraints

- synthetic/dummy/anonymized prototype data unless real data is officially authorized;
- reference/true world in synthetic data is simulator ground truth, not evidence that equivalent production data is available;
- production cross-source reconciliation remains a dependency, not an assumption promoted to fact.

## 9. Decision boundary

JAGA-JKN may:
- detect or calculate discrepancies;
- prioritize review candidates;
- explain signals/evidence;
- recommend a review action;
- represent uncertainty/abstention.

JAGA-JKN may not:
- declare fraud;
- issue legal findings;
- establish sanction/debt;
- perform enforcement automatically.

## 10. Policy boundary

Policy-as-code is allowed only when:
- source is identified;
- source authority is known;
- policy version/effective period is known;
- missing/ambiguous policy fails closed.

## 11. Candidate business outcome measures

These are measurement dimensions, not committed numerical targets:
- risk capture at a declared review budget;
- false escalation rate;
- evidence coverage;
- abstention correctness;
- episode onset delay;
- time-to-resolution / recurrence only when a valid lifecycle dataset exists.

## 12. Open business unknowns

- exact operational user and authority;
- reviewer capacity;
- available production reference data;
- employer-risk prevalence/base rates;
- current internal tools/process;
- consolidated production thresholds/exceptions.

## 13. Freeze status

**HOLD**.

This BRD is REVIEWED for contradiction audit. It is not authoritative enough for PRD/SRS implementation until Phase B freeze gate passes.
