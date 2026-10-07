# Change Log

## 2026-10-07 — M-B06 CR approval isolation

- accepted Independent Pass 3 closure of H-B03 and H-B06;
- enforced CR approval commit snapshot isolation;
- approval base may change exactly one path: the newly introduced approved CR file;
- rejected approval commits that mix unrelated artifacts, a second CR, manifest/change-log edits, or target changes;
- added regression for CR + unrelated reviewed artifact;
- added regression for CR + second CR;
- clarified M-B01 requires strict / branch-up-to-date required checks to close latest-base TOCTOU;
- synchronized Phase B contradiction audit to Independent Pass 3.

No merge, freeze, A4 drafting, or implementation was authorized.
