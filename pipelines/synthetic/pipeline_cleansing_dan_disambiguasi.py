"""Final synthetic data decision layer for JAGA-JKN.

Pipeline semantics are deliberately separated:
EVIDENCE -> OBSERVATION -> RULE RESULT -> WORKFLOW STATE -> PRESENTATION.

Raw evidence never authorizes itself. Rule evaluators consume immutable trusted
contexts from trusted_context.py. Synthetic exposure is presentation-only.
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
from trusted_context import (
    CONTRIBUTION_POLICY_CONTEXT,
    REGISTRATION_AUTHORITY_CONTEXT,
    WAGE_POLICY_CONTEXT,
    RuleAuthorityContext,
)

REGISTRATION_RULE_ID = "REG-001"
WAGE_RULE_ID = "WAGE-001"
CONTRIBUTION_RULE_ID = "CONTRIB-001"

REGISTRATION_RULE_RESULTS = {
    "CONSISTENT",
    "POTENTIAL_REGISTRATION_GAP",
    "ABSTAIN",
}
WAGE_RULE_RESULTS = {
    "CONSISTENT",
    "POTENTIAL_WAGE_DIVERGENCE",
    "ABSTAIN",
}
CONTRIBUTION_RULE_RESULTS = {
    "CONSISTENT",
    "POTENTIAL_CONTRIBUTION_IRREGULARITY",
    "ABSTAIN",
}
REVIEW_STATES = {"NORMAL", "REVIEW", "NEEDS_ENRICHMENT", "ABSTAIN"}
OVERALL_REVIEW_STATES = REVIEW_STATES | {"PARTIAL"}

VALID_EVIDENCE_QUALITIES = {"HIGH", "MEDIUM", "LOW"}
VALID_SOURCE_FRESHNESS = {"CURRENT", "STALE"}
VALID_EXPLANATION_REASONS = {"PROJECT_OR_SEASON_END_SYNTHETIC"}
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

AUTHORITY_UNRESOLVED_REASON = "AUTHORITY_OR_APPLICABLE_VERSION_UNRESOLVED"
POLICY_UNRESOLVED_REASON = "POLICY_REQUIRED_BUT_UNRESOLVED"
EVIDENCE_INVALID_REASON = "INVALID_OR_MISSING_EVIDENCE"
EVIDENCE_QUALITY_REASON = "EVIDENCE_QUALITY_INSUFFICIENT"


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
    return (
        f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}."
        f"{digits[8]}-{digits[9:12]}.{digits[12:]}"
    )


def _strict_bool(value: object) -> bool | None:
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    return None


def _is_missing_scalar(value: object) -> bool:
    if value is None:
        return True
    try:
        missing = pd.isna(value)
    except (TypeError, ValueError):
        return False
    return bool(missing) if isinstance(missing, (bool, np.bool_)) else False


def _valid_period(value: object) -> bool:
    if not isinstance(value, str):
        return False
    return re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", value) is not None


def _valid_source_id(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _valid_nonnegative_number(value: object) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return False
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(number) and number >= 0


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


def validate_source_metadata(
    *,
    source_ids: Iterable[object],
    source_periods: Iterable[object],
    evaluated_period: object,
    freshness: object,
    conflict: object,
) -> dict[str, object]:
    ids = list(source_ids)
    periods = list(source_periods)

    ids_valid = bool(ids) and all(_valid_source_id(value) for value in ids)
    evaluated_period_valid = _valid_period(evaluated_period)
    periods_valid = (
        bool(periods)
        and all(_valid_period(value) for value in periods)
        and evaluated_period_valid
        and all(value == evaluated_period for value in periods)
    )
    freshness_valid = (
        isinstance(freshness, str) and freshness in VALID_SOURCE_FRESHNESS
    )
    conflict_value = _strict_bool(conflict)
    conflict_valid = conflict_value is not None

    reasons: list[str] = []
    if not ids_valid:
        reasons.append("MISSING_OR_INVALID_SOURCE_ID")
    if not periods_valid:
        reasons.append("SOURCE_PERIOD_MISMATCH_OR_INVALID")
    if not freshness_valid:
        reasons.append("MISSING_OR_INVALID_SOURCE_FRESHNESS")
    if not conflict_valid:
        reasons.append("MISSING_OR_INVALID_SOURCE_CONFLICT_STATE")

    return {
        "valid": ids_valid and periods_valid and freshness_valid and conflict_valid,
        "source_ids": [str(value) for value in ids if _valid_source_id(value)],
        "source_periods": [
            str(value) for value in periods if isinstance(value, str)
        ],
        "period_binding_valid": periods_valid,
        "source_stale": freshness == "STALE" if freshness_valid else False,
        "source_conflict": bool(conflict_value) if conflict_valid else False,
        "reasons": reasons,
    }


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


def _quality_from_flags(
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
            "discrepancy_detected": None,
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
        "discrepancy_detected": derived > 0,
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
    evaluated_period: object,
    payment_state: object,
    bank_state: object,
    settlement_delay_flag: object,
    payer_timestamp: object,
    bank_timestamp: object,
) -> dict[str, object]:
    flag = _strict_bool(settlement_delay_flag)
    if (
        not _valid_period(evaluated_period)
        or payment_state not in VALID_PAYMENT_STATES
        or bank_state not in VALID_BANK_STATES
        or flag is None
    ):
        return {
            "valid": False,
            "payment_gap_observed": None,
            "validated_payment_state": "UNKNOWN",
            "settlement_pending": False,
            "reason": "INVALID_PAYMENT_ENUM_FLAG_OR_PERIOD",
        }

    combination = (payment_state, bank_state, flag)
    if combination not in ALLOWED_PAYMENT_COMBINATIONS:
        return {
            "valid": False,
            "payment_gap_observed": None,
            "validated_payment_state": "UNKNOWN",
            "settlement_pending": bank_state == "SETTLEMENT_PENDING",
            "reason": "INCONSISTENT_PAYMENT_STATE_COMBINATION",
        }

    payer = _parse_timestamp_strict(payer_timestamp)
    bank = _parse_timestamp_strict(bank_timestamp)
    if (payer["present"] and not payer["valid"]) or (
        bank["present"] and not bank["valid"]
    ):
        return {
            "valid": False,
            "payment_gap_observed": None,
            "validated_payment_state": "UNKNOWN",
            "settlement_pending": bank_state == "SETTLEMENT_PENDING",
            "reason": "INVALID_PAYMENT_TIMESTAMP_FORMAT",
        }

    evaluated = str(evaluated_period)

    if combination == ("PAID_ON_TIME", "POSTED_ON_TIME", False):
        valid = (
            payer["present"]
            and bank["present"]
            and payer["value"].strftime("%Y-%m") == evaluated
            and bank["value"] >= payer["value"]
            and bank["value"].date() == payer["value"].date()
        )
        reason = "NONE" if valid else "INCONSISTENT_PAYMENT_TEMPORAL_BINDING"
    elif combination == ("PAID_ON_TIME", "POSTED_NEXT_DAY", True):
        valid = (
            payer["present"]
            and bank["present"]
            and payer["value"].strftime("%Y-%m") == evaluated
            and bank["value"] > payer["value"]
            and bank["value"].date() == payer["value"].date() + timedelta(days=1)
        )
        reason = "NONE" if valid else "INCONSISTENT_PAYMENT_TEMPORAL_BINDING"
    elif combination == ("PAYMENT_PENDING", "SETTLEMENT_PENDING", False):
        valid = (
            payer["present"]
            and not bank["present"]
            and payer["value"].strftime("%Y-%m") == evaluated
        )
        reason = "NONE" if valid else "INCONSISTENT_PAYMENT_TEMPORAL_BINDING"
    else:
        valid = not payer["present"] and not bank["present"]
        reason = "NONE" if valid else "INCONSISTENT_PAYMENT_TEMPORAL_BINDING"

    if not valid:
        return {
            "valid": False,
            "payment_gap_observed": None,
            "validated_payment_state": "UNKNOWN",
            "settlement_pending": bank_state == "SETTLEMENT_PENDING",
            "reason": reason,
        }

    validated_state = (
        "PAID_ON_TIME"
        if payment_state == "PAID_ON_TIME"
        else "UNKNOWN"
        if payment_state == "PAYMENT_PENDING"
        else "UNPAID"
    )
    return {
        "valid": True,
        "payment_gap_observed": payment_state in {"PAYMENT_PENDING", "UNPAID"},
        "validated_payment_state": validated_state,
        "settlement_pending": bank_state == "SETTLEMENT_PENDING",
        "reason": (
            "BANK_SETTLEMENT_DELAY_VERIFIED_SYNTHETIC"
            if combination == ("PAID_ON_TIME", "POSTED_NEXT_DAY", True)
            else "SETTLEMENT_PENDING__DO_NOT_ESCALATE"
            if combination == ("PAYMENT_PENDING", "SETTLEMENT_PENDING", False)
            else "NO_SETTLEMENT_EXCEPTION"
        ),
    }


def _context_ready(context: RuleAuthorityContext) -> bool:
    return context.authorized and context.applicable_period_verified


def _evaluate_registration_rule_with_context(
    evidence: dict[str, object],
    context: RuleAuthorityContext,
) -> tuple[str, str]:
    if not _context_ready(context):
        return "ABSTAIN", AUTHORITY_UNRESOLVED_REASON
    if not bool(evidence["valid"]):
        return "ABSTAIN", EVIDENCE_INVALID_REASON
    if evidence["quality"] != "HIGH":
        return "ABSTAIN", EVIDENCE_QUALITY_REASON
    if bool(evidence["discrepancy_detected"]):
        return "POTENTIAL_REGISTRATION_GAP", "OBSERVED_SET_DISCREPANCY"
    return "CONSISTENT", "NO_OBSERVED_REGISTRATION_DISCREPANCY"


def _evaluate_wage_rule_with_context(
    evidence: dict[str, object],
    context: RuleAuthorityContext,
) -> tuple[str, str]:
    if not _context_ready(context):
        return "ABSTAIN", POLICY_UNRESOLVED_REASON
    if not bool(evidence["valid"]):
        return "ABSTAIN", EVIDENCE_INVALID_REASON
    if evidence["quality"] != "HIGH":
        return "ABSTAIN", EVIDENCE_QUALITY_REASON
    if bool(evidence["discrepancy_detected"]):
        return "POTENTIAL_WAGE_DIVERGENCE", "OBSERVED_WAGE_DISCREPANCY"
    return "CONSISTENT", "NO_OBSERVED_WAGE_DISCREPANCY"


def _evaluate_contribution_rule_with_context(
    evidence: dict[str, object],
    context: RuleAuthorityContext,
) -> tuple[str, str]:
    if not _context_ready(context):
        return "ABSTAIN", POLICY_UNRESOLVED_REASON
    if not bool(evidence["valid"]):
        return "ABSTAIN", EVIDENCE_INVALID_REASON
    if evidence["quality"] != "HIGH":
        return "ABSTAIN", EVIDENCE_QUALITY_REASON
    if bool(evidence["discrepancy_detected"]):
        return (
            "POTENTIAL_CONTRIBUTION_IRREGULARITY",
            "OBSERVED_CONTRIBUTION_PAYMENT_GAP",
        )
    return "CONSISTENT", "NO_OBSERVED_CONTRIBUTION_PAYMENT_GAP"


def evaluate_registration_rule(
    evidence: dict[str, object],
) -> tuple[str, str]:
    return _evaluate_registration_rule_with_context(
        evidence,
        REGISTRATION_AUTHORITY_CONTEXT,
    )


def evaluate_wage_rule(evidence: dict[str, object]) -> tuple[str, str]:
    return _evaluate_wage_rule_with_context(evidence, WAGE_POLICY_CONTEXT)


def evaluate_contribution_rule(
    evidence: dict[str, object],
) -> tuple[str, str]:
    return _evaluate_contribution_rule_with_context(
        evidence,
        CONTRIBUTION_POLICY_CONTEXT,
    )


def _map_review_state(
    *,
    rule_result: str,
    rule_reason: str,
    potential_result: str,
    evidence_valid: bool,
    evidence_quality: str,
    legitimate_explanation_present: bool = False,
) -> tuple[str, str]:
    if rule_result == "CONSISTENT":
        return "NORMAL", "RULE_RESULT_CONSISTENT"
    if rule_result == potential_result:
        if legitimate_explanation_present:
            return "NEEDS_ENRICHMENT", "LEGITIMATE_EXPLANATION_REQUIRES_ENRICHMENT"
        return "REVIEW", "POTENTIAL_SIGNAL_REQUIRES_HUMAN_REVIEW"
    if rule_result != "ABSTAIN":
        raise ValueError(f"unsupported rule result: {rule_result}")

    if rule_reason in {AUTHORITY_UNRESOLVED_REASON, POLICY_UNRESOLVED_REASON}:
        return "ABSTAIN", rule_reason
    if not evidence_valid or evidence_quality in {"LOW", "MEDIUM"}:
        return "NEEDS_ENRICHMENT", "EVIDENCE_ENRICHMENT_REQUIRED"
    return "ABSTAIN", rule_reason


def map_registration_review_state(
    *,
    rule_result: str,
    rule_reason: str,
    evidence_valid: bool,
    evidence_quality: str,
    legitimate_explanation_present: bool,
) -> tuple[str, str]:
    return _map_review_state(
        rule_result=rule_result,
        rule_reason=rule_reason,
        potential_result="POTENTIAL_REGISTRATION_GAP",
        evidence_valid=evidence_valid,
        evidence_quality=evidence_quality,
        legitimate_explanation_present=legitimate_explanation_present,
    )


def map_wage_review_state(
    *,
    rule_result: str,
    rule_reason: str,
    evidence_valid: bool,
    evidence_quality: str,
) -> tuple[str, str]:
    return _map_review_state(
        rule_result=rule_result,
        rule_reason=rule_reason,
        potential_result="POTENTIAL_WAGE_DIVERGENCE",
        evidence_valid=evidence_valid,
        evidence_quality=evidence_quality,
    )


def map_contribution_review_state(
    *,
    rule_result: str,
    rule_reason: str,
    evidence_valid: bool,
    evidence_quality: str,
) -> tuple[str, str]:
    return _map_review_state(
        rule_result=rule_result,
        rule_reason=rule_reason,
        potential_result="POTENTIAL_CONTRIBUTION_IRREGULARITY",
        evidence_valid=evidence_valid,
        evidence_quality=evidence_quality,
    )


def derive_overall_review_state(*states: str) -> str:
    if any(state not in REVIEW_STATES for state in states):
        raise ValueError("per-signal review state outside workflow enum")
    unique = set(states)
    return states[0] if len(unique) == 1 else "PARTIAL"


def overall_recommendation(state: str) -> str:
    return {
        "NORMAL": "NO_MATERIAL_DISCREPANCY",
        "REVIEW": "HUMAN_REVIEW_NO_AUTOMATED_PRIORITY",
        "NEEDS_ENRICHMENT": "EVIDENCE_ENRICHMENT_REQUIRED",
        "ABSTAIN": "ABSTAIN__AUTHORITY_OR_POLICY_UNRESOLVED",
        "PARTIAL": "PARTIAL_SIGNAL_STATES__REVIEW_INDEPENDENTLY",
    }[state]


def _context_fields(prefix: str, context: RuleAuthorityContext) -> dict[str, object]:
    return {
        f"{prefix}_authority_authorized": context.authorized,
        f"{prefix}_authority_id": context.authority_id,
        f"{prefix}_rule_version": context.rule_version,
        f"{prefix}_applicable_period_verified": context.applicable_period_verified,
        f"{prefix}_authority_effective_from": context.effective_from,
        f"{prefix}_authority_effective_to": context.effective_to,
        f"{prefix}_authority_source_ids_json": json.dumps(
            list(context.source_ids),
            separators=(",", ":"),
        ),
    }


def _source_ids_json(source_metadata: dict[str, object]) -> str:
    return json.dumps(source_metadata["source_ids"], separators=(",", ":"))


def _source_periods_json(source_metadata: dict[str, object]) -> str:
    return json.dumps(source_metadata["source_periods"], separators=(",", ":"))


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
        evaluated_period = row.get("periode_bulan")

        registration_source = validate_source_metadata(
            source_ids=(
                row.get("registration_reference_source_id"),
                row.get("registration_observed_source_id"),
            ),
            source_periods=(
                row.get("registration_reference_period"),
                row.get("registration_observed_period"),
            ),
            evaluated_period=evaluated_period,
            freshness=row.get("registration_source_freshness"),
            conflict=row.get("registration_source_conflict"),
        )
        explanation = validate_explanation_metadata(
            indicator=row.get("seasonal_or_project_change_indicator"),
            reason=row.get("seasonal_or_project_reason"),
        )

        reference_verified = _strict_bool(row.get("reference_worker_set_verified"))
        observed_verified = _strict_bool(row.get("observed_worker_set_verified"))
        worker_set_valid = reference_verified is True and observed_verified is True
        reconciliation = None
        worker_error = "NONE"
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
            worker_error = type(exc).__name__

        registration_valid = (
            worker_set_valid
            and bool(registration_source["valid"])
            and bool(explanation["valid"])
        )
        registration_quality, registration_quality_reasons = _quality_from_flags(
            evidence_valid=registration_valid,
            source_stale=bool(registration_source["source_stale"]),
            source_conflict=bool(registration_source["source_conflict"]),
        )
        registration_discrepancy = (
            (
                int(reconciliation["missing_worker_count"]) > 0
                or int(reconciliation["unexpected_worker_count"]) > 0
            )
            if reconciliation is not None
            else None
        )
        registration_evidence = {
            "valid": registration_valid,
            "quality": registration_quality,
            "discrepancy_detected": registration_discrepancy,
        }
        registration_rule_result, registration_rule_reason = (
            evaluate_registration_rule(registration_evidence)
        )
        registration_review_state, registration_review_reason = (
            map_registration_review_state(
                rule_result=registration_rule_result,
                rule_reason=registration_rule_reason,
                evidence_valid=registration_valid,
                evidence_quality=registration_quality,
                legitimate_explanation_present=bool(explanation["present"]),
            )
        )

        wage_source = validate_source_metadata(
            source_ids=(
                row.get("wage_reference_source_id"),
                row.get("wage_observed_source_id"),
            ),
            source_periods=(
                row.get("wage_reference_period"),
                row.get("wage_observed_period"),
            ),
            evaluated_period=evaluated_period,
            freshness=row.get("wage_source_freshness"),
            conflict=row.get("wage_source_conflict"),
        )
        wage_semantics = validate_wage_semantics(
            reference_wage=row.get("reference_wage_signal_rp"),
            observed_wage=row.get("observed_wage_signal_rp"),
            supplied_discrepancy=row.get("wage_discrepancy_raw_rp"),
        )
        wage_valid = bool(wage_source["valid"]) and bool(wage_semantics["valid"])
        wage_quality, wage_quality_reasons = _quality_from_flags(
            evidence_valid=wage_valid,
            source_stale=bool(wage_source["source_stale"]),
            source_conflict=bool(wage_source["source_conflict"]),
        )
        wage_evidence = {
            "valid": wage_valid,
            "quality": wage_quality,
            "discrepancy_detected": wage_semantics["discrepancy_detected"],
        }
        wage_rule_result, wage_rule_reason = evaluate_wage_rule(wage_evidence)
        wage_review_state, wage_review_reason = map_wage_review_state(
            rule_result=wage_rule_result,
            rule_reason=wage_rule_reason,
            evidence_valid=wage_valid,
            evidence_quality=wage_quality,
        )

        contribution_source = validate_source_metadata(
            source_ids=(
                row.get("contribution_expected_source_id"),
                row.get("contribution_payment_source_id"),
            ),
            source_periods=(
                row.get("contribution_expected_period"),
                row.get("contribution_payment_period"),
            ),
            evaluated_period=evaluated_period,
            freshness=row.get("contribution_source_freshness"),
            conflict=row.get("contribution_source_conflict"),
        )
        payment_semantics = validate_payment_semantics(
            evaluated_period=evaluated_period,
            payment_state=row.get("payment_state_observed"),
            bank_state=row.get("bank_observed_state"),
            settlement_delay_flag=row.get("flag_bank_settlement_delay"),
            payer_timestamp=row.get("payer_timestamp_synthetic"),
            bank_timestamp=row.get("bank_posting_timestamp_synthetic"),
        )
        contribution_valid = (
            bool(contribution_source["valid"])
            and bool(payment_semantics["valid"])
        )
        contribution_quality, contribution_quality_reasons = _quality_from_flags(
            evidence_valid=contribution_valid,
            source_stale=bool(contribution_source["source_stale"]),
            source_conflict=bool(contribution_source["source_conflict"]),
            extra_low_reason=(
                "PAYMENT_SETTLEMENT_PENDING"
                if bool(payment_semantics["settlement_pending"])
                else None
            ),
        )
        contribution_evidence = {
            "valid": contribution_valid,
            "quality": contribution_quality,
            "discrepancy_detected": payment_semantics["payment_gap_observed"],
        }
        contribution_rule_result, contribution_rule_reason = (
            evaluate_contribution_rule(contribution_evidence)
        )
        contribution_review_state, contribution_review_reason = (
            map_contribution_review_state(
                rule_result=contribution_rule_result,
                rule_reason=contribution_rule_reason,
                evidence_valid=contribution_valid,
                evidence_quality=contribution_quality,
            )
        )

        overall_state = derive_overall_review_state(
            registration_review_state,
            wage_review_state,
            contribution_review_state,
        )

        discrepancy_types: list[str] = []
        if registration_discrepancy is True:
            discrepancy_types.append("REGISTRATION_SET_DISCREPANCY")
        if wage_semantics["discrepancy_detected"] is True:
            discrepancy_types.append("WAGE_DISCREPANCY")
        if payment_semantics["payment_gap_observed"] is True:
            discrepancy_types.append("CONTRIBUTION_PAYMENT_GAP")

        registration_source_ids = _source_ids_json(registration_source)
        wage_source_ids = _source_ids_json(wage_source)
        contribution_source_ids = _source_ids_json(contribution_source)

        row_out = {
            "id_badan_usaha": row["id_badan_usaha"],
            "periode_bulan": evaluated_period,
            "source_record_id": row["source_record_id"],

            "reference_worker_count": (
                int(reconciliation["reference_count"])
                if reconciliation is not None
                else None
            ),
            "observed_registered_worker_count": (
                int(reconciliation["observed_count"])
                if reconciliation is not None
                else None
            ),
            "missing_worker_count": (
                int(reconciliation["missing_worker_count"])
                if reconciliation is not None
                else None
            ),
            "unexpected_worker_count": (
                int(reconciliation["unexpected_worker_count"])
                if reconciliation is not None
                else None
            ),
            "missing_worker_ids_json": (
                json.dumps(reconciliation["missing_worker_ids"], separators=(",", ":"))
                if reconciliation is not None
                else None
            ),
            "unexpected_worker_ids_json": (
                json.dumps(
                    reconciliation["unexpected_worker_ids"],
                    separators=(",", ":"),
                )
                if reconciliation is not None
                else None
            ),
            "registration_discrepancy_detected": registration_discrepancy,
            "registration_evidence_valid": registration_valid,
            "registration_evidence_quality": registration_quality,
            "registration_evidence_reasons": (
                "|".join(registration_quality_reasons)
                if registration_quality_reasons
                else "NONE"
            ),
            "registration_source_metadata_valid": bool(registration_source["valid"]),
            "registration_period_binding_valid": bool(
                registration_source["period_binding_valid"]
            ),
            "registration_source_ids_json": registration_source_ids,
            "registration_source_periods_json": _source_periods_json(
                registration_source
            ),
            "registration_worker_set_valid": worker_set_valid,
            "registration_worker_set_error": worker_error,
            "registration_explanation_metadata_valid": bool(explanation["valid"]),
            "registration_explanation_reason": str(explanation["reason"]),
            "registration_rule_id": REGISTRATION_RULE_ID,
            "registration_rule_result": registration_rule_result,
            "registration_rule_reason": registration_rule_reason,
            "registration_review_state": registration_review_state,
            "registration_review_reason": registration_review_reason,
            "registration_lineage": (
                f"{registration_source_ids} -> set reconciliation -> "
                f"{REGISTRATION_RULE_ID}@{REGISTRATION_AUTHORITY_CONTEXT.rule_version} -> "
                f"{registration_rule_result} -> {registration_review_state}"
            ),

            "reference_wage_signal_rp": (
                int(row["reference_wage_signal_rp"])
                if wage_semantics["derived_discrepancy"] is not None
                else None
            ),
            "observed_wage_signal_rp": (
                int(row["observed_wage_signal_rp"])
                if wage_semantics["derived_discrepancy"] is not None
                else None
            ),
            "wage_discrepancy_signal_rp": wage_semantics["derived_discrepancy"],
            "wage_discrepancy_detected": wage_semantics["discrepancy_detected"],
            "wage_evidence_valid": wage_valid,
            "wage_evidence_quality": wage_quality,
            "wage_evidence_reasons": (
                "|".join(wage_quality_reasons) if wage_quality_reasons else "NONE"
            ),
            "wage_source_metadata_valid": bool(wage_source["valid"]),
            "wage_period_binding_valid": bool(wage_source["period_binding_valid"]),
            "wage_source_ids_json": wage_source_ids,
            "wage_source_periods_json": _source_periods_json(wage_source),
            "wage_semantic_consistency_valid": bool(wage_semantics["valid"]),
            "wage_rule_id": WAGE_RULE_ID,
            "wage_rule_result": wage_rule_result,
            "wage_rule_reason": wage_rule_reason,
            "wage_review_state": wage_review_state,
            "wage_review_reason": wage_review_reason,
            "wage_lineage": (
                f"{wage_source_ids} -> wage observation -> "
                f"{WAGE_RULE_ID}@{WAGE_POLICY_CONTEXT.rule_version} -> "
                f"{wage_rule_result} -> {wage_review_state}"
            ),

            "observed_payment_state": row.get("payment_state_observed"),
            "validated_payment_state": payment_semantics["validated_payment_state"],
            "contribution_payment_gap_observed": payment_semantics[
                "payment_gap_observed"
            ],
            "contribution_evidence_valid": contribution_valid,
            "contribution_evidence_quality": contribution_quality,
            "contribution_evidence_reasons": (
                "|".join(contribution_quality_reasons)
                if contribution_quality_reasons
                else "NONE"
            ),
            "contribution_source_metadata_valid": bool(
                contribution_source["valid"]
            ),
            "contribution_period_binding_valid": bool(
                contribution_source["period_binding_valid"]
            ),
            "contribution_source_ids_json": contribution_source_ids,
            "contribution_source_periods_json": _source_periods_json(
                contribution_source
            ),
            "payment_semantic_consistency_valid": bool(payment_semantics["valid"]),
            "payment_evidence_reason": str(payment_semantics["reason"]),
            "contribution_rule_id": CONTRIBUTION_RULE_ID,
            "contribution_rule_result": contribution_rule_result,
            "contribution_rule_reason": contribution_rule_reason,
            "contribution_review_state": contribution_review_state,
            "contribution_review_reason": contribution_review_reason,
            "contribution_lineage": (
                f"{contribution_source_ids} -> payment observation -> "
                f"{CONTRIBUTION_RULE_ID}@{CONTRIBUTION_POLICY_CONTEXT.rule_version} -> "
                f"{contribution_rule_result} -> {contribution_review_state}"
            ),

            "overall_review_state": overall_state,
            "human_review_recommendation": overall_recommendation(overall_state),
            "observed_discrepancy_types": (
                "|".join(discrepancy_types) if discrepancy_types else "NONE"
            ),
            "estimated_exposure_synthetic_rp": (
                int(row["estimated_exposure_synthetic_rp"])
                if _valid_nonnegative_number(
                    row.get("estimated_exposure_synthetic_rp")
                )
                else None
            ),
            "exposure_decision_role": (
                "SIMULATED_ESTIMATE__NOT_EMPIRICAL_LOSS__NOT_FOR_DECISION"
            ),
            "synthetic_risk_mode_ground_truth": row[
                "synthetic_risk_mode_ground_truth"
            ],
            "is_synthetic": True,
        }

        row_out.update(
            _context_fields("registration", REGISTRATION_AUTHORITY_CONTEXT)
        )
        row_out.update(_context_fields("wage", WAGE_POLICY_CONTEXT))
        row_out.update(
            _context_fields("contribution", CONTRIBUTION_POLICY_CONTEXT)
        )
        rows.append(row_out)

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
    print(
        "status: FINAL SYNTHETIC EVIDENCE CURATED; RULE AND WORKFLOW LAYERS SEPARATED"
    )


if __name__ == "__main__":
    main()
