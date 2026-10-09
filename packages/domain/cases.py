"""Human review workflow for the prototype; no legal or policy execution authority."""

from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AfterValidator, BeforeValidator, Field

from packages.domain.read_models import CompanyId, DatasetRef, MonthlyEvidence, Period, ReadModel

Status = Literal["OPEN", "IN_REVIEW", "WAITING_EVIDENCE", "RESOLVED", "DISMISSED"]
Action = Literal[
    "START_REVIEW", "REQUEST_EVIDENCE", "RESUME_REVIEW", "RESOLVE", "DISMISS", "REOPEN"
]
Role = Literal["REVIEWER", "SUPERVISOR"]
TERMINAL = {"RESOLVED", "DISMISSED"}
PRIVILEGED = {"RESOLVE", "DISMISS", "REOPEN"}
TRANSITIONS = {
    ("OPEN", "START_REVIEW"): "IN_REVIEW",
    ("IN_REVIEW", "REQUEST_EVIDENCE"): "WAITING_EVIDENCE",
    ("WAITING_EVIDENCE", "RESUME_REVIEW"): "IN_REVIEW",
    ("IN_REVIEW", "RESOLVE"): "RESOLVED",
    ("IN_REVIEW", "DISMISS"): "DISMISSED",
    ("RESOLVED", "REOPEN"): "OPEN",
    ("DISMISSED", "REOPEN"): "OPEN",
}


class WorkflowError(Exception):
    def __init__(self, status: int, code: str, headers: dict[str, str] | None = None):
        self.status, self.code, self.headers = status, code, headers
        super().__init__(code)


def clean_note(value):
    if not isinstance(value, str) or "\x00" in value:
        raise ValueError("Expected text without NUL characters")
    return value.strip()


def canonical_uuid(value: str) -> str:
    if str(UUID(value)) != value:
        raise ValueError("Expected a canonical UUID")
    return value


def utc_due_time(value):
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("Expected an ISO timestamp with timezone")  # noqa: TRY004 -- Pydantic validation error, not a server exception
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("Timezone required")
    try:
        return parsed.astimezone(UTC).isoformat()
    except OverflowError as exc:
        raise ValueError("UTC timestamp is outside the supported calendar range") from exc


Note = Annotated[str, BeforeValidator(clean_note), Field(min_length=1, max_length=2000)]
CaseId = Annotated[str, Field(min_length=36, max_length=36), AfterValidator(canonical_uuid)]


class Actor(ReadModel):
    actor_id: str
    role: Role
    auth_mode: Literal["DEMO_STATIC_TOKEN"] = "DEMO_STATIC_TOKEN"


class CreateCase(ReadModel):
    id_badan_usaha: CompanyId
    periode_bulan: Period
    reason: Note
    recurrence_of: CaseId | None = None


class TransitionRequest(ReadModel):
    action: Action
    reason: Note


class NoteRequest(ReadModel):
    text: Note


class InterventionRequest(ReadModel):
    kind: Literal["REQUEST_DOCUMENTS", "CONTACT_REVIEW", "FOLLOW_UP"]
    note: Note
    due_at: Annotated[str | None, BeforeValidator(utc_due_time)] = None


class OutcomeRequest(ReadModel):
    outcome: Literal["COMPLETED", "CANCELLED"]
    note: Note


class Intervention(ReadModel):
    intervention_id: CaseId
    case_id: CaseId
    kind: str
    status: Literal["PLANNED", "COMPLETED", "CANCELLED"]
    note: str
    due_at: str | None
    created_at: str
    created_by: str
    completed_at: str | None
    outcome_note: str | None


class CaseSummary(ReadModel):
    case_id: CaseId
    id_badan_usaha: CompanyId
    periode_bulan: Period
    status: Status
    version: int
    reason: str
    status_reason: str
    created_at: str
    updated_at: str
    created_by: str
    recurrence_of: CaseId | None
    dataset: DatasetRef


class CaseDetail(CaseSummary):
    evidence_snapshot: MonthlyEvidence
    interventions: tuple[Intervention, ...]


class CaseEvent(ReadModel):
    event_id: CaseId
    case_id: CaseId
    version: int
    actor_id: str
    actor_role: Role
    action: str
    payload: dict
    created_at: str


class MutationResult(ReadModel):
    case_id: CaseId
    status: Status
    version: int
    event_id: CaseId
    intervention_id: CaseId | None = None
