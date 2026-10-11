"""Read-only, opt-in inference for a trusted synthetic model bundle.

This module must not be imported into the default backend startup path until ML
serving is explicitly enabled; the ordinary backend has no ML dependency group.
Unpickling is never safe for artifacts from untrusted publishers.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import Field

from packages.data.snapshot import Snapshot
from packages.domain.read_models import Company, MonthlyEvidence, ReadModel

FILE_PREFIX = "data/synthetic/curated/"


class ExperimentalResult(ReadModel):
    status: Literal["EXPERIMENTAL_SYNTHETIC", "ABSTAIN"]
    id_badan_usaha: str
    period_month: str
    target_period: str | None
    model_version: str
    model_name: str
    score: float | None = Field(ge=0, le=1, allow_inf_nan=False)
    score_semantics: Literal["uncalibrated_synthetic_non_normal_score"]
    threshold: float | None = Field(ge=0, le=1, allow_inf_nan=False)
    experimental_prediction: Literal[0, 1] | None
    is_synthetic: Literal[True] = True
    policy_status: Literal["UNRESOLVED"] = "UNRESOLVED"
    reason_code: Literal["EVIDENCE_NOT_VALIDATED", "INCOMPLETE_INPUT"] | None = None


@dataclass(frozen=True)
class ModelService:
    bundle: dict
    model_version: str
    model_name: str


class InferenceUnavailable(Exception):
    """A model calculation failed; no partially computed score may escape."""


def open_trusted_model(snapshot: Snapshot, path: Path) -> ModelService:
    """Check dataset lineage before loading any pickle, then validate its bundle."""
    from packages.ml.inference import load_bundle

    if snapshot.ref.is_synthetic is not True:
        raise ValueError("Synthetic snapshot required")
    metadata = json.loads(path.with_name("metadata.json").read_text(encoding="utf-8"))
    if metadata.get("status") != "EXPERIMENTAL_SYNTHETIC":
        raise ValueError("Model has no experimental synthetic designation")
    if metadata.get("calibration_status") != "NOT_CALIBRATED":
        raise ValueError("Model calibration declaration mismatch")
    if metadata.get("operational_threshold") is not None:
        raise ValueError("Operational threshold is not permitted")
    if metadata.get("dataset_commit") != snapshot.ref.source_commit:
        raise ValueError("Source commit mismatch")
    expected_files = {FILE_PREFIX + key: value for key, value in snapshot.info.files.items()}
    if metadata.get("data_sha256") != expected_files:
        raise ValueError("Curated dataset hashes do not match the artifact")
    bundle = load_bundle(path, path.with_name("metadata.json"))
    if not isinstance(bundle, dict):
        raise ValueError("Model bundle is not a mapping")
    for field in ("model_version", "model_name"):
        if not isinstance(bundle.get(field), str) or not bundle[field]:
            raise ValueError("Model identity unavailable")
    return ModelService(
        bundle=bundle, model_version=bundle["model_version"], model_name=bundle["model_name"]
    )


def _abstain(service: ModelService, company: Company, evidence: MonthlyEvidence, reason: str):
    return ExperimentalResult(
        status="ABSTAIN",
        id_badan_usaha=company.id_badan_usaha,
        period_month=evidence.periode_bulan,
        target_period=None,
        model_version=service.model_version,
        model_name=service.model_name,
        score=None,
        score_semantics="uncalibrated_synthetic_non_normal_score",
        threshold=None,
        experimental_prediction=None,
        reason_code=reason,
    )


def assess(
    snapshot: Snapshot, service: ModelService, company: Company, evidence: MonthlyEvidence
) -> ExperimentalResult:
    """Fail closed for invalid evidence; neither score nor case mutation on abstention."""
    from packages.ml.inference import predict_record, record_from_api

    if company.id_badan_usaha != evidence.id_badan_usaha:
        raise InferenceUnavailable("Identity mismatch")
    groups = (evidence.registration, evidence.wage, evidence.contribution)
    if any(
        not group.evidence_valid
        or not group.source_metadata_valid
        or not group.period_binding_valid
        for group in groups
    ):
        return _abstain(service, company, evidence, "EVIDENCE_NOT_VALIDATED")
    if not (
        evidence.registration.worker_set_valid
        and evidence.registration.explanation_metadata_valid
        and evidence.wage.semantic_consistency_valid
        and evidence.contribution.semantic_consistency_valid
    ):
        return _abstain(service, company, evidence, "EVIDENCE_NOT_VALIDATED")
    meta = snapshot.ref.model_dump(mode="json")
    try:
        raw = record_from_api(
            {"data": company.model_dump(mode="json"), "meta": meta},
            {"data": evidence.model_dump(mode="json"), "meta": meta},
        )
        prediction = predict_record(service.bundle, raw)
    except (ValueError, KeyError, TypeError, OverflowError) as exc:
        # Invalid/missing evidence is an abstention, not a disguised risk score.
        return _abstain(service, company, evidence, "INCOMPLETE_INPUT")
    except Exception as exc:
        raise InferenceUnavailable("Model calculation failed") from exc

    if (
        prediction.get("status") != "EXPERIMENTAL_SYNTHETIC"
        or prediction.get("policy_status") != "UNRESOLVED"
        or prediction.get("is_synthetic") is not True
        or prediction.get("period_month") != evidence.periode_bulan
        or prediction.get("model_version") != service.model_version
        or prediction.get("model_name") != service.model_name
    ):
        raise InferenceUnavailable("Model response contract mismatch")
    try:
        return ExperimentalResult(
            status="EXPERIMENTAL_SYNTHETIC",
            id_badan_usaha=company.id_badan_usaha,
            period_month=prediction["period_month"],
            target_period=prediction["target_period"],
            model_version=service.model_version,
            model_name=service.model_name,
            score=prediction["score"],
            score_semantics=prediction["score_semantics"],
            threshold=prediction["threshold"],
            experimental_prediction=prediction["experimental_prediction"],
        )
    except (ValueError, KeyError, TypeError) as exc:
        raise InferenceUnavailable("Malformed model output") from exc
