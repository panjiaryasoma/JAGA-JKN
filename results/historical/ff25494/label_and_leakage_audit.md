# Feature Leakage Audit & EDA Report

**Lead ML Engineer:** Haidir 
**Dataset Commit Reference:** `9390d36a1adbef6f17aa6804dd6c56d290e06d04`  
**Total Records:** 12,000 | **Enterprises:** 500 | **Observation Period:** 2025-01 to 2026-12  

---

## 1. Ground Truth Label Distribution

| Original Ground Truth Risk Mode | Sample Count | Proportion |
|---|---:|---:|
| `NORMAL` | 7,571 | 63.1% |
| `WORKER_REGISTRATION_GAP` | 1,861 | 15.5% |
| `CONTRIBUTION_PAYMENT_GAP` | 1,059 | 8.8% |
| `WAGE_REPORTING_GAP` | 940 | 7.8% |
| `MULTI_SIGNAL` | 569 | 4.7% |

| Binary Classification Target | Sample Count | Proportion |
|---|---:|---:|
| `NORMAL (0)` | 7,571 | 63.1% |
| `NON-NORMAL (1)` | 4,429 | 36.9% |

> Dataset exhibits mild imbalance (~63:37). Managed using `class_weight='balanced'`.

---

## 2. Point-Biserial Correlation Audit vs Binary Target

> Classification Thresholds: |corr| > 0.6 = VERY HIGH (Leakage) | > 0.4 = HIGH | > 0.2 = MEDIUM | <= 0.2 = LOW

| Feature | Correlation | Leakage Risk | Policy Decision |
|---|---:|---|---|
| `contribution_payment_gap_observed` | 0.5180 | HIGH | FORBIDDEN (Policy) |
| `wage_discrepancy_detected` | 0.4959 | HIGH | FORBIDDEN (Policy) |
| `wage_discrepancy_signal_rp` | 0.4532 | HIGH | FORBIDDEN (Policy) |
| `registration_discrepancy_detected` | 0.4336 | HIGH | FORBIDDEN (Policy) |
| `missing_worker_count` | 0.3402 | MEDIUM | FORBIDDEN (Policy) |
| `month_index` | 0.2509 | MEDIUM | HOLD |
| `unexpected_worker_count` | -0.1046 | LOW | ALLOWED |
| `is_semester_end` | 0.0449 | LOW | ALLOWED |
| `observed_registered_worker_count` | -0.0374 | LOW | ALLOWED |
| `observed_wage_signal_rp` | -0.0309 | LOW | ALLOWED |
| `registration_evidence_quality` | 0.0000 | LOW | ALLOWED |
| `registration_evidence_valid` | 0.0000 | LOW | ALLOWED |
| `registration_period_binding_valid` | 0.0000 | LOW | ALLOWED |
| `registration_source_metadata_valid` | 0.0000 | LOW | ALLOWED |
| `contribution_evidence_valid` | 0.0000 | LOW | ALLOWED |
| `wage_semantic_consistency_valid` | 0.0000 | LOW | ALLOWED |
| `registration_worker_set_valid` | 0.0000 | LOW | ALLOWED |
| `registration_explanation_metadata_valid` | 0.0000 | LOW | ALLOWED |
| `wage_evidence_valid` | 0.0000 | LOW | ALLOWED |
| `wage_evidence_quality` | 0.0000 | LOW | ALLOWED |
| `contribution_evidence_quality` | 0.0000 | LOW | ALLOWED |
| `contribution_source_metadata_valid` | 0.0000 | LOW | ALLOWED |
| `contribution_period_binding_valid` | 0.0000 | LOW | ALLOWED |
| `payment_semantic_consistency_valid` | 0.0000 | LOW | ALLOWED |
| `wage_source_metadata_valid` | 0.0000 | LOW | ALLOWED |
| `wage_period_binding_valid` | 0.0000 | LOW | ALLOWED |
| `registration_quality_score` | 0.0000 | LOW | ALLOWED |
| `evidence_quality_composite` | 0.0000 | LOW | ALLOWED |
| `wage_quality_score` | 0.0000 | LOW | ALLOWED |
| `contribution_quality_score` | 0.0000 | LOW | ALLOWED |
| `total_evidence_flags` | 0.0000 | LOW | ALLOWED |
| `registration_rule_result` | 0.0000 | LOW | FORBIDDEN (Policy) |
| `wage_rule_result` | 0.0000 | LOW | FORBIDDEN (Policy) |
| `contribution_rule_result` | 0.0000 | LOW | FORBIDDEN (Policy) |
| `registration_review_state` | 0.0000 | LOW | FORBIDDEN (Policy) |
| `wage_review_state` | 0.0000 | LOW | FORBIDDEN (Policy) |

---

## 3. Mutual Information Scores (Top 20 Features)

| Feature | Mutual Information Score |
|---|---:|
| `observed_wage_signal_rp` | 0.5000 |
| `observed_registered_worker_count` | 0.0777 |
| `month_index` | 0.0646 |
| `unexpected_worker_count` | 0.0112 |
| `wage_evidence_valid` | 0.0063 |
| `registration_period_binding_valid` | 0.0060 |
| `contribution_quality_score` | 0.0056 |
| `is_semester_end` | 0.0055 |
| `wage_evidence_quality` | 0.0041 |
| `total_evidence_flags` | 0.0040 |
| `registration_explanation_metadata_valid` | 0.0039 |
| `registration_worker_set_valid` | 0.0038 |
| `wage_semantic_consistency_valid` | 0.0033 |
| `contribution_source_metadata_valid` | 0.0022 |
| `evidence_quality_composite` | 0.0022 |
| `wage_quality_score` | 0.0021 |
| `registration_source_metadata_valid` | 0.0011 |
| `payment_semantic_consistency_valid` | 0.0002 |
| `wage_period_binding_valid` | 0.0000 |
| `wage_source_metadata_valid` | 0.0000 |

---

## 4. Final Admitted Feature Vector (32 Features)

- **16 Evidence Quality Flags:** `*_evidence_valid`, `*_evidence_quality`, `*_metadata_valid`, etc.
- **3 Pre-adjudication Observations:** `observed_registered_worker_count` (-0.037), `unexpected_worker_count` (-0.105), `observed_wage_signal_rp` (-0.031)
- **6 Enterprise Demographics:** `business_scale`, `industry_sector`, `kbli_code`, `legal_entity_type`, `province`, `bpjs_branch_office`
- **7 Engineered Temporal & Composite Metrics:** `month_index`, `is_semester_end`, `evidence_quality_composite`, `total_evidence_flags`, `*_quality_score`

## 5. Strictly Prohibited Features (Data Leakage & Post-adjudication Outputs)

- `contribution_payment_gap_observed` — Perfect correlation 1.0
- `registration_discrepancy_detected` — Deterministic with label
- `wage_discrepancy_signal_rp` — High correlation 0.453
- `missing_worker_count` — Moderate correlation 0.340
- All `*_rule_result`, `*_review_state`, `overall_review_state` — Downstream adjudication outputs

---

> Disclaimer: Synthetic benchmark dataset. Strictly forbidden for real JKN operational sanctions.