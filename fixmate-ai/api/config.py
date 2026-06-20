"""Environment-driven API configuration with safe localhost defaults."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from src.database import DEFAULT_DB_PATH


def _positive_int(value: str | None, default: int, maximum: int) -> int:
    """Parse a bounded positive integer or return a safe default."""
    try:
        parsed = int(value or default)
    except (TypeError, ValueError):
        return default
    return max(1, min(parsed, maximum))


def _allowed_origins(raw: str | None) -> tuple[str, ...]:
    """Parse explicit HTTP(S) origins while rejecting wildcard CORS."""
    defaults = ("http://127.0.0.1:8501", "http://localhost:8501")
    if not raw:
        return defaults
    origins: list[str] = []
    for candidate in raw.split(","):
        origin = candidate.strip().rstrip("/")
        parsed = urlparse(origin)
        if origin == "*" or parsed.scheme not in {"http", "https"} or not parsed.netloc:
            continue
        origins.append(origin)
    return tuple(dict.fromkeys(origins)) or defaults


@dataclass(frozen=True)
class ApiSettings:
    """Validated API settings; secret values are never represented in status output."""

    database_path: Path = DEFAULT_DB_PATH
    api_token: str = ""
    allowed_origins: tuple[str, ...] = (
        "http://127.0.0.1:8501",
        "http://localhost:8501",
    )
    max_request_bytes: int = 65_536
    diagnostic_rate_limit: int = 5
    assistant_rate_limit: int = 20
    rate_window_seconds: int = 60
    host: str = "127.0.0.1"
    port: int = 8000

    @classmethod
    def from_environment(cls) -> "ApiSettings":
        """Load configuration from environment variables without dotenv side effects."""
        database = os.environ.get("FIXMATE_DATABASE_PATH", "").strip()
        host = os.environ.get("FIXMATE_API_HOST", "127.0.0.1").strip()
        if host not in {"127.0.0.1", "localhost", "::1"}:
            host = "127.0.0.1"
        return cls(
            database_path=Path(database) if database else DEFAULT_DB_PATH,
            api_token=os.environ.get("FIXMATE_API_TOKEN", ""),
            allowed_origins=_allowed_origins(os.environ.get("FIXMATE_API_CORS_ORIGINS")),
            max_request_bytes=_positive_int(
                os.environ.get("FIXMATE_API_MAX_REQUEST_BYTES"), 65_536, 1_048_576
            ),
            diagnostic_rate_limit=_positive_int(
                os.environ.get("FIXMATE_API_DIAGNOSTIC_RATE_LIMIT"), 5, 1000
            ),
            assistant_rate_limit=_positive_int(
                os.environ.get("FIXMATE_API_ASSISTANT_RATE_LIMIT"), 20, 1000
            ),
            rate_window_seconds=_positive_int(
                os.environ.get("FIXMATE_API_RATE_WINDOW_SECONDS"), 60, 3600
            ),
            host=host,
            port=_positive_int(os.environ.get("FIXMATE_API_PORT"), 8000, 65535),
        )

