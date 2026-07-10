"""Tests for FIXMATE_DATABASE_URL parsing, redaction, and backend resolution."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.db_url import (
    BUILTIN_DB_PATH,
    classify_backend,
    get_database_backend,
    get_database_url,
    parse_database_url,
    redact_database_url,
    resolve_database_config,
)


def test_default_sqlite_path_when_no_environment_variables() -> None:
    """Missing FIXMATE_DATABASE_URL and FIXMATE_DB_PATH uses built-in SQLite."""
    sqlite_path, database_url, backend = resolve_database_config({})
    assert backend == "sqlite"
    assert database_url is None
    assert sqlite_path == BUILTIN_DB_PATH


def test_fixmate_database_url_sqlite_path() -> None:
    """A sqlite:/// URL resolves to SQLite with the extracted path."""
    env = {"FIXMATE_DATABASE_URL": "sqlite:///tmp/fixmate_test.db"}
    sqlite_path, database_url, backend = resolve_database_config(env)
    assert backend == "sqlite"
    assert database_url == "sqlite:///tmp/fixmate_test.db"
    # On Windows the leading slash is dropped by Path; verify the tail matches.
    assert sqlite_path.name == "fixmate_test.db"


def test_fixmate_db_path_fallback() -> None:
    """FIXMATE_DB_PATH is used when FIXMATE_DATABASE_URL is absent."""
    env = {"FIXMATE_DB_PATH": "/custom/path.db"}
    sqlite_path, database_url, backend = resolve_database_config(env)
    assert backend == "sqlite"
    assert sqlite_path == Path("/custom/path.db")


def test_fixmate_database_path_backward_compatible() -> None:
    """FIXMATE_DATABASE_PATH acts as a backward-compatible alias."""
    env = {"FIXMATE_DATABASE_PATH": "/legacy/path.db"}
    sqlite_path, database_url, backend = resolve_database_config(env)
    assert backend == "sqlite"
    assert sqlite_path == Path("/legacy/path.db")


def test_postgresql_url_classified_correctly() -> None:
    """postgresql:// and postgres:// both map to the postgresql backend."""
    assert classify_backend("postgresql://user:pass@host/db") == "postgresql"
    assert classify_backend("postgres://user:pass@host/db") == "postgresql"


def test_empty_or_none_url_defaults_to_sqlite() -> None:
    """None or empty strings mean SQLite."""
    assert classify_backend(None) == "sqlite"
    assert classify_backend("") == "sqlite"
    assert classify_backend("   ") == "sqlite"


def test_unrecognized_url_scheme_defaults_to_sqlite() -> None:
    """Unknown schemes are treated as SQLite for safety."""
    assert classify_backend("mysql://host/db") == "sqlite"


def test_parse_database_url_components() -> None:
    """URL components are extracted correctly."""
    parsed = parse_database_url("postgresql://user:secret@db.example.com:5432/fixmate")
    assert parsed["scheme"] == "postgresql"
    assert parsed["hostname"] == "db.example.com"
    assert parsed["port"] == 5432
    assert parsed["path"] == "/fixmate"
    assert parsed["username"] == "user"
    assert parsed["password"] == "secret"


def test_parse_database_url_without_credentials() -> None:
    """URLs without auth have None for username and password."""
    parsed = parse_database_url("postgresql://db.example.com/fixmate")
    assert parsed["username"] is None
    assert parsed["password"] is None


def test_redact_database_url_with_password() -> None:
    """Passwords are replaced with *** in redacted output."""
    raw = "postgresql://user:secret@host:5432/db"
    redacted = redact_database_url(raw)
    assert "secret" not in redacted
    assert "***" in redacted
    assert redacted == "postgresql://user:***@host:5432/db"


def test_redact_database_url_without_password() -> None:
    """URLs without passwords are returned unchanged."""
    raw = "postgresql://user@host:5432/db"
    assert redact_database_url(raw) == raw


def test_redact_database_url_sqlite_unchanged() -> None:
    """SQLite paths without a scheme are returned as-is."""
    raw = "/data/fixmate.db"
    assert redact_database_url(raw) == raw


def test_redact_database_url_sqlite_with_scheme() -> None:
    """SQLite URLs without passwords are returned unchanged."""
    raw = "sqlite:///data/fixmate.db"
    assert redact_database_url(raw) == raw


def test_resolve_database_config_postgresql_url() -> None:
    """PostgreSQL URLs keep the raw URL and still provide a fallback SQLite path."""
    env = {"FIXMATE_DATABASE_URL": "postgresql://user:pass@postgres:5432/fixmate"}
    sqlite_path, database_url, backend = resolve_database_config(env)
    assert backend == "postgresql"
    assert database_url == "postgresql://user:pass@postgres:5432/fixmate"
    assert sqlite_path == BUILTIN_DB_PATH


def test_no_secret_leakage_in_redact_helper() -> None:
    """Ensure the redaction helper does not accidentally expose credentials."""
    secret = "sk-tp-super-secret-key-value"
    raw = f"postgresql://user:{secret}@host:5432/db"
    redacted = redact_database_url(raw)
    assert secret not in redacted
    assert "user:" in redacted
    assert "@host" in redacted


def test_classify_backend_is_case_insensitive() -> None:
    """Scheme classification is case-insensitive."""
    assert classify_backend("POSTGRESQL://host/db") == "postgresql"
    assert classify_backend("POSTGRES://host/db") == "postgresql"
    assert classify_backend("SQLITE:///path/db") == "sqlite"


def test_get_database_url_missing_returns_none() -> None:
    """Missing FIXMATE_DATABASE_URL returns None."""
    assert get_database_url({}) is None


def test_get_database_url_from_environment() -> None:
    """FIXMATE_DATABASE_URL is returned when present."""
    assert get_database_url({"FIXMATE_DATABASE_URL": "sqlite:///test.db"}) == "sqlite:///test.db"
    assert get_database_url({"FIXMATE_DATABASE_URL": "postgresql://u:p@host/db"}) == "postgresql://u:p@host/db"


def test_get_database_backend_defaults_to_sqlite() -> None:
    """Missing URL defaults to sqlite backend."""
    assert get_database_backend({}) == "sqlite"


def test_get_database_backend_from_url() -> None:
    """Backend is inferred from the URL scheme."""
    assert get_database_backend({"FIXMATE_DATABASE_URL": "sqlite:///test.db"}) == "sqlite"
    assert get_database_backend({"FIXMATE_DATABASE_URL": "postgresql://u:p@host/db"}) == "postgresql"
    assert get_database_backend({"FIXMATE_DATABASE_URL": "postgres://u:p@host/db"}) == "postgresql"


def test_no_secret_leakage_in_error_or_status_messages() -> None:
    """Database URL must never appear with credentials in messages."""
    secret = "my-secret-123"
    url = f"postgresql://user:{secret}@host:5432/db"
    redacted = redact_database_url(url)
    assert secret not in redacted
    assert "***" in redacted
    assert "postgresql://user:***@host:5432/db" == redacted
