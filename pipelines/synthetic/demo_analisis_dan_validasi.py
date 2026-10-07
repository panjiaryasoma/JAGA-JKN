"""Structural validation for the synthetic remediation sandbox.

This proves contract-alignment properties only. It does not certify B1/B2,
production policy, ML readiness, or merge readiness.
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("JAGA_DATA_DIR", BASE_DIR / "data"))
POWERBI_DATA_DIR = Path(
    os.getenv("JAGA_POWERBI_DATA_DIR", BASE_DIR / "powerbi" / "data")
)

FORBIDDEN_SYSTEM_ACTION_TERMS = {
    "sanksi", "kejaksaan", "skk datun", "surat teguran", "audit investigasi",
}


def main() -> None:
    master = pd.read_csv(DATA_DIR / "master_badan_usaha.csv")
    monthly = pd.read_csv(DATA_DIR / "kepatuhan_bulanan_badan_usaha.csv")
    curated = pd.read_csv(DATA_DIR / "curated_kepatuhan_evidence.csv")
    ml_candidate = pd.read_csv(DATA_DIR / "dataset_candidate_ml_audit.csv")
    fact = pd.read_csv(POWERBI_DATA_DIR / "Fact_Risk_Evidence.csv")

    assert set(monthly["id_badan_usaha"]).issubset(set(master["id_badan_usaha"]))
    assert set(curated["id_badan_usaha"]).issubset(set(master["id_badan_usaha"]))
    assert curated[["id_badan_usaha", "periode_bulan", "source_record_id"]].isna().sum().sum() == 0

    required = {
        "reference_worker_count", "observed_registered_worker_count",
        "raw_worker_discrepancy_count", "worker_discrepancy_count",
        "risk_strength", "evidence_quality", "decision_state",
        "human_review_recommendation", "policy_rule_id",
        "lineage_source_to_signal", "exposure_decision_role",
    }
    assert required.issubset(curated.columns)
    assert set(curated["decision_state"]).issubset(
        {"NORMAL", "REVIEW", "NEEDS_ENRICHMENT", "ABSTAIN"}
    )
    assert curated["risk_strength"].eq(
        "UNSCORED__THRESHOLDS_NOT_AUTHORIZED"
    ).all()
    assert curated["raw_worker_discrepancy_count"].eq(
        curated["worker_discrepancy_count"]
    ).all()
    assert curated["policy_rule_id"].eq("POLICY-PENDING-B2").all()
    assert curated["exposure_decision_role"].eq(
        "VISUALIZATION_ONLY__MUST_NOT_INFLUENCE_DECISION"
    ).all()
    assert curated["is_synthetic"].astype(bool).all()
    assert fact["exposure_label"].eq(
        "SIMULATED_ESTIMATE__NOT_EMPIRICAL_LOSS"
    ).all()
    assert ml_candidate["ml_status"].str.contains("CANDIDATE_ONLY").all()

    recommendations = " ".join(
        curated["human_review_recommendation"].astype(str).str.lower().unique()
    )
    for term in FORBIDDEN_SYSTEM_ACTION_TERMS:
        assert term not in recommendations

    print("STATUS: SANDBOX REMEDIATION EVIDENCE VALID")
    print("RISK STRENGTH: UNSCORED / THRESHOLDS NOT AUTHORIZED")
    print("B2 POLICY EXECUTION: DISABLED")
    print("ML TRAINING READINESS: NOT CERTIFIED")
    print("MERGE READINESS: NOT CLAIMED")


if __name__ == "__main__":
    main()
