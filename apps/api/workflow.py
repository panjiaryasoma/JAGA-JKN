"""HTTP adapters for the local review workflow and honest capability reporting."""

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Header, Query, Request, Response
from fastapi.responses import JSONResponse

from apps.api.auth import require_actor
from apps.api.schemas import (
    DataResponse,
    EmptyQuery,
    ObjectResponse,
    PageQuery,
    Pagination,
    WorkflowPage,
)
from packages.data.case_store import CaseStore
from packages.domain.cases import (
    Actor,
    CaseDetail,
    CaseEvent,
    CaseId,
    CaseSummary,
    CreateCase,
    InterventionRequest,
    MutationResult,
    NoteRequest,
    OutcomeRequest,
    Status,
    TransitionRequest,
    WorkflowError,
)
from packages.domain.read_models import CompanyId, Period, ReadModel

router = APIRouter(prefix="/api/v1")
ActorDep = Annotated[Actor, Depends(require_actor)]
NoQuery = Annotated[EmptyQuery, Query()]


class CaseQuery(PageQuery):
    status: Status | None = None
    id_badan_usaha: CompanyId | None = None
    periode_bulan: Period | None = None


class DashboardQuery(EmptyQuery):
    periode_bulan: Period


class DomainCounts(ReadModel):
    discrepancy: dict[Literal["true", "false", "unknown"], int]
    quality: dict[Literal["HIGH", "MEDIUM", "LOW"], int]
    abstain_count: int


class Dashboard(ReadModel):
    periode_bulan: Period
    company_count: int
    registration: DomainCounts
    wage: DomainCounts
    contribution: DomainCounts


class MLStatus(ReadModel):
    status: Literal["NOT_CONFIGURED"] = "NOT_CONFIGURED"
    model_version: None = None
    prediction_available: Literal[False] = False


class Capabilities(ReadModel):
    scope: Literal["SYNTHETIC_PROTOTYPE"] = "SYNTHETIC_PROTOTYPE"
    snapshot: Literal["AVAILABLE", "UNAVAILABLE"]
    case_store: Literal["AVAILABLE", "UNAVAILABLE"]
    authentication: Literal["DEMO_STATIC_TOKEN", "NOT_CONFIGURED"]
    ml: Literal["NOT_CONFIGURED"] = "NOT_CONFIGURED"
    policy: Literal["UNRESOLVED"] = "UNRESOLVED"


@dataclass(frozen=True)
class WriteContext:
    actor: Actor
    key: str
    expected_version: int | None


def write_context(
    request: Request,
    actor: ActorDep,
    idempotency_key: Annotated[
        str,
        Header(alias="Idempotency-Key", min_length=8, max_length=128, pattern=r"^[A-Za-z0-9_-]+$"),
    ],
    if_match: Annotated[str | None, Header(alias="If-Match", max_length=32)] = None,
) -> WriteContext:
    if (
        len(request.headers.getlist("idempotency-key")) != 1
        or len(request.headers.getlist("if-match")) > 1
    ):
        raise WorkflowError(422, "VALIDATION_ERROR")
    version = None
    if if_match is not None:
        match = re.fullmatch(r'"v([1-9][0-9]*)"', if_match)
        if match is None:
            raise WorkflowError(422, "VALIDATION_ERROR")
        version = int(match.group(1))
    return WriteContext(actor=actor, key=idempotency_key, expected_version=version)


WriteDep = Annotated[WriteContext, Depends(write_context)]


def store(request: Request) -> CaseStore:
    if request.app.state.case_store is None:
        raise WorkflowError(503, "PERSISTENCE_UNAVAILABLE")
    return request.app.state.case_store


def paged(items, total, query, item_model):
    return WorkflowPage[item_model](
        data=items,
        pagination=Pagination(
            page=query.page,
            page_size=query.page_size,
            total=total,
            total_pages=(total + query.page_size - 1) // query.page_size,
        ),
    )


def mutation(request, context, operation, payload, *, case_id=None, intervention_id=None):
    if operation != "CREATE" and context.expected_version is None:
        raise WorkflowError(428, "PRECONDITION_REQUIRED")
    if operation == "CREATE" and context.expected_version is not None:
        raise WorkflowError(422, "VALIDATION_ERROR")
    values = payload.model_dump(mode="json")
    fingerprint = hashlib.sha256(
        json.dumps(
            {
                "method": request.method,
                "path": request.url.path,
                "payload": values,
                "expected_version": context.expected_version,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    receipt = store(request).mutate(
        actor=context.actor,
        key=context.key,
        fingerprint=fingerprint,
        operation=operation,
        payload=values,
        case_id=case_id,
        expected_version=context.expected_version,
        intervention_id=intervention_id,
        snapshot=request.app.state.snapshot,
        dataset_error=request.app.state.dataset_error,
    )
    response = ObjectResponse[MutationResult](data=receipt.result)
    return JSONResponse(
        status_code=receipt.status_code,
        content=response.model_dump(mode="json"),
        headers={
            "ETag": f'"v{receipt.result.version}"',
            "Idempotent-Replay": str(receipt.replayed).lower(),
            "Location": f"/api/v1/cases/{receipt.result.case_id}",
        },
    )


@router.get("/me", response_model=ObjectResponse[Actor], tags=["Access"])
def me(actor: ActorDep, params: NoQuery):
    return ObjectResponse[Actor](data=actor)


@router.get("/capabilities", response_model=ObjectResponse[Capabilities], tags=["Capabilities"])
def capabilities(request: Request, params: NoQuery):
    persistence = "UNAVAILABLE"
    try:
        store(request).check_ready()
        persistence = "AVAILABLE"
    except WorkflowError:
        pass  # Capabilities reports component state; readiness supplies the error response.
    return ObjectResponse[Capabilities](
        data=Capabilities(
            snapshot="AVAILABLE" if request.app.state.snapshot is not None else "UNAVAILABLE",
            case_store=persistence,
            authentication="DEMO_STATIC_TOKEN"
            if request.app.state.auth_registry
            else "NOT_CONFIGURED",
        )
    )


@router.get("/ml/status", response_model=ObjectResponse[MLStatus], tags=["Capabilities"])
def ml_status(params: NoQuery):
    return ObjectResponse[MLStatus](data=MLStatus())


@router.get("/dashboard", response_model=DataResponse[Dashboard], tags=["Dataset"])
def dashboard(request: Request, params: Annotated[DashboardQuery, Query()]):
    snapshot = request.app.state.snapshot
    if snapshot is None:
        raise WorkflowError(503, request.app.state.dataset_error)
    records = [
        snapshot.evidence_index[(company.id_badan_usaha, params.periode_bulan)]
        for company in snapshot.companies
        if (company.id_badan_usaha, params.periode_bulan) in snapshot.evidence_index
    ]
    if not records:
        raise WorkflowError(404, "NOT_FOUND")
    groups = {}
    for name in ("registration", "wage", "contribution"):
        discrepancy = {"true": 0, "false": 0, "unknown": 0}
        quality = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
        abstain = 0
        for record in records:
            group = getattr(record, name)
            value = (
                group.payment_gap_observed if name == "contribution" else group.discrepancy_detected
            )
            discrepancy["true" if value is True else "false" if value is False else "unknown"] += 1
            quality[group.evidence_quality] += 1
            abstain += group.rule_result == "ABSTAIN"
        groups[name] = DomainCounts(discrepancy=discrepancy, quality=quality, abstain_count=abstain)
    return DataResponse[Dashboard](
        data=Dashboard(
            periode_bulan=params.periode_bulan,
            company_count=len(records),
            **groups,
        ),
        meta=snapshot.ref,
    )


@router.get("/cases", response_model=WorkflowPage[CaseSummary], tags=["Cases"])
def cases(request: Request, actor: ActorDep, params: Annotated[CaseQuery, Query()]):
    items, total = store(request).list_cases(
        page=params.page,
        page_size=params.page_size,
        status=params.status,
        company_id=params.id_badan_usaha,
        period=params.periode_bulan,
    )
    return paged(items, total, params, CaseSummary)


@router.post(
    "/cases", response_model=ObjectResponse[MutationResult], status_code=201, tags=["Cases"]
)
def create_case(request: Request, payload: CreateCase, context: WriteDep, params: NoQuery):
    return mutation(request, context, "CREATE", payload)


@router.get("/cases/{case_id}", response_model=ObjectResponse[CaseDetail], tags=["Cases"])
def case(case_id: CaseId, request: Request, response: Response, actor: ActorDep, params: NoQuery):
    detail = store(request).get_case(case_id)
    response.headers["ETag"] = f'"v{detail.version}"'
    return ObjectResponse[CaseDetail](data=detail)


@router.get("/cases/{case_id}/events", response_model=WorkflowPage[CaseEvent], tags=["Cases"])
def events(
    case_id: CaseId, request: Request, actor: ActorDep, params: Annotated[PageQuery, Query()]
):
    items, total = store(request).list_events(case_id, page=params.page, page_size=params.page_size)
    return paged(items, total, params, CaseEvent)


@router.post(
    "/cases/{case_id}/transitions", response_model=ObjectResponse[MutationResult], tags=["Cases"]
)
def transition(
    case_id: CaseId,
    request: Request,
    payload: TransitionRequest,
    context: WriteDep,
    params: NoQuery,
):
    return mutation(request, context, "TRANSITION", payload, case_id=case_id)


@router.post(
    "/cases/{case_id}/notes", response_model=ObjectResponse[MutationResult], tags=["Cases"]
)
def note(
    case_id: CaseId, request: Request, payload: NoteRequest, context: WriteDep, params: NoQuery
):
    return mutation(request, context, "NOTE", payload, case_id=case_id)


@router.post(
    "/cases/{case_id}/interventions",
    response_model=ObjectResponse[MutationResult],
    status_code=201,
    tags=["Interventions"],
)
def plan_intervention(
    case_id: CaseId,
    request: Request,
    payload: InterventionRequest,
    context: WriteDep,
    params: NoQuery,
):
    return mutation(request, context, "INTERVENTION", payload, case_id=case_id)


@router.post(
    "/cases/{case_id}/interventions/{intervention_id}/outcomes",
    response_model=ObjectResponse[MutationResult],
    tags=["Interventions"],
)
def outcome(
    case_id: CaseId,
    intervention_id: CaseId,
    request: Request,
    payload: OutcomeRequest,
    context: WriteDep,
    params: NoQuery,
):
    return mutation(
        request, context, "OUTCOME", payload, case_id=case_id, intervention_id=intervention_id
    )
