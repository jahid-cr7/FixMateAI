"""Authenticated ingestion endpoints for endpoint agents."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request, status

from api.dependencies import (
    enforce_agent_rate_limit,
    get_device_service,
    require_device_enrollment_token,
)
from api.responses import api_error, success
from api.schemas.common import ApiResponse
from api.schemas.devices import (
    DeviceHeartbeatRequest,
    DeviceHeartbeatResult,
    DeviceRegistrationRequest,
    DeviceRegistrationResult,
    DeviceScanBatch,
    DeviceScanUploadRequest,
)
from api.services.device_service import DeviceService

router = APIRouter(
    prefix="/api/v1/agent",
    tags=["Endpoint Agent"],
    dependencies=[Depends(enforce_agent_rate_limit)],
)


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[DeviceRegistrationResult],
)
def register_device(
    payload: DeviceRegistrationRequest,
    request: Request,
    service: Annotated[DeviceService, Depends(get_device_service)],
    token: Annotated[str, Depends(require_device_enrollment_token)],
) -> dict:
    """Register or refresh a device using the configured enrollment token."""
    device = service.register(payload, token)
    return success(
        request,
        {"device": device, "message": "Device registered successfully."},
    )


def _authenticated_token(
    service: DeviceService, device_id: str, supplied_token: str | None
) -> None:
    if supplied_token is None or not service.authenticate(device_id, supplied_token):
        raise api_error(
            401, "invalid_device_token", "A valid X-Device-Token header is required."
        )


@router.post(
    "/heartbeat", response_model=ApiResponse[DeviceHeartbeatResult]
)
def record_heartbeat(
    payload: DeviceHeartbeatRequest,
    request: Request,
    service: Annotated[DeviceService, Depends(get_device_service)],
    token: Annotated[str | None, Header(alias="X-Device-Token")] = None,
) -> dict:
    """Record a device heartbeat after per-device token verification."""
    _authenticated_token(service, payload.device_id, token)
    return success(request, service.heartbeat(payload))


@router.post(
    "/scans",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[DeviceScanBatch],
)
def upload_scan(
    payload: DeviceScanUploadRequest,
    request: Request,
    service: Annotated[DeviceService, Depends(get_device_service)],
    token: Annotated[str | None, Header(alias="X-Device-Token")] = None,
) -> dict:
    """Store one privacy-minimized scan batch after device authentication."""
    _authenticated_token(service, payload.device_id, token)
    return success(request, service.upload_scan(payload))
