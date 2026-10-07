"""Structural validator for the synthetic remediation sandbox."""

from __future__ import annotations

import pandas as pd

from paths import CANDIDATE_ML_DIR, CURATED_DIR, POWERBI_DATA_DIR, SCENARIO_DIR

FORBIDDEN_SYSTEM_ACTION_TERMS = {
    "sanksi", "kejaksaan", "skk datun", "surat teguran", "audit investigasi",
}


def main() -> None:
    master = pd.read_csv(SCENARIO_DIR / "master_badan_usaha.csv")
    curated = pd.read_csv(CURATED_DIR / "curated_kepatuhan_evidence.csv")
    ml_candidate = pd.read_csv(CANDIDATE_ML_DIR / "dataset_candidate_ml_audit.csv")
    fact = pd.read_csv(POWERBI_DATA_DIR / "Fact_Risk_Evidence.csv")

    assert set(curated["id_badan_usaha"]).issubset(set(master["id_badan_usaha"]))
    assert curated[["id_badan_usaha", "periode_bulan", "source_record_id"]].isna().sum().sum() == 0

    required = {
        "registration_evidence_quality", "registration_evidence_reasons",
        "registration_signal_state", "registration_rule_id",
        "registration_source_ids_json", "registration_lineage",
        "wage_evidence_quality", "wage_evidence_reasons",
        "wage_signal_state", "wage_rule_id", "wage_source_ids_json", "wage_lineage",
        "contribution_evidence_quality", "contribution_evidence_reasons",
        "contribution_signal_state", "contribution_rule_id",
        "contribution_source_ids_json", "contribution_lineage",
        "overall_review_state", "risk_strength",
        "trusted_policy_context_authorized", "exposure_decision_role",
    }
    assert required.issubset(curated.columns)

    assert "evidence_quality" not in curated.columns
    assert "evidence_quality_reasons" not in curated.columns

    assert curated["registration_rule_id"].eq("REG-001").all()
    assert curated["wage_rule_id"].eq("WAGE-001").all()
    assert curated["contribution_rule_id"].eq("CONTRIB-001").all()

    for column in (
        "registration_evidence_quality",
        "wage_evidence_quality",
        "contribution_evidence_quality",
    ):
        assert set(curated[column]).issubset({"HIGH", "MEDIUM", "LOW"})

    assert not (
        (~curated["worker_set_evidence_valid"].astype(bool))
        & curated["registration_signal_state"].eq("NORMAL")
    ).any()
    assert not (
        (~curated["wage_evidence_valid"].astype(bool))
        & curated["wage_signal_state"].eq("NORMAL")
    ).any()
    assert not (
        (~curated["contribution_evidence_valid"].astype(bool))
        & curated["contribution_signal_state"].eq("NORMAL")
    ).any()

    assert curated["risk_strength"].eq("UNSCORED__THRESHOLDS_NOT_AUTHORIZED").all()
    assert curated["trusted_policy_context_authorized"].astype(bool).eq(False).all()
    assert set(curated["overall_review_state"]).issubset(
        {"NORMAL", "REVIEW", "NEEDS_ENRICHMENT", "ABSTAIN", "PARTIAL"}
    )
    assert curated["exposure_decision_role"].eq(
        "VISUALIZATION_ONLY__MUST_NOT_INFLUENCE_DECISION"
    ).all()
    assert fact["exposure_label"].eq("SIMULATED_ESTIMATE__NOT_EMPIRICAL_LOSS").all()
    assert ml_candidate["ml_status"].str.contains("CANDIDATE_ONLY").all()

    recommendations = " ".join(curated["human_review_recommendation"].astype(str).str.lower().unique())
    for term in FORBIDDEN_SYSTEM_ACTION_TERMS:
        assert term not in recommendations

    print("STATUS: SANDBOX REMEDIATION EVIDENCE VALID")
    print("EVIDENCE VALIDITY: CHECKED BEFORE NORMALIZATION")
    print("EVIDENCE QUALITY: ISOLATED PER SIGNAL")
    print("PROVENANCE: RULE + SOURCE + LINEAGE PER SIGNAL")
    print("B2 POLICY AUTHORITY: FAIL-CLOSED / TRUSTED CONTEXT FALSE")
    print("ML TRAINING READINESS: NOT CERTIFIED")
    print("MERGE READINESS: NOT CLAIMED")


if __name__ == "__main__":
    main()
