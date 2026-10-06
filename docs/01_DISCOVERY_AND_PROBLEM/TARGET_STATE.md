---
project: JAGA-JKN
competition: BPJS Kesehatan Healthkathon 2026
status: REVIEWED
version: 0.2.0
owner: Panji
authority: Discovery Target Hypothesis
authority_level: A2
last_updated: 2026-10-07
---

# Target State

## Target capability

A decision-support workflow that can:

1. construct a policy/reference expectation for an employer-period;
2. compare that expectation with an observed/reported state;
3. preserve the discrepancy as evidence rather than immediately declaring a violation;
4. link related discrepancies across time into a reviewable episode;
5. separate risk strength from evidence quality;
6. abstain when evidence is insufficient or contradictory;
7. suggest a proportional next action;
8. preserve human review/decision authority;
9. record resolution and recurrence.

## State lifecycle hypothesis

`NORMAL → EARLY_WARNING → RISK_EPISODE → INTERVENTION → RESOLUTION → MONITORING → RECURRENCE`

This lifecycle is a **product hypothesis** to be tested against domain requirements in Phase B. It is not claimed to be BPJS's current official workflow.

## Success boundary

The target is **not**:
- an automated fraud adjudicator;
- an automated sanction engine;
- an estimator presented as official financial loss;
- a replacement for BPJS officer judgment.

## Production dependency

The target cannot be promoted from prototype to production without:
- verified authoritative policy rules;
- lawful/authorized reference data;
- internal workflow validation;
- security/privacy approval;
- real-world performance validation.
