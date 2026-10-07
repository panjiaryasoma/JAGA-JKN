"""Curate raw synthetic evidence using fail-closed, per-signal semantics.

Key invariants:
- worker registration uses set reconciliation, not count subtraction;
- row-supplied policy metadata cannot authorize policy-dependent decisions;
- evidence quality is a closed enum and invalid values fail closed;
- registration, wage, and contribution signals retain independent states;
- synthetic monetary exposure is visualization-only.
"""

from __future__ import annotations

import json
import re
from typing import Iterable

import pandas as pd

from paths import CURATED_DIR, RAW_DIR, ensure_output_dirs

UNSCORED = "UNSCORED__THRESHOLDS_NOT_AUTHORIZED"
VALID_EVIDENCE_QUALITIES = {"HIGH", "MEDIUM", "LOW"}
TRUSTED_B2_POLICY_CONTEXT_AUTHORIZED = False


def clean_company_name(value: object) -> str:
    if pd.isna(value):
        return "UNKNOWN_ENTITY"
    text = re.sub(r"\s+", " ", str(value).strip())
    text = re.sub(
        r"^(PT\.?|CV\.?)\s*",
        lambda match: match.group(1).replace(".", "").upper() + " ",
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


def parse_worker_set(serialized: object) -> set[str]:
    if not isinstance(serialized, str) or not serialized.strip():
        raise ValueError("worker set must be a non-empty JSON array string")
    value = json.loads(serialized)
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise ValueError("worker set must contain non-empty string worker IDs")
    if len(value) != len(set(value)):
        raise ValueError("worker set contains duplicate worker IDs")
    return set(value)


def reconcile_worker_sets(
    reference_worker_set: Iterable[str],
    observed_registered_worker_set: Iterable[str],
) -> dict[str, object]:
    reference = set(reference_worker_set)
    observed = set(observed_registered_worker_set)
    missing = reference - observed
    unexpected = observed - reference
    return {
        "reference_count": len(reference),
        "observed_count": len(observed),
        "missing_worker_ids": sorted(missing),
        "unexpected_worker_ids": sorted(unexpected),
        "missing_worker_count": len(missing),
        "unexpected_worker_count": len(unexpected),
        "sets_equal": reference == observed,
    }


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


def _validate_evidence_quality(value: object) -> str | None:
    if not isinstance(value, str) or value not in VALID_EVIDENCE_QUALITIES:
        return None
    return value


def derive_registration_state(
    *,
    missing_worker_count: int,
    unexpected_worker_count: int,
    evidence_quality: object,
    explanation_present: bool,
) -> tuple[str, str]:
    quality = _validate_evidence_quality(evidence_quality)
    has_signal = missing_worker_count > 0 or unexpected_worker_count > 0
    if not has_signal:
        return "NORMAL", "NO_REGISTRATION_SET_DISCREPANCY"
    if quality is None:
        return "ABSTAIN", "INVALID_OR_UNKNOWN_EVIDENCE_QUALITY"
    if quality == "LOW":
        return "ABSTAIN", "INSUFFICIENT_OR_CONFLICTING_EVIDENCE"
    if explanation_present or quality == "MEDIUM":
        return "NEEDS_ENRICHMENT", "EVIDENCE_ENRICHMENT_REQUIRED"
    return "REVIEW", "HUMAN_REVIEW_NO_AUTOMATED_PRIORITY"


def derive_wage_state(
    *,
    wage_discrepancy_signal_rp: int,
    evidence_quality: object,
) -> tuple[str, str]:
    if wage_discrepancy_signal_rp <= 0:
        return "NORMAL", "NO_WAGE_DISCREPANCY"
    if _validate_evidence_quality(evidence_quality) is None:
        return "ABSTAIN", "INVALID_OR_UNKNOWN_EVIDENCE_QUALITY"
    if not TRUSTED_B2_POLICY_CONTEXT_AUTHORIZED:
        return "ABSTAIN", "POLICY_REQUIRED_BUT_UNRESOLVED"
    raise RuntimeError("authorized B2 policy path is intentionally not implemented in this sandbox")


def derive_contribution_state(
    *,
    contribution_payment_evidence_gap: bool,
    evidence_quality: object,
) -> tuple[str, str]:
    if not contribution_payment_evidence_gap:
        return "NORMAL", "NO_CONTRIBUTION_PAYMENT_EVIDENCE_GAP"
    if _validate_evidence_quality(evidence_quality) is None:
        return "ABSTAIN", "INVALID_OR_UNKNOWN_EVIDENCE_QUALITY"
    if not TRUSTED_B2_POLICY_CONTEXT_AUTHORIZED:
        return "ABSTAIN", "POLICY_REQUIRED_BUT_UNRESOLVED"
    raise RuntimeError("authorized B2 policy path is intentionally not implemented in this sandbox")


def derive_overall_review_state(*states: str) -> str:
    active = [state for state in states if state != "NORMAL"]
    if not active:
        return "NORMAL"
    unique = set(active)
    if len(unique) == 1:
        return active[0]
    return "PARTIAL"


def overall_recommendation(state: str) -> str:
    return {
        "NORMAL": "NO_MATERIAL_DISCREPANCY",
        "REVIEW": "HUMAN_REVIEW_NO_AUTOMATED_PRIORITY",
        "NEEDS_ENRICHMENT": "EVIDENCE_ENRICHMENT_REQUIRED",
        "ABSTAIN": "ABSTAIN__SEE_SIGNAL_STATES",
        "PARTIAL": "PARTIAL_SIGNAL_STATES__REVIEW_INDEPENDENTLY",
    }[state]


def curate() -> dict[str, pd.DataFrame]:
    raw_master = pd.read_csv(RAW_DIR / "raw_master_badan_usaha.csv")
    raw = pd.read_csv(RAW_DIR / "raw_kepatuhan_bulanan_badan_usaha.csv")

    curated_master = raw_master.copy()
    curated_master["nama_badan_usaha_terstandarisasi"] = curated_master[
        "nama_badan_usaha_raw"
    ].map(clean_company_name)
    curated_master["npwp_tervalidasi"] = curated_master[
        "npwp_badan_usaha_raw"
    ].map(clean_npwp)

    rows: list[dict] = []
    for _, row in raw.iterrows():
        try:
            reference_set = parse_worker_set(row["reference_worker_set_json"])
            observed_set = parse_worker_set(row["observed_registered_worker_set_json"])
            reconciliation = reconcile_worker_sets(reference_set, observed_set)
            worker_set_valid = True
            worker_set_error = "NONE"
        except (ValueError, json.JSONDecodeError, TypeError) as exc:
            reconciliation = {
                "reference_count": 0,
                "observed_count": 0,
                "missing_worker_ids": [],
                "unexpected_worker_ids": [],
                "missing_worker_count": 0,
                "unexpected_worker_count": 0,
                "sets_equal": False,
            }
            worker_set_valid = False
            worker_set_error = type(exc).__name__

        settlement_pending = row["bank_observed_state"] == "SETTLEMENT_PENDING"
        quality, quality_reasons = evidence_quality_from_flags(
            external_source_stale=row["external_source_freshness"] == "STALE",
            external_source_conflict=bool(row["external_source_conflict"]),
            settlement_pending=settlement_pending,
        )
        if not worker_set_valid:
            quality = "LOW"
            quality_reasons.append("INVALID_WORKER_SET_EVIDENCE")

        explanation = (
            str(row["seasonal_or_project_reason"])
            if bool(row["seasonal_or_project_change_indicator"])
            else "NONE"
        )

        payment_state = row["payment_state_observed"]
        if bool(row["flag_bank_settlement_delay"]):
            validated_payment_state = "PAID_ON_TIME"
            payment_reason = "BANK_SETTLEMENT_DELAY_VERIFIED_SYNTHETIC"
        elif settlement_pending:
            validated_payment_state = "UNKNOWN"
            payment_reason = "SETTLEMENT_PENDING__DO_NOT_ESCALATE"
        else:
            validated_payment_state = payment_state
            payment_reason = "NO_SETTLEMENT_EXCEPTION"

        wage_gap = int(row["wage_discrepancy_raw_rp"])
        contribution_gap = validated_payment_state in {"UNPAID", "PAYMENT_PENDING", "UNKNOWN"}

        registration_state, registration_reason = derive_registration_state(
            missing_worker_count=int(reconciliation["missing_worker_count"]),
            unexpected_worker_count=int(reconciliation["unexpected_worker_count"]),
            evidence_quality=quality,
            explanation_present=explanation != "NONE",
        )
        wage_state, wage_reason = derive_wage_state(
            wage_discrepancy_signal_rp=wage_gap,
            evidence_quality=quality,
        )
        contribution_state, contribution_reason = derive_contribution_state(
            contribution_payment_evidence_gap=contribution_gap,
            evidence_quality=quality,
        )
        overall_state = derive_overall_review_state(
            registration_state,
            wage_state,
            contribution_state,
        )

        signal_types: list[str] = []
        if int(reconciliation["missing_worker_count"]) > 0 or int(reconciliation["unexpected_worker_count"]) > 0:
            signal_types.append("WORKER_REGISTRATION_SET_DISCREPANCY")
        if wage_gap > 0:
            signal_types.append("WAGE_REPORTING_DISCREPANCY")
        if contribution_gap:
            signal_types.append("CONTRIBUTION_PAYMENT_EVIDENCE_GAP")

        rows.append({
            "id_badan_usaha": row["id_badan_usaha"],
            "periode_bulan": row["periode_bulan"],
            "source_record_id": row["source_record_id"],
            "reference_worker_count": int(reconciliation["reference_count"]),
            "observed_registered_worker_count": int(reconciliation["observed_count"]),
            "missing_worker_count": int(reconciliation["missing_worker_count"]),
            "unexpected_worker_count": int(reconciliation["unexpected_worker_count"]),
            "missing_worker_ids_json": json.dumps(reconciliation["missing_worker_ids"], separators=(",", ":")),
            "unexpected_worker_ids_json": json.dumps(reconciliation["unexpected_worker_ids"], separators=(",", ":")),
            "worker_sets_equal": bool(reconciliation["sets_equal"]),
            "worker_set_evidence_valid": worker_set_valid,
            "worker_set_evidence_error": worker_set_error,
            "worker_discrepancy_explanation": explanation,
            "reference_wage_signal_rp": int(row["reference_wage_signal_rp"]),
            "observed_wage_signal_rp": int(row["observed_wage_signal_rp"]),
            "wage_discrepancy_signal_rp": wage_gap,
            "estimated_exposure_synthetic_rp": int(row["estimated_exposure_synthetic_rp"]),
            "exposure_decision_role": "VISUALIZATION_ONLY__MUST_NOT_INFLUENCE_DECISION",
            "observed_payment_state": payment_state,
            "validated_payment_state": validated_payment_state,
            "payment_evidence_reason": payment_reason,
            "external_source_freshness": row["external_source_freshness"],
            "external_source_conflict": bool(row["external_source_conflict"]),
            "evidence_quality": quality,
            "evidence_quality_reasons": "|".join(quality_reasons) if quality_reasons else "NONE",
            "registration_signal_state": registration_state,
            "registration_signal_reason": registration_reason,
            "wage_signal_state": wage_state,
            "wage_signal_reason": wage_reason,
            "contribution_signal_state": contribution_state,
            "contribution_signal_reason": contribution_reason,
            "overall_review_state": overall_state,
            "human_review_recommendation": overall_recommendation(overall_state),
            "risk_strength": UNSCORED,
            "risk_signal_types": "|".join(signal_types) if signal_types else "NONE",
            "policy_rule_id": "POLICY-PENDING-B2",
            "policy_effective_period": "UNVERIFIED",
            "policy_status_metadata_only": row["policy_status_metadata_only"],
            "trusted_policy_context_authorized": TRUSTED_B2_POLICY_CONTEXT_AUTHORIZED,
            "lineage_source_to_signal": (
                f"{row['source_record_id']} -> worker-set reconciliation / evidence curation -> "
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
    ensure_output_dirs()
    for filename, frame in curate().items():
        path = CURATED_DIR / filename
        frame.to_csv(path, index=False, encoding="utf-8-sig")
        print(f"wrote {path}: {len(frame):,} rows")
    print("status: CURATED EVIDENCE READY; POLICY AUTHORITY FAILS CLOSED")


if __name__ == "__main__":
    main()
