---
project: JAGA-JKN
status: DRAFT
version: 0.2.0
owner: Panji
authority: Technical experimental model compatibility only
last_updated: 2026-10-12
---

# MODEL CONTRACT — Synthetic Research Bundle (BE-020)

## Authority boundary

This document defines a narrowly approved *technical interface*, not a domain/legal decision policy. Scores come from a synthetic simulator, are not calibrated to real compliance risk, and must not trigger or recommend legal consequences. Operational policy remains UNRESOLVED and operational ML status remains NOT_CONFIGURED.

## Artifact identity and compatibility

The trusted training job produces `models/best_model.pkl` and adjacent `models/metadata.json`. The pickle contains a fitted preprocessing transform, model, feature ordering, version, name and validation-selected threshold. The pickle is not committed. Load only trusted training/CI outputs; checksums alone do not authenticate publishers.

Before loading any pickle, serving checks `metadata.json` for the exact active synthetic source commit, the exact two curated CSV hashes, EXPERIMENTAL_SYNTHETIC designation, NOT_CALIBRATED calibration status and null operational threshold. The ML loader additionally validates artifact schema version 1, pickle SHA-256, declared feature ordering, package/runtime versions, estimator classes and valid threshold. The process must explicitly opt in via `JAGA_EXPERIMENTAL_ML_ENABLED=1`; model filenames and paths are not HTTP inputs.

## Features, output and limits

Inputs are reconstructed from the backend immutable snapshot using a company ID and evidence month. Public HTTP cannot send feature arrays. Shared training/inference feature code builds the frozen 31-feature schema; boolean and HIGH/MEDIUM/LOW quality encodings remain distinct. No future outcome/label, source rule result, legal classification, employee identifiers, NPWP or case status is permitted as predictor input.

The model forecasts the next month's simulator NON-NORMAL class. The returned score is a finite 0–1 **uncalibrated synthetic class score**, not an operational probability; `experimental_prediction` is a binary validation-threshold comparison, not a risk or legal decision. All scored responses carry `status=EXPERIMENTAL_SYNTHETIC`, synthetic provenance, model version, and `policy_status=UNRESOLVED`. Missing or unreliable evidence produces ABSTAIN with null score/decision. A computation error or mismatched model is an unavailable error, never a low-risk default.

## Existing evidence and decisions

The evidence browsing API and stored review workflow remain unchanged, even when the model is enabled. A request must not modify case events, case lifecycle, incident status, intervention priority, or approved baseline policy. Model readiness is explicitly separate from core backend readiness. Never substitute an experimental score for official validation of JKN compliance.

## Verification and release gates

- Reproduce/trust exact model artifact and version in pinned Python 3.12 or 3.13 runtime.
- Verify artifact and curated dataset provenance before unpickling.
- Verify missing/unknown evidence abstains and model corruption cannot yield a score.
- Verify auth, HTTP schema, response sanitization, operational status invariants and no case mutation.
- Run backend and ML CI plus the real trained-model HTTP integration suite.
- Preserve baseline benchmark caveat. The previously inspected synthetic group_time benchmark yielded macro F1 ~0.5905 and company_holdout ~0.5833; neither supports a real-world effectiveness claim.

Scope remains experimental even after all technical tests pass. Dataset-specific drift, operational calibration, bias/fairness, leakage-free external validation, legal/policy authority, and production security need separate review and acceptance.
