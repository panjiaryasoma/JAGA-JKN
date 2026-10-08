"""Release-style validator for the final synthetic data contract sandbox."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from paths import CANDIDATE_ML_DIR, CURATED_DIR, POWERBI_DATA_DIR, SCENARIO_DIR
from trusted_context import (
    CONTRIBUTION_POLICY_CONTEXT,
    REGISTRATION_AUTHORITY_CONTEXT,
    WAGE_POLICY_CONTEXT,
)

REG_RESULTS = {"CONSISTENT", "POTENTIAL_REGISTRATION_GAP", "ABSTAIN"}
WAGE_RESULTS = {"CONSISTENT", "POTENTIAL_WAGE_DIVERGENCE", "ABSTAIN"}
CONTRIB_RESULTS = {
    "CONSISTENT",
    "POTENTIAL_CONTRIBUTION_IRREGULARITY",
    "ABSTAIN",
}
REVIEW_STATES = {"NORMAL", "REVIEW", "NEEDS_ENRICHMENT", "ABSTAIN"}
OVERALL_STATES = REVIEW_STATES | {"PARTIAL"}
LEGACY_COLUMNS = {
    "registration_signal_state",
    "wage_signal_state",
    "contribution_signal_state",
}
FORBIDDEN_SYSTEM_ACTION_TERMS = {
    "sanksi",
    "kejaksaan",
    "skk datun",
    "surat teguran",
    "audit investigasi",
}


def _nonempty_json_list(value: object) -> bool:
    try:
        parsed = json.loads(str(value))
    except (json.JSONDecodeError, TypeError):
        return False
    return (
        isinstance(parsed, list)
        and len(parsed) >= 2
        and all(isinstance(item, str) and item for item in parsed)
    )


def _assert_exposure_not_in_decision_functions() -> None:
    source = (
        Path(__file__).resolve().parent
        / "pipeline_cleansing_dan_disambiguasi.py"
    ).read_text(encoding="utf-8")
    decision_function_names = [
        "def _evaluate_registration_rule_with_context(",
        "def _evaluate_wage_rule_with_context(",
        "def _evaluate_contribution_rule_with_context(",
        "def map_registration_review_state(",
        "def map_wage_review_state(",
        "def map_contribution_review_state(",
    ]
    for marker in decision_function_names:
        start = source.index(marker)
        next_def = source.find("\ndef ", start + len(marker))
        block = source[start:] if next_def < 0 else source[start:next_def]
        assert "exposure" not in block.lower()


def main() -> None:
    master = pd.read_csv(SCENARIO_DIR / "master_badan_usaha.csv")
    curated = pd.read_csv(CURATED_DIR / "curated_kepatuhan_evidence.csv")
    ml_candidate = pd.read_csv(CANDIDATE_ML_DIR / "dataset_candidate_ml_audit.csv")
    fact = pd.read_csv(POWERBI_DATA_DIR / "Fact_Risk_Evidence.csv")

    assert set(curated["id_badan_usaha"]).issubset(
        set(master["id_badan_usaha"])
    )
    assert LEGACY_COLUMNS.isdisjoint(curated.columns)

    required = {
        "registration_discrepancy_detected",
        "registration_rule_result",
        "registration_review_state",
        "registration_evidence_valid",
        "registration_evidence_quality",
        "registration_lineage",
        "registration_authority_authorized",
        "registration_rule_version",
        "registration_period_binding_valid",
        "wage_discrepancy_detected",
        "wage_rule_result",
        "wage_review_state",
        "wage_evidence_valid",
        "wage_evidence_quality",
        "wage_lineage",
        "wage_authority_authorized",
        "wage_rule_version",
        "wage_period_binding_valid",
        "contribution_payment_gap_observed",
        "contribution_rule_result",
        "contribution_review_state",
        "contribution_evidence_valid",
        "contribution_evidence_quality",
        "contribution_lineage",
        "contribution_authority_authorized",
        "contribution_rule_version",
        "contribution_period_binding_valid",
        "overall_review_state",
        "human_review_recommendation",
        "estimated_exposure_synthetic_rp",
        "exposure_decision_role",
        "is_synthetic",
    }
    assert required.issubset(curated.columns)

    assert set(curated["registration_rule_result"]).issubset(REG_RESULTS)
    assert set(curated["wage_rule_result"]).issubset(WAGE_RESULTS)
    assert set(curated["contribution_rule_result"]).issubset(CONTRIB_RESULTS)

    for column in (
        "registration_review_state",
        "wage_review_state",
        "contribution_review_state",
    ):
        assert set(curated[column]).issubset(REVIEW_STATES)
    assert set(curated["overall_review_state"]).issubset(OVERALL_STATES)

    # Current trusted contexts are unresolved and must fail closed.
    assert not REGISTRATION_AUTHORITY_CONTEXT.authorized
    assert not WAGE_POLICY_CONTEXT.authorized
    assert not CONTRIBUTION_POLICY_CONTEXT.authorized
    assert curated["registration_rule_result"].eq("ABSTAIN").all()
    assert curated["wage_rule_result"].eq("ABSTAIN").all()
    assert curated["contribution_rule_result"].eq("ABSTAIN").all()

    for column in (
        "registration_source_metadata_valid",
        "wage_source_metadata_valid",
        "contribution_source_metadata_valid",
        "registration_period_binding_valid",
        "wage_period_binding_valid",
        "contribution_period_binding_valid",
        "registration_explanation_metadata_valid",
        "wage_semantic_consistency_valid",
        "payment_semantic_consistency_valid",
    ):
        assert curated[column].astype(bool).all()

    for column in (
        "registration_source_ids_json",
        "wage_source_ids_json",
        "contribution_source_ids_json",
    ):
        assert curated[column].map(_nonempty_json_list).all()

    for column in (
        "registration_lineage",
        "wage_lineage",
        "contribution_lineage",
    ):
        assert curated[column].notna().all()
        assert curated[column].astype(str).str.len().gt(0).all()

    assert curated["exposure_decision_role"].eq(
        "SIMULATED_ESTIMATE__NOT_EMPIRICAL_LOSS__NOT_FOR_DECISION"
    ).all()
    _assert_exposure_not_in_decision_functions()

    assert fact["presentation_contract"].eq(
        "OBSERVATION_RULE_WORKFLOW_V1"
    ).all()
    assert fact["exposure_label"].eq(
        "SIMULATED_ESTIMATE__NOT_EMPIRICAL_LOSS"
    ).all()

    recommendations = " ".join(
        curated["human_review_recommendation"].astype(str).str.lower().unique()
    )
    for term in FORBIDDEN_SYSTEM_ACTION_TERMS:
        assert term not in recommendations

    assert ml_candidate["ml_status"].str.contains("CANDIDATE_ONLY").all()
    assert not ml_candidate["ml_status"].str.contains("TRAINING_READY").any()

    print("STATUS:")
    print("FINAL SYNTHETIC DATA CONTRACT VALID")
    print("")
    print("REGISTRATION AUTHORITY:")
    print("UNRESOLVED / FAIL-CLOSED")
    print("")
    print("WAGE POLICY:")
    print("B2 UNRESOLVED / FAIL-CLOSED")
    print("")
    print("CONTRIBUTION POLICY:")
    print("B2 UNRESOLVED / FAIL-CLOSED")
    print("")
    print("ML:")
    print("CANDIDATE ONLY")
    print("")
    print("PBIX:")
    print("REBIND REQUIRED")
    print("")
    print("MERGE READINESS:")
    print("NOT CLAIMED")


if __name__ == "__main__":
    main()
