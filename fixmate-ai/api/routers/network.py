"""Versioned network diagnostic endpoints."""

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
from api.schemas.network import (
    NetworkDiagnostic,
    NetworkDiagnosticRequest,
    NetworkHistoryItem,
)
from api.services.data_service import DataService
from api.services.diagnostic_service import DiagnosticService
from api.services.errors import ServiceUnavailableError

router = APIRouter(prefix="/api/v1/network", tags=["Network"])


@router.get("/latest", response_model=ApiResponse[NetworkDiagnostic])
def latest_network(
    request: Request,
    service: Annotated[DataService, Depends(get_data_service)],
) -> dict:
    """Return the latest privacy-safe network diagnostic."""
    result = service.latest_network()
    if result is None:
        raise api_error(
            404, "network_diagnostic_not_found", "No network diagnostic is available."
        )
    return success(request, result)


@router.get("/history", response_model=ApiResponse[PageData[NetworkHistoryItem]])
def network_history(
    request: Request,
    service: Annotated[DataService, Depends(get_data_service)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> dict:
    """Return paginated network history with optional date filtering."""
    if date_from and date_to and date_from > date_to:
        raise api_error(422, "invalid_date_range", "date_from must be before date_to.")
    return success(
        request,
        service.network_history(page, page_size, date_from, date_to),
    )


@router.post(
    "/diagnostics",
    response_model=ApiResponse[NetworkDiagnostic],
    status_code=201,
    dependencies=[
        Depends(require_api_token),
        Depends(enforce_diagnostic_rate_limit),
    ],
)
def create_network_diagnostic(
    payload: NetworkDiagnosticRequest,
    request: Request,
    service: Annotated[DiagnosticService, Depends(get_diagnostic_service)],
) -> dict:
    """Run one bounded connectivity diagnostic using existing business logic."""
    try:
        result = service.run_network_diagnostic(
            payload.host,
            payload.port,
            payload.timeout_seconds,
            payload.latency_threshold_ms,
        )
    except ServiceUnavailableError:
        raise api_error(503, "network_diagnostic_failed", "Network diagnostic failed.")
    return success(request, result)

