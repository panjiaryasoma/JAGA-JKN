from __future__ import annotations

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
    "demo_analisis_dan_validasi.py",
]


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
        for script in SCRIPTS[:-1]:
            subprocess.run([sys.executable, str(HERE / script)], env=env, check=True, capture_output=True, text=True)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_powerbi_consumes_curated_evidence(self):
        text = (HERE / "prepare_powerbi_dataset.py").read_text(encoding="utf-8")
        self.assertIn("curated_kepatuhan_evidence.csv", text)
        self.assertNotIn("C:\\Users\\", text)

    def test_spouse_is_not_an_exemption_signal(self):
        for name in ["generate_raw_dataset_bpjs.py", "pipeline_cleansing_dan_disambiguasi.py"]:
            text = (HERE / name).read_text(encoding="utf-8").lower()
            self.assertNotIn("gap_setelah_pasangan", text)
            self.assertNotIn("legal exemption", text)

    def test_system_recommendations_stop_at_human_review(self):
        curated = pd.read_csv(self.data_dir / "curated_kepatuhan_evidence.csv")
        allowed = {"NO_MATERIAL_DISCREPANCY", "LOW_STRENGTH_SIGNAL", "PRIORITIZE_HUMAN_REVIEW", "EVIDENCE_ENRICHMENT_REQUIRED", "INSUFFICIENT_OR_CONFLICTING_EVIDENCE"}
        self.assertTrue(set(curated["human_review_recommendation"]).issubset(allowed))

    def test_risk_strength_and_evidence_quality_are_separate(self):
        curated = pd.read_csv(self.data_dir / "curated_kepatuhan_evidence.csv")
        self.assertIn("risk_strength", curated.columns)
        self.assertIn("evidence_quality", curated.columns)
        self.assertNotEqual(curated["risk_strength"].name, curated["evidence_quality"].name)

    def test_low_quality_high_risk_never_auto_escalates(self):
        curated = pd.read_csv(self.data_dir / "curated_kepatuhan_evidence.csv")
        subset = curated[(curated["risk_strength"] == "HIGH") & (curated["evidence_quality"] == "LOW")]
        if not subset.empty:
            self.assertTrue(subset["decision_state"].eq("ABSTAIN").all())

    def test_policy_is_explicitly_pending_b2(self):
        curated = pd.read_csv(self.data_dir / "curated_kepatuhan_evidence.csv")
        self.assertTrue(curated["policy_rule_id"].eq("POLICY-PENDING-B2").all())
        self.assertTrue(curated["policy_status"].str.contains("B2_POLICY_NOT_AUTHORIZED").all())

    def test_synthetic_kpis_are_labeled(self):
        fact = pd.read_csv(self.powerbi_dir / "data" / "Fact_Risk_Evidence.csv")
        self.assertTrue(fact["exposure_label"].eq("SIMULATED_ESTIMATE__NOT_EMPIRICAL_LOSS").all())

    def test_sector_dimension_has_no_empirical_risk_verdict(self):
        sector = pd.read_csv(self.powerbi_dir / "data" / "Dim_Sektor_KBLI.csv")
        self.assertTrue(sector["sector_prior_status"].eq("NO_EMPIRICAL_PRIOR__DO_NOT_INFER_RISK_FROM_SECTOR_ALONE").all())

    def test_ml_dataset_is_candidate_not_training_ready(self):
        candidate = pd.read_csv(self.data_dir / "dataset_candidate_ml_audit.csv")
        self.assertTrue(candidate["ml_status"].str.contains("CANDIDATE_ONLY").all())
        self.assertFalse((self.data_dir / "dataset_intelijen_kepatuhan_ml.csv").exists())

    def test_end_to_end_validator_passes(self):
        result = subprocess.run(
            [sys.executable, str(HERE / "demo_analisis_dan_validasi.py")],
            env=self.env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("ML TRAINING READINESS: NOT CERTIFIED", result.stdout)


if __name__ == "__main__":
    unittest.main()
