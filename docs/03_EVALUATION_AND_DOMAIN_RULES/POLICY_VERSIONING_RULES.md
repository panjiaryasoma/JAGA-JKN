---
project: JAGA-JKN
status: REVIEWED
version: 0.3.0
owner: Panji
artifact_authority_level: A3
authority: Domain Rules
last_updated: 2026-10-07
---

# Policy Versioning Rules

## Source chain reviewed

### BPJS statutory basis
- UU 24/2011 — BPJS;
- UU 24/2011 has been amended through the Cipta Kerja chain; the currently relevant latest amendment identified in this review is **UU 6/2023**.
- Before using a specific UU 24/2011 article as executable policy, confirm whether that article's wording was affected by the amendment chain.

### Jaminan Kesehatan presidential regulation
- Perpres 82/2018;
- Perpres 75/2019 — first amendment;
- Perpres 64/2020 — second amendment;
- Perpres 59/2024 — third amendment.

As of the 2026-10-07 review, JDIH BPK identifies Perpres 59/2024 as the latest amendment found in this chain.

### Employer registration / data correctness
- PP 86/2013.
- Pasal 3(2)(b) directly states that reported wage data must correspond to wages received by workers. This is a direct normative anchor for wage-reporting semantics.

### Contribution collection / payment / recording
- Peraturan BPJS Kesehatan 5/2018 — base regulation;
- Peraturan BPJS Kesehatan 3/2020 — first amendment;
- Peraturan BPJS Kesehatan 2/2024 — second amendment, effective 2024-10-03.

The 2/2024 official metadata explicitly identifies this amendment chain. Arrears/timing logic must be derived from the consolidated chain, not from the latest amendment in isolation.

## Rules

1. Never overwrite a historical policy value in place.
2. Add a new policy version with explicit effective period.
3. Historical evaluation selects the rule effective for the evaluated period.
4. If authoritative sources conflict, mark `CONFLICT` and stop authoritative calculation.
5. Project summaries are derived registries, not A0 source truth.
6. A rule becomes executable only after domain/source verification and freeze.
7. “Latest amendment” is not automatically a consolidated rule text.
8. Every executable rule must record which base provision and amendments produced the final semantics.
