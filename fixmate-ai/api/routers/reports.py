"""Versioned report discovery and authenticated generation endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from api.dependencies import (
    enforce_report_rate_limit,
    get_report_service,
    require_api_token,
)
from api.responses import success
from api.schemas.common import ApiResponse
from api.schemas.reports import (
    GeneratedReportResult,
    GenerateReportRequest,
    ReportTypesResult,
    report_types_result,
)
from api.services.report_service import ReportService

router = APIRouter(prefix="/api/v1/reports", tags=["Reports"])


@router.get("/types", response_model=ApiResponse[ReportTypesResult])
def list_report_types(request: Request) -> dict:
    """List supported report scopes, formats, and selectable sections."""
    return success(request, report_types_result())


@router.post(
    "/generate",
    response_model=ApiResponse[GeneratedReportResult],
    dependencies=[Depends(require_api_token), Depends(enforce_report_rate_limit)],
)
def generate_report(
    payload: GenerateReportRequest,
    request: Request,
    service: Annotated[ReportService, Depends(get_report_service)],
) -> dict:
    """Generate and return a report in memory without writing an export file."""
    return success(request, service.generate(payload))

