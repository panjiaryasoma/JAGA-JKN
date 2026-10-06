---
project: JAGA-JKN
status: REVIEWED
version: 0.2.0
owner: Panji
authority_level: A3
authority: Business Requirements
---

# Business Requirements

| ID | Requirement | Provenance | Epistemic state |
|---|---|---|---|
| BR-001 | The solution must support identification of potential discrepancies relevant to the selected employer-risk MVP slices. | SRC-COMP-001/002 | VERIFIED BASIS |
| BR-002 | The solution must preserve evidence/source provenance for any surfaced discrepancy. | Competition technical/governance requirements + project decision | SUPPORTED |
| BR-003 | A surfaced discrepancy must not be represented as a confirmed violation solely from automated rule/ML output. | Human-in-the-loop requirement | VERIFIED BASIS |
| BR-004 | Final review/operational decision must remain with a human role. Exact BPJS role remains UNKNOWN. | SRC-COMP-002 | VERIFIED BASIS / ROLE UNKNOWN |
| BR-005 | Prototype data must be synthetic/dummy/anonymized unless official authorization permits real JKN data. | SRC-COMP-001/002 | VERIFIED |
| BR-006 | When required reference data, policy authority, or evidence quality is insufficient, the decision-support flow must be able to return UNKNOWN/ABSTAIN. | Project governance | DECIDED |
| BR-007 | Policy-dependent expectations must identify the rule source/version/effective period used. | JKN regulation amendment history | VERIFIED BASIS |
| BR-008 | Risk strength and evidence quality must be representable separately. | Project safety hypothesis | ASSUMED / REVIEWED |
| BR-009 | Temporal context must be preserved so transient discrepancies are not automatically treated as persistent non-compliance. | HYP-RC-002 | ASSUMED / REVIEWED |
| BR-010 | The prototype should represent review outcome, resolution, and recurrence without claiming this mirrors BPJS's current internal workflow. | H-003 | ASSUMED / REVIEWED |
| BR-011 | The project must not claim operational prevalence, financial loss, or internal BPJS process performance without evidence. | Phase A non-claim boundary | VERIFIED GOVERNANCE |
| BR-012 | Impact claims used in proposal/demo must be measurable and traceable to evaluation evidence. | SRC-COMP-002 | VERIFIED BASIS |
