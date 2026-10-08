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

    def test_b2_unresolved_zero_wage_gap_cannot_normalize(self):
        self.assertEqual(
            CURATION.derive_wage_state(
                wage_discrepancy_signal_rp=0,
                evidence_valid=True,
                evidence_quality="HIGH",
            ),
            ("ABSTAIN", "POLICY_REQUIRED_BUT_UNRESOLVED"),
        )

    def test_b2_unresolved_no_payment_gap_cannot_normalize(self):
        self.assertEqual(
            CURATION.derive_contribution_state(
                contribution_payment_evidence_gap=False,
                evidence_valid=True,
                evidence_quality="HIGH",
            ),
            ("ABSTAIN", "POLICY_REQUIRED_BUT_UNRESOLVED"),
        )

    def test_missing_registration_source_id_invalidates_evidence(self):
        source = CURATION.validate_source_metadata(
            source_ids=(None, None),
            freshness="CURRENT",
            conflict=False,
        )
        self.assertFalse(source["valid"])
        self.assertIn("MISSING_OR_INVALID_SOURCE_ID", source["reasons"])

    def test_missing_source_freshness_invalidates_evidence(self):
        source = CURATION.validate_source_metadata(
            source_ids=("A", "B"),
            freshness=None,
            conflict=False,
        )
        self.assertFalse(source["valid"])
        self.assertIn("MISSING_OR_INVALID_SOURCE_FRESHNESS", source["reasons"])

    def test_missing_source_conflict_state_invalidates_evidence(self):
        source = CURATION.validate_source_metadata(
            source_ids=("A", "B"),
            freshness="CURRENT",
            conflict=None,
        )
        self.assertFalse(source["valid"])
        self.assertIn("MISSING_OR_INVALID_SOURCE_CONFLICT_STATE", source["reasons"])

    def test_missing_provenance_cannot_produce_registration_review(self):
        source = CURATION.validate_source_metadata(
            source_ids=(None, None),
            freshness="CURRENT",
            conflict=False,
        )
        quality, _ = CURATION.registration_evidence_quality(
            evidence_valid=bool(source["valid"]),
            source_stale=bool(source["source_stale"]),
            source_conflict=bool(source["source_conflict"]),
            validity_reasons=source["reasons"],
        )
        state, _ = CURATION.derive_registration_state(
            missing_worker_count=1,
            unexpected_worker_count=0,
            evidence_valid=bool(source["valid"]),
            evidence_quality=quality,
            explanation_present=False,
        )
        self.assertEqual(state, "ABSTAIN")

    def test_wage_discrepancy_mismatch_invalidates_evidence(self):
        result = CURATION.validate_wage_semantics(
            reference_wage=10_000_000,
            observed_wage=5_000_000,
            supplied_discrepancy=0,
        )
        self.assertFalse(result["valid"])
        self.assertEqual(result["derived_discrepancy"], 5_000_000)
        self.assertEqual(result["reason"], "INCONSISTENT_WAGE_DISCREPANCY")

    def test_wage_discrepancy_consistent_pair_is_valid(self):
        result = CURATION.validate_wage_semantics(
            reference_wage=10_000_000,
            observed_wage=5_000_000,
            supplied_discrepancy=5_000_000,
        )
        self.assertTrue(result["valid"])
        self.assertEqual(result["derived_discrepancy"], 5_000_000)

    def test_paid_on_time_without_bank_evidence_is_invalid(self):
        result = CURATION.validate_payment_semantics(
            payment_state="PAID_ON_TIME",
            bank_state="NO_PAYMENT_EVIDENCE",
            settlement_delay_flag=False,
            payer_timestamp="2026-01-09 10:00:00",
            bank_timestamp=None,
        )
        self.assertFalse(result["valid"])
        self.assertEqual(result["reason"], "INCONSISTENT_PAYMENT_STATE_COMBINATION")

    def test_unpaid_cannot_be_rescued_by_settlement_flag(self):
        result = CURATION.validate_payment_semantics(
            payment_state="UNPAID",
            bank_state="NO_PAYMENT_EVIDENCE",
            settlement_delay_flag=True,
            payer_timestamp=None,
            bank_timestamp=None,
        )
        self.assertFalse(result["valid"])
        self.assertEqual(result["validated_payment_state"], "UNKNOWN")

    def test_valid_payment_combinations_are_accepted(self):
        cases = [
            ("PAID_ON_TIME", "POSTED_ON_TIME", False, "2026-01-09 10:00:00", "2026-01-09 10:00:00"),
            ("PAID_ON_TIME", "POSTED_NEXT_DAY", True, "2026-01-10 23:10:00", "2026-01-11 00:10:00"),
            ("PAYMENT_PENDING", "SETTLEMENT_PENDING", False, "2026-01-10 16:00:00", None),
            ("UNPAID", "NO_PAYMENT_EVIDENCE", False, None, None),
        ]
        for case in cases:
            with self.subTest(case=case):
                self.assertTrue(
                    CURATION.validate_payment_semantics(
                        payment_state=case[0],
                        bank_state=case[1],
                        settlement_delay_flag=case[2],
                        payer_timestamp=case[3],
                        bank_timestamp=case[4],
                    )["valid"]
                )

    def test_malformed_worker_evidence_cannot_normalize(self):
        state, reason = CURATION.derive_registration_state(
            missing_worker_count=0,
            unexpected_worker_count=0,
            evidence_valid=False,
            evidence_quality="LOW",
            explanation_present=False,
        )
        self.assertEqual((state, reason), ("ABSTAIN", "INVALID_OR_MISSING_REGISTRATION_EVIDENCE"))

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

    def test_source_domains_remain_isolated(self):
        registration = CURATION.registration_evidence_quality(
            evidence_valid=True,
            source_stale=False,
            source_conflict=False,
        )[0]
        contribution = CURATION.contribution_evidence_quality(
            evidence_valid=True,
            source_stale=False,
            source_conflict=False,
            settlement_pending=True,
        )[0]
        self.assertEqual(registration, "HIGH")
        self.assertEqual(contribution, "LOW")

    def test_equal_count_different_worker_sets_are_detected(self):
        result = CURATION.reconcile_worker_sets({"A", "B", "C"}, {"A", "B", "D"})
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
            reference_authority_verified=True,
            applicable_version_verified=True,
        )
        self.assertEqual((state, reason), ("REVIEW", "HUMAN_REVIEW_NO_AUTOMATED_PRIORITY"))

    def test_policy_dependent_positive_signals_remain_fail_closed(self):
        self.assertEqual(
            CURATION.derive_wage_state(
                wage_discrepancy_signal_rp=1,
                evidence_valid=True,
                evidence_quality="HIGH",
            )[0],
            "ABSTAIN",
        )
        self.assertEqual(
            CURATION.derive_contribution_state(
                contribution_payment_evidence_gap=True,
                evidence_valid=True,
                evidence_quality="HIGH",
            )[0],
            "ABSTAIN",
        )

    def test_mixed_signal_states_remain_independent(self):
        registration = CURATION.derive_registration_state(
            missing_worker_count=1,
            unexpected_worker_count=0,
            evidence_valid=True,
            evidence_quality="HIGH",
            explanation_present=False,
            reference_authority_verified=True,
            applicable_version_verified=True,
        )[0]
        wage = CURATION.derive_wage_state(
            wage_discrepancy_signal_rp=1,
            evidence_valid=True,
            evidence_quality="HIGH",
        )[0]
        contribution = CURATION.derive_contribution_state(
            contribution_payment_evidence_gap=False,
            evidence_valid=True,
            evidence_quality="HIGH",
        )[0]
        self.assertEqual((registration, wage, contribution), ("REVIEW", "ABSTAIN", "ABSTAIN"))
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
            reference_authority_verified=True,
            applicable_version_verified=True,
        )
        self.assertEqual(reconciliation["missing_worker_count"], 1)
        self.assertEqual(state, "NEEDS_ENRICHMENT")

    def test_curated_output_has_required_source_metadata_validity(self):
        curated = pd.read_csv(self.data_root / "curated" / "curated_kepatuhan_evidence.csv")
        required = {
            "registration_source_metadata_valid",
            "wage_source_metadata_valid",
            "contribution_source_metadata_valid",
        }
        self.assertTrue(required.issubset(curated.columns))
        self.assertTrue(curated[list(required)].astype(bool).all().all())

    def test_curated_output_cross_field_consistency_is_valid(self):
        curated = pd.read_csv(self.data_root / "curated" / "curated_kepatuhan_evidence.csv")
        self.assertTrue(curated["wage_semantic_consistency_valid"].astype(bool).all())
        self.assertTrue(curated["payment_semantic_consistency_valid"].astype(bool).all())

    def test_curated_policy_dependent_states_never_normal_while_b2_false(self):
        curated = pd.read_csv(self.data_root / "curated" / "curated_kepatuhan_evidence.csv")
        self.assertTrue(curated["trusted_policy_context_authorized"].astype(bool).eq(False).all())
        self.assertFalse(curated["wage_signal_state"].eq("NORMAL").any())
        self.assertFalse(curated["contribution_signal_state"].eq("NORMAL").any())

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



class Pass5BoundaryRegressionTests(unittest.TestCase):
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

    def test_registration_authority_unresolved_blocks_review(self):
        state, reason = CURATION.derive_registration_state(
            missing_worker_count=1,
            unexpected_worker_count=0,
            evidence_valid=True,
            evidence_quality="HIGH",
            explanation_present=False,
        )
        self.assertEqual(
            (state, reason),
            ("ABSTAIN", "REFERENCE_AUTHORITY_OR_RULE_VERSION_UNRESOLVED"),
        )

    def test_registration_authority_unresolved_blocks_normal_too(self):
        state, reason = CURATION.derive_registration_state(
            missing_worker_count=0,
            unexpected_worker_count=0,
            evidence_valid=True,
            evidence_quality="HIGH",
            explanation_present=False,
        )
        self.assertEqual(
            (state, reason),
            ("ABSTAIN", "REFERENCE_AUTHORITY_OR_RULE_VERSION_UNRESOLVED"),
        )

    def test_registration_trusted_context_is_not_row_authorized(self):
        context = CURATION.trusted_registration_authority_context()
        self.assertFalse(context["reference_authority_verified"])
        self.assertFalse(context["applicable_version_verified"])
        self.assertEqual(context["reference_authority"], "UNRESOLVED")
        self.assertEqual(context["rule_version"], "UNVERIFIED")
        self.assertEqual(
            context["context_source"],
            "TRUSTED_IMPLEMENTATION_CONTEXT__NOT_ROW_DATA",
        )

    def test_spoofed_source_id_does_not_establish_registration_authority(self):
        source = CURATION.validate_source_metadata(
            source_ids=("trust-me-bro-ref", "whatever-observed"),
            freshness="CURRENT",
            conflict=False,
        )
        self.assertTrue(source["valid"])
        state, _ = CURATION.derive_registration_state(
            missing_worker_count=1,
            unexpected_worker_count=0,
            evidence_valid=True,
            evidence_quality="HIGH",
            explanation_present=False,
        )
        self.assertEqual(state, "ABSTAIN")

    def test_invalid_timestamp_strings_are_rejected(self):
        result = CURATION.validate_payment_semantics(
            payment_state="PAID_ON_TIME",
            bank_state="POSTED_ON_TIME",
            settlement_delay_flag=False,
            payer_timestamp="banana",
            bank_timestamp="potato",
        )
        self.assertFalse(result["valid"])
        self.assertEqual(result["reason"], "INVALID_PAYMENT_TIMESTAMP_FORMAT")

    def test_posted_next_day_cannot_happen_before_payer(self):
        result = CURATION.validate_payment_semantics(
            payment_state="PAID_ON_TIME",
            bank_state="POSTED_NEXT_DAY",
            settlement_delay_flag=True,
            payer_timestamp="2026-01-11 23:10:00",
            bank_timestamp="2026-01-10 00:10:00",
        )
        self.assertFalse(result["valid"])
        self.assertEqual(result["reason"], "INCONSISTENT_PAYMENT_CHRONOLOGY")

    def test_posted_next_day_requires_next_calendar_day(self):
        result = CURATION.validate_payment_semantics(
            payment_state="PAID_ON_TIME",
            bank_state="POSTED_NEXT_DAY",
            settlement_delay_flag=True,
            payer_timestamp="2026-01-10 10:00:00",
            bank_timestamp="2026-01-10 11:00:00",
        )
        self.assertFalse(result["valid"])
        self.assertEqual(result["reason"], "INCONSISTENT_PAYMENT_DATE_RELATIONSHIP")

    def test_posted_on_time_requires_same_calendar_day(self):
        result = CURATION.validate_payment_semantics(
            payment_state="PAID_ON_TIME",
            bank_state="POSTED_ON_TIME",
            settlement_delay_flag=False,
            payer_timestamp="2026-01-10 23:59:00",
            bank_timestamp="2026-01-11 00:01:00",
        )
        self.assertFalse(result["valid"])
        self.assertEqual(result["reason"], "INCONSISTENT_PAYMENT_DATE_RELATIONSHIP")

    def test_nan_explanation_indicator_is_invalid(self):
        result = CURATION.validate_explanation_metadata(
            indicator=float("nan"),
            reason=float("nan"),
        )
        self.assertFalse(result["valid"])
        self.assertEqual(result["validation_reason"], "INVALID_EXPLANATION_INDICATOR")

    def test_string_false_explanation_indicator_is_invalid(self):
        result = CURATION.validate_explanation_metadata(
            indicator="False",
            reason="NONE",
        )
        self.assertFalse(result["valid"])
        self.assertEqual(result["validation_reason"], "INVALID_EXPLANATION_INDICATOR")

    def test_true_explanation_requires_allowed_reason(self):
        result = CURATION.validate_explanation_metadata(
            indicator=True,
            reason=None,
        )
        self.assertFalse(result["valid"])
        self.assertEqual(
            result["validation_reason"],
            "MISSING_OR_INVALID_EXPLANATION_REASON",
        )

    def test_false_explanation_rejects_substantive_reason(self):
        result = CURATION.validate_explanation_metadata(
            indicator=False,
            reason="PROJECT_OR_SEASON_END_SYNTHETIC",
        )
        self.assertFalse(result["valid"])
        self.assertEqual(
            result["validation_reason"],
            "EXPLANATION_REASON_WITH_FALSE_INDICATOR",
        )

    def test_valid_explanation_can_enrich_without_mutating_discrepancy(self):
        metadata = CURATION.validate_explanation_metadata(
            indicator=True,
            reason="PROJECT_OR_SEASON_END_SYNTHETIC",
        )
        reconciliation = CURATION.reconcile_worker_sets({"A", "B", "C"}, {"A", "B"})
        state, _ = CURATION.derive_registration_state(
            missing_worker_count=reconciliation["missing_worker_count"],
            unexpected_worker_count=reconciliation["unexpected_worker_count"],
            evidence_valid=True,
            evidence_quality="HIGH",
            explanation_present=bool(metadata["present"]),
            reference_authority_verified=True,
            applicable_version_verified=True,
        )
        self.assertTrue(metadata["valid"])
        self.assertEqual(reconciliation["missing_worker_count"], 1)
        self.assertEqual(state, "NEEDS_ENRICHMENT")

    def test_generated_curated_registration_stays_abstain_until_authority_verified(self):
        curated = pd.read_csv(
            self.data_root / "curated" / "curated_kepatuhan_evidence.csv"
        )
        self.assertTrue(
            curated["registration_reference_authority_verified"]
            .astype(bool)
            .eq(False)
            .all()
        )
        self.assertTrue(
            curated["registration_applicable_version_verified"]
            .astype(bool)
            .eq(False)
            .all()
        )
        self.assertFalse(
            curated["registration_signal_state"].isin(["NORMAL", "REVIEW"]).any()
        )

    def test_generated_explanation_metadata_is_strictly_valid(self):
        curated = pd.read_csv(
            self.data_root / "curated" / "curated_kepatuhan_evidence.csv"
        )
        self.assertTrue(
            curated["registration_explanation_metadata_valid"].astype(bool).all()
        )


if __name__ == "__main__":
    unittest.main()
