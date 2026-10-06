# Change Log

## 2026-10-07 — H-B03 governance hardening

- changed FROZEN protection from head-only to base+head evaluation;
- blocked FROZEN status downgrade/removal bypass;
- changed CR authorization from existence-only to pre-approved-base-CR semantics;
- added path/ID/approver/approval-date/validation-plan CR validation;
- added machine-readable approval authority registry;
- added trusted-base `pull_request_target` workflow design;
- added downgrade, dummy-CR, valid-CR, and self-modification regression tests;
- added manifest/frontmatter consistency checks;
- recorded `main` as unprotected with required checks off;
- expanded legal provenance for UU 24/2011 amendments, PP 86/2013 wage semantics, and PerBPJS contribution chain;
- split Phase B freeze into B1 boundary freeze and B2 executable-policy freeze.

No artifact was FROZEN and PR #1 was not merged.
