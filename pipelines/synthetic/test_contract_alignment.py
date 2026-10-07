from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
SCRIPTS = [
    "generate_dataset_bpjs.py",
    "generate_raw_dataset_bpjs.py",
    "pipeline_cleansing_dan_disambiguasi.py",
    "prepare_powerbi_dataset.py",
]


def load_curation_module():
    spec = importlib.util.spec_from_file_location(
        "jaga_curation",
        HERE / "pipeline_cleansing_dan_disambiguasi.py",
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.path.insert(0, str(HERE))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(HERE))
    return module


CURATION = load_curation_module()


class ContractAlignmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.data_root = Path(cls.tmp.name) / "data" / "synthetic"
        cls.powerbi_root = Path(cls.tmp.name) / "powerbi"
        env = os.environ.copy()
        env.update({
            "JAGA_DATA_ROOT": str(cls.data_root),
            "JAGA_POWERBI_DIR": str(cls.powerbi_root),
            "JAGA_POWERBI_DATA_DIR": str(cls.powerbi_root / "data"),
            "JAGA_N_COMPANIES": "20",
            "JAGA_SYNTHETIC_SEED": "42",
        })
        cls.env = env
        for script in SCRIPTS:
            subprocess.run(
                [sys.executable, str(HERE / script)],
                env=env,
                check=True,
                capture_output=True,
                text=True,
            )

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_root_level_default_layout_is_encoded(self):
        text = (HERE / "paths.py").read_text(encoding="utf-8")
        self.assertIn('ROOT_DIR / "data" / "synthetic"', text)
        self.assertIn('ROOT_DIR / "powerbi"', text)

    def test_powerbi_consumes_curated_evidence(self):
        text = (HERE / "prepare_powerbi_dataset.py").read_text(encoding="utf-8")
        self.assertIn("curated_kepatuhan_evidence.csv", text)
        self.assertNotIn("C:\\Users\\", text)

    def test_spouse_is_not_an_exemption_signal(self):
        for name in ["generate_raw_dataset_bpjs.py", "pipeline_cleansing_dan_disambiguasi.py"]:
            text = (HERE / name).read_text(encoding="utf-8").lower()
            self.assertNotIn("gap_setelah_pasangan", text)
            self.assertNotIn("legal exemption", text)

    def test_policy_authority_unknown_cannot_open_wage_review(self):
        state, reason = CURATION.derive_wage_state(
            wage_discrepancy_signal_rp=1,
            evidence_quality="HIGH",
        )
        self.assertEqual((state, reason), ("ABSTAIN", "POLICY_REQUIRED_BUT_UNRESOLVED"))

    def test_policy_authority_missing_cannot_open_contribution_review(self):
        state, reason = CURATION.derive_contribution_state(
            contribution_payment_evidence_gap=True,
            evidence_quality="HIGH",
        )
        self.assertEqual((state, reason), ("ABSTAIN", "POLICY_REQUIRED_BUT_UNRESOLVED"))

    def test_spoofed_row_policy_metadata_has_no_decision_authority(self):
        text = (HERE / "pipeline_cleansing_dan_disambiguasi.py").read_text(encoding="utf-8")
        self.assertIn("TRUSTED_B2_POLICY_CONTEXT_AUTHORIZED = False", text)
        self.assertNotIn('"AUTHORIZED" in policy_status', text)

    def test_equal_count_different_worker_sets_are_detected(self):
        result = CURATION.reconcile_worker_sets({"A", "B", "C"}, {"A", "B", "D"})
        self.assertEqual(result["reference_count"], 3)
        self.assertEqual(result["observed_count"], 3)
        self.assertEqual(result["missing_worker_ids"], ["C"])
        self.assertEqual(result["unexpected_worker_ids"], ["D"])
        self.assertFalse(result["sets_equal"])

    def test_registration_state_uses_set_reconciliation_outputs(self):
        state, reason = CURATION.derive_registration_state(
            missing_worker_count=1,
            unexpected_worker_count=1,
            evidence_quality="HIGH",
            explanation_present=False,
        )
        self.assertEqual((state, reason), ("REVIEW", "HUMAN_REVIEW_NO_AUTOMATED_PRIORITY"))

    def test_invalid_evidence_quality_fails_closed(self):
        for invalid in ["UNKNOWN", "", None, "VERY_HIGH"]:
            with self.subTest(invalid=invalid):
                state, reason = CURATION.derive_registration_state(
                    missing_worker_count=1,
                    unexpected_worker_count=0,
                    evidence_quality=invalid,
                    explanation_present=False,
                )
                self.assertEqual(state, "ABSTAIN")
                self.assertEqual(reason, "INVALID_OR_UNKNOWN_EVIDENCE_QUALITY")

    def test_invalid_evidence_quality_fails_closed_for_policy_signals_too(self):
        for invalid in ["UNKNOWN", "", None]:
            with self.subTest(invalid=invalid):
                self.assertEqual(
                    CURATION.derive_wage_state(
                        wage_discrepancy_signal_rp=1,
                        evidence_quality=invalid,
                    )[0],
                    "ABSTAIN",
                )
                self.assertEqual(
                    CURATION.derive_contribution_state(
                        contribution_payment_evidence_gap=True,
                        evidence_quality=invalid,
                    )[0],
                    "ABSTAIN",
                )

    def test_multi_signal_states_remain_independent(self):
        registration = CURATION.derive_registration_state(
            missing_worker_count=1,
            unexpected_worker_count=0,
            evidence_quality="HIGH",
            explanation_present=False,
        )[0]
        wage = CURATION.derive_wage_state(
            wage_discrepancy_signal_rp=1,
            evidence_quality="HIGH",
        )[0]
        contribution = CURATION.derive_contribution_state(
            contribution_payment_evidence_gap=False,
            evidence_quality="HIGH",
        )[0]
        overall = CURATION.derive_overall_review_state(registration, wage, contribution)
        self.assertEqual(registration, "REVIEW")
        self.assertEqual(wage, "ABSTAIN")
        self.assertEqual(contribution, "NORMAL")
        self.assertEqual(overall, "PARTIAL")

    def test_seasonal_explanation_does_not_mutate_set_discrepancy(self):
        reconciliation = CURATION.reconcile_worker_sets({"A", "B", "C"}, {"A", "B"})
        state, _ = CURATION.derive_registration_state(
            missing_worker_count=reconciliation["missing_worker_count"],
            unexpected_worker_count=reconciliation["unexpected_worker_count"],
            evidence_quality="HIGH",
            explanation_present=True,
        )
        self.assertEqual(reconciliation["missing_worker_count"], 1)
        self.assertEqual(state, "NEEDS_ENRICHMENT")

    def test_synthetic_exposure_remains_visualization_only(self):
        curated = pd.read_csv(self.data_root / "curated" / "curated_kepatuhan_evidence.csv")
        self.assertTrue(
            curated["exposure_decision_role"].eq(
                "VISUALIZATION_ONLY__MUST_NOT_INFLUENCE_DECISION"
            ).all()
        )

    def test_risk_strength_remains_unscored(self):
        curated = pd.read_csv(self.data_root / "curated" / "curated_kepatuhan_evidence.csv")
        self.assertTrue(curated["risk_strength"].eq("UNSCORED__THRESHOLDS_NOT_AUTHORIZED").all())

    def test_no_invented_threshold_scoring_function_remains(self):
        text = (HERE / "pipeline_cleansing_dan_disambiguasi.py").read_text(encoding="utf-8")
        self.assertNotIn("def risk_strength(", text)
        self.assertNotIn("5_000_000", text)
        self.assertNotIn("500_000", text)
        self.assertNotIn("duration_hint", text)

    def test_curated_output_contains_independent_signal_states(self):
        curated = pd.read_csv(self.data_root / "curated" / "curated_kepatuhan_evidence.csv")
        required = {
            "registration_signal_state",
            "wage_signal_state",
            "contribution_signal_state",
            "overall_review_state",
            "missing_worker_count",
            "unexpected_worker_count",
        }
        self.assertTrue(required.issubset(curated.columns))

    def test_ml_dataset_is_candidate_not_training_ready(self):
        candidate = pd.read_csv(self.data_root / "candidate_ml" / "dataset_candidate_ml_audit.csv")
        self.assertTrue(candidate["ml_status"].str.contains("CANDIDATE_ONLY").all())
        self.assertFalse((self.data_root / "candidate_ml" / "dataset_intelijen_kepatuhan_ml.csv").exists())

    def test_end_to_end_validator_passes(self):
        result = subprocess.run(
            [sys.executable, str(HERE / "demo_analisis_dan_validasi.py")],
            env=self.env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("MERGE READINESS: NOT CLAIMED", result.stdout)


if __name__ == "__main__":
    unittest.main()
