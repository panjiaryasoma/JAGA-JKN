---
project: JAGA-JKN
competition: BPJS Kesehatan Healthkathon 2026
status: REVIEWED
version: 0.2.0
owner: Panji
authority: Discovery Control
authority_level: A2
last_updated: 2026-10-07
---

# Assumption and Hypothesis Register

| ID | Type | Statement | Evidence state | Impact if false | Treatment |
|---|---|---|---|---|---|
| A-001 | ASSUMPTION | Prototype will use synthetic/dummy data | VERIFIED allowed; chosen strategy | LOW | Keep |
| A-002 | ASSUMPTION | BPJS can define or obtain a trustworthy reference state for at least some employer-risk modes | UNKNOWN | CRITICAL | Production blocker; prototype simulates reference world |
| A-003 | ASSUMPTION | Employer review has finite capacity and benefits from prioritization | UNKNOWN | HIGH | Do not optimize capacity until evidence exists |
| A-004 | ASSUMPTION | Temporal persistence is useful for separating transient discrepancies from sustained risk | UNKNOWN | HIGH | Test in synthetic scenarios; require domain validation |
| A-005 | ASSUMPTION | BPJS officer is the final operational decision maker | SUPPORTED by competition human-in-the-loop requirement, exact role unknown | MEDIUM | Keep generic role until validated |
| A-006 | ASSUMPTION | PDUK, under-reporting wage, and contribution irregularity are suitable MVP slices | Organizer validates modes; prioritization UNKNOWN | HIGH | Re-evaluate in BRD/domain gate |
| A-007 | ASSUMPTION | Cross-source reconciliation is legally/technically possible in production | UNKNOWN | CRITICAL | No production claim; design adapter boundary only |
| H-001 | HYPOTHESIS | Episode-based review is more useful than isolated monthly alerts | UNKNOWN | MEDIUM | Evaluate against scenario suite |
| H-002 | HYPOTHESIS | Separating evidence quality from risk strength reduces unsafe escalation | LOGICALLY SUPPORTED | MEDIUM | Define acceptance tests before implementation |
| H-003 | HYPOTHESIS | Tracking correction and recurrence improves compliance lifecycle management | UNKNOWN | MEDIUM | Preserve as product hypothesis |
| U-001 | UNKNOWN | Exact internal BPJS workflow for employer compliance | UNKNOWN | HIGH | Seek organizer/domain validation |
| U-002 | UNKNOWN | Exact production data sources and schemas | UNKNOWN | CRITICAL | Block production assumptions |
| U-003 | UNKNOWN | Base rate / financial impact of each employer-risk mode | UNKNOWN | HIGH | Do not invent proposal numbers |
| U-004 | UNKNOWN | Current authoritative consolidated thresholds/exceptions for all policy rules | PARTIAL | CRITICAL | Legal/domain review before rule freeze |

## Rule

Unknowns may be converted only by new evidence. They must never disappear merely because a downstream design needs a value.
