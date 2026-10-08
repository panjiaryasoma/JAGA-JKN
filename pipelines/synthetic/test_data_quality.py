"""Adversarial unit checks for dataset quality and intentional synthetic missingness."""

from __future__ import annotations

import unittest
import pandas as pd

from validate_dataset_quality import (
    key_issues,
    missing_classification,
    month_grid_issues,
    observation_labels,
    _numeric_profile,
)


class DataQualityInvariantTests(unittest.TestCase):
    def test_missing_registration_key_fails(self):
        frame = pd.DataFrame({
            "id_badan_usaha": ["BU-1", None],
            "periode_bulan": ["2025-01", "2025-01"],
        })
        self.assertEqual(
            key_issues(frame, ("id_badan_usaha", "periode_bulan"))["null_key_rows"], 1
        )

    def test_duplicate_company_period_is_detected(self):
        frame = pd.DataFrame({
            "id_badan_usaha": ["BU-1", "BU-1"],
            "periode_bulan": ["2025-01", "2025-01"],
        })
        self.assertEqual(
            key_issues(frame, ("id_badan_usaha", "periode_bulan"))["duplicate_key_rows"], 2
        )

    def test_empty_period_grid_is_detected(self):
        frame = pd.DataFrame({
            "id_badan_usaha": ["BU-1"],
            "periode_bulan": ["2025-01"],
        })
        issues = month_grid_issues(frame, {"BU-1", "BU-2"}, ("2025-01", "2025-02"))
        self.assertEqual(issues["missing_company_period_pairs"], 3)

    def test_complete_period_grid_passes(self):
        frame = pd.DataFrame({
            "id_badan_usaha": ["BU-1", "BU-1", "BU-2", "BU-2"],
            "periode_bulan": ["2025-01", "2025-02", "2025-01", "2025-02"],
        })
        self.assertEqual(
            month_grid_issues(frame, {"BU-1", "BU-2"}, ("2025-01", "2025-02")),
            {"missing_company_period_pairs": 0, "unexpected_pairs": 0},
        )

    def test_intentional_missing_is_not_treated_as_error(self):
        self.assertEqual(
            missing_classification("raw_monthly", "bank_posting_timestamp_synthetic"),
            "EXPECTED_SYNTHETIC_ABSENCE",
        )
        self.assertEqual(
            missing_classification("curated_monthly", "wage_authority_effective_from"),
            "EXPECTED_SYNTHETIC_ABSENCE",
        )

    def test_unknown_missing_is_flagged_for_review(self):
        self.assertEqual(
            missing_classification("curated_monthly", "registration_rule_result"),
            "REVIEW_UNEXPECTED_MISSING",
        )

    def test_unknown_observation_is_neither_true_nor_false(self):
        labels = observation_labels(pd.Series([True, False, None, float("nan")]))
        self.assertEqual(labels.tolist(), ["TRUE", "FALSE", "UNKNOWN", "UNKNOWN"])

    def test_negative_contractual_value_is_reported(self):
        frame = pd.DataFrame({"reference_worker_count_scenario": [3, -1, 5]})
        _, issues = _numeric_profile({"scenario_monthly": frame})
        self.assertEqual(issues.iloc[0]["issue"], "NEGATIVE_VALUE")
        self.assertEqual(int(issues.iloc[0]["count"]), 1)

    def test_descriptive_iqr_outlier_is_not_contract_failure(self):
        frame = pd.DataFrame({"reference_worker_count_scenario": [3, 3, 3, 3, 100]})
        profiles, issues = _numeric_profile({"scenario_monthly": frame})
        self.assertTrue(issues.empty)
        self.assertGreater(int(profiles.iloc[0]["iqr_outliers_descriptive"]), 0)


if __name__ == "__main__":
    unittest.main()
