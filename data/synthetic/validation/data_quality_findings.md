# Synthetic Data Quality Findings: JAGA-JKN

Status: **PASS**

Seed: **42**, raw generator seed: **43**.
Companies: **500**, months: **24**.
Monthly scenario rows: **12000**, curated rows: **12000**.

## Integrity findings

- No hard integrity violations detected.

## Descriptive missing-data observations

- No unclassified missing values detected. Expected evidence absences are separately classified in missing_values.csv.

## Interpretation limits

- This is a seeded synthetic sandbox, NOT empirical BPJS/JKN data.
- Observed discrepancies are factual simulated observations, NOT legal determinations.
- IQR outliers are descriptive and do not trigger compliance decisions.
- B1/B2 registration/policy authority is unresolved; rule outputs remain ABSTAIN.
- Synthetic exposure is not measured financial loss and must not affect decisions.
- ML candidate files are not training-ready; label/leakage audits are pending.
- Power BI PBIX rebind is pending.

## Generated evidence

- anomaly_distribution.csv
- contribution_payment_distribution.csv
- dataset_summary.csv
- duplicate_keys.csv
- evidence_quality_distribution.csv
- missing_values.csv
- numeric_range_issues.csv
- numeric_range_summary.csv
- payment_state_distribution.csv
- registration_discrepancy_distribution.csv
- scenario_profile_distribution.csv
- temporal_consistency.csv
- wage_discrepancy_distribution.csv
- reports/data_quality/scenario_profile_distribution.png
- reports/data_quality/observed_discrepancy_by_month.png
- reports/data_quality/evidence_quality_distribution.png
- reports/data_quality/payment_state_distribution.png
