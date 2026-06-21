"""Admin-authenticated fleet read endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from api.dependencies import get_device_service, require_api_token
from api.responses import api_error, success
from api.schemas.common import ApiResponse, PageData
from api.schemas.devices import DeviceScanBatch, DeviceSummary
from api.services.device_service import DeviceService

router = APIRouter(
    prefix="/api/v1/devices",
    tags=["Devices"],
    dependencies=[Depends(require_api_token)],
)


@router.get("", response_model=ApiResponse[list[DeviceSummary]])
def list_devices(
    request: Request,
    service: Annotated[DeviceService, Depends(get_device_service)],
    operating_system: Annotated[str | None, Query(max_length=100)] = None,
    status: Annotated[str | None, Query(pattern=r"^(online|offline|unknown)$")] = None,
    severity: Annotated[
        str | None, Query(pattern=r"^(none|low|medium|high|critical)$")
    ] = None,
) -> dict:
    """List privacy-safe fleet summaries with optional filters."""
    return success(
        request, service.list_devices(operating_system, status, severity)
    )


@router.get("/{device_id}", response_model=ApiResponse[DeviceSummary])
def get_device(
    device_id: str,
    request: Request,
    service: Annotated[DeviceService, Depends(get_device_service)],
) -> dict:
    """Return one device without token hashes or raw secrets."""
    device = service.get_device(device_id)
    if device is None:
        raise api_error(404, "device_not_found", "The requested device does not exist.")
    return success(request, device)


@router.get(
    "/{device_id}/latest", response_model=ApiResponse[DeviceScanBatch]
)
def latest_device_scan(
    device_id: str,
    request: Request,
    service: Annotated[DeviceService, Depends(get_device_service)],
) -> dict:
    """Return the latest minimized scan batch for one device."""
    if service.get_device(device_id) is None:
        raise api_error(404, "device_not_found", "The requested device does not exist.")
    latest = service.latest(device_id)
    if latest is None:
        raise api_error(404, "device_scan_not_found", "This device has no scan batch.")
    return success(request, latest)


@router.get(
    "/{device_id}/history",
    response_model=ApiResponse[PageData[DeviceScanBatch]],
)
def device_scan_history(
    device_id: str,
    request: Request,
    service: Annotated[DeviceService, Depends(get_device_service)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> dict:
    """Return paginated minimized scan history for one device."""
    if service.get_device(device_id) is None:
        raise api_error(404, "device_not_found", "The requested device does not exist.")
    return success(request, service.history(device_id, page, page_size))

