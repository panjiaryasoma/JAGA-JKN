---
project: JAGA-JKN
competition: BPJS Kesehatan Healthkathon 2026
status: REVIEWED
version: 0.2.0
owner: Panji
authority: Discovery Evidence
authority_level: A2
last_updated: 2026-10-07
---

# Discovery Real-World Evidence

## Evidence standard

- **VERIFIED**: directly supported by an official competition or legal/regulatory source.
- **SUPPORTED**: supported by an official source but does not prove the full operational claim.
- **ASSUMED**: working hypothesis required for prototype design.
- **UNKNOWN**: no adequate evidence currently available.

## Evidence register

| ID | Status | Evidence | What it supports | What it does **not** prove |
|---|---|---|---|---|
| RWE-001 | VERIFIED_WITH_CONFLICT | Participant Guide lists six employer-risk modes; Proposal Guide conflicts on classification of item #6 | Employer compliance/risk is an organizer-recognized problem class; five core modes are consistent across both summaries | Item #6 taxonomy is not unambiguous; frequency/magnitude not proven |
| RWE-002 | VERIFIED | Participant Guide permits one or more subcategories inside one selected category | One JAGA-JKN solution may cover multiple related employer-risk modes | That all six should be MVP scope |
| RWE-003 | VERIFIED | Participant Guide confidentiality section requires dummy/anonymized data when real JKN data is not authorized | Synthetic prototype strategy is competition-compatible | Synthetic performance transfers to production |
| RWE-004 | VERIFIED | Proposal Guide requires credible problem evidence, technical/data flow, measurable impact, privacy, AI limitations, and human role | Evidence-first and human-in-the-loop proposal design | Any specific internal BPJS workflow |
| RWE-005 | VERIFIED | Perpres 82/2018 establishes employer obligations around worker registration, contribution, and responsibility when workers are not registered/paid | A normative expected state exists conceptually | Exact production policy logic without full current legal consolidation |
| RWE-006 | VERIFIED | Perpres 64/2020 states PPU contribution is 5% of wage: 4% employer + 1% participant | Contribution/wage obligation is rule-based and machine-representable | That this single rule is sufficient or unchanged for every current case |
| RWE-007 | SUPPORTED | JDIH BPK marks Perpres 82/2018 as still applicable but amended, including by Perpres 59/2024 | Policy-as-code must be versioned and effective-date aware | Final consolidated policy values for implementation |
| RWE-008 | SUPPORTED | Current BPJS Kesehatan site exposes e-Dabu Badan Usaha and highlights employer-compliance/OSS initiatives | Employer administration/compliance is an active operational domain | Internal review process, data schemas, reviewer capacity, or current pain points |

## Primary sources

### SRC-COMP-001 — Participant Guide Healthkathon 2026
Official Google Drive file supplied through Healthkathon participant channels.

https://drive.google.com/file/d/1WKfwNceTudNiKazIhg8HEd4QXolTUKHC/view

### SRC-COMP-002 — Panduan Pembuatan Proposal Peserta Healthkathon 2026
Official Google Drive file supplied through Healthkathon participant channels.

https://drive.google.com/file/d/1-g0_ZAkw6r4sKqZF_D0TafZ3tzInVju4/view

### SRC-REG-001 — Perpres No. 82 Tahun 2018 tentang Jaminan Kesehatan
JDIH BPK.

https://peraturan.bpk.go.id/Details/94711/perpres-no-82-tahun-2018

### SRC-REG-002 — Perpres No. 64 Tahun 2020
JDIH BPK.

https://peraturan.bpk.go.id/Details/136650/perpres-no-64-tahun-2020

### SRC-BPJS-001 — BPJS Kesehatan official website
Used only for externally visible service/domain context.

https://www.bpjs-kesehatan.go.id/

## Evidence gaps

The following are deliberately **not inferred**:

1. **Operational user identity**: exact BPJS unit/role that would own review and intervention.
2. **Current workflow**: how employer-compliance cases are currently detected, triaged, escalated, and closed.
3. **Available data**: which external/reference datasets BPJS can legally and technically access.
4. **Observed base rates**: prevalence of the six organizer-defined risk modes.
5. **Reviewer capacity**: number of cases/review-hours available.
6. **Production policy**: consolidated current regulation and exception handling.
7. **Existing internal tooling**: whether BPJS already has an equivalent risk engine.

These gaps become explicit assumptions or validation questions. They must not silently become product facts.

## Discovery conclusion

The evidence is sufficient to validate **the problem category and legal/normative basis** for a prototype. Taxonomy item #6 remains an explicit non-blocking A0 conflict. It is not sufficient to claim we understand BPJS's internal operations. Therefore Phase A closes as `PASS_WITH_CONSTRAINTS`, not unconditional validation.
