from __future__ import annotations

import importlib.util
import inspect
import json
import os
import subprocess
import sys
import tempfile
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import patch

import pandas as pd

HERE = Path(__file__).resolve().parent
SCRIPTS = [
    "generate_dataset_bpjs.py",
    "generate_raw_dataset_bpjs.py",
    "pipeline_cleansing_dan_disambiguasi.py",
    "prepare_powerbi_dataset.py",
]

_TMP = None
DATA_ROOT = None
POWERBI_ROOT = None
ENV = None


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.path.insert(0, str(HERE))
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        if sys.modules.get(name) is module:
            del sys.modules[name]
        raise
    finally:
        sys.path.remove(str(HERE))
    return module


CURATION = _load_module(
    "jaga_curation",
    "pipeline_cleansing_dan_disambiguasi.py",
)
TRUSTED = sys.modules["trusted_context"]
POWERBI = _load_module("jaga_powerbi_presentation", "prepare_powerbi_dataset.py")


def setUpModule():
    global _TMP, DATA_ROOT, POWERBI_ROOT, ENV
    _TMP = tempfile.TemporaryDirectory()
    DATA_ROOT = Path(_TMP.name) / "data" / "synthetic"
    POWERBI_ROOT = Path(_TMP.name) / "powerbi"
    ENV = os.environ.copy()
    ENV.update({
        "JAGA_DATA_ROOT": str(DATA_ROOT),
        "JAGA_POWERBI_DIR": str(POWERBI_ROOT),
        "JAGA_POWERBI_DATA_DIR": str(POWERBI_ROOT / "data"),
        "JAGA_N_COMPANIES": "20",
        "JAGA_SYNTHETIC_SEED": "42",
    })
    for script in SCRIPTS:
        subprocess.run(
            [sys.executable, str(HERE / script)],
            env=ENV,
            check=True,
            capture_output=True,
            text=True,
        )


def tearDownModule():
    if _TMP is not None:
        _TMP.cleanup()


class AuthorityInvariantTests(unittest.TestCase):
    def test_contexts_are_frozen(self):
        with self.assertRaises(FrozenInstanceError):
            TRUSTED.REGISTRATION_AUTHORITY_CONTEXT.authorized = True

    def test_all_sandbox_contexts_are_unresolved(self):
        for context in (
            TRUSTED.REGISTRATION_AUTHORITY_CONTEXT,
            TRUSTED.WAGE_POLICY_CONTEXT,
            TRUSTED.CONTRIBUTION_POLICY_CONTEXT,
        ):
            self.assertFalse(context.authorized)
            self.assertFalse(context.applicable_period_verified)
            self.assertEqual(context.rule_version, "UNVERIFIED")

    def test_public_evaluators_accept_only_evidence(self):
        for fn in (
            CURATION.evaluate_registration_rule,
            CURATION.evaluate_wage_rule,
            CURATION.evaluate_contribution_rule,
        ):
            self.assertEqual(list(inspect.signature(fn).parameters), ["evidence"])

    def test_row_cannot_self_authorize(self):
        evidence = {
            "valid": True,
            "quality": "HIGH",
            "discrepancy_detected": True,
            "authority": "AUTHORIZED",
            "rule_version": "FINAL",
        }
        self.assertEqual(
            CURATION.evaluate_registration_rule(evidence)[0],
            "ABSTAIN",
        )

    def test_registration_context_false_always_abstains(self):
        for discrepancy in (False, True):
            result, reason = CURATION.evaluate_registration_rule({
                "valid": True,
                "quality": "HIGH",
                "discrepancy_detected": discrepancy,
            })
            self.assertEqual(result, "ABSTAIN")
            self.assertEqual(reason, CURATION.AUTHORITY_UNRESOLVED_REASON)

    def test_b2_false_wage_always_abstains(self):
        for discrepancy in (False, True):
            result, reason = CURATION.evaluate_wage_rule({
                "valid": True,
                "quality": "HIGH",
                "discrepancy_detected": discrepancy,
            })
            self.assertEqual(result, "ABSTAIN")
            self.assertEqual(reason, CURATION.POLICY_UNRESOLVED_REASON)

    def test_b2_false_contribution_always_abstains(self):
        for discrepancy in (False, True):
            result, reason = CURATION.evaluate_contribution_rule({
                "valid": True,
                "quality": "HIGH",
                "discrepancy_detected": discrepancy,
            })
            self.assertEqual(result, "ABSTAIN")
            self.assertEqual(reason, CURATION.POLICY_UNRESOLVED_REASON)


class RuleEnumInvariantTests(unittest.TestCase):
    @staticmethod
    def _authorized_context():
        return TRUSTED.RuleAuthorityContext(
            authorized=True,
            authority_id="TEST_ONLY",
            rule_version="TEST-V1",
            applicable_period_verified=True,
            effective_from="2026-01",
            effective_to="2026-12",
            source_ids=("TEST-SOURCE",),
        )

    def test_registration_rule_exact_enum(self):
        context = self._authorized_context()
        with patch.object(TRUSTED, 'TRUSTED_RULE_AUTHORITY_REGISTRY', (context,)):
            consistent = CURATION._evaluate_registration_rule_with_context(
                {"valid": True, "quality": "HIGH", "discrepancy_detected": False, "evaluated_period": "2026-06"},
                context,
            )[0]
            potential = CURATION._evaluate_registration_rule_with_context(
                {"valid": True, "quality": "HIGH", "discrepancy_detected": True, "evaluated_period": "2026-06"},
                context,
            )[0]
            self.assertEqual(consistent, "CONSISTENT")
            self.assertEqual(potential, "POTENTIAL_REGISTRATION_GAP")
            self.assertNotIn(consistent, CURATION.REVIEW_STATES)
            self.assertNotIn(potential, CURATION.REVIEW_STATES)

    def test_wage_rule_exact_enum(self):
        context = self._authorized_context()
        with patch.object(TRUSTED, 'TRUSTED_RULE_AUTHORITY_REGISTRY', (context,)):
            self.assertEqual(
                CURATION._evaluate_wage_rule_with_context(
                    {"valid": True, "quality": "HIGH", "discrepancy_detected": True, "evaluated_period": "2026-06"},
                    context,
                )[0],
                "POTENTIAL_WAGE_DIVERGENCE",
            )

    def test_contribution_rule_exact_enum(self):
        context = self._authorized_context()
        with patch.object(TRUSTED, 'TRUSTED_RULE_AUTHORITY_REGISTRY', (context,)):
            self.assertEqual(
                CURATION._evaluate_contribution_rule_with_context(
                    {"valid": True, "quality": "HIGH", "discrepancy_detected": True, "evaluated_period": "2026-06"},
                    context,
                )[0],
                "POTENTIAL_CONTRIBUTION_IRREGULARITY",
            )

    def test_invalid_evidence_rule_abstains_when_context_authorized(self):
        context = self._authorized_context()
        with patch.object(TRUSTED, 'TRUSTED_RULE_AUTHORITY_REGISTRY', (context,)):
            result, reason = CURATION._evaluate_registration_rule_with_context(
                {"valid": False, "quality": "LOW", "discrepancy_detected": None, "evaluated_period": "2026-06"},
                context,
            )
            self.assertEqual((result, reason), ("ABSTAIN", CURATION.EVIDENCE_INVALID_REASON))


class AuthorityActivationBoundaryTests(unittest.TestCase):
    @staticmethod
    def _context(**changes):
        from dataclasses import replace
        return replace(RuleEnumInvariantTests._authorized_context(), **changes)

    def test_python_loader_class_identity(self):
        self.assertIs(CURATION.RuleAuthorityContext, TRUSTED.RuleAuthorityContext)

    def test_valid_context_inclusive_period_boundaries(self):
        ctx = self._context()
        self.assertFalse(TRUSTED.authority_context_ready(ctx, "2026-06"))
        with patch.object(TRUSTED, "TRUSTED_RULE_AUTHORITY_REGISTRY", (ctx,)):
            for period in ("2026-01", "2026-06", "2026-12"):
                self.assertTrue(TRUSTED.authority_context_ready(ctx, period))

    def test_invalid_authority_fields_fail_closed(self):
        valid_context = self._context()
        invalid = [
            {"authority_id": "B2_UNRESOLVED"},
            {"authority_id": "B2_UNVERIFIED"},
            {"authority_id": "PENDING_B2"},
            {"authority_id": "FAKE_AUTHORITY"},
            {"authority_id": "UNREGISTERED_AUTHORITY"},
            {"source_ids": ("FAKE-SOURCE",)},
            {"rule_version": "B2_UNVERIFIED"},
            {"authority_id": "UNRESOLVED"},
            {"rule_version": "UNVERIFIED"},
            {"source_ids": ()},
            {"source_ids": ("",)},
            {"effective_from": None},
            {"effective_to": None},
            {"effective_from": "2026-13"},
            {"effective_to": "2025-12"},
            {"authorized": False},
            {"applicable_period_verified": False},
        ]
        for change in invalid:
            with self.subTest(change=change):
                ctx = self._context(**change)
                with patch.object(TRUSTED, "TRUSTED_RULE_AUTHORITY_REGISTRY", (valid_context,)):
                    self.assertFalse(TRUSTED.authority_context_ready(ctx, "2026-06"))
                for fn in (
                    CURATION._evaluate_registration_rule_with_context,
                    CURATION._evaluate_wage_rule_with_context,
                    CURATION._evaluate_contribution_rule_with_context,
                ):
                    result, _ = fn(
                        {"valid": True, "quality": "HIGH",
                         "discrepancy_detected": True, "evaluated_period": "2026-06"},
                        ctx,
                    )
                    self.assertEqual(result, "ABSTAIN")

    def test_outside_period_and_missing_period_abstains(self):
        ctx = self._context()
        for period in ("2025-12", "2027-01", "2026-00", "invalid", None):
            with self.subTest(period=period):
                with patch.object(TRUSTED, "TRUSTED_RULE_AUTHORITY_REGISTRY", (ctx,)):
                    self.assertFalse(TRUSTED.authority_context_ready(ctx, period))
                result, _ = CURATION._evaluate_registration_rule_with_context(
                    {"valid": True, "quality": "HIGH",
                     "discrepancy_detected": False, "evaluated_period": period},
                    ctx,
                )
                self.assertEqual(result, "ABSTAIN")


class TrustedRegistryHardeningTests(unittest.TestCase):
    def test_production_registry_empty_and_authority_not_ready(self):
        self.assertEqual(TRUSTED.TRUSTED_RULE_AUTHORITY_REGISTRY, ())
        context = RuleEnumInvariantTests._authorized_context()
        self.assertFalse(TRUSTED.authority_context_ready(context, "2026-06"))

    def test_spoofed_placeholder_denied_even_when_injected_into_registry(self):
        from dataclasses import replace
        valid = RuleEnumInvariantTests._authorized_context()
        for authority in ("B2_UNRESOLVED", "B2_UNVERIFIED", "PENDING_B2"):
            with self.subTest(authority=authority):
                forged = replace(valid, authority_id=authority)
                with patch.object(
                    TRUSTED, "TRUSTED_RULE_AUTHORITY_REGISTRY", (forged,)
                ):
                    self.assertFalse(
                        TRUSTED.authority_context_ready(forged, "2026-06")
                    )

    def test_forged_source_never_matches_known_registry(self):
        from dataclasses import replace
        original = RuleEnumInvariantTests._authorized_context()
        tampered = replace(original, source_ids=("TRUST-ME-BRO-REF",))
        with patch.object(
            TRUSTED, "TRUSTED_RULE_AUTHORITY_REGISTRY", (original,)
        ):
            self.assertFalse(
                TRUSTED.authority_context_ready(tampered, "2026-06")
            )

    def test_unregistered_plausible_authority_denied(self):
        from dataclasses import replace
        original = RuleEnumInvariantTests._authorized_context()
        tampered = replace(original, authority_id="OFFICIAL_SOMETHING")
        with patch.object(
            TRUSTED, "TRUSTED_RULE_AUTHORITY_REGISTRY", (original,)
        ):
            self.assertFalse(
                TRUSTED.authority_context_ready(tampered, "2026-06")
            )


class WorkflowMappingInvariantTests(unittest.TestCase):
    def test_consistent_maps_normal(self):
        state, _ = CURATION.map_registration_review_state(
            rule_result="CONSISTENT",
            rule_reason="NO_OBSERVED_REGISTRATION_DISCREPANCY",
            evidence_valid=True,
            evidence_quality="HIGH",
            legitimate_explanation_present=False,
        )
        self.assertEqual(state, "NORMAL")

    def test_registration_potential_maps_review(self):
        state, _ = CURATION.map_registration_review_state(
            rule_result="POTENTIAL_REGISTRATION_GAP",
            rule_reason="OBSERVED_SET_DISCREPANCY",
            evidence_valid=True,
            evidence_quality="HIGH",
            legitimate_explanation_present=False,
        )
        self.assertEqual(state, "REVIEW")

    def test_legitimate_explanation_only_changes_workflow(self):
        evidence = {
            "valid": True,
            "quality": "HIGH",
            "discrepancy_detected": True,
            "evaluated_period": "2026-06",
        }
        context = RuleEnumInvariantTests._authorized_context()
        with patch.object(TRUSTED, 'TRUSTED_RULE_AUTHORITY_REGISTRY', (context,)):
            rule_before = CURATION._evaluate_registration_rule_with_context(
                evidence,
                context,
            )
            state, _ = CURATION.map_registration_review_state(
                rule_result=rule_before[0],
                rule_reason=rule_before[1],
                evidence_valid=True,
                evidence_quality="HIGH",
                legitimate_explanation_present=True,
            )
            rule_after = CURATION._evaluate_registration_rule_with_context(
                evidence,
                context,
            )
            self.assertEqual(rule_before, rule_after)
            self.assertEqual(rule_before[0], "POTENTIAL_REGISTRATION_GAP")
            self.assertEqual(state, "NEEDS_ENRICHMENT")

    def test_authority_abstain_maps_abstain(self):
        state, _ = CURATION.map_registration_review_state(
            rule_result="ABSTAIN",
            rule_reason=CURATION.AUTHORITY_UNRESOLVED_REASON,
            evidence_valid=True,
            evidence_quality="HIGH",
            legitimate_explanation_present=False,
        )
        self.assertEqual(state, "ABSTAIN")

    def test_evidence_abstain_can_map_enrichment(self):
        state, _ = CURATION.map_wage_review_state(
            rule_result="ABSTAIN",
            rule_reason=CURATION.EVIDENCE_INVALID_REASON,
            evidence_valid=False,
            evidence_quality="LOW",
        )
        self.assertEqual(state, "NEEDS_ENRICHMENT")

    def test_partial_is_overall_only(self):
        self.assertEqual(
            CURATION.derive_overall_review_state("REVIEW", "ABSTAIN", "ABSTAIN"),
            "PARTIAL",
        )
        with self.assertRaises(ValueError):
            CURATION.derive_overall_review_state("PARTIAL", "ABSTAIN", "ABSTAIN")


class EvidenceValidityInvariantTests(unittest.TestCase):
    def test_missing_source_invalid(self):
        result = CURATION.validate_source_metadata(
            source_ids=(None, None),
            source_periods=("2026-01", "2026-01"),
            evaluated_period="2026-01",
            freshness="CURRENT",
            conflict=False,
        )
        self.assertFalse(result["valid"])

    def test_invalid_quality_domains_are_isolated(self):
        reg = CURATION._quality_from_flags(
            evidence_valid=True,
            source_stale=False,
            source_conflict=False,
        )[0]
        contrib = CURATION._quality_from_flags(
            evidence_valid=True,
            source_stale=False,
            source_conflict=False,
            extra_low_reason="PAYMENT_SETTLEMENT_PENDING",
        )[0]
        self.assertEqual(reg, "HIGH")
        self.assertEqual(contrib, "LOW")

    def test_equal_count_different_identity_is_discrepancy(self):
        result = CURATION.reconcile_worker_sets({"A", "B", "C"}, {"A", "B", "D"})
        self.assertEqual(result["reference_count"], result["observed_count"])
        self.assertEqual(result["missing_worker_ids"], ["C"])
        self.assertEqual(result["unexpected_worker_ids"], ["D"])
        self.assertFalse(result["sets_equal"])

    def test_empty_reference_set_rejected(self):
        with self.assertRaises(ValueError):
            CURATION.parse_worker_set("[]")

    def test_wage_cross_field_mismatch_invalid(self):
        result = CURATION.validate_wage_semantics(
            reference_wage=10_000_000,
            observed_wage=5_000_000,
            supplied_discrepancy=0,
        )
        self.assertFalse(result["valid"])
        self.assertEqual(result["derived_discrepancy"], 5_000_000)

    def test_explanation_indicator_is_strict_bool(self):
        for invalid in (float("nan"), "False", 0, 1):
            with self.subTest(invalid=invalid):
                self.assertFalse(
                    CURATION.validate_explanation_metadata(
                        indicator=invalid,
                        reason="NONE",
                    )["valid"]
                )


class TemporalBindingInvariantTests(unittest.TestCase):
    def test_source_period_mismatch_invalid(self):
        result = CURATION.validate_source_metadata(
            source_ids=("A", "B"),
            source_periods=("2026-01", "2025-01"),
            evaluated_period="2026-01",
            freshness="CURRENT",
            conflict=False,
        )
        self.assertFalse(result["valid"])
        self.assertFalse(result["period_binding_valid"])

    def test_wrong_payment_evaluated_period_invalid(self):
        result = CURATION.validate_payment_semantics(
            evaluated_period="2026-02",
            payment_state="PAID_ON_TIME",
            bank_state="POSTED_ON_TIME",
            settlement_delay_flag=False,
            payer_timestamp="2026-01-10 10:00:00",
            bank_timestamp="2026-01-10 10:01:00",
        )
        self.assertFalse(result["valid"])

    def test_next_day_month_rollover_valid(self):
        result = CURATION.validate_payment_semantics(
            evaluated_period="2026-01",
            payment_state="PAID_ON_TIME",
            bank_state="POSTED_NEXT_DAY",
            settlement_delay_flag=True,
            payer_timestamp="2026-01-31 23:55:00",
            bank_timestamp="2026-02-01 00:05:00",
        )
        self.assertTrue(result["valid"])

    def test_invalid_timestamp_rejected(self):
        result = CURATION.validate_payment_semantics(
            evaluated_period="2026-01",
            payment_state="PAID_ON_TIME",
            bank_state="POSTED_ON_TIME",
            settlement_delay_flag=False,
            payer_timestamp="banana",
            bank_timestamp="potato",
        )
        self.assertFalse(result["valid"])


class SyntheticIsolationInvariantTests(unittest.TestCase):
    def test_exposure_not_part_of_rule_inputs(self):
        evidence_a = {
            "valid": True,
            "quality": "HIGH",
            "discrepancy_detected": True,
            "estimated_exposure_synthetic_rp": 1,
        }
        evidence_b = dict(evidence_a)
        evidence_b["estimated_exposure_synthetic_rp"] = 10**15
        self.assertEqual(
            CURATION.evaluate_registration_rule(evidence_a),
            CURATION.evaluate_registration_rule(evidence_b),
        )

    def test_curated_exposure_is_explicitly_non_decision(self):
        curated = pd.read_csv(
            DATA_ROOT / "curated" / "curated_kepatuhan_evidence.csv"
        )
        self.assertTrue(
            curated["exposure_decision_role"].eq(
                "SIMULATED_ESTIMATE__NOT_EMPIRICAL_LOSS__NOT_FOR_DECISION"
            ).all()
        )

    def test_synthetic_target_stays_audit_only(self):
        candidate = pd.read_csv(
            DATA_ROOT / "candidate_ml" / "dataset_candidate_ml_audit.csv"
        )
        self.assertTrue(candidate["ml_status"].str.contains("CANDIDATE_ONLY").all())


class CuratedSchemaInvariantTests(unittest.TestCase):
    def setUp(self):
        self.curated = pd.read_csv(
            DATA_ROOT / "curated" / "curated_kepatuhan_evidence.csv"
        )

    def test_legacy_signal_states_removed(self):
        for column in (
            "registration_signal_state",
            "wage_signal_state",
            "contribution_signal_state",
        ):
            self.assertNotIn(column, self.curated.columns)

    def test_observation_rule_workflow_fields_present(self):
        required = {
            "registration_discrepancy_detected",
            "registration_rule_result",
            "registration_review_state",
            "wage_discrepancy_detected",
            "wage_rule_result",
            "wage_review_state",
            "contribution_payment_gap_observed",
            "contribution_rule_result",
            "contribution_review_state",
            "overall_review_state",
        }
        self.assertTrue(required.issubset(self.curated.columns))

    def test_current_sandbox_rule_results_all_abstain(self):
        self.assertTrue(self.curated["registration_rule_result"].eq("ABSTAIN").all())
        self.assertTrue(self.curated["wage_rule_result"].eq("ABSTAIN").all())
        self.assertTrue(self.curated["contribution_rule_result"].eq("ABSTAIN").all())

    def test_period_binding_valid_for_generated_fixture(self):
        for column in (
            "registration_period_binding_valid",
            "wage_period_binding_valid",
            "contribution_period_binding_valid",
        ):
            self.assertTrue(self.curated[column].astype(bool).all())

    def test_lineage_present_per_signal(self):
        for column in (
            "registration_lineage",
            "wage_lineage",
            "contribution_lineage",
        ):
            self.assertTrue(self.curated[column].notna().all())
            self.assertTrue(self.curated[column].astype(str).str.len().gt(0).all())


class PowerBIPresentationContractTests(unittest.TestCase):
    def setUp(self):
        self.fact = pd.read_csv(POWERBI_ROOT / "data" / "Fact_Risk_Evidence.csv")

    def test_powerbi_has_observation_rule_workflow_contract(self):
        required = {
            "registration_discrepancy_detected",
            "registration_rule_result",
            "registration_review_state",
            "registration_evidence_quality",
            "registration_evidence_valid",
            "wage_discrepancy_detected",
            "wage_rule_result",
            "wage_review_state",
            "wage_evidence_quality",
            "wage_evidence_valid",
            "contribution_payment_gap_observed",
            "contribution_rule_result",
            "contribution_review_state",
            "contribution_evidence_quality",
            "contribution_evidence_valid",
            "overall_review_state",
            "estimated_exposure_synthetic_rp",
            "exposure_label",
            "is_synthetic",
        }
        self.assertTrue(required.issubset(self.fact.columns))

    def test_powerbi_does_not_expose_legacy_signal_state(self):
        self.assertFalse(
            {
                "registration_signal_state",
                "wage_signal_state",
                "contribution_signal_state",
            }
            & set(self.fact.columns)
        )

    def test_powerbi_exposure_label_is_non_empirical(self):
        self.assertTrue(
            self.fact["exposure_label"].eq(
                "SIMULATED_ESTIMATE__NOT_EMPIRICAL_LOSS"
            ).all()
        )


class AttentionFlagInvariantTests(unittest.TestCase):
    def _flags(self, reg, wage, contribution, reg_reason):
        frame = pd.DataFrame([{
            "registration_review_state": reg,
            "wage_review_state": wage,
            "contribution_review_state": contribution,
            "registration_rule_reason": reg_reason,
            "wage_rule_reason": CURATION.POLICY_UNRESOLVED_REASON,
            "contribution_rule_reason": CURATION.POLICY_UNRESOLVED_REASON,
        }])
        return POWERBI.attach_attention_flags(frame).iloc[0]

    def test_pure_governance_abstain_not_operator_queue(self):
        row = self._flags(
            "ABSTAIN", "ABSTAIN", "ABSTAIN",
            CURATION.AUTHORITY_UNRESOLVED_REASON,
        )
        self.assertEqual(
            tuple(int(row[k]) for k in (
                "flag_reviewable", "flag_needs_enrichment", "flag_abstain",
                "flag_governance_blocked", "flag_needs_human_attention",
            )),
            (0, 0, 1, 1, 0),
        )

    def test_review_plus_governance_blocker_is_actionable(self):
        row = self._flags(
            "REVIEW", "ABSTAIN", "ABSTAIN", "OBSERVED_SET_DISCREPANCY",
        )
        self.assertEqual(int(row["flag_reviewable"]), 1)
        self.assertEqual(int(row["flag_governance_blocked"]), 1)
        self.assertEqual(int(row["flag_needs_human_attention"]), 1)

    def test_enrichment_separately_actionable(self):
        row = self._flags(
            "NEEDS_ENRICHMENT", "ABSTAIN", "ABSTAIN", "EVIDENCE_INSUFFICIENT",
        )
        self.assertEqual(int(row["flag_reviewable"]), 0)
        self.assertEqual(int(row["flag_needs_enrichment"]), 1)
        self.assertEqual(int(row["flag_needs_human_attention"]), 1)

    def test_current_synthetic_dataset_has_no_fake_operator_queue(self):
        fact = pd.read_csv(POWERBI_ROOT / "data" / "Fact_Risk_Evidence.csv")
        self.assertTrue(fact["flag_reviewable"].eq(0).all())
        self.assertTrue(fact["flag_needs_enrichment"].eq(0).all())
        self.assertTrue(fact["flag_abstain"].eq(1).all())
        self.assertTrue(fact["flag_governance_blocked"].eq(1).all())
        self.assertTrue(fact["flag_needs_human_attention"].eq(0).all())


class DeterminismAndEndToEndTests(unittest.TestCase):
    def test_raw_generator_is_deterministic(self):
        raw_path = DATA_ROOT / "raw" / "raw_kepatuhan_bulanan_badan_usaha.csv"
        before = raw_path.read_bytes()
        subprocess.run(
            [sys.executable, str(HERE / "generate_raw_dataset_bpjs.py")],
            env=ENV,
            check=True,
            capture_output=True,
            text=True,
        )
        after = raw_path.read_bytes()
        self.assertEqual(before, after)

    def test_validator_reports_final_contract_valid(self):
        result = subprocess.run(
            [sys.executable, str(HERE / "demo_analisis_dan_validasi.py")],
            env=ENV,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("FINAL SYNTHETIC DATA CONTRACT VALID", result.stdout)
        self.assertIn("REBIND REQUIRED", result.stdout)
        self.assertIn("NOT CLAIMED", result.stdout)


if __name__ == "__main__":
    unittest.main()
