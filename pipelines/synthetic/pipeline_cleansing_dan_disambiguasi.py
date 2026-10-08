"""Curate raw synthetic evidence with fail-closed per-signal semantics.

Invariants:
- evidence and provenance validity are checked before any NORMAL state;
- WAGE-001 and CONTRIB-001 cannot emit NORMAL while trusted B2 policy is unresolved;
- source metadata is required evidence, not decorative lineage;
- wage/payment fields are validated for cross-field semantic consistency;
- registration, wage, and contribution retain isolated quality/state/provenance.
"""

from __future__ import annotations

import json
import math
import re
from datetime import datetime, timedelta
from typing import Iterable

import numpy as np
import pandas as pd

from paths import CURATED_DIR, RAW_DIR, ensure_output_dirs

UNSCORED = "UNSCORED__THRESHOLDS_NOT_AUTHORIZED"
VALID_EVIDENCE_QUALITIES = {"HIGH", "MEDIUM", "LOW"}
VALID_SOURCE_FRESHNESS = {"CURRENT", "STALE"}
TRUSTED_B2_POLICY_CONTEXT_AUTHORIZED = False

# Registration authority is trusted implementation context, never row-provided metadata.
# It remains unresolved in this sandbox until an authoritative registry is available.
TRUSTED_REGISTRATION_REFERENCE_AUTHORITY = "UNRESOLVED"
TRUSTED_REGISTRATION_REFERENCE_AUTHORITY_VERIFIED = False
TRUSTED_REGISTRATION_RULE_VERSION = "UNVERIFIED"
TRUSTED_REGISTRATION_APPLICABLE_VERSION_VERIFIED = False

VALID_EXPLANATION_REASONS = {"PROJECT_OR_SEASON_END_SYNTHETIC"}

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
ALLOWED_PAYMENT_COMBINATIONS = {
    ("PAID_ON_TIME", "POSTED_ON_TIME", False),
    ("PAID_ON_TIME", "POSTED_NEXT_DAY", True),
    ("PAYMENT_PENDING", "SETTLEMENT_PENDING", False),
    ("UNPAID", "NO_PAYMENT_EVIDENCE", False),
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


def _strict_bool(value: object) -> bool | None:
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    return None


def _valid_source_id(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_source_metadata(
    *,
    source_ids: Iterable[object],
    freshness: object,
    conflict: object,
) -> dict[str, object]:
    ids = list(source_ids)
    ids_valid = bool(ids) and all(_valid_source_id(value) for value in ids)
    freshness_valid = isinstance(freshness, str) and freshness in VALID_SOURCE_FRESHNESS
    conflict_value = _strict_bool(conflict)
    conflict_valid = conflict_value is not None
    valid = ids_valid and freshness_valid and conflict_valid

    reasons: list[str] = []
    if not ids_valid:
        reasons.append("MISSING_OR_INVALID_SOURCE_ID")
    if not freshness_valid:
        reasons.append("MISSING_OR_INVALID_SOURCE_FRESHNESS")
    if not conflict_valid:
        reasons.append("MISSING_OR_INVALID_SOURCE_CONFLICT_STATE")

    return {
        "valid": valid,
        "source_ids": [str(value) for value in ids if _valid_source_id(value)],
        "source_stale": freshness == "STALE" if freshness_valid else False,
        "source_conflict": bool(conflict_value) if conflict_valid else False,
        "reasons": reasons,
    }


def trusted_registration_authority_context() -> dict[str, object]:
    return {
        "reference_authority": TRUSTED_REGISTRATION_REFERENCE_AUTHORITY,
        "reference_authority_verified": TRUSTED_REGISTRATION_REFERENCE_AUTHORITY_VERIFIED,
        "rule_version": TRUSTED_REGISTRATION_RULE_VERSION,
        "applicable_version_verified": TRUSTED_REGISTRATION_APPLICABLE_VERSION_VERIFIED,
        "context_source": "TRUSTED_IMPLEMENTATION_CONTEXT__NOT_ROW_DATA",
    }


def _is_missing_scalar(value: object) -> bool:
    if value is None:
        return True
    try:
        missing = pd.isna(value)
    except (TypeError, ValueError):
        return False
    return bool(missing) if isinstance(missing, (bool, np.bool_)) else False


def validate_explanation_metadata(
    *,
    indicator: object,
    reason: object,
) -> dict[str, object]:
    flag = _strict_bool(indicator)
    if flag is None:
        return {
            "valid": False,
            "present": False,
            "reason": "NONE",
            "validation_reason": "INVALID_EXPLANATION_INDICATOR",
        }

    if flag:
        if isinstance(reason, str) and reason in VALID_EXPLANATION_REASONS:
            return {
                "valid": True,
                "present": True,
                "reason": reason,
                "validation_reason": "NONE",
            }
        return {
            "valid": False,
            "present": False,
            "reason": "NONE",
            "validation_reason": "MISSING_OR_INVALID_EXPLANATION_REASON",
        }

    if _is_missing_scalar(reason) or reason == "NONE":
        return {
            "valid": True,
            "present": False,
            "reason": "NONE",
            "validation_reason": "NONE",
        }

    return {
        "valid": False,
        "present": False,
        "reason": "NONE",
        "validation_reason": "EXPLANATION_REASON_WITH_FALSE_INDICATOR",
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
    validity_reasons: Iterable[str] = (),
    extra_low_reason: str | None = None,
) -> tuple[str, list[str]]:
    reasons = list(validity_reasons)
    if not evidence_valid and "INVALID_OR_MISSING_EVIDENCE" not in reasons:
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
    evidence_valid: bool,
    source_stale: bool,
    source_conflict: bool,
    validity_reasons: Iterable[str] = (),
) -> tuple[str, list[str]]:
    return _quality_from_domain_flags(
        evidence_valid=evidence_valid,
        source_stale=source_stale,
        source_conflict=source_conflict,
        validity_reasons=validity_reasons,
    )


def wage_evidence_quality(
    *,
    evidence_valid: bool,
    source_stale: bool,
    source_conflict: bool,
    validity_reasons: Iterable[str] = (),
) -> tuple[str, list[str]]:
    return _quality_from_domain_flags(
        evidence_valid=evidence_valid,
        source_stale=source_stale,
        source_conflict=source_conflict,
        validity_reasons=validity_reasons,
    )


def contribution_evidence_quality(
    *,
    evidence_valid: bool,
    source_stale: bool,
    source_conflict: bool,
    settlement_pending: bool,
    validity_reasons: Iterable[str] = (),
) -> tuple[str, list[str]]:
    return _quality_from_domain_flags(
        evidence_valid=evidence_valid,
        source_stale=source_stale,
        source_conflict=source_conflict,
        validity_reasons=validity_reasons,
        extra_low_reason="PAYMENT_SETTLEMENT_PENDING" if settlement_pending else None,
    )


def _invalid_evidence_gate(
    *,
    evidence_valid: bool,
    evidence_quality: object,
    invalid_reason: str,
) -> tuple[str, str] | None:
    if not evidence_valid:
        return "ABSTAIN", invalid_reason
    if _validate_evidence_quality(evidence_quality) is None:
        return "ABSTAIN", "INVALID_OR_UNKNOWN_EVIDENCE_QUALITY"
    return None


def _quality_gate(evidence_quality: object) -> tuple[str, str] | None:
    quality = _validate_evidence_quality(evidence_quality)
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
    reference_authority_verified: bool | None = None,
    applicable_version_verified: bool | None = None,
) -> tuple[str, str]:
    invalid = _invalid_evidence_gate(
        evidence_valid=evidence_valid,
        evidence_quality=evidence_quality,
        invalid_reason="INVALID_OR_MISSING_REGISTRATION_EVIDENCE",
    )
    if invalid is not None:
        return invalid

    authority_verified = (
        TRUSTED_REGISTRATION_REFERENCE_AUTHORITY_VERIFIED
        if reference_authority_verified is None
        else reference_authority_verified
    )
    version_verified = (
        TRUSTED_REGISTRATION_APPLICABLE_VERSION_VERIFIED
        if applicable_version_verified is None
        else applicable_version_verified
    )
    if authority_verified is not True or version_verified is not True:
        return "ABSTAIN", "REFERENCE_AUTHORITY_OR_RULE_VERSION_UNRESOLVED"

    quality_gate = _quality_gate(evidence_quality)
    if quality_gate is not None:
        return quality_gate
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
    invalid = _invalid_evidence_gate(
        evidence_valid=evidence_valid,
        evidence_quality=evidence_quality,
        invalid_reason="INVALID_OR_MISSING_WAGE_EVIDENCE",
    )
    if invalid is not None:
        return invalid

    # WAGE-001 requires trusted applicable-policy context even to conclude NORMAL.
    if not TRUSTED_B2_POLICY_CONTEXT_AUTHORIZED:
        return "ABSTAIN", "POLICY_REQUIRED_BUT_UNRESOLVED"

    quality_gate = _quality_gate(evidence_quality)
    if quality_gate is not None:
        return quality_gate
    if wage_discrepancy_signal_rp <= 0:
        return "NORMAL", "NO_WAGE_DISCREPANCY"
    raise RuntimeError("authorized B2 wage evaluation path is intentionally not implemented")


def derive_contribution_state(
    *,
    contribution_payment_evidence_gap: bool,
    evidence_valid: bool,
    evidence_quality: object,
) -> tuple[str, str]:
    invalid = _invalid_evidence_gate(
        evidence_valid=evidence_valid,
        evidence_quality=evidence_quality,
        invalid_reason="INVALID_OR_MISSING_CONTRIBUTION_EVIDENCE",
    )
    if invalid is not None:
        return invalid

    # CONTRIB-001 needs applicable contribution policy before NORMAL is knowable.
    if not TRUSTED_B2_POLICY_CONTEXT_AUTHORIZED:
        return "ABSTAIN", "POLICY_REQUIRED_BUT_UNRESOLVED"

    quality_gate = _quality_gate(evidence_quality)
    if quality_gate is not None:
        return quality_gate
    if not contribution_payment_evidence_gap:
        return "NORMAL", "NO_CONTRIBUTION_PAYMENT_EVIDENCE_GAP"
    raise RuntimeError("authorized B2 contribution evaluation path is intentionally not implemented")


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
    if isinstance(value, (bool, np.bool_)):
        return False
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(number) and number >= 0


def validate_wage_semantics(
    *,
    reference_wage: object,
    observed_wage: object,
    supplied_discrepancy: object,
) -> dict[str, object]:
    values_valid = all(
        _valid_nonnegative_number(value)
        for value in (reference_wage, observed_wage, supplied_discrepancy)
    )
    if not values_valid:
        return {
            "valid": False,
            "derived_discrepancy": None,
            "reason": "INVALID_WAGE_NUMERIC_EVIDENCE",
        }

    reference = float(reference_wage)
    observed = float(observed_wage)
    supplied = float(supplied_discrepancy)
    derived = max(0.0, reference - observed)
    consistent = math.isclose(supplied, derived, rel_tol=0.0, abs_tol=0.5)

    return {
        "valid": consistent,
        "derived_discrepancy": int(round(derived)),
        "reason": "NONE" if consistent else "INCONSISTENT_WAGE_DISCREPANCY",
    }


def _parse_timestamp_strict(value: object) -> dict[str, object]:
    if _is_missing_scalar(value):
        return {"present": False, "valid": True, "value": None}
    if not isinstance(value, str) or not value.strip():
        return {"present": True, "valid": False, "value": None}
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return {"present": True, "valid": False, "value": None}
    return {"present": True, "valid": True, "value": parsed}


def validate_payment_semantics(
    *,
    payment_state: object,
    bank_state: object,
    settlement_delay_flag: object,
    payer_timestamp: object,
    bank_timestamp: object,
) -> dict[str, object]:
    flag = _strict_bool(settlement_delay_flag)
    enum_valid = (
        payment_state in VALID_PAYMENT_STATES
        and bank_state in VALID_BANK_STATES
        and flag is not None
    )
    if not enum_valid:
        return {
            "valid": False,
            "settlement_pending": False,
            "validated_payment_state": "UNKNOWN",
            "reason": "INVALID_PAYMENT_ENUM_OR_FLAG",
        }

    combination = (payment_state, bank_state, flag)
    if combination not in ALLOWED_PAYMENT_COMBINATIONS:
        return {
            "valid": False,
            "settlement_pending": bank_state == "SETTLEMENT_PENDING",
            "validated_payment_state": "UNKNOWN",
            "reason": "INCONSISTENT_PAYMENT_STATE_COMBINATION",
        }

    payer = _parse_timestamp_strict(payer_timestamp)
    bank = _parse_timestamp_strict(bank_timestamp)
    if (payer["present"] and not payer["valid"]) or (bank["present"] and not bank["valid"]):
        return {
            "valid": False,
            "settlement_pending": bank_state == "SETTLEMENT_PENDING",
            "validated_payment_state": "UNKNOWN",
            "reason": "INVALID_PAYMENT_TIMESTAMP_FORMAT",
        }

    if combination == ("PAID_ON_TIME", "POSTED_ON_TIME", False):
        if not payer["present"] or not bank["present"]:
            reason = "INCONSISTENT_PAYMENT_TIMESTAMPS"
        elif bank["value"] < payer["value"]:
            reason = "INCONSISTENT_PAYMENT_CHRONOLOGY"
        elif bank["value"].date() != payer["value"].date():
            reason = "INCONSISTENT_PAYMENT_DATE_RELATIONSHIP"
        else:
            reason = "NONE"
    elif combination == ("PAID_ON_TIME", "POSTED_NEXT_DAY", True):
        if not payer["present"] or not bank["present"]:
            reason = "INCONSISTENT_PAYMENT_TIMESTAMPS"
        elif bank["value"] <= payer["value"]:
            reason = "INCONSISTENT_PAYMENT_CHRONOLOGY"
        elif bank["value"].date() != payer["value"].date() + timedelta(days=1):
            reason = "INCONSISTENT_PAYMENT_DATE_RELATIONSHIP"
        else:
            reason = "NONE"
    elif combination == ("PAYMENT_PENDING", "SETTLEMENT_PENDING", False):
        reason = (
            "NONE"
            if payer["present"] and not bank["present"]
            else "INCONSISTENT_PAYMENT_TIMESTAMPS"
        )
    else:
        reason = (
            "NONE"
            if not payer["present"] and not bank["present"]
            else "INCONSISTENT_PAYMENT_TIMESTAMPS"
        )

    if reason != "NONE":
        return {
            "valid": False,
            "settlement_pending": bank_state == "SETTLEMENT_PENDING",
            "validated_payment_state": "UNKNOWN",
            "reason": reason,
        }

    validated = (
        "PAID_ON_TIME"
        if payment_state == "PAID_ON_TIME"
        else "UNKNOWN"
        if payment_state == "PAYMENT_PENDING"
        else "UNPAID"
    )
    return {
        "valid": True,
        "settlement_pending": bank_state == "SETTLEMENT_PENDING",
        "validated_payment_state": validated,
        "reason": (
            "BANK_SETTLEMENT_DELAY_VERIFIED_SYNTHETIC"
            if combination == ("PAID_ON_TIME", "POSTED_NEXT_DAY", True)
            else "SETTLEMENT_PENDING__DO_NOT_ESCALATE"
            if combination == ("PAYMENT_PENDING", "SETTLEMENT_PENDING", False)
            else "NO_SETTLEMENT_EXCEPTION"
        ),
    }


def _source_ids_json(source_metadata: dict[str, object]) -> str:

def _source_ids_json(source_metadata: dict[str, object]) -> str:
    return json.dumps(source_metadata["source_ids"], separators=(",", ":"))


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
        registration_source = validate_source_metadata(
            source_ids=(
                row.get("registration_reference_source_id"),
                row.get("registration_observed_source_id"),
            ),
            freshness=row.get("registration_source_freshness"),
            conflict=row.get("registration_source_conflict"),
        )

        reference_verified = _strict_bool(row.get("reference_worker_set_verified"))
        observed_verified = _strict_bool(row.get("observed_worker_set_verified"))
        worker_verification_valid = reference_verified is True and observed_verified is True
        worker_set_valid = worker_verification_valid
        worker_set_error = "NONE"
        reconciliation = None

        try:
            reference_set = parse_worker_set(
                row.get("reference_worker_set_json"),
                allow_empty=False,
            )
            observed_set = parse_worker_set(
                row.get("observed_registered_worker_set_json"),
                allow_empty=observed_verified is True,
            )
            reconciliation = reconcile_worker_sets(reference_set, observed_set)
        except (ValueError, json.JSONDecodeError, TypeError) as exc:
            worker_set_valid = False
            worker_set_error = type(exc).__name__

        explanation_metadata = validate_explanation_metadata(
            indicator=row.get("seasonal_or_project_change_indicator"),
            reason=row.get("seasonal_or_project_reason"),
        )
        registration_authority = trusted_registration_authority_context()

        registration_evidence_valid = (
            worker_set_valid
            and bool(registration_source["valid"])
            and bool(explanation_metadata["valid"])
        )
        registration_validity_reasons = list(registration_source["reasons"])
        if not worker_verification_valid:
            registration_validity_reasons.append("INVALID_WORKER_SET_VERIFICATION_STATE")
        if not worker_set_valid:
            registration_validity_reasons.append("INVALID_WORKER_SET_EVIDENCE")
        if not bool(explanation_metadata["valid"]):
            registration_validity_reasons.append(
                str(explanation_metadata["validation_reason"])
            )

        registration_quality, registration_quality_reasons = registration_evidence_quality(
            evidence_valid=registration_evidence_valid,
            source_stale=bool(registration_source["source_stale"]),
            source_conflict=bool(registration_source["source_conflict"]),
            validity_reasons=registration_validity_reasons,
        )

        wage_source = validate_source_metadata(
            source_ids=(
                row.get("wage_reference_source_id"),
                row.get("wage_observed_source_id"),
            ),
            freshness=row.get("wage_source_freshness"),
            conflict=row.get("wage_source_conflict"),
        )
        wage_semantics = validate_wage_semantics(
            reference_wage=row.get("reference_wage_signal_rp"),
            observed_wage=row.get("observed_wage_signal_rp"),
            supplied_discrepancy=row.get("wage_discrepancy_raw_rp"),
        )
        wage_evidence_valid = bool(wage_source["valid"]) and bool(wage_semantics["valid"])
        wage_validity_reasons = list(wage_source["reasons"])
        if wage_semantics["reason"] != "NONE":
            wage_validity_reasons.append(str(wage_semantics["reason"]))

        wage_quality, wage_quality_reasons = wage_evidence_quality(
            evidence_valid=wage_evidence_valid,
            source_stale=bool(wage_source["source_stale"]),
            source_conflict=bool(wage_source["source_conflict"]),
            validity_reasons=wage_validity_reasons,
        )
        wage_gap = (
            int(wage_semantics["derived_discrepancy"])
            if wage_semantics["derived_discrepancy"] is not None
            else 0
        )

        contribution_source = validate_source_metadata(
            source_ids=(
                row.get("contribution_expected_source_id"),
                row.get("contribution_payment_source_id"),
            ),
            freshness=row.get("contribution_source_freshness"),
            conflict=row.get("contribution_source_conflict"),
        )
        payment_semantics = validate_payment_semantics(
            payment_state=row.get("payment_state_observed"),
            bank_state=row.get("bank_observed_state"),
            settlement_delay_flag=row.get("flag_bank_settlement_delay"),
            payer_timestamp=row.get("payer_timestamp_synthetic"),
            bank_timestamp=row.get("bank_posting_timestamp_synthetic"),
        )
        contribution_evidence_valid = (
            bool(contribution_source["valid"])
            and bool(payment_semantics["valid"])
        )
        contribution_validity_reasons = list(contribution_source["reasons"])
        if not bool(payment_semantics["valid"]):
            contribution_validity_reasons.append(str(payment_semantics["reason"]))

        settlement_pending = bool(payment_semantics["settlement_pending"])
        contribution_quality, contribution_quality_reasons = contribution_evidence_quality(
            evidence_valid=contribution_evidence_valid,
            source_stale=bool(contribution_source["source_stale"]),
            source_conflict=bool(contribution_source["source_conflict"]),
            settlement_pending=settlement_pending,
            validity_reasons=contribution_validity_reasons,
        )

        validated_payment_state = str(payment_semantics["validated_payment_state"])
        payment_reason = str(payment_semantics["reason"])
        contribution_gap = (
            validated_payment_state in {"UNPAID", "UNKNOWN"}
            if contribution_evidence_valid
            else False
        )

        explanation = str(explanation_metadata["reason"])

        missing_count = int(reconciliation["missing_worker_count"]) if reconciliation else 0
        unexpected_count = int(reconciliation["unexpected_worker_count"]) if reconciliation else 0

        registration_state, registration_reason = derive_registration_state(
            missing_worker_count=missing_count,
            unexpected_worker_count=unexpected_count,
            evidence_valid=registration_evidence_valid,
            evidence_quality=registration_quality,
            explanation_present=bool(explanation_metadata["present"]),
            reference_authority_verified=bool(
                registration_authority["reference_authority_verified"]
            ),
            applicable_version_verified=bool(
                registration_authority["applicable_version_verified"]
            ),
        )
        wage_state, wage_reason = derive_wage_state(
            wage_discrepancy_signal_rp=wage_gap,
            evidence_valid=wage_evidence_valid,
            evidence_quality=wage_quality,
        )
        contribution_state, contribution_reason = derive_contribution_state(
            contribution_payment_evidence_gap=contribution_gap,
            evidence_valid=contribution_evidence_valid,
            evidence_quality=contribution_quality,
        )
        overall_state = derive_overall_review_state(
            registration_state,
            wage_state,
            contribution_state,
        )

        signal_types: list[str] = []
        if registration_evidence_valid and (missing_count > 0 or unexpected_count > 0):
            signal_types.append("WORKER_REGISTRATION_SET_DISCREPANCY")
        if wage_evidence_valid and wage_gap > 0:
            signal_types.append("WAGE_REPORTING_DISCREPANCY")
        if contribution_evidence_valid and contribution_gap:
            signal_types.append("CONTRIBUTION_PAYMENT_EVIDENCE_GAP")

        reference_count = int(reconciliation["reference_count"]) if reconciliation else None
        observed_count = int(reconciliation["observed_count"]) if reconciliation else None
        missing_ids = reconciliation["missing_worker_ids"] if reconciliation else None
        unexpected_ids = reconciliation["unexpected_worker_ids"] if reconciliation else None
        sets_equal = bool(reconciliation["sets_equal"]) if reconciliation else None

        registration_source_ids = _source_ids_json(registration_source)
        wage_source_ids = _source_ids_json(wage_source)
        contribution_source_ids = _source_ids_json(contribution_source)

        rows.append({
            "id_badan_usaha": row["id_badan_usaha"],
            "periode_bulan": row["periode_bulan"],
            "source_record_id": row["source_record_id"],

            "reference_worker_count": reference_count,
            "observed_registered_worker_count": observed_count,
            "missing_worker_count": missing_count if registration_evidence_valid else None,
            "unexpected_worker_count": unexpected_count if registration_evidence_valid else None,
            "missing_worker_ids_json": (
                json.dumps(missing_ids, separators=(",", ":")) if missing_ids is not None else None
            ),
            "unexpected_worker_ids_json": (
                json.dumps(unexpected_ids, separators=(",", ":")) if unexpected_ids is not None else None
            ),
            "worker_sets_equal": sets_equal,
            "worker_set_evidence_valid": worker_set_valid,
            "registration_source_metadata_valid": bool(registration_source["valid"]),
            "registration_explanation_metadata_valid": bool(explanation_metadata["valid"]),
            "registration_explanation_metadata_reason": str(
                explanation_metadata["validation_reason"]
            ),
            "registration_evidence_valid": registration_evidence_valid,
            "worker_set_evidence_error": worker_set_error,
            "worker_discrepancy_explanation": explanation,
            "registration_reference_authority": str(
                registration_authority["reference_authority"]
            ),
            "registration_reference_authority_verified": bool(
                registration_authority["reference_authority_verified"]
            ),
            "registration_rule_version": str(registration_authority["rule_version"]),
            "registration_applicable_version_verified": bool(
                registration_authority["applicable_version_verified"]
            ),
            "registration_authority_context_source": str(
                registration_authority["context_source"]
            ),
            "registration_evidence_quality": registration_quality,
            "registration_evidence_reasons": (
                "|".join(registration_quality_reasons) if registration_quality_reasons else "NONE"
            ),
            "registration_signal_state": registration_state,
            "registration_signal_reason": registration_reason,
            "registration_rule_id": REGISTRATION_RULE_ID,
            "registration_source_ids_json": registration_source_ids,
            "registration_authority_dependency": (
                "TRUSTED_REFERENCE_AUTHORITY_AND_APPLICABLE_RULE_VERSION"
            ),
            "registration_lineage": (
                f"{registration_source_ids} -> set reconciliation -> "
                f"authority={registration_authority['reference_authority']} -> "
                f"rule={REGISTRATION_RULE_ID}@{registration_authority['rule_version']} -> "
                f"{registration_state}"
            ),

            "reference_wage_signal_rp": (
                int(row["reference_wage_signal_rp"])
                if wage_semantics["derived_discrepancy"] is not None else None
            ),
            "observed_wage_signal_rp": (
                int(row["observed_wage_signal_rp"])
                if wage_semantics["derived_discrepancy"] is not None else None
            ),
            "wage_discrepancy_signal_rp": (
                wage_gap if wage_semantics["derived_discrepancy"] is not None else None
            ),
            "wage_source_metadata_valid": bool(wage_source["valid"]),
            "wage_semantic_consistency_valid": bool(wage_semantics["valid"]),
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
                f"{wage_source_ids} -> wage consistency validation -> {WAGE_RULE_ID} "
                f"-> {wage_state}"
            ),

            "estimated_exposure_synthetic_rp": (
                int(row["estimated_exposure_synthetic_rp"])
                if _valid_nonnegative_number(row.get("estimated_exposure_synthetic_rp"))
                else None
            ),
            "exposure_decision_role": "VISUALIZATION_ONLY__MUST_NOT_INFLUENCE_DECISION",
            "observed_payment_state": row.get("payment_state_observed"),
            "validated_payment_state": validated_payment_state,
            "payment_evidence_reason": payment_reason,
            "contribution_source_metadata_valid": bool(contribution_source["valid"]),
            "payment_semantic_consistency_valid": bool(payment_semantics["valid"]),
            "contribution_evidence_valid": contribution_evidence_valid,
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
                f"{contribution_source_ids} -> payment consistency validation -> "
                f"{CONTRIBUTION_RULE_ID} -> {contribution_state}"
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
    print("status: CURATED EVIDENCE READY; POLICY + PROVENANCE + CROSS-FIELD GATES FAIL CLOSED")


if __name__ == "__main__":
    main()
