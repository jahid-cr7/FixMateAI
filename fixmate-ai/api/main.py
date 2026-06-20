"""Production-style FastAPI application factory for FixMate AI."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

import uvicorn
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from api.config import ApiSettings
from api.middleware import RequestContextMiddleware
from api.responses import utc_now
from api.routers import assistant, general, issues, network, reports, screenshot, system
from api.schemas.common import ErrorResponse
from api.security import InMemoryRateLimiter
from src.database import initialize_database


def _request_id(request: Request) -> str:
    """Return the middleware request ID or a safe fallback."""
    return getattr(request.state, "request_id", "unavailable")


def _error_response(
    request: Request,
    status_code: int,
    code: str,
    message: str,
) -> JSONResponse:
    """Build a trace-free structured error response."""
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "request_id": _request_id(request),
            },
            "timestamp": utc_now().isoformat(),
        },
        headers={"X-Request-ID": _request_id(request)},
    )


def create_app(settings: ApiSettings | None = None) -> FastAPI:
    """Create an isolated API app suitable for production or temporary tests."""
    configured = settings or ApiSettings.from_environment()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        initialize_database(configured.database_path)
        yield

    application = FastAPI(
        title="FixMate AI API",
        summary="Versioned local diagnostics and troubleshooting API",
        description=(
            "A localhost-first REST API over FixMate AI's existing system, network, "
            "issue, screenshot-analysis, and deterministic assistant services."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
        responses={
            401: {"model": ErrorResponse},
            404: {"model": ErrorResponse},
            413: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
            429: {"model": ErrorResponse},
            500: {"model": ErrorResponse},
            503: {"model": ErrorResponse},
        },
    )
    application.state.settings = configured
    application.state.rate_limiter = InMemoryRateLimiter()
    application.add_middleware(RequestContextMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(configured.allowed_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "X-API-Token", "X-Request-ID"],
    )

    @application.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, error: StarletteHTTPException
    ) -> JSONResponse:
        detail = error.detail if isinstance(error.detail, dict) else {}
        return _error_response(
            request,
            error.status_code,
            str(detail.get("code", "http_error")),
            str(detail.get("message", "The request could not be completed.")),
        )

    @application.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, error: RequestValidationError
    ) -> JSONResponse:
        return _error_response(
            request,
            422,
            "validation_error",
            "Request parameters or body are invalid.",
        )

    @application.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, error: Exception) -> JSONResponse:
        return _error_response(
            request,
            500,
            "internal_error",
            "An internal server error occurred.",
        )

    application.include_router(general.router)
    application.include_router(system.router)
    application.include_router(network.router)
    application.include_router(issues.router)
    application.include_router(screenshot.router)
    application.include_router(assistant.router)
    application.include_router(reports.router)
    return application


app = create_app()


if __name__ == "__main__":
    runtime_settings = ApiSettings.from_environment()
    uvicorn.run(
        "api.main:app",
        host=runtime_settings.host,
        port=runtime_settings.port,
        reload=False,
    )
