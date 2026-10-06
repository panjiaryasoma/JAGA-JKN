---
project: JAGA-JKN
status: REVIEWED
version: 0.2.0
owner: Panji
authority_level: A3
authority: Business / Domain Boundary
---

# Business Rules

## Safety/governance rules

- **BRULE-GOV-001**: `rule signal != ML signal != confirmed violation`.
- **BRULE-GOV-002**: automated output may recommend review; it may not impose sanction, establish debt, or determine fraud.
- **BRULE-GOV-003**: insufficient or conflicting authoritative evidence must remain UNKNOWN/ABSTAIN.
- **BRULE-GOV-004**: numeric exposure estimates must be labeled estimates unless based on authoritative adjudicated values.
- **BRULE-GOV-005**: real JKN participant data requires official authorization.

## Source/policy rules

- **BRULE-SRC-001**: every normative calculation must identify `source_id`, `policy_version`, and applicable/effective period.
- **BRULE-SRC-002**: project interpretation never overrides an A0 legal/official source.
- **BRULE-SRC-003**: if applicable policy is ambiguous or unresolved, downstream decision logic must not silently choose a value.
- **BRULE-SRC-004**: rules must be evaluated against the policy effective for the evaluated period, not merely the newest policy.

## Verified legal anchors

- **LAW-REG-001**: UU 24/2011 Pasal 15 requires employers, in stages, to register themselves and workers with BPJS and provide employer/worker/family data completely and correctly.
- **LAW-CONTRIB-001**: Perpres 64/2020 documents PPU contribution at 5% of monthly wage, with 4% employer and 1% participant, paid directly by the employer to BPJS Kesehatan.
- **LAW-VERSION-001**: JDIH BPK lists Perpres 82/2018 as effective and amended by Perpres 75/2019, 64/2020, and 59/2024.
- **LAW-COMPLY-001**: PP 86/2013 provides an administrative-sanction framework for employer failure to meet relevant BPJS registration/data duties.
- **LAW-IURAN-001**: BPJS Kesehatan Regulation 2/2024 addresses collection, payment/recording, arrears, and increased supervision/examination of contribution-payment compliance.

These anchors are **not a complete consolidated implementation policy**.

## MVP boundary

The MVP may model PDUK, under-reporting wage, and contribution irregularity as review signals. It may not encode production thresholds or lawful exceptions that have not been verified.
