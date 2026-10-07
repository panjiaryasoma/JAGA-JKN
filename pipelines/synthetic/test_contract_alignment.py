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

    def test_empty_reference_worker_set_is_not_valid_evidence(self):
        with self.assertRaises(ValueError):
            CURATION.parse_worker_set("[]")

    def test_malformed_worker_evidence_cannot_normalize(self):
        state, reason = CURATION.derive_registration_state(
            missing_worker_count=0,
            unexpected_worker_count=0,
            evidence_valid=False,
            evidence_quality="LOW",
            explanation_present=False,
        )
        self.assertEqual(state, "ABSTAIN")
        self.assertEqual(reason, "INVALID_OR_MISSING_REGISTRATION_EVIDENCE")

    def test_invalid_quality_with_no_registration_gap_cannot_normalize(self):
        state, reason = CURATION.derive_registration_state(
            missing_worker_count=0,
            unexpected_worker_count=0,
            evidence_valid=True,
            evidence_quality="UNKNOWN",
            explanation_present=False,
        )
        self.assertEqual((state, reason), ("ABSTAIN", "INVALID_OR_UNKNOWN_EVIDENCE_QUALITY"))

    def test_invalid_quality_with_no_wage_gap_cannot_normalize(self):
        state, reason = CURATION.derive_wage_state(
            wage_discrepancy_signal_rp=0,
            evidence_valid=True,
            evidence_quality="UNKNOWN",
        )
        self.assertEqual((state, reason), ("ABSTAIN", "INVALID_OR_UNKNOWN_EVIDENCE_QUALITY"))

    def test_invalid_quality_with_no_payment_gap_cannot_normalize(self):
        state, reason = CURATION.derive_contribution_state(
            contribution_payment_evidence_gap=False,
            evidence_valid=True,
            evidence_quality="UNKNOWN",
        )
        self.assertEqual((state, reason), ("ABSTAIN", "INVALID_OR_UNKNOWN_EVIDENCE_QUALITY"))

    def test_missing_wage_evidence_cannot_normalize(self):
        state, reason = CURATION.derive_wage_state(
            wage_discrepancy_signal_rp=0,
            evidence_valid=False,
            evidence_quality="LOW",
        )
        self.assertEqual((state, reason), ("ABSTAIN", "INVALID_OR_MISSING_WAGE_EVIDENCE"))

    def test_missing_contribution_evidence_cannot_normalize(self):
        state, reason = CURATION.derive_contribution_state(
            contribution_payment_evidence_gap=False,
            evidence_valid=False,
            evidence_quality="LOW",
        )
        self.assertEqual((state, reason), ("ABSTAIN", "INVALID_OR_MISSING_CONTRIBUTION_EVIDENCE"))

    def test_medium_quality_without_apparent_gap_requires_enrichment(self):
        self.assertEqual(
            CURATION.derive_registration_state(
                missing_worker_count=0,
                unexpected_worker_count=0,
                evidence_valid=True,
                evidence_quality="MEDIUM",
                explanation_present=False,
            )[0],
            "NEEDS_ENRICHMENT",
        )
        self.assertEqual(
            CURATION.derive_wage_state(
                wage_discrepancy_signal_rp=0,
                evidence_valid=True,
                evidence_quality="MEDIUM",
            )[0],
            "NEEDS_ENRICHMENT",
        )

    def test_settlement_pending_does_not_reduce_registration_quality(self):
        registration = CURATION.registration_evidence_quality(
            worker_set_evidence_valid=True,
            source_stale=False,
            source_conflict=False,
        )
        contribution = CURATION.contribution_evidence_quality(
            payment_evidence_valid=True,
            source_stale=False,
            source_conflict=False,
            settlement_pending=True,
        )
        self.assertEqual(registration[0], "HIGH")
        self.assertEqual(contribution[0], "LOW")

    def test_worker_source_conflict_does_not_reduce_contribution_quality(self):
        registration = CURATION.registration_evidence_quality(
            worker_set_evidence_valid=True,
            source_stale=False,
            source_conflict=True,
        )
        contribution = CURATION.contribution_evidence_quality(
            payment_evidence_valid=True,
            source_stale=False,
            source_conflict=False,
            settlement_pending=False,
        )
        self.assertEqual(registration[0], "LOW")
        self.assertEqual(contribution[0], "HIGH")

    def test_wage_source_problem_does_not_reduce_registration_quality(self):
        wage = CURATION.wage_evidence_quality(
            wage_evidence_valid=True,
            source_stale=False,
            source_conflict=True,
        )
        registration = CURATION.registration_evidence_quality(
            worker_set_evidence_valid=True,
            source_stale=False,
            source_conflict=False,
        )
        self.assertEqual(wage[0], "LOW")
        self.assertEqual(registration[0], "HIGH")

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
            evidence_valid=True,
            evidence_quality="HIGH",
            explanation_present=False,
        )
        self.assertEqual((state, reason), ("REVIEW", "HUMAN_REVIEW_NO_AUTOMATED_PRIORITY"))

    def test_policy_dependent_signals_remain_fail_closed(self):
        self.assertEqual(
            CURATION.derive_wage_state(
                wage_discrepancy_signal_rp=1,
                evidence_valid=True,
                evidence_quality="HIGH",
            ),
            ("ABSTAIN", "POLICY_REQUIRED_BUT_UNRESOLVED"),
        )
        self.assertEqual(
            CURATION.derive_contribution_state(
                contribution_payment_evidence_gap=True,
                evidence_valid=True,
                evidence_quality="HIGH",
            ),
            ("ABSTAIN", "POLICY_REQUIRED_BUT_UNRESOLVED"),
        )

    def test_multi_signal_states_and_qualities_remain_independent(self):
        registration_quality = CURATION.registration_evidence_quality(
            worker_set_evidence_valid=True,
            source_stale=False,
            source_conflict=False,
        )[0]
        wage_quality = CURATION.wage_evidence_quality(
            wage_evidence_valid=True,
            source_stale=False,
            source_conflict=False,
        )[0]
        contribution_quality = CURATION.contribution_evidence_quality(
            payment_evidence_valid=True,
            source_stale=False,
            source_conflict=False,
            settlement_pending=False,
        )[0]

        registration = CURATION.derive_registration_state(
            missing_worker_count=1,
            unexpected_worker_count=0,
            evidence_valid=True,
            evidence_quality=registration_quality,
            explanation_present=False,
        )[0]
        wage = CURATION.derive_wage_state(
            wage_discrepancy_signal_rp=1,
            evidence_valid=True,
            evidence_quality=wage_quality,
        )[0]
        contribution = CURATION.derive_contribution_state(
            contribution_payment_evidence_gap=False,
            evidence_valid=True,
            evidence_quality=contribution_quality,
        )[0]

        self.assertEqual((registration, wage, contribution), ("REVIEW", "ABSTAIN", "NORMAL"))
        self.assertEqual(
            CURATION.derive_overall_review_state(registration, wage, contribution),
            "PARTIAL",
        )

    def test_seasonal_explanation_preserves_registration_discrepancy(self):
        reconciliation = CURATION.reconcile_worker_sets({"A", "B", "C"}, {"A", "B"})
        state, _ = CURATION.derive_registration_state(
            missing_worker_count=reconciliation["missing_worker_count"],
            unexpected_worker_count=reconciliation["unexpected_worker_count"],
            evidence_valid=True,
            evidence_quality="HIGH",
            explanation_present=True,
        )
        self.assertEqual(reconciliation["missing_worker_count"], 1)
        self.assertEqual(state, "NEEDS_ENRICHMENT")

    def test_curated_output_has_isolated_evidence_quality(self):
        curated = pd.read_csv(self.data_root / "curated" / "curated_kepatuhan_evidence.csv")
        self.assertNotIn("evidence_quality", curated.columns)
        self.assertTrue({
            "registration_evidence_quality",
            "wage_evidence_quality",
            "contribution_evidence_quality",
        }.issubset(curated.columns))

    def test_curated_output_has_per_signal_provenance(self):
        curated = pd.read_csv(self.data_root / "curated" / "curated_kepatuhan_evidence.csv")
        required = {
            "registration_rule_id", "registration_source_ids_json", "registration_lineage",
            "wage_rule_id", "wage_source_ids_json", "wage_lineage",
            "contribution_rule_id", "contribution_source_ids_json", "contribution_lineage",
        }
        self.assertTrue(required.issubset(curated.columns))
        self.assertTrue(curated["registration_rule_id"].eq("REG-001").all())
        self.assertTrue(curated["wage_rule_id"].eq("WAGE-001").all())
        self.assertTrue(curated["contribution_rule_id"].eq("CONTRIB-001").all())

    def test_invalid_pipeline_evidence_never_becomes_normal(self):
        curated = pd.read_csv(self.data_root / "curated" / "curated_kepatuhan_evidence.csv")
        self.assertFalse(
            (
                (~curated["worker_set_evidence_valid"].astype(bool))
                & curated["registration_signal_state"].eq("NORMAL")
            ).any()
        )
        self.assertFalse(
            (
                (~curated["wage_evidence_valid"].astype(bool))
                & curated["wage_signal_state"].eq("NORMAL")
            ).any()
        )
        self.assertFalse(
            (
                (~curated["contribution_evidence_valid"].astype(bool))
                & curated["contribution_signal_state"].eq("NORMAL")
            ).any()
        )

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
