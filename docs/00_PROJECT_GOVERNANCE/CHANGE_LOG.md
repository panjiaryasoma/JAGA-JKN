# Change Log

## 2026-10-07 — M-B07 / M-B08 governance evidence hardening

- accepted Independent Pass 4 closure of M-B06;
- added authenticated GitHub merge-actor binding for CR approver identity;
- CR schema v3 adds approval_pr_number;
- Governance Trusted now has read-only pull-request permission and queries approval PR metadata;
- approval PR must be merged, merge to the exact approval base, and merged_by must equal CR.approver;
- added append-only CR evidence ledger rules;
- new CRs are parsed and validated at ingest rather than first use;
- existing CR modification/deletion/identity rewrite is rejected;
- added adversarial tests for malformed/unauthorized CR ingest, historical rewrite, authenticated actor mismatch, merge-SHA mismatch, and PR-number mismatch;
- clarified M-B01 is a post-bootstrap enforcement gate rather than a circular bootstrap blocker.

No merge, freeze, A4 drafting, or implementation was authorized.
