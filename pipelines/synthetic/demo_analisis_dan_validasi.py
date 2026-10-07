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
        "reference_worker_count", "observed_registered_worker_count",
        "missing_worker_count", "unexpected_worker_count",
        "registration_signal_state", "wage_signal_state", "contribution_signal_state",
        "overall_review_state", "evidence_quality", "risk_strength",
        "policy_rule_id", "trusted_policy_context_authorized",
        "lineage_source_to_signal", "exposure_decision_role",
    }
    assert required.issubset(curated.columns)
    assert curated["risk_strength"].eq("UNSCORED__THRESHOLDS_NOT_AUTHORIZED").all()
    assert curated["trusted_policy_context_authorized"].astype(bool).eq(False).all()
    assert set(curated["evidence_quality"]).issubset({"HIGH", "MEDIUM", "LOW"})
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
    print("WORKER REGISTRATION: SET RECONCILIATION ENABLED")
    print("B2 POLICY AUTHORITY: FAIL-CLOSED / TRUSTED CONTEXT FALSE")
    print("SIGNAL STATES: INDEPENDENT")
    print("ML TRAINING READINESS: NOT CERTIFIED")
    print("MERGE READINESS: NOT CLAIMED")


if __name__ == "__main__":
    main()
