---
project: JAGA-JKN
competition: BPJS Kesehatan Healthkathon 2026
status: REVIEWED
version: 0.2.0
owner: Panji
authority_level: A1
authority: Project Governance
last_updated: 2026-10-07
---

# Project Charter

## 1. Project identity

**JAGA-JKN — Sistem Intelijen Kepatuhan Pemberi Kerja JKN**

Project type: Healthkathon prototype / decision-support concept.

This charter does **not** imply sponsorship, endorsement, or internal adoption by BPJS Kesehatan beyond the public competition context.

## 2. Business need

Healthkathon 2026 asks participants to propose digital solutions that identify, detect, and mitigate risks in JKN. JAGA-JKN selects the **Efisiensi Risiko pada Pemberi Kerja** category.

Official competition material consistently includes:
- partial worker registration (PDUK);
- under-reporting wage;
- contribution remittance irregularity.

These form the candidate MVP risk slices.

## 3. Purpose

Create an evidence-aware prototype that helps a candidate BPJS operational reviewer inspect potential employer-compliance discrepancies without converting an automated signal into an authoritative finding of violation.

## 4. Objectives

- O-01: reconstruct a policy/reference expectation when adequate authority and data exist;
- O-02: compare expected/reference and observed/reported states;
- O-03: surface potential discrepancies with evidence lineage;
- O-04: preserve temporal context so isolated signals are not automatically treated as persistent episodes;
- O-05: support review prioritization while keeping evidence quality visible;
- O-06: support explicit abstention when required evidence is missing or conflicting;
- O-07: preserve human decision authority;
- O-08: demonstrate the approach using synthetic, seeded, versioned, validated data;
- O-09: produce auditable evidence for Healthkathon proposal and demo claims.

## 5. Project constraints

- real JKN participant data is not used without official authorization;
- internal BPJS workflow is UNKNOWN;
- production data availability is UNKNOWN;
- prevalence and financial magnitude of employer-risk modes are UNKNOWN;
- production policy thresholds/exceptions must not be guessed;
- product implementation is not authorized until downstream preproduction gates pass.

## 6. Success criteria for the prototype

Success means the project can demonstrate, with traceable evidence:
1. selected risk scenarios are generated reproducibly;
2. expected-vs-observed discrepancy logic is rule/source aware;
3. unsupported cases abstain rather than fabricate certainty;
4. decisions remain human-controlled;
5. claims in the proposal map to actual implementation/test evidence.

Numerical model thresholds are intentionally not charter-level commitments.

## 7. Governance

Authority precedence: `A0 > A1 > A2 > A3 > A4 > A5 > A6`.

This charter is REVIEWED, not FROZEN. It may not be frozen until the Phase B contradiction audit passes and repository enforcement required by Change Control is verified.
