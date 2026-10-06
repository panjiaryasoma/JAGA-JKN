---
project: JAGA-JKN
status: REVIEWED
version: 0.4.0
owner: Panji
artifact_authority_level: A6
authority: Verification & Governance Evidence
last_updated: 2026-10-07
---

# Phase B Contradiction Audit

## Latest independent result

Independent Pass 2 result:

- H-B03 original bypass: **CLOSED**
- H-B06 CR authorization replay/scope binding: **OPEN HIGH**
- Phase B content: **CONDITIONALLY PASS**
- PR #1 merge: **HOLD**
- B1 freeze: **HOLD**
- B2 freeze: **HOLD**
- implementation: **NOT AUTHORIZED**

## H-B06 remediation

The previous CR model approved path/ID scope but did not bind approval to one exact state transition. A valid historical CR could therefore become standing authorization.

Remediation on this branch introduces **CR schema v2**.

Authorization is now bound to:
- `authorized_base_sha`;
- source blob SHA-256 for every protected target;
- exact target blob SHA-256, or explicit DELETE;
- approved path;
- affected IDs as defense-in-depth;
- valid approver;
- parseable approval date;
- non-empty validation plan.

### One-shot base binding

A CR must be newly introduced in the semantic PR's base commit, whose first parent equals the CR's `authorized_base_sha`.

This solves the self-reference problem of trying to embed the CR-containing commit's own SHA in the CR while still ensuring the authorization expires when main advances.

### Replay resistance

A→B approval cannot authorize B→C because:
1. after A→B merges, the CR is no longer newly introduced in the current base;
2. the current source blob is B, not approved source A;
3. C cannot equal the approved B target hash.

### H-B06 adversarial regressions

The security suite now covers:

- old approved CR reused for a second different change → REJECT;
- exact target hash mismatch → REJECT;
- authorized base SHA mismatch → REJECT;
- ID-scoped CR with semantic change lacking identifiable ID context → REJECT;
- explicit DELETE target → ACCEPT deletion only;
- same exact approved target → ACCEPT;
- CR filename vs `cr_id` mismatch → REJECT;
- malformed `approved_at` → REJECT;
- original downgrade attack → REJECT;
- same-PR dummy CR → REJECT;
- trusted validator self-change without one-shot CR → REJECT.

**H-B06 status: REMEDIATED / PENDING INDEPENDENT PASS 3.**

The project does not self-close the HIGH until independent Pass 3 attempts to break the new authorization state.

## Other findings

### M-B01
**OPEN.** Main remains unprotected; required checks are off; rulesets are empty. B1 freeze remains blocked.

### M-B02
**OPEN / B2 only.** Legal provenance improved further:
- exact UU 6/2023 source URL added;
- exact PerBPJS 5/2018 source URL added;
- PP 86/2013 → WAGE-001 trace added;
- 5/2018 → 3/2020 → 2/2024 → CONTRIB-001 trace added.

Executable policy still requires consolidated article/effective-date/exception/timing semantics.

### M-B03
**CLOSED.**

### M-B04
**CLOSED.**

### M-B05
**PARTIAL**, largely constrained by M-B01.

## Gate

```text
PHASE A
PASS_WITH_CONSTRAINTS
        ↓
PHASE B CONTENT
CONDITIONALLY PASS
        ↓
H-B03
CLOSED
        ↓
H-B06
REMEDIATED
PENDING INDEPENDENT PASS 3
        ↓
PR #1 MERGE / B1 FREEZE
HOLD
        ↓
B2 EXECUTABLE POLICY
HOLD
        ↓
A4 / IMPLEMENTATION
NOT AUTHORIZED
```
