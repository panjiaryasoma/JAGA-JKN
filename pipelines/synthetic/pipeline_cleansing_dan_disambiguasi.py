"""Curate raw synthetic evidence into contract-aligned risk-review facts.

The output separates reference/observed/discrepancy, risk strength, evidence
quality, and abstention. It never establishes fraud, violation, debt, sanction,
or enforcement action.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("JAGA_DATA_DIR", BASE_DIR / "data"))


def clean_company_name(value: object) -> str:
    if pd.isna(value):
        return "UNKNOWN_ENTITY"
    text = re.sub(r"\s+", " ", str(value).strip())
    text = re.sub(r"^(PT\.?|CV\.?)\s*", lambda m: m.group(1).replace(".", "").upper() + " ", text, flags=re.I)
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


def evidence_quality(row: pd.Series) -> tuple[str, list[str]]:
    reasons: list[str] = []
    score = 3
    if row["external_source_freshness"] == "STALE":
        score -= 1
        reasons.append("STALE_EXTERNAL_SOURCE")
    if bool(row["external_source_conflict"]):
        score -= 1
        reasons.append("CONFLICTING_EXTERNAL_SOURCE")
    if row["bank_observed_state"] == "SETTLEMENT_PENDING":
        score -= 1
        reasons.append("PAYMENT_SETTLEMENT_PENDING")
    if score >= 3:
        return "HIGH", reasons
    if score == 2:
        return "MEDIUM", reasons
    return "LOW", reasons


def risk_strength(worker_gap: int, wage_gap: int, exposure: int, duration_hint: int = 0) -> str:
    score = 0
    if worker_gap > 0:
        score += 1 if worker_gap < 5 else 2
    if wage_gap > 0:
        score += 1 if wage_gap < 500_000 else 2
    if exposure > 0:
        score += 1 if exposure < 5_000_000 else 2
    if duration_hint >= 4:
        score += 1
    if score == 0:
        return "NONE"
    if score <= 2:
        return "LOW"
    if score <= 4:
        return "MEDIUM"
    return "HIGH"


def review_state(strength: str, quality: str, evidence_reasons: list[str]) -> tuple[str, str]:
    if quality == "LOW":
        return "ABSTAIN", "INSUFFICIENT_OR_CONFLICTING_EVIDENCE"
    if evidence_reasons and quality == "MEDIUM" and strength in {"MEDIUM", "HIGH"}:
        return "NEEDS_ENRICHMENT", "EVIDENCE_ENRICHMENT_REQUIRED"
    if strength == "NONE":
        return "NORMAL", "NO_MATERIAL_DISCREPANCY"
    if strength == "LOW":
        return "MONITOR", "LOW_STRENGTH_SIGNAL"
    return "REVIEW", "PRIORITIZE_HUMAN_REVIEW"


def curate() -> dict[str, pd.DataFrame]:
    raw_master = pd.read_csv(DATA_DIR / "raw_master_badan_usaha.csv")
    raw = pd.read_csv(DATA_DIR / "raw_kepatuhan_bulanan_badan_usaha.csv")
    clean_monthly = pd.read_csv(DATA_DIR / "kepatuhan_bulanan_badan_usaha.csv")

    curated_master = raw_master.copy()
    curated_master["nama_badan_usaha_terstandarisasi"] = curated_master["nama_badan_usaha_raw"].map(clean_company_name)
    curated_master["npwp_tervalidasi"] = curated_master["npwp_badan_usaha_raw"].map(clean_npwp)

    duration_map = clean_monthly.set_index(["id_badan_usaha", "periode_bulan"])["episode_duration_months"].to_dict()

    rows: list[dict] = []
    for _, row in raw.iterrows():
        worker_gap = int(row["worker_discrepancy_raw"])
        legitimate_reason = "NONE"

        # Contract-aligned hard negative: project/season completion can explain a
        # worker-count difference. Spouse participation is deliberately absent.
        if bool(row["seasonal_or_project_change_indicator"]):
            worker_gap = 0
            legitimate_reason = row["seasonal_or_project_reason"]

        payment_state = row["payment_state_observed"]
        if bool(row["flag_bank_settlement_delay"]):
            payment_state_validated = "PAID_ON_TIME"
            payment_reason = "BANK_SETTLEMENT_DELAY_VERIFIED_SYNTHETIC"
        elif row["bank_observed_state"] == "SETTLEMENT_PENDING":
            payment_state_validated = "UNKNOWN"
            payment_reason = "SETTLEMENT_PENDING__DO_NOT_ESCALATE"
        else:
            payment_state_validated = payment_state
            payment_reason = "NO_SETTLEMENT_EXCEPTION"

        quality, quality_reasons = evidence_quality(row)
        duration = int(duration_map.get((row["id_badan_usaha"], row["periode_bulan"]), 0))
        strength = risk_strength(
            worker_gap,
            int(row["wage_discrepancy_raw_rp"]),
            int(row["estimated_exposure_synthetic_rp"]),
            duration,
        )
        state, recommendation = review_state(strength, quality, quality_reasons)

        signal_types: list[str] = []
        if worker_gap > 0:
            signal_types.append("WORKER_REGISTRATION_DISCREPANCY")
        if int(row["wage_discrepancy_raw_rp"]) > 0:
            signal_types.append("WAGE_REPORTING_DISCREPANCY")
        if payment_state_validated in {"UNPAID", "PAYMENT_PENDING", "UNKNOWN"}:
            signal_types.append("CONTRIBUTION_PAYMENT_EVIDENCE_GAP")

        rows.append({
            "id_badan_usaha": row["id_badan_usaha"],
            "periode_bulan": row["periode_bulan"],
            "source_record_id": row["source_record_id"],
            "reference_worker_count": int(row["naker_external_reference_observed"]),
            "observed_registered_worker_count": int(row["naker_registered_observed"]),
            "worker_discrepancy_count": worker_gap,
            "reference_wage_signal_rp": int(row["reference_wage_signal_rp"]),
            "observed_wage_signal_rp": int(row["observed_wage_signal_rp"]),
            "wage_discrepancy_signal_rp": int(row["wage_discrepancy_raw_rp"]),
            "estimated_exposure_synthetic_rp": int(row["estimated_exposure_synthetic_rp"]),
            "observed_payment_state": payment_state,
            "validated_payment_state": payment_state_validated,
            "payment_evidence_reason": payment_reason,
            "legitimate_worker_gap_reason": legitimate_reason,
            "external_source_freshness": row["external_source_freshness"],
            "external_source_conflict": bool(row["external_source_conflict"]),
            "risk_signal_types": "|".join(signal_types) if signal_types else "NONE",
            "risk_strength": strength,
            "evidence_quality": quality,
            "evidence_quality_reasons": "|".join(quality_reasons) if quality_reasons else "NONE",
            "decision_state": state,
            "human_review_recommendation": recommendation,
            "policy_rule_id": "POLICY-PENDING-B2",
            "policy_effective_period": "UNVERIFIED",
            "policy_status": row["policy_status"],
            "lineage_source_to_signal": f"{row['source_record_id']} -> curated evidence -> {('|'.join(signal_types) if signal_types else 'NONE')}",
            "synthetic_risk_mode_ground_truth": row["synthetic_risk_mode_ground_truth"],
            "is_synthetic": True,
        })

    curated = pd.DataFrame(rows)
    return {
        "curated_master_badan_usaha.csv": curated_master,
        "curated_kepatuhan_evidence.csv": curated,
    }


def main() -> None:
    outputs = curate()
    for filename, frame in outputs.items():
        frame.to_csv(DATA_DIR / filename, index=False, encoding="utf-8-sig")
        print(f"wrote {filename}: {len(frame):,} rows")
    print("status: CURATED EVIDENCE READY FOR DEMO REVIEW; LEGAL VERDICT + ML READINESS NOT CLAIMED")


if __name__ == "__main__":
    main()
