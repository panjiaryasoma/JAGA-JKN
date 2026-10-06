---
project: JAGA-JKN
competition: BPJS Kesehatan Healthkathon 2026
status: REVIEWED
version: 0.2.0
owner: Panji
authority: Discovery Hypothesis
authority_level: A2
last_updated: 2026-10-07
---

# Root Cause Analysis

This document is intentionally a **causal hypothesis map**, not a claim that BPJS internal root causes have been observed.

## Observable problem class

Official competition guidance defines employer-risk modes where the registered/reported state may diverge from the state required by JKN obligations.

## Causal hypotheses

### HYP-RC-001 — State divergence
A compliance risk becomes detectable when a trustworthy reference or normative state differs materially from the observed/reported state.

**Status:** SUPPORTED conceptually by official risk definitions and employer obligations.

### HYP-RC-002 — Temporal ambiguity
A one-period discrepancy may represent legitimate administrative timing rather than persistent non-compliance; therefore persistence/correction over time may be necessary to distinguish transient from sustained cases.

**Status:** ASSUMED. Requires domain validation.

### HYP-RC-003 — Evidence-quality limitation
Some risk types cannot be established from BPJS self-reported employer data alone because the missing truth may exist outside the system.

**Status:** SUPPORTED logically, but operational data access is UNKNOWN.

### HYP-RC-004 — Review capacity
When potential cases exceed review capacity, prioritization may create operational value.

**Status:** ASSUMED. Reviewer capacity has not been evidenced.

### HYP-RC-005 — Resolution blindness
A detection-only system can repeatedly surface a case without knowing whether it was corrected, explained, or recurred.

**Status:** PRODUCT HYPOTHESIS, not an observed deficiency of BPJS current systems.

## What is not a validated root cause

We do **not** currently claim:
- BPJS reviews are predominantly manual;
- BPJS lacks cross-source reconciliation;
- existing BPJS systems cannot track resolution;
- staff shortage is the direct cause of employer-compliance risk.

Those claims require internal evidence or an authoritative publication.
