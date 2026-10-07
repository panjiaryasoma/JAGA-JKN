"""Structural validator for the synthetic remediation sandbox."""

from __future__ import annotations

import json

import pandas as pd

from paths import CANDIDATE_ML_DIR, CURATED_DIR, POWERBI_DATA_DIR, SCENARIO_DIR

FORBIDDEN_SYSTEM_ACTION_TERMS = {
    "sanksi", "kejaksaan", "skk datun", "surat teguran", "audit investigasi",
}


def _nonempty_source_ids(value: object) -> bool:
    try:
        parsed = json.loads(str(value))
    except (json.JSONDecodeError, TypeError):
        return False
    return isinstance(parsed, list) and len(parsed) >= 2 and all(
        isinstance(item, str) and item for item in parsed
    )


def main() -> None:
    master = pd.read_csv(SCENARIO_DIR / "master_badan_usaha.csv")
    curated = pd.read_csv(CURATED_DIR / "curated_kepatuhan_evidence.csv")
    ml_candidate = pd.read_csv(CANDIDATE_ML_DIR / "dataset_candidate_ml_audit.csv")
    fact = pd.read_csv(POWERBI_DATA_DIR / "Fact_Risk_Evidence.csv")

    assert set(curated["id_badan_usaha"]).issubset(set(master["id_badan_usaha"]))
    assert curated[["id_badan_usaha", "periode_bulan", "source_record_id"]].isna().sum().sum() == 0

    required = {
        "registration_source_metadata_valid", "registration_evidence_valid",
        "registration_evidence_quality", "registration_signal_state",
        "registration_rule_id", "registration_source_ids_json", "registration_lineage",
        "wage_source_metadata_valid", "wage_semantic_consistency_valid",
        "wage_evidence_valid", "wage_evidence_quality", "wage_signal_state",
        "wage_rule_id", "wage_source_ids_json", "wage_lineage",
        "contribution_source_metadata_valid", "payment_semantic_consistency_valid",
        "contribution_evidence_valid", "contribution_evidence_quality",
        "contribution_signal_state", "contribution_rule_id",
        "contribution_source_ids_json", "contribution_lineage",
        "overall_review_state", "risk_strength",
        "trusted_policy_context_authorized", "exposure_decision_role",
    }
    assert required.issubset(curated.columns)

    assert curated["registration_rule_id"].eq("REG-001").all()
    assert curated["wage_rule_id"].eq("WAGE-001").all()
    assert curated["contribution_rule_id"].eq("CONTRIB-001").all()

    for column in (
        "registration_evidence_quality",
        "wage_evidence_quality",
        "contribution_evidence_quality",
    ):
        assert set(curated[column]).issubset({"HIGH", "MEDIUM", "LOW"})

    # Missing/invalid source metadata must never yield a trusted normal/review state.
    assert not (
        (~curated["registration_source_metadata_valid"].astype(bool))
        & curated["registration_signal_state"].isin(["NORMAL", "REVIEW"])
    ).any()
    assert not (
        (~curated["wage_source_metadata_valid"].astype(bool))
        & curated["wage_signal_state"].eq("NORMAL")
    ).any()
    assert not (
        (~curated["contribution_source_metadata_valid"].astype(bool))
        & curated["contribution_signal_state"].eq("NORMAL")
    ).any()

    # Cross-field inconsistency must fail closed.
    assert not (
        (~curated["wage_semantic_consistency_valid"].astype(bool))
        & curated["wage_signal_state"].eq("NORMAL")
    ).any()
    assert not (
        (~curated["payment_semantic_consistency_valid"].astype(bool))
        & curated["contribution_signal_state"].eq("NORMAL")
    ).any()

    # B2 is unresolved in this sandbox, therefore policy-dependent rules cannot NORMAL.
    assert curated["trusted_policy_context_authorized"].astype(bool).eq(False).all()
    assert not curated["wage_signal_state"].eq("NORMAL").any()
    assert not curated["contribution_signal_state"].eq("NORMAL").any()

    for column in (
        "registration_source_ids_json",
        "wage_source_ids_json",
        "contribution_source_ids_json",
    ):
        valid_rows = curated[column].map(_nonempty_source_ids)
        assert valid_rows.all()

    assert curated["risk_strength"].eq("UNSCORED__THRESHOLDS_NOT_AUTHORIZED").all()
    assert set(curated["overall_review_state"]).issubset(
        {"NORMAL", "REVIEW", "NEEDS_ENRICHMENT", "ABSTAIN", "PARTIAL"}
    )
    assert curated["exposure_decision_role"].eq(
        "VISUALIZATION_ONLY__MUST_NOT_INFLUENCE_DECISION"
    ).all()
    assert fact["exposure_label"].eq("SIMULATED_ESTIMATE__NOT_EMPIRICAL_LOSS").all()
    assert ml_candidate["ml_status"].str.contains("CANDIDATE_ONLY").all()

    recommendations = " ".join(
        curated["human_review_recommendation"].astype(str).str.lower().unique()
    )
    for term in FORBIDDEN_SYSTEM_ACTION_TERMS:
        assert term not in recommendations

    print("STATUS: SANDBOX REMEDIATION EVIDENCE VALID")
    print("B2 POLICY GATE: BEFORE NORMAL FOR WAGE + CONTRIBUTION")
    print("SOURCE METADATA: REQUIRED FOR EVIDENCE VALIDITY")
    print("CROSS-FIELD SEMANTICS: VALIDATED")
    print("ML TRAINING READINESS: NOT CERTIFIED")
    print("MERGE READINESS: NOT CLAIMED")


if __name__ == "__main__":
    main()
