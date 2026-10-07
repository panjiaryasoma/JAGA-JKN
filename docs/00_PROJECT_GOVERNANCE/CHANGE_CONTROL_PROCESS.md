---
project: JAGA-JKN
status: REVIEWED
version: 0.7.0
owner: Panji
artifact_authority_level: A1
authority: Project Governance
last_updated: 2026-10-07
---

# Change Control Process

## Core invariant

A protected change is authorized only when a human-approved CR is bound to the **specific source state and exact intended target state**.

Approval of a path or requirement ID alone is never a standing authorization.

## Protected changes

Class 2 protection applies to:
- any artifact that is `FROZEN` in the PR base;
- lifecycle/authority metadata of a base-FROZEN artifact;
- trusted governance controls after governance bootstrap.

Base protection survives downgrade, supersession, manifest-row removal, and file deletion attempts.

## One-shot CR sequencing

CR authorization is intentionally two-step:

```text
B0 = current protected main
        ↓
CR-only approval PR
diff(B0, B1) = exactly one CR file
CR declares authorized_base_sha = B0
source hashes = state at B0
target hashes = exact intended new content
        ↓
B1 = commit/merge that introduces approved CR directly on top of B0
        ↓
semantic-change PR MUST use B1 as its base
        ↓
validator checks exact target
        ↓
semantic change merges
        ↓
CR can no longer authorize another change
```

Why `authorized_base_sha` refers to **B0**, not B1: B1 contains the CR itself, so making the CR contain B1's own commit SHA would be self-referential. The validator instead requires B1's first parent to equal `authorized_base_sha`, and requires the approved CR file to be newly introduced in B1.

If main moves after CR approval and before the semantic PR, the authorization expires. Re-approval is required. Repository enforcement must therefore require the Governance Trusted check in **strict / branch-up-to-date mode**, so a stale green check cannot survive a base movement. Annoying, yes. Also substantially less exciting than reusable governance exploits.

## CR schema v3

```json
{
  "schema_version": 3,
  "cr_id": "CR-2026-001",
  "decision": "APPROVE",
  "approver": "panjiaryasoma",
  "approved_at": "2026-10-07",
  "approval_pr_number": 42,
  "authorized_base_sha": "<B0 git sha>",
  "targets": {
    "docs/.../BRD.md": {
      "source_sha256": "<sha256 of B0 blob>",
      "target_state": "PRESENT",
      "target_sha256": "<sha256 of exact approved target blob>",
      "affected_ids": ["BR-001"]
    }
  },
  "validation_plan": "Concrete non-empty validation plan."
}
```

For deletion:

```json
{
  "source_sha256": "<current blob sha256>",
  "target_state": "DELETE",
  "affected_ids": ["BR-001"]
}
```

A DELETE target must not carry `target_sha256`.

## Validator requirements

For an approved CR to authorize a protected path:

1. CR filename ID equals JSON `cr_id`;
2. `approved_at` is a valid ISO `YYYY-MM-DD` date;
3. `approval_pr_number` binds the CR to the exact CR-only approval PR;
4. approver is authorized for every target path;
5. `authorized_base_sha` equals the first parent of the semantic PR base;
6. CR did not exist at `authorized_base_sha`;
7. source blob SHA-256 at authorized base equals `source_sha256`;
8. the CR-approval commit changes **exactly one path: that CR file itself**;
9. the trusted validator queries GitHub and requires approval PR `merged=true`, `merge_commit_sha == approval_base`, and authenticated `merged_by.login == CR.approver`;
10. therefore the approval commit cannot alter target/context and the approver identity cannot be self-asserted;
11. semantic PR head exactly equals `target_sha256`, or is absent for explicit DELETE;
12. ID scope is checked as defense-in-depth;
13. the CR record is immutable after entering base;
14. `CHANGE_LOG.md` is updated by the later semantic-change PR.

## Replay rule

An approved CR is deliberately retained forever as evidence, but is **not reusable**.

After A→B merges:
- current base is no longer the commit that introduced the CR directly above its authorized base;
- source blob no longer equals A;
- a later B→C target cannot equal the previously approved B hash.

One approval therefore authorizes one exact state transition.

## Trusted-control rule

After bootstrap, modifications to the trusted workflow, validator, CODEOWNERS, manifest, Change Control Process, or Approval Authority registry require the same one-shot CR semantics.

The trusted `pull_request_target` workflow uses the validator from trusted base and treats PR head as data.

## Freeze prerequisites

No first FROZEN artifact until:
- latest independent audit has no unresolved HIGH affecting B1;
- repository protection requires PR + Governance Trusted;
- required status checks run in strict / branch-must-be-up-to-date mode;
- force-push/deletion bypass is constrained;
- manifest/frontmatter are consistent;
- provenance/ownership are complete.

CI success without branch/ruleset enforcement remains evidence, not prevention.


## CR evidence ledger

`change_requests/CR-*.md` is append-only evidence.

At CR ingest time the trusted validator requires:
- exactly one new CR file and no other changed path;
- schema parse succeeds immediately;
- filename equals `cr_id`;
- decision is `APPROVE`;
- valid ISO approval date;
- positive `approval_pr_number`, equal to the current approval PR number;
- authorized approver;
- `authorized_base_sha` equals current PR base;
- every source hash matches the current base.

Once a CR exists in base:
- modification → REJECT;
- deletion → REJECT;
- rename/copy used to rewrite identity → REJECT.

Historical corrections must be new records. Existing evidence is never rewritten.

## Approval identity binding

The CR field `approver` is a claim until the CR-only approval PR is merged.

When a later protected semantic change attempts to consume the CR, Governance Trusted queries the GitHub Pull Request API using a read-only token and requires:

```text
approval PR is merged
AND approval PR merge_commit_sha == semantic PR base
AND approval PR merged_by.login == CR.approver
AND CR.approver is authorized for every target
```

For the current single accountable approver model, the authenticated merge actor is the approval ceremony. This avoids relying on self-asserted text and avoids a sole-CODEOWNER self-review deadlock.


## Authorization ledger contract

`change_requests/` is the **approved authorization ledger only**.

Drafting may use `PENDING` in a working copy/template, but a record may enter the repository ledger only with `decision=APPROVE`.

`REJECT` and `DEFER` are not authorization records and therefore do not enter this ledger. Their evidence remains in the GitHub PR/issue discussion or other separately governed decision evidence. Historical approved CR records are immutable.
