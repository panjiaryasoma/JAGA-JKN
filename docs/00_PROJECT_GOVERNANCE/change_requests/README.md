# Change Requests

`change_requests/` is the **approved authorization ledger** for Class 2 protected changes.

Create `CR-YYYY-NNN.md` from `../CHANGE_REQUEST_TEMPLATE.md`, prepare it against the current protected base, and ingest it only through an isolated CR-only approval PR.

Repository-ledger rules:

- `decision` must be `APPROVE` at ingest;
- one approval PR introduces exactly one CR file and no unrelated changes;
- CR IDs are never reused;
- once merged, a CR is immutable and append-only;
- corrections use a new CR record, never rewrite history.

Draft `PENDING`, `REJECT`, and `DEFER` states do not enter this authorization ledger. Rejected/deferred proposals remain evidenced by their GitHub PR/issue history or another separately governed decision record.
