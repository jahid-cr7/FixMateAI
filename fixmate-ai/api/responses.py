"""Success envelope and safe HTTP error helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, Request


def utc_now() -> datetime:
    """Return an aware UTC timestamp."""
    return datetime.now(timezone.utc)


def success(request: Request, data: Any) -> dict[str, Any]:
    """Wrap endpoint data in the shared API envelope."""
    return {
        "data": data,
        "meta": {
            "request_id": request.state.request_id,
            "api_version": "v1",
            "timestamp": utc_now(),
        },
    }


def api_error(status_code: int, code: str, message: str) -> HTTPException:
    """Create an HTTP exception with safe structured detail."""
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message},
    )

