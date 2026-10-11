"""Public read models. No simulator targets, personal identifiers, or ML scores."""

import re
from datetime import date
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field


def calendar_month(value: str) -> str:
    if re.fullmatch(r"[0-9]{4}-(0[1-9]|1[0-2])", value) is None:
        raise ValueError("Expected a calendar month in YYYY-MM format")
    date.fromisoformat(f"{value}-01")
    return value


CompanyId = Annotated[str, Field(pattern=r"^BU-[0-9]{4}$", max_length=7)]
Period = Annotated[str, AfterValidator(calendar_month)]
Text = Annotated[str, Field(min_length=1, max_length=4096)]
Quantity = Annotated[int, Field(ge=0, le=9007199254740991)]


class ReadModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class Company(ReadModel):
    id_badan_usaha: CompanyId
    nama_badan_usaha: Text | None
    bentuk_badan_hukum: Text | None
    kode_kbli: Text | None
    sektor_industri: Text | None
    skala_usaha: Text | None
    provinsi: Text | None
    kantor_cabang_bpjs: Text | None


class Authority(ReadModel):
    authorized: Literal[False]
    id: Text
    rule_version: Literal["UNVERIFIED"]
    applicable_period_verified: Literal[False]
    effective_from: None
    effective_to: None
    source_ids: tuple[Text, ...]


class EvidenceGroup(ReadModel):
    evidence_valid: bool
    evidence_quality: Literal["HIGH", "MEDIUM", "LOW"]
    evidence_reasons: tuple[Text, ...]
    source_metadata_valid: bool
    period_binding_valid: bool
    source_ids: tuple[Text, ...]
    source_periods: tuple[Period, ...]
    rule_result: Literal["ABSTAIN"]
    rule_reason: Text
    review_state: Literal["ABSTAIN"]
    review_reason: Text
    lineage: Text
    authority: Authority


class RegistrationEvidence(EvidenceGroup):
    rule_id: Literal["REG-001"]
    reference_worker_count: Quantity | None
    observed_registered_worker_count: Quantity | None
    missing_worker_count: Quantity | None
    unexpected_worker_count: Quantity | None
    discrepancy_detected: bool | None
    worker_set_valid: bool
    worker_set_error: Text
    explanation_metadata_valid: bool
    explanation_reason: Text


class WageEvidence(EvidenceGroup):
    rule_id: Literal["WAGE-001"]
    reference_wage_signal_rp: Quantity | None
    observed_wage_signal_rp: Quantity | None
    wage_discrepancy_signal_rp: Quantity | None
    discrepancy_detected: bool | None
    semantic_consistency_valid: bool


class ContributionEvidence(EvidenceGroup):
    rule_id: Literal["CONTRIB-001"]
    observed_payment_state: Literal["PAID_ON_TIME", "PAYMENT_PENDING", "UNPAID"] | None
    validated_payment_state: Literal["PAID_ON_TIME", "PAYMENT_PENDING", "UNPAID", "UNKNOWN"]
    payment_gap_observed: bool | None
    semantic_consistency_valid: bool
    payment_evidence_reason: Text


class MonthlyEvidence(ReadModel):
    id_badan_usaha: CompanyId
    periode_bulan: Period
    source_record_id: Text
    registration: RegistrationEvidence
    wage: WageEvidence
    contribution: ContributionEvidence
    overall_review_state: Literal["ABSTAIN"]
    human_review_recommendation: Literal["ABSTAIN__AUTHORITY_OR_POLICY_UNRESOLVED"]
    observed_discrepancy_types: tuple[
        Literal["REGISTRATION_SET_DISCREPANCY", "WAGE_DISCREPANCY", "CONTRIBUTION_PAYMENT_GAP"], ...
    ]


class DatasetRef(ReadModel):
    dataset_id: str
    source_commit: str
    is_synthetic: Literal[True] = True
    ml_status: Literal["NOT_CONFIGURED"] = "NOT_CONFIGURED"
    policy_status: Literal["UNRESOLVED"] = "UNRESOLVED"


class DatasetInfo(ReadModel):
    company_count: int
    evidence_record_count: int
    period_from: Period
    period_to: Period
    assumption_version: str
    generation_seed: int
    raw_seed: int
    files: dict[str, str]
