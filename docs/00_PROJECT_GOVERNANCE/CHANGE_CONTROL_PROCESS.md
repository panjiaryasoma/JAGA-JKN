---
project: JAGA-JKN
status: REVIEWED
version: 0.4.0
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

If main moves after CR approval and before the semantic PR, the authorization expires. Re-approval is required. Annoying, yes. Also substantially less exciting than reusable governance exploits.

## CR schema v2

```json
{
  "schema_version": 2,
  "cr_id": "CR-2026-001",
  "decision": "APPROVE",
  "approver": "panjiaryasoma",
  "approved_at": "2026-10-07",
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
3. approver is authorized for every target path;
4. `authorized_base_sha` equals the first parent of the semantic PR base;
5. CR did not exist at `authorized_base_sha`;
6. source blob SHA-256 at authorized base equals `source_sha256`;
7. the CR-approval commit itself did not alter the target;
8. semantic PR head exactly equals `target_sha256`, or is absent for explicit DELETE;
9. ID scope is checked as defense-in-depth;
10. the CR record used for authorization is not edited in the semantic PR;
11. `CHANGE_LOG.md` is updated.

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
- force-push/deletion bypass is constrained;
- manifest/frontmatter are consistent;
- provenance/ownership are complete.

CI success without branch/ruleset enforcement remains evidence, not prevention.
