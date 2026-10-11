# Training-only feature diagnostics

Status: DRAFT — synthetic experiment only.

Rows: 4900; companies: 350; target: `target_lead_1`.
Feature count: 31. Source: primary group_time training partition only.

Association is not evidence of leakage or of safe admission. No feature is automatically allowed or removed by a correlation cutoff.
month_index remains excluded (prior HOLD). All features require operational availability/domain review before real-data use.
Complete ingest/as-of timestamps are missing. Period separation cannot prove all features were available at prediction time.

| Feature | Pearson correlation | Constant |
|---|---:|---|
| registration_evidence_valid | N/A | True |
| registration_evidence_quality | 0.021017 | False |
| registration_source_metadata_valid | N/A | True |
| registration_period_binding_valid | N/A | True |
| registration_worker_set_valid | N/A | True |
| registration_explanation_metadata_valid | N/A | True |
| wage_evidence_valid | N/A | True |
| wage_evidence_quality | -0.017113 | False |
| wage_source_metadata_valid | N/A | True |
| wage_period_binding_valid | N/A | True |
| wage_semantic_consistency_valid | N/A | True |
| contribution_evidence_valid | N/A | True |
| contribution_evidence_quality | -0.110512 | False |
| contribution_source_metadata_valid | N/A | True |
| contribution_period_binding_valid | N/A | True |
| payment_semantic_consistency_valid | N/A | True |
| observed_registered_worker_count | -0.041738 | False |
| unexpected_worker_count | -0.100869 | False |
| observed_wage_signal_rp | -0.034500 | False |
| business_scale | N/A | False |
| industry_sector | N/A | False |
| kbli_code | N/A | False |
| legal_entity_type | N/A | False |
| province | N/A | False |
| bpjs_branch_office | N/A | False |
| is_semester_end | 0.056576 | False |
| evidence_quality_composite | N/A | True |
| total_evidence_flags | N/A | True |
| registration_quality_score | N/A | True |
| wage_quality_score | N/A | True |
| contribution_quality_score | N/A | True |

Categorical Pearson values are omitted; constant columns have undefined association.

| Feature | Mutual information |
|---|---:|
| observed_wage_signal_rp | 0.314658 |
| observed_registered_worker_count | 0.065802 |
| industry_sector | 0.008482 |
| kbli_code | 0.008482 |
| unexpected_worker_count | 0.008397 |
| bpjs_branch_office | 0.007623 |
| province | 0.007623 |
| contribution_evidence_quality | 0.005945 |
| legal_entity_type | 0.003122 |
| is_semester_end | 0.001565 |
| business_scale | 0.001369 |
| registration_evidence_quality | 0.000715 |
| wage_evidence_quality | 0.000155 |

MI is a finite-sample diagnostic, not a causal or governance decision. Constant features are excluded from MI estimation.

Excluded features: `month_index`, `registration_discrepancy_detected`, `wage_discrepancy_signal_rp`, `wage_discrepancy_detected`, `missing_worker_count`, `contribution_payment_gap_observed`, `registration_rule_result`, `wage_rule_result`, `contribution_rule_result`, `registration_review_state`, `wage_review_state`, `contribution_review_state`, `overall_review_state`, `human_review_recommendation`, `observed_discrepancy_types`, `estimated_exposure_synthetic_rp`, `exposure_decision_role`, `risk_mode_ground_truth`, `synthetic_risk_mode_ground_truth`, `scenario_profile_synthetic`, `missing_worker_ids_json`, `unexpected_worker_ids_json`, `baseline_tenaga_kerja_synthetic`, `baseline_upah_synthetic_rp`
