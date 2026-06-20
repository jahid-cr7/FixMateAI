"""Privacy-safe screenshot-analysis history endpoint."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from api.dependencies import get_data_service
from api.responses import api_error, success
from api.schemas.common import ApiResponse, PageData
from api.schemas.screenshot import ScreenshotAnalysisRecord
from api.services.data_service import DataService

router = APIRouter(prefix="/api/v1/screenshot-analyses", tags=["Screenshot Analysis"])


@router.get("", response_model=ApiResponse[PageData[ScreenshotAnalysisRecord]])
def list_screenshot_analyses(
    request: Request,
    service: Annotated[DataService, Depends(get_data_service)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> dict:
    """Return metadata only; never return image, filename, or OCR text."""
    if date_from and date_to and date_from > date_to:
        raise api_error(422, "invalid_date_range", "date_from must be before date_to.")
    return success(
        request,
        service.screenshot_analyses(page, page_size, date_from, date_to),
    )

