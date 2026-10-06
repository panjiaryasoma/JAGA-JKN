# Change Log

## 2026-10-07 — H-B06 CR authorization binding

- replaced reusable path/ID CR authorization with one-shot source→target binding;
- added CR schema v2 with authorized base SHA, source SHA-256, exact target SHA-256 or DELETE;
- required CR filename to match cr_id;
- required parseable ISO approval date;
- bound approved CR to the base commit that introduces it directly over its declared authorized base;
- added replay, target mismatch, base mismatch, ID-scope, explicit-delete, exact-target, filename, and date regressions;
- preserved H-B03 downgrade/dummy-CR/self-modification tests;
- completed exact source URLs for UU 6/2023 and PerBPJS 5/2018;
- added PP 86/2013 → WAGE-001 and full PerBPJS amendment-chain → CONTRIB-001 traceability.

No merge, freeze, A4 drafting, or implementation was authorized.
