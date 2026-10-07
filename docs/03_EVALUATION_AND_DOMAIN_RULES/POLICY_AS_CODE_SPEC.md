---
project: JAGA-JKN
status: REVIEWED
version: 0.2.0
owner: Panji
authority_level: A3
authority: Domain Rules
---

# Policy-as-Code Specification

## Required policy record

Every executable policy rule must carry:

- `rule_id`
- `source_id`
- `source_title`
- `source_authority`
- `effective_from`
- `effective_until`
- `policy_version`
- `jurisdiction/scope`
- `inputs`
- `calculation/condition`
- `exceptions`
- `missing_data_behavior`
- `output_semantics`
- `verification_status`

## Fail-closed rule

A rule with unresolved source conflict, unknown effective date, unverified exception, or missing required input is not executable for an authoritative expected-state calculation.

## Separation

- normative policy rule: what the applicable obligation says;
- detection rule: how the prototype recognizes a possible discrepancy;
- prioritization rule/model: how review order is suggested;
- human decision: authoritative operational conclusion.

These layers must not share semantics implicitly.

## Current status

Phase B defines schema and boundaries only. Production policy consolidation is not complete.
