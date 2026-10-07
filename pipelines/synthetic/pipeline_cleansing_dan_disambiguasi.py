"""Curate raw synthetic evidence with fail-closed per-signal semantics.

Evidence validity is evaluated before discrepancy. Registration, wage, and
contribution maintain isolated evidence quality, state, rule identity, and lineage.
"""

from __future__ import annotations

import json
import math
import re
from typing import Iterable

import pandas as pd

from paths import CURATED_DIR, RAW_DIR, ensure_output_dirs

UNSCORED = "UNSCORED__THRESHOLDS_NOT_AUTHORIZED"
VALID_EVIDENCE_QUALITIES = {"HIGH", "MEDIUM", "LOW"}
TRUSTED_B2_POLICY_CONTEXT_AUTHORIZED = False

REGISTRATION_RULE_ID = "REG-001"
WAGE_RULE_ID = "WAGE-001"
CONTRIBUTION_RULE_ID = "CONTRIB-001"

VALID_PAYMENT_STATES = {"PAID_ON_TIME", "PAYMENT_PENDING", "UNPAID"}
VALID_BANK_STATES = {
    "POSTED_ON_TIME",
    "POSTED_NEXT_DAY",
    "SETTLEMENT_PENDING",
    "NO_PAYMENT_EVIDENCE",
}


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


def parse_worker_set(serialized: object, *, allow_empty: bool = False) -> set[str]:
    if not isinstance(serialized, str) or not serialized.strip():
        raise ValueError("worker set must be a JSON array string")
    value = json.loads(serialized)
    if not isinstance(value, list):
        raise ValueError("worker set must be a JSON array")
    if not value and not allow_empty:
        raise ValueError("empty worker set requires explicit verified-empty semantics")
    if any(not isinstance(item, str) or not item for item in value):
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


def _validate_evidence_quality(value: object) -> str | None:
    if not isinstance(value, str) or value not in VALID_EVIDENCE_QUALITIES:
        return None
    return value


def _quality_from_domain_flags(
    *,
    evidence_valid: bool,
    source_stale: bool,
    source_conflict: bool,
    extra_low_reason: str | None = None,
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    if not evidence_valid:
        reasons.append("INVALID_OR_MISSING_EVIDENCE")
    if source_conflict:
        reasons.append("CONFLICTING_SOURCE")
    if source_stale:
        reasons.append("STALE_SOURCE")
    if extra_low_reason:
        reasons.append(extra_low_reason)

    if not evidence_valid or source_conflict or extra_low_reason:
        return "LOW", reasons
    if source_stale:
        return "MEDIUM", reasons
    return "HIGH", reasons


def registration_evidence_quality(
    *,
    worker_set_evidence_valid: bool,
    source_stale: bool,
    source_conflict: bool,
) -> tuple[str, list[str]]:
    return _quality_from_domain_flags(
        evidence_valid=worker_set_evidence_valid,
        source_stale=source_stale,
        source_conflict=source_conflict,
    )


def wage_evidence_quality(
    *,
    wage_evidence_valid: bool,
    source_stale: bool,
    source_conflict: bool,
) -> tuple[str, list[str]]:
    return _quality_from_domain_flags(
        evidence_valid=wage_evidence_valid,
        source_stale=source_stale,
        source_conflict=source_conflict,
    )


def contribution_evidence_quality(
    *,
    payment_evidence_valid: bool,
    source_stale: bool,
    source_conflict: bool,
    settlement_pending: bool,
) -> tuple[str, list[str]]:
    return _quality_from_domain_flags(
        evidence_valid=payment_evidence_valid,
        source_stale=source_stale,
        source_conflict=source_conflict,
        extra_low_reason="PAYMENT_SETTLEMENT_PENDING" if settlement_pending else None,
    )


def _evidence_gate(
    *,
    evidence_valid: bool,
    evidence_quality: object,
    invalid_reason: str,
) -> tuple[str, str] | None:
    if not evidence_valid:
        return "ABSTAIN", invalid_reason
    quality = _validate_evidence_quality(evidence_quality)
    if quality is None:
        return "ABSTAIN", "INVALID_OR_UNKNOWN_EVIDENCE_QUALITY"
    if quality == "LOW":
        return "ABSTAIN", "INSUFFICIENT_OR_CONFLICTING_EVIDENCE"
    if quality == "MEDIUM":
        return "NEEDS_ENRICHMENT", "EVIDENCE_ENRICHMENT_REQUIRED"
    return None


def derive_registration_state(
    *,
    missing_worker_count: int,
    unexpected_worker_count: int,
    evidence_valid: bool,
    evidence_quality: object,
    explanation_present: bool,
) -> tuple[str, str]:
    gated = _evidence_gate(
        evidence_valid=evidence_valid,
        evidence_quality=evidence_quality,
        invalid_reason="INVALID_OR_MISSING_REGISTRATION_EVIDENCE",
    )
    if gated is not None:
        return gated
    if explanation_present:
        return "NEEDS_ENRICHMENT", "EVIDENCE_ENRICHMENT_REQUIRED"
    if missing_worker_count <= 0 and unexpected_worker_count <= 0:
        return "NORMAL", "NO_REGISTRATION_SET_DISCREPANCY"
    return "REVIEW", "HUMAN_REVIEW_NO_AUTOMATED_PRIORITY"


def derive_wage_state(
    *,
    wage_discrepancy_signal_rp: int,
    evidence_valid: bool,
    evidence_quality: object,
) -> tuple[str, str]:
    gated = _evidence_gate(
        evidence_valid=evidence_valid,
        evidence_quality=evidence_quality,
        invalid_reason="INVALID_OR_MISSING_WAGE_EVIDENCE",
    )
    if gated is not None:
        return gated
    if wage_discrepancy_signal_rp <= 0:
        return "NORMAL", "NO_WAGE_DISCREPANCY"
    if not TRUSTED_B2_POLICY_CONTEXT_AUTHORIZED:
        return "ABSTAIN", "POLICY_REQUIRED_BUT_UNRESOLVED"
    raise RuntimeError("authorized B2 policy path is intentionally not implemented in this sandbox")


def derive_contribution_state(
    *,
    contribution_payment_evidence_gap: bool,
    evidence_valid: bool,
    evidence_quality: object,
) -> tuple[str, str]:
    gated = _evidence_gate(
        evidence_valid=evidence_valid,
        evidence_quality=evidence_quality,
        invalid_reason="INVALID_OR_MISSING_CONTRIBUTION_EVIDENCE",
    )
    if gated is not None:
        return gated
    if not contribution_payment_evidence_gap:
        return "NORMAL", "NO_CONTRIBUTION_PAYMENT_EVIDENCE_GAP"
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


def _valid_nonnegative_number(value: object) -> bool:
    if isinstance(value, bool):
        return False
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(number) and number >= 0


def _source_ids(*values: object) -> str:
    valid = [str(value) for value in values if isinstance(value, str) and value]
    return json.dumps(valid, separators=(",", ":"))


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
        reference_verified = bool(row.get("reference_worker_set_verified", False))
        observed_verified = bool(row.get("observed_worker_set_verified", False))
        worker_set_valid = reference_verified and observed_verified
        worker_set_error = "NONE"

        try:
            reference_set = parse_worker_set(
                row.get("reference_worker_set_json"),
                allow_empty=False,
            )
            observed_set = parse_worker_set(
                row.get("observed_registered_worker_set_json"),
                allow_empty=observed_verified,
            )
            reconciliation = reconcile_worker_sets(reference_set, observed_set)
        except (ValueError, json.JSONDecodeError, TypeError) as exc:
            worker_set_valid = False
            worker_set_error = type(exc).__name__
            reconciliation = None

        registration_quality, registration_quality_reasons = registration_evidence_quality(
            worker_set_evidence_valid=worker_set_valid,
            source_stale=row.get("registration_source_freshness") == "STALE",
            source_conflict=bool(row.get("registration_source_conflict", False)),
        )

        wage_evidence_valid = all(
            _valid_nonnegative_number(row.get(column))
            for column in (
                "reference_wage_signal_rp",
                "observed_wage_signal_rp",
                "wage_discrepancy_raw_rp",
            )
        )
        wage_quality, wage_quality_reasons = wage_evidence_quality(
            wage_evidence_valid=wage_evidence_valid,
            source_stale=row.get("wage_source_freshness") == "STALE",
            source_conflict=bool(row.get("wage_source_conflict", False)),
        )
        wage_gap = int(row["wage_discrepancy_raw_rp"]) if wage_evidence_valid else 0

        payment_state = row.get("payment_state_observed")
        bank_state = row.get("bank_observed_state")
        payment_evidence_valid = (
            payment_state in VALID_PAYMENT_STATES
            and bank_state in VALID_BANK_STATES
        )
        settlement_pending = bank_state == "SETTLEMENT_PENDING"
        contribution_quality, contribution_quality_reasons = contribution_evidence_quality(
            payment_evidence_valid=payment_evidence_valid,
            source_stale=row.get("contribution_source_freshness") == "STALE",
            source_conflict=bool(row.get("contribution_source_conflict", False)),
            settlement_pending=settlement_pending,
        )

        if payment_evidence_valid and bool(row.get("flag_bank_settlement_delay", False)):
            validated_payment_state = "PAID_ON_TIME"
            payment_reason = "BANK_SETTLEMENT_DELAY_VERIFIED_SYNTHETIC"
        elif payment_evidence_valid and settlement_pending:
            validated_payment_state = "UNKNOWN"
            payment_reason = "SETTLEMENT_PENDING__DO_NOT_ESCALATE"
        elif payment_evidence_valid:
            validated_payment_state = payment_state
            payment_reason = "NO_SETTLEMENT_EXCEPTION"
        else:
            validated_payment_state = "UNKNOWN"
            payment_reason = "INVALID_OR_MISSING_PAYMENT_EVIDENCE"

        contribution_gap = (
            validated_payment_state in {"UNPAID", "PAYMENT_PENDING", "UNKNOWN"}
            if payment_evidence_valid
            else False
        )

        explanation = (
            str(row.get("seasonal_or_project_reason"))
            if bool(row.get("seasonal_or_project_change_indicator", False))
            else "NONE"
        )

        missing_count = int(reconciliation["missing_worker_count"]) if reconciliation else 0
        unexpected_count = int(reconciliation["unexpected_worker_count"]) if reconciliation else 0

        registration_state, registration_reason = derive_registration_state(
            missing_worker_count=missing_count,
            unexpected_worker_count=unexpected_count,
            evidence_valid=worker_set_valid,
            evidence_quality=registration_quality,
            explanation_present=explanation != "NONE",
        )
        wage_state, wage_reason = derive_wage_state(
            wage_discrepancy_signal_rp=wage_gap,
            evidence_valid=wage_evidence_valid,
            evidence_quality=wage_quality,
        )
        contribution_state, contribution_reason = derive_contribution_state(
            contribution_payment_evidence_gap=contribution_gap,
            evidence_valid=payment_evidence_valid,
            evidence_quality=contribution_quality,
        )
        overall_state = derive_overall_review_state(
            registration_state,
            wage_state,
            contribution_state,
        )

        signal_types: list[str] = []
        if worker_set_valid and (missing_count > 0 or unexpected_count > 0):
            signal_types.append("WORKER_REGISTRATION_SET_DISCREPANCY")
        if wage_evidence_valid and wage_gap > 0:
            signal_types.append("WAGE_REPORTING_DISCREPANCY")
        if payment_evidence_valid and contribution_gap:
            signal_types.append("CONTRIBUTION_PAYMENT_EVIDENCE_GAP")

        reference_count = int(reconciliation["reference_count"]) if reconciliation else None
        observed_count = int(reconciliation["observed_count"]) if reconciliation else None
        missing_ids = reconciliation["missing_worker_ids"] if reconciliation else None
        unexpected_ids = reconciliation["unexpected_worker_ids"] if reconciliation else None
        sets_equal = bool(reconciliation["sets_equal"]) if reconciliation else None

        registration_source_ids = _source_ids(
            row.get("registration_reference_source_id"),
            row.get("registration_observed_source_id"),
        )
        wage_source_ids = _source_ids(
            row.get("wage_reference_source_id"),
            row.get("wage_observed_source_id"),
        )
        contribution_source_ids = _source_ids(
            row.get("contribution_expected_source_id"),
            row.get("contribution_payment_source_id"),
        )

        rows.append({
            "id_badan_usaha": row["id_badan_usaha"],
            "periode_bulan": row["periode_bulan"],
            "source_record_id": row["source_record_id"],

            "reference_worker_count": reference_count,
            "observed_registered_worker_count": observed_count,
            "missing_worker_count": missing_count if worker_set_valid else None,
            "unexpected_worker_count": unexpected_count if worker_set_valid else None,
            "missing_worker_ids_json": (
                json.dumps(missing_ids, separators=(",", ":")) if missing_ids is not None else None
            ),
            "unexpected_worker_ids_json": (
                json.dumps(unexpected_ids, separators=(",", ":")) if unexpected_ids is not None else None
            ),
            "worker_sets_equal": sets_equal,
            "worker_set_evidence_valid": worker_set_valid,
            "worker_set_evidence_error": worker_set_error,
            "worker_discrepancy_explanation": explanation,
            "registration_evidence_quality": registration_quality,
            "registration_evidence_reasons": (
                "|".join(registration_quality_reasons) if registration_quality_reasons else "NONE"
            ),
            "registration_signal_state": registration_state,
            "registration_signal_reason": registration_reason,
            "registration_rule_id": REGISTRATION_RULE_ID,
            "registration_source_ids_json": registration_source_ids,
            "registration_authority_dependency": "WORKER_REFERENCE_SET_AND_JKN_REGISTRATION_SET",
            "registration_lineage": (
                f"{registration_source_ids} -> set reconciliation -> {REGISTRATION_RULE_ID} "
                f"-> {registration_state}"
            ),

            "reference_wage_signal_rp": (
                int(row["reference_wage_signal_rp"]) if wage_evidence_valid else None
            ),
            "observed_wage_signal_rp": (
                int(row["observed_wage_signal_rp"]) if wage_evidence_valid else None
            ),
            "wage_discrepancy_signal_rp": wage_gap if wage_evidence_valid else None,
            "wage_evidence_valid": wage_evidence_valid,
            "wage_evidence_quality": wage_quality,
            "wage_evidence_reasons": (
                "|".join(wage_quality_reasons) if wage_quality_reasons else "NONE"
            ),
            "wage_signal_state": wage_state,
            "wage_signal_reason": wage_reason,
            "wage_rule_id": WAGE_RULE_ID,
            "wage_source_ids_json": wage_source_ids,
            "wage_authority_dependency": "WAGE_EVIDENCE_PLUS_TRUSTED_B2_POLICY_CONTEXT",
            "wage_lineage": (
                f"{wage_source_ids} -> wage evidence -> {WAGE_RULE_ID} -> {wage_state}"
            ),

            "estimated_exposure_synthetic_rp": (
                int(row["estimated_exposure_synthetic_rp"])
                if _valid_nonnegative_number(row.get("estimated_exposure_synthetic_rp"))
                else None
            ),
            "exposure_decision_role": "VISUALIZATION_ONLY__MUST_NOT_INFLUENCE_DECISION",
            "observed_payment_state": payment_state,
            "validated_payment_state": validated_payment_state,
            "payment_evidence_reason": payment_reason,
            "contribution_evidence_valid": payment_evidence_valid,
            "contribution_evidence_quality": contribution_quality,
            "contribution_evidence_reasons": (
                "|".join(contribution_quality_reasons)
                if contribution_quality_reasons else "NONE"
            ),
            "contribution_signal_state": contribution_state,
            "contribution_signal_reason": contribution_reason,
            "contribution_rule_id": CONTRIBUTION_RULE_ID,
            "contribution_source_ids_json": contribution_source_ids,
            "contribution_authority_dependency": "PAYMENT_EVIDENCE_PLUS_TRUSTED_B2_POLICY_CONTEXT",
            "contribution_lineage": (
                f"{contribution_source_ids} -> payment evidence -> {CONTRIBUTION_RULE_ID} "
                f"-> {contribution_state}"
            ),

            "overall_review_state": overall_state,
            "human_review_recommendation": overall_recommendation(overall_state),
            "risk_strength": UNSCORED,
            "risk_signal_types": "|".join(signal_types) if signal_types else "NONE",
            "trusted_policy_context_authorized": TRUSTED_B2_POLICY_CONTEXT_AUTHORIZED,
            "policy_effective_period": "UNVERIFIED",
            "policy_status_metadata_only": row.get("policy_status_metadata_only"),
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
    print("status: CURATED EVIDENCE READY; VALIDITY + QUALITY + PROVENANCE ISOLATED PER SIGNAL")


if __name__ == "__main__":
    main()
