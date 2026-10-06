# Decision Log

| ID | Date | Decision | Status | Rationale |
|---|---|---|---|---|
| DEC-001 | 2026-10-07 | Authority precedence is A0 > A1 > A2 > A3 > A4 > A5 > A6; lower number is higher authority | REVIEWED | Removes ambiguous “higher authority level” wording |
| DEC-002 | 2026-10-07 | A0 belongs to official external sources; repository summaries use source_authority=A0 and artifact_role=A0_DERIVED_REGISTRY | REVIEWED | Prevents authority laundering |
| DEC-003 | 2026-10-07 | Taxonomy conflict for Kolusi/Surat Fiktif is OPEN_NON_BLOCKING_CURRENT_MVP | REVIEWED | Two official guides classify it differently |
| DEC-004 | 2026-10-07 | Phase B work occurs on branch/PR before merge; no A1/A3 freeze yet | REVIEWED | Supports contradiction audit |
| DEC-005 | 2026-10-07 | Branch protection verification is prerequisite to first FROZEN artifact | REVIEWED | CI-only detection cannot prevent direct-push bypass |
