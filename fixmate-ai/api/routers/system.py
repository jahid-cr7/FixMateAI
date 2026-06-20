"""Versioned system scan endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from api.dependencies import (
    enforce_diagnostic_rate_limit,
    get_data_service,
    get_diagnostic_service,
    require_api_token,
)
from api.responses import api_error, success
from api.schemas.common import ApiResponse, PageData
from api.schemas.system import SystemHistoryItem, SystemScan
from api.services.data_service import DataService
from api.services.diagnostic_service import DiagnosticService
from api.services.errors import ServiceUnavailableError

router = APIRouter(prefix="/api/v1/system", tags=["System"])


@router.get("/latest", response_model=ApiResponse[SystemScan])
def latest_system(
    request: Request,
    service: Annotated[DataService, Depends(get_data_service)],
) -> dict:
    """Return the latest stored system scan."""
    result = service.latest_system()
    if result is None:
        raise api_error(404, "system_scan_not_found", "No system scan is available.")
    return success(request, result)


@router.get("/history", response_model=ApiResponse[PageData[SystemHistoryItem]])
def system_history(
    request: Request,
    service: Annotated[DataService, Depends(get_data_service)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> dict:
    """Return paginated system history with optional date filtering."""
    if date_from and date_to and date_from > date_to:
        raise api_error(422, "invalid_date_range", "date_from must be before date_to.")
    return success(
        request,
        service.system_history(page, page_size, date_from, date_to),
    )


@router.post(
    "/scans",
    response_model=ApiResponse[SystemScan],
    status_code=201,
    dependencies=[
        Depends(require_api_token),
        Depends(enforce_diagnostic_rate_limit),
    ],
)
def create_system_scan(
    request: Request,
    service: Annotated[DiagnosticService, Depends(get_diagnostic_service)],
) -> dict:
    """Run and store a safe system scan using existing business logic."""
    try:
        result = service.run_system_scan()
    except ServiceUnavailableError:
        raise api_error(503, "system_scan_failed", "System metric collection failed.")
    return success(request, result)

