# JAGA-JKN | Data-to-ML Handoff Contract

**Document ID:** JAGA-DATA-ML-HO-001  
**Version:** 0.1.0 (handoff draft; not an authorized ML feature/target freeze)  
**Prepared for:** Haidir (ML Engineering)  
**From:** JAGA-JKN Data Engineering / Project Governance  
**Data branch:** `lintang-data-contract-alignment`  
**Dataset source commit (immutable):** `9390d36a1adbef6f17aa6804dd6c56d290e06d04`  
**Verified generation & validation run:** `37759059714` (62/62 tests PASS before CSV publication), followed by CSV publication run `37806124944` (SUCCESS).  
**Scope:** synthetic sandbox for prototyping/evaluation, **not empirical BPJS/JKN data**, production scoring, enforcement, legal or policy authorization.  
**Status:** **DATA DELIVERY READY / ML FEATURE–LABEL CONTRACT PENDING**.

> **Decision boundary:** This document is a handoff, not permission to train arbitrary columns, infer violations, enforce sanctions, or announce production performance. B1/B2 authority remains unresolved; rule evaluation is intentionally fail-closed (`ABSTAIN`).

## A. Canonical input datasets

All links below point to the exact dataset publication SHA, not moving `main`.

| Classification | Exact relative path | Grain / volume | Purpose and restrictions |
|---|---|---|---|
| **Primary ML feature-source candidate** | `data/synthetic/curated/curated_kepatuhan_evidence.csv` | **employer-period**, 500 × 24 = **12,000** rows | Curated observation + evidence validity / provenance; select **only approved as-of features**, not all columns. Contains synthetic label and derived rule/workflow fields that must be excluded from X. |
| Reference/label-generation world | `data/synthetic/scenario/kepatuhan_bulanan_badan_usaha.csv` | employer-period, 12,000 rows | Holds simulated underlying reference, observed scenario and `synthetic_risk_mode_ground_truth`. Use **only for target construction, simulator evaluation and audits**, not as an unscreened feature source. |
| Raw-world audit | `data/synthetic/raw/raw_kepatuhan_bulanan_badan_usaha.csv` | employer-period, 12,000 rows | Source evidence with injected noise, conflicts, freshness and timestamps. Allows replay and feature availability tracing; **do not treat raw source as independent ground truth**. |
| Curated employer dimension | `data/synthetic/curated/curated_master_badan_usaha.csv` | employer, 500 rows | Join on `id_badan_usaha`; metadata features such as `skala_usaha` or `kode_kbli` are **conditionally** usable with explicit inference-availability and fairness/proxy review. Contains simulator `scenario_profile_synthetic`, **never X**. |
| Prebuilt **audit-only** ML snapshot | `data/synthetic/candidate_ml/dataset_candidate_ml_audit.csv` | employer latest snapshot, 500 rows | **NOT TRAINING_READY**; explicit status `CANDIDATE_ONLY__REQUIRES_LEAKAGE_LABEL_AND_EVALUATION_AUDIT`. May be explored for leakage checks only. |
| Simulated human workflow | `data/synthetic/scenario/log_review_petugas_synthetic.csv` | review events, 244 rows in this dataset | Narrative simulation only; **not observed real user feedback, supervised truth, or reward labels**. |
| Data-quality evidence | `data/synthetic/validation/` | profiling reports and CSV | Inspect `dataset_summary.json`, `missing_values.csv`, `duplicate_keys.csv`, `temporal_consistency.csv`, distributions. Synthetic missingness is intentionally present in some fields. |
| Dashboard exports | `powerbi/data/` | presentation star-schema | **Not the canonical ML train source.** Presentation contract is separate and PBIX rebind pending. |

Pinned branch browse: https://github.com/panjiaryasoma/JAGA-JKN/tree/9390d36a1adbef6f17aa6804dd6c56d290e06d04/data/synthetic  
Source implementation: https://github.com/panjiaryasoma/JAGA-JKN/tree/9390d36a1adbef6f17aa6804dd6c56d290e06d04/pipelines/synthetic

### Delivered quality proof

- `dataset_summary.json` declares `PASS`, 500 employers, 24 months, 12,000 monthly rows in scenario and curated, zero hard issues and zero residual descriptive warnings.
- GitHub Actions generated, validated and committed **26 CSV + 2 text/JSON validation summaries**; the 4 PNG quality plots were uploaded as an Actions artifact rather than committed in this SHA.
- **62 unit/contract/data-quality tests PASS** at verified run and publish workflow completed `SUCCESS`. These are **data pipeline tests, not ML validation metrics**.
- Generator version: `SYN-2026-10-08-v3`; default `JAGA_N_COMPANIES=500`; period Jan 2025–Dec 2026.
- **Actual runtime seeds:** synthetic scenario `JAGA_SYNTHETIC_SEED=42` (Python `random` + NumPy `default_rng`); raw-world random generator uses `42 + 1 = 43`. Scenario CSVs had deterministic hash recheck; raw-generator determinism was unit-tested. A full two-run hash comparison for all raw/curated files is not claimed.
- The **DRAFT** Dataset Strategy mentions `generation_seed=20261006`, `split_seed=20261007`, `model_seed=20261008`. These **do not override actual runtime seed 42/43**. Neither split nor model seed has been executed or formally frozen.

## B. Contract: grain, joins and chronology

1. `id_badan_usaha` identifies the simulated employer. `periode_bulan` has `YYYY-MM` format, 2025-01 through 2026-12. The composite (`id_badan_usaha`, `periode_bulan`) is the unique employer-month key.
2. The 500-employer dimension joins via `id_badan_usaha`; never use employer ID, company name, NPWP, phone, worker identifiers or row/source identifiers as ML X features. The synthetic generator may repeat names, so joining on employer name is invalid.
3. Distinguish **reference/true world** (synthetic scenario assumptions), **observed/raw world**, **curated evidence**, **rule result**, and **workflow/presentation**. This separation is correctness-bearing.
4. Establish `prediction_cutoff` and record which fields were available *at or before* that cutoff. Same-month evidence may be perfectly legitimate for a contemporaneous explanation but leaked for a *future prediction*.
5. All values and class proportions represent one seeded simulator. They are not BPJS population rates; no claims of real-world fairness or accuracy can follow from this dataset alone.

## C. Column eligibility, default-deny

**Full 91-column curated-evidence matrix is attached:** `JAGA_JKN_ML_FEATURE_ELIGIBILITY_MATRIX.csv`. **Every curated column defaults to `default_in_X=NO` until Haidir explicitly approves a feature contract.** Summary:

| Role | Columns / exact examples | Default use |
|---|---|---|
| `JOIN_KEY_NOT_FEATURE` | `id_badan_usaha`, `periode_bulan`, `source_record_id` | For join, grouping, time cutoffs and trace only. `periode_bulan` may yield derived calendar features only after as-of review. |
| `TARGET_CANDIDATE_ONLY` | `synthetic_risk_mode_ground_truth` | Candidate **y** for a simulator-only experiment; **never X**. `scenario_profile_synthetic` is also simulator truth, not a feature. |
| `CONDITIONAL_OBSERVATION` | `observed_registered_worker_count`, `reference_worker_count`, `missing_worker_count`, `registration_discrepancy_detected`, `observed_wage_signal_rp`, `wage_discrepancy_signal_rp`, `observed_payment_state`, `contribution_payment_gap_observed` | Only if evidence availability, label independence, scenario leakage, and cutoff are demonstrated. Reference-world-like values require extra provenance scrutiny. |
| `CONDITIONAL_EVIDENCE_QUALITY` | `registration_evidence_valid`, `wage_evidence_quality`, `contribution_period_binding_valid`, etc. | Use only if that evidence quality assessment exists *at prediction time*; abstain when missing instead of silently filling false. |
| `DO_NOT_USE_AS_FEATURE` | `*_rule_result`, `*_review_state`, `overall_review_state`, `human_review_recommendation`, `observed_discrepancy_types`, `estimated_exposure_synthetic_rp`, worker-ID lists | Outcome/decision contamination, exact labels, simulated loss estimate, identity misuse. **No unrestricted X access**. |
| `METADATA_AUDIT_ONLY` | authority ID/version/period metadata, source IDs, `*_lineage`, reason strings, `is_synthetic`, rule ID, etc. | Explain/trace/audit only; exclude from X by default. |

Matrix role counts: `CONDITIONAL_EVIDENCE_QUALITY`=16, `CONDITIONAL_OBSERVATION`=12, `DO_NOT_USE_AS_FEATURE`=19, `JOIN_KEY_NOT_FEATURE`=3, `METADATA_AUDIT_ONLY`=40, `TARGET_CANDIDATE_ONLY`=1. Do not interpret `CONDITIONAL` as automatic approval.

**Do not accidentally train on synthetic labeling logic.** In the generator, `synthetic_risk_mode_ground_truth` is derived from scenario conditions controlling worker, wage and payment gaps. Feeding those direct or near-direct gap features to a classifier predicts the generator's formula, not necessarily generalizable risk. A very high F1 here can be spurious evidence of leakage. Also, `RECURRENCE` is a scenario *profile* and does not necessarily appear as an equivalent `synthetic_risk_mode_ground_truth` class.

## D. Target proposals and required sign-off (Haidir owns)

**No ML task/label contract has been frozen.** Haidir must choose and document one proposal:

- **Option A: contemporaneous simulated risk-mode classification** (`y_t = synthetic_risk_mode_ground_truth`), explicitly a simulator reproduction experiment. Suitable for smoke tests only after a leakage-safe feature set is shown. Does **not** establish legal compliance or real operational detection.
- **Option B: forward-looking early warning** (`y_(t+h)` constructed from a future simulator observation, for explicitly selected horizon `h`), using only features available at cutoff `t`. Requires a separate time-indexed feature table, target-horizon design, and temporally aware evaluation; not available as a prepared training set yet. This is the more relevant research direction if the goal is early detection, **but it is not approved**.

`registration_rule_result`, `wage_rule_result`, `contribution_rule_result`, or `overall_review_state` are **NOT targets for this synthetic baseline**: unresolved trusted authority forces ABSTAIN, making them unsuitable as supervised legal-risk labels. Simulated human review outcomes are not ground truth.

## E. Train/validation/test split instructions (ML owns; NOT executed)

The dataset contains **no committed train/val/test split files**. Do not claim otherwise.

1. **Group identity:** `group = id_badan_usaha`. A company and all its rows belong entirely to one partition for employer-held-out generalization.
2. **Suggested baseline only:** 70%/15%/15% across **500 distinct employers** → 350/75/75 employers. For 24 complete monthly rows/employer, that corresponds to 8,400/1,800/1,800 employer-month rows. This is a proposal, **not observed split output**.
3. **Separate temporal experiment:** reserve future periods for out-of-time evaluation; compute rolling windows and lag features from past data only. Do not conflate company-held-out and time-held-out claims.
4. **No leakage:** fit imputers, encoders, scalers, target transforms, feature selection, balancing, calibration, and hyperparameter search using training data only (validation for selection/calibration when explicitly allowed; test is held out until final scoring).
5. **Proposed split seed:** 20261007 per DRAFT data-strategy document, **not applied**. Haidir must specify and persist actual `split_seed`, group lists, class distribution and artifact SHA. Model seed likewise belongs to ML.
6. **Evidence:** export split manifests with employer IDs, per-partition counts, target distribution, datetime cutoff, code SHA and zero group overlap. Preserve a blinded untouched test set where possible.
7. **Do not use row-random split** on the 12,000 employer-period records: it allows the same employer to appear in train and test. Group-held-out CV/forward-chaining evaluation are different tests, and both should be reported if attempted.

Recommended future Haidir-owned outputs (not present yet):

    data/synthetic/ml_splits/train.csv
    data/synthetic/ml_splits/validation.csv
    data/synthetic/ml_splits/test.csv
    data/synthetic/ml_splits/split_manifest.json
    results/ml_baseline_metrics.json
    results/label_and_leakage_audit.md
    models/metadata.json

Publishing those paths requires a separate implementation scope, passing ML acceptance gates, and explicit repository ACC. Dataset inputs currently remain immutable in this handoff.

## F. Acceptance / reject checklist

| ID | Criterion | Current state | Responsible |
|---|---|---|---|
| ML-HO-001 | Pin exact SHA, readable source files, row counts, join keys | **PASS / delivered** | Data Engineering |
| ML-HO-002 | Data-quality and contract validators PASS; missing-value semantics documented | **PASS / delivered** | Data Engineering |
| ML-HO-003 | Generator provenance and actual seed traceable; no synthetic-as-real claims | **PASS / delivered** | Data Engineering |
| ML-HO-004 | All 91 curated columns classified, with default-deny feature policy | **PASS / proposed matrix**, await Haidir review | Data Engineering → ML |
| ML-HO-005 | ML objective, prediction time/horizon and target definition approved | **PENDING** | Haidir + Product/Domain Owner |
| ML-HO-006 | Exact `X` list, source availability, feature provenance and leakage audit | **PENDING** | Haidir |
| ML-HO-007 | No simulator ground truth, rule/workflow/decision/exposure in X | **PENDING runtime proof** | Haidir |
| ML-HO-008 | Group-disjoint split implemented; temporal test appropriately designed | **PENDING** | Haidir |
| ML-HO-009 | Actual split/model seeds and manifests logged | **PENDING** | Haidir |
| ML-HO-010 | Baseline, metrics, class/slice breakdown, calibration and residual risk | **PENDING** | Haidir |
| ML-HO-011 | Explicit statement of synthetic-only validity; no legal/policy authority inferred | **REQUIRED** | All |

**Stop/go decision:** Data Engineering handoff **READY FOR HAIDIR TO START FEATURE/LABEL AUDIT**. ML model training is **NOT GREEN** until ML-HO-005 through ML-HO-009 are satisfied. No PR, merge, or source mutation is implied by this document.

## G. Implementation handoff instructions to Haidir

1. Check out the pinned SHA, verify `dataset_summary.json`, and read the eligibility matrix before opening a notebook.
2. Specify the ML business question, unit of prediction, cutoff, horizon and benchmark; do **not** treat simulated discrepancy as proven JKN policy violation.
3. Draft exact approved feature list and target lineage. For every proposed X feature, cite source field, availability time and leakage test. Explicitly exclude downstream rules/workflow, synthetic exposure, and simulation-only meta fields.
4. Choose group split, temporal validation protocol, and metric targets; save split manifest and random seeds.
5. Only then run training, evaluate on held-out data, and produce artifacts plus synthetic-to-real limitations. No claim of production eligibility.

## H. Pinned reference links

- Data snapshot: https://github.com/panjiaryasoma/JAGA-JKN/tree/9390d36a1adbef6f17aa6804dd6c56d290e06d04/data/synthetic
- Candidate snapshot: https://github.com/panjiaryasoma/JAGA-JKN/blob/9390d36a1adbef6f17aa6804dd6c56d290e06d04/data/synthetic/candidate_ml/dataset_candidate_ml_audit.csv
- Curated evidence: https://github.com/panjiaryasoma/JAGA-JKN/blob/9390d36a1adbef6f17aa6804dd6c56d290e06d04/data/synthetic/curated/curated_kepatuhan_evidence.csv
- Scenario ground truth: https://github.com/panjiaryasoma/JAGA-JKN/blob/9390d36a1adbef6f17aa6804dd6c56d290e06d04/data/synthetic/scenario/kepatuhan_bulanan_badan_usaha.csv
- Data-quality summary: https://github.com/panjiaryasoma/JAGA-JKN/blob/9390d36a1adbef6f17aa6804dd6c56d290e06d04/data/synthetic/validation/dataset_summary.json
- Generation source: https://github.com/panjiaryasoma/JAGA-JKN/blob/9390d36a1adbef6f17aa6804dd6c56d290e06d04/pipelines/synthetic/generate_dataset_bpjs.py
- Data contract source: https://github.com/panjiaryasoma/JAGA-JKN/blob/9390d36a1adbef6f17aa6804dd6c56d290e06d04/pipelines/synthetic/pipeline_cleansing_dan_disambiguasi.py
- Full quality run: https://github.com/panjiaryasoma/JAGA-JKN/actions/runs/37759059714
- Successful repository CSV push: https://github.com/panjiaryasoma/JAGA-JKN/actions/runs/37806124944
