---
project: JAGA-JKN
status: REVIEWED
version: 0.2.0
owner: Panji
authority_level: A3
authority: Domain Rules
---

# Expected State Rules

## Principle

“Expected state” is not a guess and not an ML prediction. It is a state derived from an authoritative rule plus sufficiently trustworthy inputs.

## ES-REG-001 — Registration coverage

If a trustworthy reference worker set exists for an employer/period, compare that set with the observed JKN-registered worker set.

Output may be:
- `CONSISTENT`;
- `POTENTIAL_REGISTRATION_GAP`;
- `ABSTAIN`.

A gap is a review signal, not a legal finding.

If trustworthy reference workforce data is unavailable: `ABSTAIN`.

## ES-WAGE-001 — Wage reporting

If a lawful/trustworthy reference wage exists and the applicable wage/contribution policy version is known, compare reference wage basis with reported wage basis.

Output may be:
- `CONSISTENT`;
- `POTENTIAL_WAGE_DIVERGENCE`;
- `ABSTAIN`.

No production tolerance/threshold is defined in Phase B.

## ES-CONTRIB-001 — Contribution expectation

When applicable policy and inputs are known, derive expected contribution from the applicable policy version and compare with observed contribution/payment records.

Output may be:
- `CONSISTENT`;
- `POTENTIAL_CONTRIBUTION_IRREGULARITY`;
- `ABSTAIN`.

Perpres 64/2020 is a verified historical/current legal anchor for PPU 5% (4% employer + 1% participant), but the implementation engine must use a consolidated policy version applicable to the evaluated period before freeze.

## Temporal semantics

Persistence windows, correction grace periods, and escalation thresholds are **TBD DOMAIN VALIDATION**.

No developer may convert a one-period discrepancy into “persistent non-compliance” without a frozen rule.

## Missing/conflicting evidence

Missing source, conflicting source, unknown effective policy, or inadequate evidence quality => `ABSTAIN`, not a default numerical substitute.
