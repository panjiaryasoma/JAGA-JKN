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
    spec.loader.exec_module(module)
    return module


CURATION = load_curation_module()


class ContractAlignmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.data_dir = Path(cls.tmp.name) / "data"
        cls.powerbi_dir = Path(cls.tmp.name) / "powerbi"
        env = os.environ.copy()
        env.update({
            "JAGA_DATA_DIR": str(cls.data_dir),
            "JAGA_POWERBI_DIR": str(cls.powerbi_dir),
            "JAGA_POWERBI_DATA_DIR": str(cls.powerbi_dir / "data"),
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

    def test_powerbi_consumes_curated_evidence(self):
        text = (HERE / "prepare_powerbi_dataset.py").read_text(encoding="utf-8")
        self.assertIn("curated_kepatuhan_evidence.csv", text)
        self.assertNotIn("C:\\Users\\", text)

    def test_spouse_is_not_an_exemption_signal(self):
        for name in [
            "generate_raw_dataset_bpjs.py",
            "pipeline_cleansing_dan_disambiguasi.py",
        ]:
            text = (HERE / name).read_text(encoding="utf-8").lower()
            self.assertNotIn("gap_setelah_pasangan", text)
            self.assertNotIn("legal exemption", text)

    def test_policy_pending_large_exposure_alone_never_causes_review(self):
        state, recommendation, strength = CURATION.derive_decision_state(
            worker_discrepancy_count=0,
            wage_discrepancy_signal_rp=0,
            contribution_payment_evidence_gap=False,
            evidence_quality="HIGH",
            explanation_present=False,
            policy_status=CURATION.POLICY_PENDING,
            synthetic_exposure_demo_rp=10**15,
        )
        self.assertEqual(state, "NORMAL")
        self.assertEqual(recommendation, "NO_MATERIAL_DISCREPANCY")
        self.assertEqual(strength, CURATION.UNSCORED)

    def test_exposure_magnitude_is_decision_invariant(self):
        common = dict(
            worker_discrepancy_count=7,
            wage_discrepancy_signal_rp=0,
            contribution_payment_evidence_gap=False,
            evidence_quality="HIGH",
            explanation_present=False,
            policy_status=CURATION.POLICY_PENDING,
        )
        low = CURATION.derive_decision_state(
            **common, synthetic_exposure_demo_rp=1
        )
        huge = CURATION.derive_decision_state(
            **common, synthetic_exposure_demo_rp=10**15
        )
        self.assertEqual(low, huge)

    def test_policy_dependent_wage_signal_abstains_when_b2_pending(self):
        state, recommendation, strength = CURATION.derive_decision_state(
            worker_discrepancy_count=0,
            wage_discrepancy_signal_rp=1,
            contribution_payment_evidence_gap=False,
            evidence_quality="HIGH",
            explanation_present=False,
            policy_status=CURATION.POLICY_PENDING,
        )
        self.assertEqual(state, "ABSTAIN")
        self.assertEqual(recommendation, "POLICY_REQUIRED_BUT_UNRESOLVED")
        self.assertEqual(strength, CURATION.UNSCORED)

    def test_policy_dependent_payment_signal_abstains_when_b2_pending(self):
        state, recommendation, _ = CURATION.derive_decision_state(
            worker_discrepancy_count=0,
            wage_discrepancy_signal_rp=0,
            contribution_payment_evidence_gap=True,
            evidence_quality="HIGH",
            explanation_present=False,
            policy_status=CURATION.POLICY_PENDING,
        )
        self.assertEqual(state, "ABSTAIN")
        self.assertEqual(recommendation, "POLICY_REQUIRED_BUT_UNRESOLVED")

    def test_low_evidence_worker_discrepancy_deterministically_abstains(self):
        state, recommendation, _ = CURATION.derive_decision_state(
            worker_discrepancy_count=10,
            wage_discrepancy_signal_rp=0,
            contribution_payment_evidence_gap=False,
            evidence_quality="LOW",
            explanation_present=False,
            policy_status=CURATION.POLICY_PENDING,
        )
        self.assertEqual(state, "ABSTAIN")
        self.assertEqual(
            recommendation, "INSUFFICIENT_OR_CONFLICTING_EVIDENCE"
        )

    def test_seasonal_explanation_preserves_discrepancy(self):
        gap, explanation = CURATION.preserve_worker_discrepancy(10, True)
        self.assertEqual(gap, 10)
        self.assertEqual(explanation, "PROJECT_OR_SEASON_END_SYNTHETIC")

    def test_explanation_triggers_enrichment_without_zeroing_gap(self):
        state, recommendation, _ = CURATION.derive_decision_state(
            worker_discrepancy_count=10,
            wage_discrepancy_signal_rp=0,
            contribution_payment_evidence_gap=False,
            evidence_quality="HIGH",
            explanation_present=True,
            policy_status=CURATION.POLICY_PENDING,
        )
        self.assertEqual(state, "NEEDS_ENRICHMENT")
        self.assertEqual(recommendation, "EVIDENCE_ENRICHMENT_REQUIRED")

    def test_worker_discrepancy_can_be_surfaced_without_priority_score(self):
        state, recommendation, strength = CURATION.derive_decision_state(
            worker_discrepancy_count=1,
            wage_discrepancy_signal_rp=0,
            contribution_payment_evidence_gap=False,
            evidence_quality="HIGH",
            explanation_present=False,
            policy_status=CURATION.POLICY_PENDING,
        )
        self.assertEqual(state, "REVIEW")
        self.assertEqual(recommendation, "HUMAN_REVIEW_NO_AUTOMATED_PRIORITY")
        self.assertEqual(strength, CURATION.UNSCORED)

    def test_all_curated_risk_strength_is_unscored(self):
        curated = pd.read_csv(
            self.data_dir / "curated_kepatuhan_evidence.csv"
        )
        self.assertTrue(
            curated["risk_strength"].eq(
                "UNSCORED__THRESHOLDS_NOT_AUTHORIZED"
            ).all()
        )

    def test_curated_discrepancy_is_mathematically_preserved(self):
        curated = pd.read_csv(
            self.data_dir / "curated_kepatuhan_evidence.csv"
        )
        expected = (
            curated["reference_worker_count"]
            - curated["observed_registered_worker_count"]
        ).clip(lower=0)
        self.assertTrue(
            curated["worker_discrepancy_count"].eq(expected).all()
        )

    def test_synthetic_exposure_is_visualization_only(self):
        curated = pd.read_csv(
            self.data_dir / "curated_kepatuhan_evidence.csv"
        )
        self.assertTrue(
            curated["exposure_decision_role"].eq(
                "VISUALIZATION_ONLY__MUST_NOT_INFLUENCE_DECISION"
            ).all()
        )

    def test_no_invented_threshold_scoring_function_remains(self):
        text = (
            HERE / "pipeline_cleansing_dan_disambiguasi.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("def risk_strength(", text)
        self.assertNotIn("5_000_000", text)
        self.assertNotIn("500_000", text)
        self.assertNotIn("duration_hint", text)

    def test_system_recommendations_stop_at_human_interpretation(self):
        curated = pd.read_csv(
            self.data_dir / "curated_kepatuhan_evidence.csv"
        )
        allowed = {
            "NO_MATERIAL_DISCREPANCY",
            "POLICY_REQUIRED_BUT_UNRESOLVED",
            "INSUFFICIENT_OR_CONFLICTING_EVIDENCE",
            "EVIDENCE_ENRICHMENT_REQUIRED",
            "HUMAN_REVIEW_NO_AUTOMATED_PRIORITY",
        }
        self.assertTrue(
            set(curated["human_review_recommendation"]).issubset(allowed)
        )

    def test_ml_dataset_is_candidate_not_training_ready(self):
        candidate = pd.read_csv(
            self.data_dir / "dataset_candidate_ml_audit.csv"
        )
        self.assertTrue(
            candidate["ml_status"].str.contains("CANDIDATE_ONLY").all()
        )
        self.assertFalse(
            (self.data_dir / "dataset_intelijen_kepatuhan_ml.csv").exists()
        )

    def test_end_to_end_validator_passes(self):
        result = subprocess.run(
            [sys.executable, str(HERE / "demo_analisis_dan_validasi.py")],
            env=self.env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            result.returncode,
            0,
            result.stdout + result.stderr,
        )
        self.assertIn("MERGE READINESS: NOT CLAIMED", result.stdout)


if __name__ == "__main__":
    unittest.main()
