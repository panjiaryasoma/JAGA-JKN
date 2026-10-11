"""HTTP envelopes and query contracts, separate from the data adapter."""

import re
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from packages.domain.read_models import DatasetRef, Period, ReadModel


class DataResponse[T](ReadModel):
    data: T
    meta: DatasetRef


class Pagination(ReadModel):
    page: int
    page_size: int
    total: int
    total_pages: int


class PageResponse[T](ReadModel):
    data: tuple[T, ...]
    meta: DatasetRef
    pagination: Pagination


class ObjectResponse[T](ReadModel):
    data: T


class WorkflowPage[T](ReadModel):
    data: tuple[T, ...]
    pagination: Pagination


class LiveResponse(ReadModel):
    status: Literal["alive"] = "alive"


class ReadyResponse(ReadModel):
    status: Literal["ready"] = "ready"
    dataset_id: str


class ErrorDetail(ReadModel):
    location: tuple[str, ...]
    code: str
    message: str


class ErrorBody(ReadModel):
    code: str
    message: str
    request_id: str
    details: tuple[ErrorDetail, ...] = ()


class ErrorResponse(ReadModel):
    error: ErrorBody


class EmptyQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PageQuery(EmptyQuery):
    page: Annotated[int, Field(ge=1, le=100000)] = 1
    page_size: Annotated[int, Field(ge=1, le=100)] = 20

    @field_validator("page", "page_size", mode="before")
    @classmethod
    def whole_decimal_number(cls, value):
        if isinstance(value, str) and re.fullmatch(r"[1-9][0-9]*", value) is None:
            raise ValueError("Expected a positive decimal integer")
        return value


class CompanyQuery(PageQuery):
    q: Annotated[str, Field(min_length=1, max_length=100)] | None = None
    provinsi: Annotated[str, Field(min_length=1, max_length=100)] | None = None
    skala_usaha: Annotated[str, Field(min_length=1, max_length=100)] | None = None
    kode_kbli: Annotated[str, Field(min_length=1, max_length=100)] | None = None

    @field_validator("q", "provinsi", "skala_usaha", "kode_kbli", mode="before")
    @classmethod
    def trim_filter(cls, value):
        return value.strip() if isinstance(value, str) else value


class HistoryQuery(PageQuery):
    page_size: Annotated[int, Field(ge=1, le=100)] = 24
    period_from: Period | None = None
    period_to: Period | None = None

    @model_validator(mode="after")
    def ordered_range(self):
        if self.period_from and self.period_to and self.period_from > self.period_to:
            raise ValueError("Period range is reversed")
        return self
