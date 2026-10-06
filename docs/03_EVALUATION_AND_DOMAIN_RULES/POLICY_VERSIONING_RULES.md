---
project: JAGA-JKN
status: REVIEWED
version: 0.2.0
owner: Panji
authority_level: A3
authority: Domain Rules
---

# Policy Versioning Rules

## Source chain reviewed

- UU 24/2011 — BPJS;
- Perpres 82/2018 — Jaminan Kesehatan;
- Perpres 75/2019 — amendment;
- Perpres 64/2020 — second amendment;
- Perpres 59/2024 — third amendment;
- PP 86/2013 — administrative sanctions;
- Peraturan BPJS Kesehatan 2/2024 — contribution collection/payment/recording amendment.

As of the 2026-10-07 source review, JDIH BPK lists Perpres 59/2024 as the latest amendment to Perpres 82/2018 found in this review.

## Rules

1. Never overwrite a historical policy value in place.
2. Add a new policy version with explicit effective period.
3. Historical evaluation selects the rule effective for the evaluated period.
4. If multiple authoritative sources conflict, mark `CONFLICT` and stop authoritative calculation.
5. Project summaries are derived registries, not A0 source truth.
6. A rule becomes executable only after domain/source verification and freeze.
