"""FastAPI dependency injection for settings, services, auth, and rate limits."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, Request

from api.config import ApiSettings
from api.responses import api_error
from api.security import InMemoryRateLimiter, token_matches
from api.services.assistant_service import AssistantService
from api.services.data_service import DataService
from api.services.diagnostic_service import DiagnosticService


def get_settings(request: Request) -> ApiSettings:
    """Return app-scoped immutable settings."""
    return request.app.state.settings


def get_data_service(
    settings: Annotated[ApiSettings, Depends(get_settings)],
) -> DataService:
    """Create a request-scoped read service for the configured database."""
    return DataService(settings.database_path)


def get_diagnostic_service(
    settings: Annotated[ApiSettings, Depends(get_settings)],
    data_service: Annotated[DataService, Depends(get_data_service)],
) -> DiagnosticService:
    """Create a request-scoped diagnostic orchestration service."""
    return DiagnosticService(settings.database_path, data_service)


def get_assistant_service(
    settings: Annotated[ApiSettings, Depends(get_settings)],
) -> AssistantService:
    """Create a request-scoped assistant service."""
    return AssistantService(settings.database_path)


def require_api_token(
    settings: Annotated[ApiSettings, Depends(get_settings)],
    supplied_token: Annotated[str | None, Header(alias="X-API-Token")] = None,
) -> None:
    """Protect mutation/compute POST endpoints with a configured local token."""
    if not settings.api_token:
        raise api_error(
            503,
            "api_token_not_configured",
            "POST endpoints are disabled until FIXMATE_API_TOKEN is configured.",
        )
    if supplied_token is None or not token_matches(settings.api_token, supplied_token):
        raise api_error(401, "invalid_api_token", "A valid X-API-Token header is required.")


def _rate_limit(request: Request, category: str, limit: int, settings: ApiSettings) -> None:
    """Apply per-client/category limits after authentication."""
    limiter: InMemoryRateLimiter = request.app.state.rate_limiter
    client = request.client.host if request.client else "local"
    if not limiter.allow(
        f"{client}:{category}", limit, settings.rate_window_seconds
    ):
        raise api_error(
            429,
            "rate_limit_exceeded",
            "Too many requests; retry after the configured rate-limit window.",
        )


def enforce_diagnostic_rate_limit(
    request: Request,
    settings: Annotated[ApiSettings, Depends(get_settings)],
) -> None:
    """Rate-limit system and network diagnostic POSTs."""
    _rate_limit(request, "diagnostic", settings.diagnostic_rate_limit, settings)


def enforce_assistant_rate_limit(
    request: Request,
    settings: Annotated[ApiSettings, Depends(get_settings)],
) -> None:
    """Rate-limit assistant POSTs independently."""
    _rate_limit(request, "assistant", settings.assistant_rate_limit, settings)

