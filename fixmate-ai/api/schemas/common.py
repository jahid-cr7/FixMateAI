"""Shared API envelopes, pagination metadata, and structured errors."""

from __future__ import annotations

from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ResponseMeta(BaseModel):
    """Metadata included in every successful response."""

    request_id: str
    api_version: str = "v1"
    timestamp: datetime


class ApiResponse(BaseModel, Generic[T]):
    """Consistent success response envelope."""

    data: T
    meta: ResponseMeta


class PageData(BaseModel, Generic[T]):
    """Paginated collection response."""

    items: list[T]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    total: int = Field(ge=0)


class ErrorDetail(BaseModel):
    """Safe machine-readable error information."""

    code: str
    message: str
    request_id: str


class ErrorResponse(BaseModel):
    """Consistent API error envelope without exception traces."""

    error: ErrorDetail
    timestamp: datetime


class MessageData(BaseModel):
    """Simple health/status result."""

    status: str
    message: str

    model_config = ConfigDict(json_schema_extra={"examples": [{"status": "ok", "message": "FixMate AI API is healthy."}]})

