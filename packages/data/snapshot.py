"""Bounded, hash-verified CSV adapter for the approved synthetic snapshot format."""

import csv
import hashlib
import io
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from packages.domain.read_models import (
    Authority,
    Company,
    ContributionEvidence,
    DatasetInfo,
    DatasetRef,
    MonthlyEvidence,
    Period,
    ReadModel,
    RegistrationEvidence,
    WageEvidence,
)

MASTER = "curated_master_badan_usaha.csv"
EVIDENCE = "curated_kepatuhan_evidence.csv"
MAX_CSV_BYTES = 64 * 1024 * 1024
MAX_MANIFEST_BYTES = 64 * 1024
SHA256 = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$", max_length=64)]


class DatasetError(Exception):
    """Public category only; row values and filesystem paths stay private."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


class FileSpec(ReadModel):
    sha256: SHA256
    rows: Annotated[int, Field(ge=1, le=100000)]


class Manifest(ReadModel):
    manifest_version: Literal["1.0"]
    source_commit: Annotated[str, Field(pattern=r"^[a-f0-9]{40}$", max_length=40)]
    assumption_version: Annotated[str, Field(min_length=1, max_length=100)]
    is_synthetic: Literal[True]
    generation_seed: Annotated[int, Field(ge=0)]
    raw_seed: Annotated[int, Field(ge=0)]
    period_from: Period
    period_to: Period
    files: dict[str, FileSpec]

    @field_validator("is_synthetic", mode="before")
    @classmethod
    def require_synthetic_bool(cls, value):
        if value is not True:
            raise ValueError("Synthetic snapshot required")
        return value

    @model_validator(mode="after")
    def validate_scope(self):
        if set(self.files) != {MASTER, EVIDENCE}:
            raise ValueError("Unexpected snapshot files")
        periods = months_between(self.period_from, self.period_to)
        if self.files[EVIDENCE].rows != self.files[MASTER].rows * len(periods):
            raise ValueError("Incomplete company-period grid")
        return self


def months_between(start: str, end: str) -> tuple[str, ...]:
    def ordinal(period):
        year, month = map(int, period.split("-"))
        return year * 12 + month - 1

    first, last = ordinal(start), ordinal(end)
    if not 0 <= last - first < 120:
        raise ValueError("Snapshot period range must contain 1 to 120 months")
    return tuple(f"{value // 12:04d}-{value % 12 + 1:02d}" for value in range(first, last + 1))


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def _bounded_read(path: Path, maximum: int) -> bytes:
    with path.open("rb") as handle:
        content = handle.read(maximum + 1)
    if len(content) > maximum:
        raise ValueError("File exceeds snapshot size limit")
    return content


def _rows(content: bytes, required: set[str], expected_rows: int):
    reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig"), newline=""), strict=True)
    header = reader.fieldnames or []
    if len(header) != len(set(header)) or not required.issubset(header):
        raise ValueError("Invalid CSV header")
    count = 0
    for count, row in enumerate(reader, start=1):
        if count > expected_rows or None in row or any(value is None for value in row.values()):
            raise ValueError("Invalid CSV row shape or count")
        yield row
    if count != expected_rows:
        raise ValueError("CSV row count mismatch")


def _boolean(value: str, *, nullable: bool = False) -> bool | None:
    if value == "" and nullable:
        return None
    if value not in {"True", "False"}:
        raise ValueError("Invalid CSV boolean")
    return value == "True"


def _quantity(value: str) -> int | None:
    if value == "":
        return None
    # Pandas may serialize nullable integral columns as 123.0; never round a float.
    if not re.fullmatch(r"[0-9]+(?:\.0+)?", value):
        raise ValueError("Expected nonnegative integral quantity")
    return int(value.split(".")[0])


def _array(value: str) -> tuple[str, ...]:
    parsed = json.loads(value)
    if not isinstance(parsed, list) or any(type(item) is not str or not item for item in parsed):
        raise ValueError("Expected a JSON array of nonempty strings")
    return tuple(parsed)


def _tokens(value: str) -> tuple[str, ...]:
    if value == "NONE":
        return ()
    parts = value.split("|")
    if any(not part or part == "NONE" for part in parts) or len(parts) != len(set(parts)):
        raise ValueError("Invalid reason list")
    return tuple(parts)


COMMON_RAW = {
    "evidence_valid",
    "evidence_quality",
    "evidence_reasons",
    "source_metadata_valid",
    "period_binding_valid",
    "source_ids_json",
    "source_periods_json",
    "rule_id",
    "rule_result",
    "rule_reason",
    "review_state",
    "review_reason",
    "lineage",
    "authority_authorized",
    "authority_id",
    "rule_version",
    "applicable_period_verified",
    "authority_effective_from",
    "authority_effective_to",
    "authority_source_ids_json",
}
COMPANY_RAW = set(Company.model_fields) - {"nama_badan_usaha"} | {
    "nama_badan_usaha_terstandarisasi",
    "synthetic_assumption_version",
}
EVIDENCE_RAW = {
    "id_badan_usaha",
    "periode_bulan",
    "source_record_id",
    "is_synthetic",
    "reference_worker_count",
    "observed_registered_worker_count",
    "missing_worker_count",
    "unexpected_worker_count",
    "registration_discrepancy_detected",
    "registration_worker_set_valid",
    "registration_worker_set_error",
    "registration_explanation_metadata_valid",
    "registration_explanation_reason",
    "reference_wage_signal_rp",
    "observed_wage_signal_rp",
    "wage_discrepancy_signal_rp",
    "wage_discrepancy_detected",
    "wage_semantic_consistency_valid",
    "observed_payment_state",
    "validated_payment_state",
    "contribution_payment_gap_observed",
    "payment_semantic_consistency_valid",
    "payment_evidence_reason",
    "overall_review_state",
    "human_review_recommendation",
    "observed_discrepancy_types",
} | {
    f"{domain}_{field}"
    for domain in ("registration", "wage", "contribution")
    for field in COMMON_RAW
}


def _common(row: dict[str, str], prefix: str) -> dict:
    def value(field):
        return row[f"{prefix}_{field}"]

    result = {
        field: value(field)
        for field in (
            "evidence_quality",
            "rule_id",
            "rule_result",
            "rule_reason",
            "review_state",
            "review_reason",
            "lineage",
        )
    }
    result.update(
        {
            field: _boolean(value(field))
            for field in (
                "evidence_valid",
                "source_metadata_valid",
                "period_binding_valid",
            )
        }
    )
    result["evidence_reasons"] = _tokens(value("evidence_reasons"))
    result["source_ids"] = _array(value("source_ids_json"))
    result["source_periods"] = _array(value("source_periods_json"))
    result["authority"] = Authority(
        authorized=_boolean(value("authority_authorized")),
        id=value("authority_id"),
        rule_version=value("rule_version"),
        applicable_period_verified=_boolean(value("applicable_period_verified")),
        effective_from=value("authority_effective_from") or None,
        effective_to=value("authority_effective_to") or None,
        source_ids=_array(value("authority_source_ids_json")),
    )
    if result["source_metadata_valid"] and (
        not result["source_ids"] or len(result["source_ids"]) != len(result["source_periods"])
    ):
        raise ValueError("Inconsistent source metadata")
    if result["period_binding_valid"] and (
        not result["source_metadata_valid"]
        or any(period != row["periode_bulan"] for period in result["source_periods"])
    ):
        raise ValueError("Inconsistent source period binding")
    return result


def _evidence(row: dict[str, str]) -> MonthlyEvidence:
    if _boolean(row["is_synthetic"]) is not True:
        raise ValueError("Non-synthetic evidence is not supported")
    registration = RegistrationEvidence(
        **_common(row, "registration"),
        **{
            field: _quantity(row[field])
            for field in (
                "reference_worker_count",
                "observed_registered_worker_count",
                "missing_worker_count",
                "unexpected_worker_count",
            )
        },
        discrepancy_detected=_boolean(row["registration_discrepancy_detected"], nullable=True),
        worker_set_valid=_boolean(row["registration_worker_set_valid"]),
        worker_set_error=row["registration_worker_set_error"],
        explanation_metadata_valid=_boolean(row["registration_explanation_metadata_valid"]),
        explanation_reason=row["registration_explanation_reason"],
    )
    wage = WageEvidence(
        **_common(row, "wage"),
        **{
            field: _quantity(row[field])
            for field in (
                "reference_wage_signal_rp",
                "observed_wage_signal_rp",
                "wage_discrepancy_signal_rp",
            )
        },
        discrepancy_detected=_boolean(row["wage_discrepancy_detected"], nullable=True),
        semantic_consistency_valid=_boolean(row["wage_semantic_consistency_valid"]),
    )
    contribution = ContributionEvidence(
        **_common(row, "contribution"),
        observed_payment_state=row["observed_payment_state"] or None,
        validated_payment_state=row["validated_payment_state"],
        payment_gap_observed=_boolean(row["contribution_payment_gap_observed"], nullable=True),
        semantic_consistency_valid=_boolean(row["payment_semantic_consistency_valid"]),
        payment_evidence_reason=row["payment_evidence_reason"],
    )
    return MonthlyEvidence(
        id_badan_usaha=row["id_badan_usaha"],
        periode_bulan=row["periode_bulan"],
        source_record_id=row["source_record_id"],
        registration=registration,
        wage=wage,
        contribution=contribution,
        overall_review_state=row["overall_review_state"],
        human_review_recommendation=row["human_review_recommendation"],
        observed_discrepancy_types=_tokens(row["observed_discrepancy_types"]),
    )


@dataclass(frozen=True)
class Snapshot:
    ref: DatasetRef
    info: DatasetInfo
    companies: tuple[Company, ...]
    company_index: Mapping[str, Company]
    evidence_index: Mapping[tuple[str, str], MonthlyEvidence]
    histories: Mapping[str, tuple[MonthlyEvidence, ...]]


def load_snapshot(data_root: Path, manifest_path: Path) -> Snapshot:
    try:
        content = _bounded_read(manifest_path, MAX_MANIFEST_BYTES)
        manifest = Manifest.model_validate(json.loads(content, object_pairs_hook=_unique_object))
        raw = {}
        for name, spec in manifest.files.items():
            raw[name] = _bounded_read(data_root / name, MAX_CSV_BYTES)
            if hashlib.sha256(raw[name]).hexdigest() != spec.sha256:
                raise ValueError("Snapshot hash mismatch")
        companies = {}
        for row in _rows(raw[MASTER], COMPANY_RAW, manifest.files[MASTER].rows):
            if row["synthetic_assumption_version"] != manifest.assumption_version:
                raise ValueError("Assumption version mismatch")
            values = {
                field: row[
                    "nama_badan_usaha_terstandarisasi" if field == "nama_badan_usaha" else field
                ]
                or None
                for field in Company.model_fields
            }
            company = Company.model_validate(values)
            if company.id_badan_usaha in companies:
                raise ValueError("Duplicate company")
            companies[company.id_badan_usaha] = company
        index, source_ids = {}, set()
        histories = {key: [] for key in companies}
        periods = months_between(manifest.period_from, manifest.period_to)
        for row in _rows(raw[EVIDENCE], EVIDENCE_RAW, manifest.files[EVIDENCE].rows):
            record = _evidence(row)
            key = (record.id_badan_usaha, record.periode_bulan)
            if record.id_badan_usaha not in companies or record.periode_bulan not in periods:
                raise ValueError("Evidence outside snapshot scope")
            if key in index or record.source_record_id in source_ids:
                raise ValueError("Duplicate evidence key")
            index[key] = record
            source_ids.add(record.source_record_id)
            histories[record.id_badan_usaha].append(record)
        if any(
            {item.periode_bulan for item in rows} != set(periods) for rows in histories.values()
        ):
            raise ValueError("Incomplete company-period grid")
        canonical = json.dumps(
            manifest.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
        )
        ref = DatasetRef(
            dataset_id="sha256:" + hashlib.sha256(canonical.encode()).hexdigest(),
            source_commit=manifest.source_commit,
        )
        info = DatasetInfo(
            company_count=len(companies),
            evidence_record_count=len(index),
            period_from=manifest.period_from,
            period_to=manifest.period_to,
            assumption_version=manifest.assumption_version,
            generation_seed=manifest.generation_seed,
            raw_seed=manifest.raw_seed,
            files={name: spec.sha256 for name, spec in manifest.files.items()},
        )
        return Snapshot(
            ref=ref,
            info=info,
            companies=tuple(companies[key] for key in sorted(companies)),
            company_index=MappingProxyType(companies),
            evidence_index=MappingProxyType(index),
            histories=MappingProxyType(
                {
                    key: tuple(sorted(rows, key=lambda row: row.periode_bulan))
                    for key, rows in histories.items()
                }
            ),
        )
    except OSError as exc:
        raise DatasetError("DATASET_UNAVAILABLE") from exc
    except (ValueError, KeyError, TypeError, csv.Error) as exc:
        raise DatasetError("DATASET_INVALID") from exc
