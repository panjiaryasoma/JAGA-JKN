---
project: JAGA-JKN
status: REVIEWED
artifact_kind: TEMPLATE
owner: Panji
artifact_authority_level: A1
authority: Project Governance
last_updated: 2026-10-07
---

# Change Request — CR-YYYY-NNN

<!-- GOVERNANCE-CR
{
  "schema_version": 2,
  "cr_id": "CR-YYYY-NNN",
  "decision": "PENDING",
  "approver": "",
  "approved_at": "",
  "authorized_base_sha": "0000000000000000000000000000000000000000",
  "targets": {
    "docs/path/to/protected-artifact.md": {
      "source_sha256": "0000000000000000000000000000000000000000000000000000000000000000",
      "target_state": "PRESENT",
      "target_sha256": "0000000000000000000000000000000000000000000000000000000000000000",
      "affected_ids": []
    }
  },
  "validation_plan": ""
}
GOVERNANCE-CR -->

## Approval procedure

1. Record `authorized_base_sha` as the protected main SHA **before** this CR is merged.
2. Record source SHA-256 from that base.
3. Prepare and review the exact intended target content.
4. Record target SHA-256, or use `target_state=DELETE`.
5. Set `decision=APPROVE`, valid approver, ISO date, and validation plan.
6. Merge this CR-only approval directly on top of the declared authorized base.
7. Create the semantic-change PR from the resulting base immediately. If base moves first, re-approve.

## Requested change

## Reason / triggering evidence

## Source authority

## Impacted artifacts / IDs

## Impact analysis

## Risks

## Validation plan

## Decision rationale

The machine-readable block is the authorization envelope. Human prose explains why the exact transition is acceptable.
