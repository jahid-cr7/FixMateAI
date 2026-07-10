"""Database URL parsing, redaction, and backend resolution."""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from pathlib import Path
from urllib.parse import urlparse, urlunparse

BUILTIN_DB_PATH = Path(__file__).resolve().parents[1] / "data" / "fixmate.db"


def parse_database_url(url: str) -> dict[str, str | int | None]:
    """Parse a database URL into its components.

    Returns a dict with keys: scheme, hostname, port, path, username, password.
    Missing components are ``None``.
    """
    parsed = urlparse(url)
    return {
        "scheme": parsed.scheme or None,
        "hostname": parsed.hostname or None,
        "port": parsed.port,
        "path": parsed.path or None,
        "username": parsed.username or None,
        "password": parsed.password or None,
    }


def redact_database_url(url: str) -> str:
    """Return *url* with any password replaced by ``***``.

    If the URL has no credential component it is returned unchanged.
    URLs without a scheme are treated as local paths and returned as-is.
    """
    if "://" not in url:
        return url
    parsed = urlparse(url)
    if parsed.password:
        netloc = parsed.netloc.replace(parsed.password, "***", 1)
        redacted = parsed._replace(netloc=netloc)
        return urlunparse(redacted)
    return url


def classify_backend(url: str | None) -> str:
    """Return ``"postgresql"`` or ``"sqlite"`` based on *url*.

    An empty or ``None`` url means SQLite (local default).
    URLs starting with ``postgresql://`` or ``postgres://`` mean PostgreSQL.
    URLs starting with ``sqlite`` mean SQLite.
    """
    if not url:
        return "sqlite"
    lower = url.strip().lower()
    if lower.startswith(("postgresql://", "postgres://")):
        return "postgresql"
    if lower.startswith("sqlite"):
        return "sqlite"
    return "sqlite"


def get_database_url(environment: Mapping[str, str] | None = None) -> str | None:
    """Return the raw ``FIXMATE_DATABASE_URL`` value or ``None``."""
    source = os.environ if environment is None else environment
    return source.get("FIXMATE_DATABASE_URL", "").strip() or None


def get_database_backend(environment: Mapping[str, str] | None = None) -> str:
    """Return ``"sqlite"`` or ``"postgresql"`` based on the environment."""
    return classify_backend(get_database_url(environment))


def resolve_database_config(
    environment: Mapping[str, str] | None = None,
) -> tuple[Path, str | None, str]:
    """Resolve the effective database configuration.

    Returns ``(sqlite_path, database_url, backend)`` where:

    - *sqlite_path* is the ``Path`` to use when the backend is SQLite.
    - *database_url* is the raw URL string (may contain credentials) or ``None``.
    - *backend* is ``"sqlite"`` or ``"postgresql"``.
    """
    source = os.environ if environment is None else environment
    database_url = source.get("FIXMATE_DATABASE_URL", "").strip() or None
    backend = classify_backend(database_url)

    if backend == "sqlite" and database_url:
        sqlite_path = _sqlite_path_from_url(database_url)
    elif backend == "sqlite":
        configured = (
            source.get("FIXMATE_DB_PATH", "").strip()
            or source.get("FIXMATE_DATABASE_PATH", "").strip()
        )
        sqlite_path = Path(configured).expanduser() if configured else BUILTIN_DB_PATH
    else:
        sqlite_path = BUILTIN_DB_PATH

    return sqlite_path, database_url, backend


def _sqlite_path_from_url(url: str) -> Path:
    """Extract the filesystem path from a ``sqlite:///`` URL."""
    stripped = re.sub(r"^sqlite:/+", "", url)
    query_split = stripped.split("?", 1)
    raw = query_split[0]
    if not raw:
        return BUILTIN_DB_PATH
    return Path(raw)
