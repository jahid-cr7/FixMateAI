"""Admin-authenticated fleet issue workflow endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from api.dependencies import get_device_service, require_api_token
from api.responses import api_error, success
from api.schemas.common import ApiResponse
from api.schemas.devices import FleetIssueRecord, FleetIssueUpdateRequest
from api.services.device_service import DeviceService

router = APIRouter(
    prefix="/api/v1/fleet-issues",
    tags=["Fleet Issues"],
    dependencies=[Depends(require_api_token)],
)


@router.get("", response_model=ApiResponse[list[FleetIssueRecord]])
def list_fleet_issues(
    request: Request,
    service: Annotated[DeviceService, Depends(get_device_service)],
    device_id: Annotated[str | None, Query(max_length=64)] = None,
    status: Annotated[
        str | None,
        Query(pattern=r"^(open|acknowledged|in_progress|resolved|false_positive)$"),
    ] = None,
) -> dict:
    """List fleet issues with optional device and status filters."""
    return success(request, service.list_fleet_issues(device_id, status))


def _transition(
    service: DeviceService,
    issue_id: int,
    target_status: str,
    technician_note: str,
) -> dict:
    result = service.update_fleet_issue(issue_id, target_status, technician_note)
    if result is None:
        raise api_error(404, "issue_not_found", "The requested issue does not exist.")
    return result


@router.post(
    "/{issue_id}/acknowledge",
    response_model=ApiResponse[FleetIssueRecord],
)
def acknowledge_issue(
    issue_id: int,
    request: Request,
    service: Annotated[DeviceService, Depends(get_device_service)],
    payload: FleetIssueUpdateRequest | None = None,
) -> dict:
    """Acknowledge an open fleet issue."""
    note = payload.technician_note if payload else ""
    return success(request, _transition(service, issue_id, "acknowledged", note))


@router.post(
    "/{issue_id}/in-progress",
    response_model=ApiResponse[FleetIssueRecord],
)
def mark_in_progress(
    issue_id: int,
    request: Request,
    service: Annotated[DeviceService, Depends(get_device_service)],
    payload: FleetIssueUpdateRequest | None = None,
) -> dict:
    """Mark a fleet issue as in progress."""
    note = payload.technician_note if payload else ""
    return success(request, _transition(service, issue_id, "in_progress", note))


@router.post(
    "/{issue_id}/resolve",
    response_model=ApiResponse[FleetIssueRecord],
)
def resolve_issue(
    issue_id: int,
    request: Request,
    service: Annotated[DeviceService, Depends(get_device_service)],
    payload: FleetIssueUpdateRequest | None = None,
) -> dict:
    """Resolve a fleet issue with an optional technician note."""
    note = payload.technician_note if payload else ""
    return success(request, _transition(service, issue_id, "resolved", note))


@router.post(
    "/{issue_id}/false-positive",
    response_model=ApiResponse[FleetIssueRecord],
)
def mark_false_positive(
    issue_id: int,
    request: Request,
    service: Annotated[DeviceService, Depends(get_device_service)],
    payload: FleetIssueUpdateRequest | None = None,
) -> dict:
    """Mark a fleet issue as a false positive with an optional technician note."""
    note = payload.technician_note if payload else ""
    return success(request, _transition(service, issue_id, "false_positive", note))
