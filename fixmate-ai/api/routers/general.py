"""Health and API capability endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from api.config import ApiSettings
from api.dependencies import get_data_service, get_settings
from api.responses import success
from api.schemas.common import ApiResponse, MessageData
from api.schemas.status import ApiStatus
from api.services.data_service import DataService
from src.llm import create_provider

router = APIRouter(tags=["General"])


@router.get(
    "/health",
    response_model=ApiResponse[MessageData],
    summary="Process health check",
)
def health(request: Request) -> dict:
    """Return process readiness without requiring authentication."""
    return success(request, {"status": "ok", "message": "FixMate AI API is healthy."})


@router.get(
    "/api/v1/status",
    response_model=ApiResponse[ApiStatus],
    summary="API and local data status",
)
def status(
    request: Request,
    settings: Annotated[ApiSettings, Depends(get_settings)],
    data_service: Annotated[DataService, Depends(get_data_service)],
) -> dict:
    """Return non-secret capability readiness."""
    provider = create_provider().status
    return success(
        request,
        {
            "status": "ok",
            "api_version": "v1",
            "database_available": data_service.database_available(),
            "post_auth_configured": bool(settings.api_token),
            "deterministic_assistant": True,
            "optional_ai_provider": provider.name,
            "optional_ai_configured": provider.configured,
        },
    )

