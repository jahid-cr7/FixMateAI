"""Unified system and network issue endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from api.dependencies import get_data_service
from api.responses import api_error, success
from api.schemas.common import ApiResponse, PageData
from api.schemas.issues import IssueRecord, IssueTypeFilter, SeverityFilter
from api.services.data_service import DataService

router = APIRouter(prefix="/api/v1/issues", tags=["Issues"])


@router.get("", response_model=ApiResponse[PageData[IssueRecord]])
def list_issues(
    request: Request,
    service: Annotated[DataService, Depends(get_data_service)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
    severity: SeverityFilter | None = None,
    issue_type: IssueTypeFilter | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> dict:
    """Return filtered, paginated system and network issues."""
    if date_from and date_to and date_from > date_to:
        raise api_error(422, "invalid_date_range", "date_from must be before date_to.")
    return success(
        request,
        service.issues(
            page,
            page_size,
            severity.value if severity else None,
            issue_type.value if issue_type else None,
            date_from,
            date_to,
        ),
    )


@router.get("/{issue_id}", response_model=ApiResponse[IssueRecord])
def get_issue(
    issue_id: str,
    request: Request,
    service: Annotated[DataService, Depends(get_data_service)],
) -> dict:
    """Return one issue by namespaced ID such as system:1 or network:2."""
    result = service.issue_by_id(issue_id)
    if result is None:
        raise api_error(404, "issue_not_found", "The requested issue does not exist.")
    return success(request, result)

