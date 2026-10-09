"""Synthetic evidence and persistent human-review workflow API."""

import json
import logging
from collections import Counter
from contextlib import asynccontextmanager
from time import perf_counter
from typing import Annotated
from uuid import uuid4

from fastapi import FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from apps.api.auth import registry
from apps.api.config import Settings
from apps.api.schemas import (
    CompanyQuery,
    DataResponse,
    EmptyQuery,
    ErrorBody,
    ErrorDetail,
    ErrorResponse,
    HistoryQuery,
    LiveResponse,
    PageQuery,
    PageResponse,
    Pagination,
    ReadyResponse,
)
from apps.api.workflow import router as workflow_router
from packages.data.case_store import CaseStore
from packages.data.snapshot import DatasetError, Snapshot, load_snapshot
from packages.domain.cases import WorkflowError as APIError
from packages.domain.read_models import Company, CompanyId, DatasetInfo, MonthlyEvidence, Period

LOGGER = logging.getLogger("jaga.api")
ERROR_MESSAGES = {
    "NOT_FOUND": "Resource tidak ditemukan.",
    "METHOD_NOT_ALLOWED": "Method tidak tersedia untuk resource ini.",
    "VALIDATION_ERROR": "Permintaan tidak sesuai kontrak API.",
    "DATASET_UNAVAILABLE": "Snapshot data belum tersedia. Hubungi pengelola prototipe.",
    "DATASET_INVALID": "Snapshot data tidak lolos validasi. Hubungi pengelola prototipe.",
    "INTERNAL_ERROR": "Terjadi kegagalan internal.",
    "AUTH_NOT_CONFIGURED": "Token akses demo belum dikonfigurasi.",
    "UNAUTHORIZED": "Token akses diperlukan atau tidak valid.",
    "FORBIDDEN": "Role tidak memiliki wewenang untuk tindakan ini.",
    "PERSISTENCE_UNAVAILABLE": "Penyimpanan kasus tidak tersedia.",
    "CASE_ALREADY_OPEN": "Sudah ada kasus aktif untuk badan usaha dan bulan ini.",
    "INVALID_TRANSITION": "Tindakan tidak sesuai status saat ini.",
    "OPEN_INTERVENTIONS": "Selesaikan atau batalkan intervensi yang masih direncanakan.",
    "INVALID_RECURRENCE": "Hubungan recurrence tidak memenuhi kontrak.",
    "VERSION_CONFLICT": "Versi kasus berubah. Muat ulang sebelum mencoba tindakan baru.",
    "IDEMPOTENCY_CONFLICT": "Idempotency-Key sudah digunakan untuk permintaan berbeda.",
    "PRECONDITION_REQUIRED": "If-Match diperlukan untuk mengubah kasus yang sudah ada.",
}
ERROR_RESPONSES = {
    status: {"model": ErrorResponse, "description": description}
    for status, description in {
        404: "Resource not found",
        405: "Method not allowed",
        422: "Request validation failed",
        401: "Authentication required",
        403: "Insufficient role",
        409: "Workflow conflict",
        412: "Case version changed",
        428: "If-Match required",
        503: "Required component unavailable or invalid",
        500: "Unexpected internal failure",
    }.items()
}


def error_response(request, status, code, *, details=(), headers=None):
    body = ErrorResponse(
        error=ErrorBody(
            code=code,
            message=ERROR_MESSAGES[code],
            request_id=request.state.request_id,
            details=details,
        )
    )
    return JSONResponse(status_code=status, content=body.model_dump(mode="json"), headers=headers)


def repository(request: Request) -> Snapshot:
    if request.app.state.snapshot is None:
        raise APIError(503, request.app.state.dataset_error)
    return request.app.state.snapshot


def page_of(rows, query: PageQuery, ref, item_model):
    total = len(rows)
    offset = (query.page - 1) * query.page_size
    return PageResponse[item_model](
        data=tuple(rows[offset : offset + query.page_size]),
        meta=ref,
        pagination=Pagination(
            page=query.page,
            page_size=query.page_size,
            total=total,
            total_pages=(total + query.page_size - 1) // query.page_size,
        ),
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings if settings is not None else Settings.from_environment()

    @asynccontextmanager
    async def lifespan(application):
        application.state.snapshot = None
        application.state.dataset_error = "DATASET_UNAVAILABLE"
        try:
            application.state.snapshot = load_snapshot(config.data_root, config.manifest_path)
        except DatasetError as exc:
            application.state.dataset_error = exc.code
            LOGGER.warning(json.dumps({"event": "dataset_load_failed", "code": exc.code}))
        application.state.case_store = None
        try:
            case_store = CaseStore(config.database_path)
            case_store.initialize()
            application.state.case_store = case_store
        except APIError as exc:
            LOGGER.warning(json.dumps({"event": "case_store_load_failed", "code": exc.code}))
        yield
        application.state.snapshot = None
        application.state.case_store = None

    application = FastAPI(
        title="JAGA-JKN Synthetic Evidence API",
        version="0.1.0",
        lifespan=lifespan,
        description="Prototipe bukti sintetis dan workflow review. ML NOT_CONFIGURED; kebijakan UNRESOLVED.",
        responses=ERROR_RESPONSES,
    )
    # Useful for ASGI clients that omit lifespan: unavailable is safer than fabricated data.
    application.state.snapshot = None
    application.state.dataset_error = "DATASET_UNAVAILABLE"
    application.state.case_store = None
    application.state.auth_registry = registry(config)

    @application.middleware("http")
    async def request_context(request: Request, call_next):
        started = perf_counter()
        request.state.request_id = str(uuid4())
        try:
            counts = Counter(key for key, _ in request.query_params.multi_items())
            if any(count > 1 for count in counts.values()):
                response = error_response(
                    request,
                    422,
                    "VALIDATION_ERROR",
                    details=(
                        ErrorDetail(
                            location=("query",),
                            code="duplicate_parameter",
                            message="Parameter query tidak boleh berulang.",
                        ),
                    ),
                )
            else:
                response = await call_next(request)
        except Exception as exc:  # noqa: BLE001 -- last HTTP boundary; sanitize unexpected failures
            LOGGER.error(
                json.dumps(
                    {
                        "event": "request_failed",
                        "request_id": request.state.request_id,
                        "exception_type": type(exc).__name__,
                    }
                )
            )
            response = error_response(request, 500, "INTERNAL_ERROR")
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["Cache-Control"] = "no-store"
        route = request.scope.get("route")
        LOGGER.info(
            json.dumps(
                {
                    "event": "request",
                    "request_id": request.state.request_id,
                    "method": request.method,
                    "route": getattr(route, "path", "<unmatched>"),
                    "status": response.status_code,
                    "duration_ms": round((perf_counter() - started) * 1000, 3),
                }
            )
        )
        return response

    @application.exception_handler(APIError)
    async def api_error(request, exc):
        return error_response(request, exc.status, exc.code, headers=exc.headers)

    @application.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        details = tuple(
            ErrorDetail(
                location=tuple(str(part) for part in error["loc"]),
                code=error["type"],
                message="Parameter tidak sesuai kontrak.",
            )
            for error in exc.errors()
        )
        return error_response(request, 422, "VALIDATION_ERROR", details=details)

    @application.exception_handler(HTTPException)
    async def http_error(request, exc):
        code = {404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}.get(exc.status_code, "INTERNAL_ERROR")
        return error_response(request, exc.status_code, code, headers=exc.headers)

    @application.get("/health/live", response_model=LiveResponse, tags=["Health"])
    def live(params: Annotated[EmptyQuery, Query()]):
        return LiveResponse()

    @application.get("/health/ready", response_model=ReadyResponse, tags=["Health"])
    def ready(request: Request, params: Annotated[EmptyQuery, Query()]):
        snapshot = repository(request)
        if request.app.state.case_store is None:
            raise APIError(503, "PERSISTENCE_UNAVAILABLE")
        request.app.state.case_store.check_ready()
        return ReadyResponse(dataset_id=snapshot.ref.dataset_id)

    @application.get("/api/v1/dataset", response_model=DataResponse[DatasetInfo], tags=["Dataset"])
    def dataset(request: Request, params: Annotated[EmptyQuery, Query()]):
        snapshot = repository(request)
        return DataResponse[DatasetInfo](data=snapshot.info, meta=snapshot.ref)

    @application.get(
        "/api/v1/badan-usaha", response_model=PageResponse[Company], tags=["Badan usaha"]
    )
    def companies(request: Request, params: Annotated[CompanyQuery, Query()]):
        snapshot = repository(request)
        rows = snapshot.companies
        if params.q:
            query = params.q.casefold()
            rows = tuple(
                row
                for row in rows
                if query in row.id_badan_usaha.casefold()
                or query in (row.nama_badan_usaha or "").casefold()
            )
        for field in ("provinsi", "skala_usaha", "kode_kbli"):
            value = getattr(params, field)
            if value is not None:
                rows = tuple(row for row in rows if getattr(row, field) == value)
        return page_of(rows, params, snapshot.ref, Company)

    @application.get(
        "/api/v1/badan-usaha/{id_badan_usaha}",
        response_model=DataResponse[Company],
        tags=["Badan usaha"],
    )
    def company(
        id_badan_usaha: CompanyId, request: Request, params: Annotated[EmptyQuery, Query()]
    ):
        snapshot = repository(request)
        data = snapshot.company_index.get(id_badan_usaha)
        if data is None:
            raise APIError(404, "NOT_FOUND")
        return DataResponse[Company](data=data, meta=snapshot.ref)

    @application.get(
        "/api/v1/badan-usaha/{id_badan_usaha}/evidence",
        response_model=PageResponse[MonthlyEvidence],
        tags=["Evidence"],
    )
    def history(
        id_badan_usaha: CompanyId, request: Request, params: Annotated[HistoryQuery, Query()]
    ):
        snapshot = repository(request)
        if id_badan_usaha not in snapshot.company_index:
            raise APIError(404, "NOT_FOUND")
        rows = tuple(
            row
            for row in snapshot.histories[id_badan_usaha]
            if (params.period_from is None or row.periode_bulan >= params.period_from)
            and (params.period_to is None or row.periode_bulan <= params.period_to)
        )
        return page_of(rows, params, snapshot.ref, MonthlyEvidence)

    @application.get(
        "/api/v1/badan-usaha/{id_badan_usaha}/evidence/{periode_bulan}",
        response_model=DataResponse[MonthlyEvidence],
        tags=["Evidence"],
    )
    def monthly(
        id_badan_usaha: CompanyId,
        periode_bulan: Period,
        request: Request,
        params: Annotated[EmptyQuery, Query()],
    ):
        snapshot = repository(request)
        data = snapshot.evidence_index.get((id_badan_usaha, periode_bulan))
        if data is None:
            raise APIError(404, "NOT_FOUND")
        return DataResponse[MonthlyEvidence](data=data, meta=snapshot.ref)

    application.include_router(workflow_router)
    return application


app = create_app()
