"""Deterministic-default troubleshooting assistant endpoint."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from api.dependencies import (
    enforce_assistant_rate_limit,
    get_assistant_service,
    require_api_token,
)
from api.responses import success
from api.schemas.assistant import (
    AssistantMode,
    AssistantQueryRequest,
    AssistantQueryResult,
)
from api.schemas.common import ApiResponse
from api.services.assistant_service import AssistantService

router = APIRouter(prefix="/api/v1/assistant", tags=["Assistant"])


@router.post(
    "/query",
    response_model=ApiResponse[AssistantQueryResult],
    dependencies=[
        Depends(require_api_token),
        Depends(enforce_assistant_rate_limit),
    ],
)
def query_assistant(
    payload: AssistantQueryRequest,
    request: Request,
    service: Annotated[AssistantService, Depends(get_assistant_service)],
) -> dict:
    """Answer from deterministic evidence with optional bounded AI enhancement."""
    result = service.query(
        payload.question,
        ai_enhanced=payload.mode == AssistantMode.ai_enhanced,
        external_consent=payload.external_consent,
    )
    return success(request, result)

