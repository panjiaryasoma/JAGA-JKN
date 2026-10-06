---
project: JAGA-JKN
status: REVIEWED
version: 0.4.0
owner: Panji
artifact_authority_level: A3
authority: Domain Rules
last_updated: 2026-10-07
---

# Policy Versioning Rules

## Source chain reviewed

### BPJS statutory basis
- UU 24/2011 — BPJS;
- UU 6/2023 — Cipta Kerja amendment chain relevant to UU 24/2011.

Exact source:
- https://peraturan.bpk.go.id/Details/246523/uu-no-6-tahun-2023

Article-level impact still must be checked before an executable rule relies on a specific UU 24/2011 provision.

### Jaminan Kesehatan presidential regulation
- Perpres 82/2018;
- Perpres 75/2019;
- Perpres 64/2020;
- Perpres 59/2024.

### Employer registration / wage correctness
- PP 86/2013;
- Pasal 3(2)(b) is a direct normative anchor that wage data reported by an employer must correspond to wage received by the worker.

### Contribution collection / payment / recording
- PerBPJS Kesehatan 5/2018 — base;
- PerBPJS Kesehatan 3/2020 — first amendment;
- PerBPJS Kesehatan 2/2024 — second amendment.

Exact base source:
- https://peraturan.go.id/id/peraturan-bpjs-kesehatan-no-5-tahun-2018

First amendment:
- https://peraturan.go.id/id/peraturan-bpjs-kesehatan-no-3-tahun-2020

Second amendment:
- https://peraturan.bpk.go.id/Details/311192/peraturan-bpjs-kesehatan-no-2-tahun-2024

The latest amendment is not a substitute for a consolidated rule text.

## Rules

1. Never overwrite historical policy values in place.
2. Add a new policy version with explicit effective period.
3. Historical evaluation selects the rule effective for the evaluated period.
4. Authoritative conflicts fail closed.
5. Project summaries remain derived registries.
6. A rule becomes executable only after domain/source verification and freeze.
7. Every executable rule records the base provision plus amendments used to derive final semantics.
