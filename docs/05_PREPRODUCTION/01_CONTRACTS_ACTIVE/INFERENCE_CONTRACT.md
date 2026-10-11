---
project: JAGA-JKN
status: DRAFT
version: 0.2.0
owner: Panji
authority: Technical inference boundary proposal (not policy approval)
last_updated: 2026-10-12
---

# INFERENCE CONTRACT — Experimental Synthetic Serving (BE-020)

## Scope and non-goals

This contract defines an **opt-in, read-only, synthetic-only** ML demonstration API. It does not decide JKN compliance, detect a legal violation, allocate interventions, authorize any sanction, or change case state. The operational policy remains `UNRESOLVED` and the operational ML capability remains `NOT_CONFIGURED`, even when experimental serving is enabled. Business/domain approval remains separate and pending.

The pinned model forecasts the *simulator's* next-month `NON-NORMAL` class. Its score is **uncalibrated**, not a probability that an employer is non-compliant. The threshold was selected on synthetic validation data for macro F1, not approved for operations.

## Preconditions and activation

- Disabled by default; explicit process-level opt-in is required. No request may choose a model file, metadata file, dataset path, or alter activation.
- A complete, trusted `best_model.pkl` and adjacent `metadata.json` must exist. Git does not contain the pickle. Never unpickle a third-party model. SHA-256 guards corruption but not malicious provenance.
- Loader validates artifact schema, complete metadata, frozen feature order, exact runtime versions, model classes, finite threshold, and model/metadata agreement before serving. The model must be aligned to the active synthetic source commitment and curated CSV hashes.
- No lazy network fetch, auto-train, model fallback, stale score cache, or failed-run fake prediction.
- Missing or invalid model must not affect evidence browsing, health/readiness of existing non-ML services, or persisted cases. ML-specific requests fail closed.
- Experiment only uses existing company and monthly evidence records identified by a stable `id_badan_usaha` and `periode_bulan`. Untrusted user-provided feature objects, future outcomes, simulator target/labels, and case status are never ML inputs.
- Require authenticated demo reviewer/supervisor access for prediction, not a public endpoint. Never log raw evidence or predictor features.

## Proposed HTTP boundary

`GET /api/v1/ml/experimental/badan-usaha/{id_badan_usaha}/{periode_bulan}`

Response envelope `{data: {...}, meta: DatasetRef}` (no mutation and no side effects). For an eligible input, `data` includes `status: EXPERIMENTAL_SYNTHETIC`, `id_badan_usaha`, `period_month`, `target_period`, `model_version`, `model_name`, `score`, `score_semantics: uncalibrated_synthetic_non_normal_score`, `threshold`, `experimental_prediction`, `is_synthetic: true`, `policy_status: UNRESOLVED`. Fields have strict JSON types and finite numeric ranges. `target_period` is precisely one calendar month after evidence; it is *not* a claim of point-in-time operational availability.

When evidence cannot support the full feature vector, respond with `status: ABSTAIN`, a finite enumerated `reason_code`, `score: null` and `experimental_prediction: null`. Do not convert missing/unknown data into zero or "low risk". Invalid, non-synthetic, or mismatched model/dataset provenance is never scored.

`GET /api/v1/ml/status` keeps operational `status: NOT_CONFIGURED` and reports an **independent** experiment readiness state, e.g. `DISABLED`, `UNAVAILABLE`, or `READY`. Readiness of ordinary evidence/workflow services must not claim ML availability.

Error requirements: unauthenticated 401 or auth not configured 503; invalid identifier/period 422; unknown record 404; disabled/missing/invalid model 503 with sanitized stable error code; unexpected inference faults return a sanitized 503/500 (without model internals). Authentication and request validation precedence follows the existing API. Evidence snapshot errors retain existing `DATASET_UNAVAILABLE`/`DATASET_INVALID` codes.

## Invariants and acceptance (BE-020 → BE-021/BE-022)

| ID | Criterion |
|---|---|
| INF-001 | Default deployment remains disabled; operational `ml` remains `NOT_CONFIGURED`. |
| INF-002 | Explicit experiment opt-in with missing/tampered artifact fails closed, never invokes untrusted fallback. |
| INF-003 | Input is assembled from same-snapshot company + evidence by exact ID/month, never from HTTP-provided features. |
| INF-004 | Model metadata must match synthetic dataset source and both curated file hashes; mismatches fail closed. |
| INF-005 | Incomplete evidence abstains; missing, nonfinite, or invalid values cannot produce a score. |
| INF-006 | Score is constrained to [0,1], described as uncalibrated simulator score, and cannot mutate cases. |
| INF-007 | Predict endpoint is authenticated, exposes no personal identifiers, raw simulator labels, or policy decisions. |
| INF-008 | Disabled model and model errors do not block snapshot, dashboard, or case-review endpoints. |
| INF-009 | Automated contract tests cover enabled success, abstain, role/auth, absent artifact, version/provenance mismatch, and score failure. |
| INF-010 | Real-HTTP smoke and pinned CI verify existing backend + ML regressions before integration is accepted. |

## Dependencies / gates

1. `models/metadata.json` and the model bundle produced by the trusted synthetic pipeline.
2. `packages/ml/inference.py` frozen feature extraction, shared with training.
3. Existing immutable snapshot, dataset metadata, authentication, and error contracts.
4. Governance review before any reclassification of an experimental score as operational risk; this contract does not authorize that transition.

**Status:** Technical design draft awaiting implementation evidence and domain acceptance. Passing tests alone does not convert DRAFT to business-approved or production-ready.
