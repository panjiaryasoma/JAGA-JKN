"""Curate raw synthetic evidence without inventing decision thresholds.

Reference, observed state, discrepancy, explanation, evidence quality, and policy
availability remain separate. Synthetic monetary exposure is visualization-only.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("JAGA_DATA_DIR", BASE_DIR / "data"))

POLICY_PENDING = "SYNTHETIC_ASSUMPTION_ONLY__B2_POLICY_NOT_AUTHORIZED"
UNSCORED = "UNSCORED__THRESHOLDS_NOT_AUTHORIZED"


def clean_company_name(value: object) -> str:
    if pd.isna(value):
        return "UNKNOWN_ENTITY"
    text = re.sub(r"\s+", " ", str(value).strip())
    text = re.sub(
        r"^(PT\.?|CV\.?)\s*",
        lambda m: m.group(1).replace(".", "").upper() + " ",
        text,
        flags=re.I,
    )
    parts = text.split(" ", 1)
    return parts[0].upper() + (" " + parts[1].title() if len(parts) == 2 else "")


def clean_npwp(value: object) -> str:
    if pd.isna(value):
        return "UNKNOWN"
    digits = re.sub(r"\D", "", str(value))
    if len(digits) < 15:
        return "INVALID_FORMAT"
    digits = digits[:15]
    return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}.{digits[8]}-{digits[9:12]}.{digits[12:]}"


def evidence_quality_from_flags(
    *,
    external_source_stale: bool,
    external_source_conflict: bool,
    settlement_pending: bool,
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    if external_source_conflict:
        reasons.append("CONFLICTING_EXTERNAL_SOURCE")
    if settlement_pending:
        reasons.append("PAYMENT_SETTLEMENT_PENDING")
    if external_source_stale:
        reasons.append("STALE_EXTERNAL_SOURCE")

    if external_source_conflict or settlement_pending:
        return "LOW", reasons
    if external_source_stale:
        return "MEDIUM", reasons
    return "HIGH", reasons


def preserve_worker_discrepancy(
    raw_gap: int,
    seasonal_or_project_explanation: bool,
) -> tuple[int, str]:
    explanation = (
        "PROJECT_OR_SEASON_END_SYNTHETIC"
        if seasonal_or_project_explanation
        else "NONE"
    )
    # Explanation never mutates the observed discrepancy.
    return int(raw_gap), explanation


def derive_decision_state(
    *,
    worker_discrepancy_count: int,
    wage_discrepancy_signal_rp: int,
    contribution_payment_evidence_gap: bool,
    evidence_quality: str,
    explanation_present: bool,
    policy_status: str,
    synthetic_exposure_demo_rp: int = 0,
) -> tuple[str, str, str]:
    # Intentionally excluded from every decision branch. The parameter exists so
    # deterministic regression tests can prove decision invariance to demo exposure.
    _ = synthetic_exposure_demo_rp

    has_worker_signal = worker_discrepancy_count > 0
    has_wage_signal = wage_discrepancy_signal_rp > 0
    has_policy_dependent_signal = has_wage_signal or contribution_payment_evidence_gap
    has_any_signal = has_worker_signal or has_policy_dependent_signal

    if not has_any_signal:
        return "NORMAL", "NO_MATERIAL_DISCREPANCY", UNSCORED

    if has_policy_dependent_signal and "B2_POLICY_NOT_AUTHORIZED" in policy_status:
        return "ABSTAIN", "POLICY_REQUIRED_BUT_UNRESOLVED", UNSCORED

    if evidence_quality == "LOW":
        return "ABSTAIN", "INSUFFICIENT_OR_CONFLICTING_EVIDENCE", UNSCORED

    if explanation_present or evidence_quality == "MEDIUM":
        return "NEEDS_ENRICHMENT", "EVIDENCE_ENRICHMENT_REQUIRED", UNSCORED

    # A present worker-count discrepancy can be surfaced for human interpretation,
    # but it is deliberately not scored, ranked, thresholded, or escalated.
    return "REVIEW", "HUMAN_REVIEW_NO_AUTOMATED_PRIORITY", UNSCORED


def curate() -> dict[str, pd.DataFrame]:
    raw_master = pd.read_csv(DATA_DIR / "raw_master_badan_usaha.csv")
    raw = pd.read_csv(DATA_DIR / "raw_kepatuhan_bulanan_badan_usaha.csv")

    curated_master = raw_master.copy()
    curated_master["nama_badan_usaha_terstandarisasi"] = curated_master[
        "nama_badan_usaha_raw"
    ].map(clean_company_name)
    curated_master["npwp_tervalidasi"] = curated_master[
        "npwp_badan_usaha_raw"
    ].map(clean_npwp)

    rows: list[dict] = []
    for _, row in raw.iterrows():
        raw_worker_gap = int(row["worker_discrepancy_raw"])
        worker_gap, explanation = preserve_worker_discrepancy(
            raw_worker_gap,
            bool(row["seasonal_or_project_change_indicator"]),
        )

        payment_state = row["payment_state_observed"]
        settlement_pending = row["bank_observed_state"] == "SETTLEMENT_PENDING"

        if bool(row["flag_bank_settlement_delay"]):
            payment_state_validated = "PAID_ON_TIME"
            payment_reason = "BANK_SETTLEMENT_DELAY_VERIFIED_SYNTHETIC"
        elif settlement_pending:
            payment_state_validated = "UNKNOWN"
            payment_reason = "SETTLEMENT_PENDING__DO_NOT_ESCALATE"
        else:
            payment_state_validated = payment_state
            payment_reason = "NO_SETTLEMENT_EXCEPTION"

        quality, quality_reasons = evidence_quality_from_flags(
            external_source_stale=row["external_source_freshness"] == "STALE",
            external_source_conflict=bool(row["external_source_conflict"]),
            settlement_pending=settlement_pending,
        )

        wage_gap = int(row["wage_discrepancy_raw_rp"])
        contribution_gap = payment_state_validated in {"UNPAID", "PAYMENT_PENDING", "UNKNOWN"}

        state, recommendation, risk_strength = derive_decision_state(
            worker_discrepancy_count=worker_gap,
            wage_discrepancy_signal_rp=wage_gap,
            contribution_payment_evidence_gap=contribution_gap,
            evidence_quality=quality,
            explanation_present=explanation != "NONE",
            policy_status=str(row["policy_status"]),
            synthetic_exposure_demo_rp=int(row["estimated_exposure_synthetic_rp"]),
        )

        signal_types: list[str] = []
        if worker_gap > 0:
            signal_types.append("WORKER_REGISTRATION_DISCREPANCY")
        if wage_gap > 0:
            signal_types.append("WAGE_REPORTING_DISCREPANCY")
        if contribution_gap:
            signal_types.append("CONTRIBUTION_PAYMENT_EVIDENCE_GAP")

        rows.append({
            "id_badan_usaha": row["id_badan_usaha"],
            "periode_bulan": row["periode_bulan"],
            "source_record_id": row["source_record_id"],
            "reference_worker_count": int(row["naker_external_reference_observed"]),
            "observed_registered_worker_count": int(row["naker_registered_observed"]),
            "raw_worker_discrepancy_count": raw_worker_gap,
            "worker_discrepancy_count": worker_gap,
            "reference_wage_signal_rp": int(row["reference_wage_signal_rp"]),
            "observed_wage_signal_rp": int(row["observed_wage_signal_rp"]),
            "wage_discrepancy_signal_rp": wage_gap,
            "estimated_exposure_synthetic_rp": int(row["estimated_exposure_synthetic_rp"]),
            "exposure_decision_role": "VISUALIZATION_ONLY__MUST_NOT_INFLUENCE_DECISION",
            "observed_payment_state": payment_state,
            "validated_payment_state": payment_state_validated,
            "payment_evidence_reason": payment_reason,
            "worker_discrepancy_explanation": explanation,
            "external_source_freshness": row["external_source_freshness"],
            "external_source_conflict": bool(row["external_source_conflict"]),
            "risk_signal_types": "|".join(signal_types) if signal_types else "NONE",
            "risk_strength": risk_strength,
            "evidence_quality": quality,
            "evidence_quality_reasons": (
                "|".join(quality_reasons) if quality_reasons else "NONE"
            ),
            "decision_state": state,
            "human_review_recommendation": recommendation,
            "policy_rule_id": "POLICY-PENDING-B2",
            "policy_effective_period": "UNVERIFIED",
            "policy_status": row["policy_status"],
            "lineage_source_to_signal": (
                f"{row['source_record_id']} -> raw discrepancy preserved -> "
                f"{('|'.join(signal_types) if signal_types else 'NONE')}"
            ),
            "synthetic_risk_mode_ground_truth": row["synthetic_risk_mode_ground_truth"],
            "is_synthetic": True,
        })

    return {
        "curated_master_badan_usaha.csv": curated_master,
        "curated_kepatuhan_evidence.csv": pd.DataFrame(rows),
    }


def main() -> None:
    outputs = curate()
    for filename, frame in outputs.items():
        frame.to_csv(DATA_DIR / filename, index=False, encoding="utf-8-sig")
        print(f"wrote {filename}: {len(frame):,} rows")
    print("status: CURATED EVIDENCE READY; THRESHOLD/POLICY-DEPENDENT SCORING DISABLED")


if __name__ == "__main__":
    main()
