"""Tests for database backend connection safety and redaction."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

from src.db_backend import (
    DatabaseConnection,
    connect_postgresql,
    connect_postgresql_readonly,
    connect_sqlite,
)


def test_postgresql_connect_error_redacts_url(monkeypatch) -> None:
    """PostgreSQL connection errors must not leak credentials."""
    secret_url = "postgresql://user:secret_password@localhost:5432/fixmate"

    def fake_connect(url: str) -> None:
        raise RuntimeError(f"Failed to connect to {url}")

    try:
        import psycopg2

        monkeypatch.setattr(psycopg2, "connect", fake_connect)
    except ImportError:
        fake_module = type(
            "psycopg2", (), {"connect": staticmethod(fake_connect)}
        )()
        monkeypatch.setitem(sys.modules, "psycopg2", fake_module)

    with pytest.raises(RuntimeError) as exc_info:
        connect_postgresql(secret_url)

    assert "secret_password" not in str(exc_info.value)
    assert "***" in str(exc_info.value)


def test_postgresql_readonly_connect_error_redacts_url(monkeypatch) -> None:
    """PostgreSQL read-only connection errors must not leak credentials."""
    secret_url = "postgresql://user:secret_password@localhost:5432/fixmate"

    def fake_connect(url: str) -> None:
        raise ConnectionError(f"bad url: {url}")

    try:
        import psycopg2

        monkeypatch.setattr(psycopg2, "connect", fake_connect)
    except ImportError:
        fake_module = type(
            "psycopg2", (), {"connect": staticmethod(fake_connect)}
        )()
        monkeypatch.setitem(sys.modules, "psycopg2", fake_module)

    with pytest.raises(ConnectionError) as exc_info:
        connect_postgresql_readonly(secret_url)

    assert "secret_password" not in str(exc_info.value)
    assert "***" in str(exc_info.value)


def test_missing_psycopg2_gives_clear_error(monkeypatch) -> None:
    """When psycopg2 is not installed, connect_postgresql raises a safe ImportError."""
    secret_url = "postgresql://user:secret_password@localhost:5432/fixmate"

    # Block psycopg2 import
    import builtins

    real_import = builtins.__import__

    def fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "psycopg2" or name.startswith("psycopg2."):
            raise ImportError(f"No module named '{name}'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(ImportError) as exc_info:
        connect_postgresql(secret_url)

    assert "secret_password" not in str(exc_info.value)
    assert "psycopg2" in str(exc_info.value).lower()


def test_database_connect_routes_to_postgresql(monkeypatch, tmp_path: Path) -> None:
    """database.connect() with a PostgreSQL URL should route to connect_postgresql."""
    from src import database as db_module

    calls: list[str] = []

    def fake_connect_postgresql(url: str) -> DatabaseConnection:
        calls.append(url)
        # Return a minimal mock that satisfies the DatabaseConnection interface
        return DatabaseConnection(None, is_postgres=True)

    monkeypatch.setattr(db_module, "connect_postgresql", fake_connect_postgresql)

    result = db_module.connect(tmp_path / "dummy.db", "postgresql://user:pass@host/db")

    assert len(calls) == 1
    assert calls[0] == "postgresql://user:pass@host/db"
    assert result.is_postgres is True


def test_database_connect_sqlite_url_uses_sqlite(monkeypatch, tmp_path: Path) -> None:
    """database.connect() with a sqlite:/// URL must use SQLite, not PostgreSQL."""
    from src import database as db_module

    pg_calls: list[str] = []

    def fake_connect_postgresql(url: str) -> DatabaseConnection:
        pg_calls.append(url)
        raise AssertionError("Should not reach PostgreSQL for SQLite URL")

    monkeypatch.setattr(db_module, "connect_postgresql", fake_connect_postgresql)

    db_path = tmp_path / "sqlite_url_test.db"
    result = db_module.connect(db_path, f"sqlite:///{db_path}")

    assert not pg_calls
    assert result.dialect == "sqlite"


def test_database_connect_defaults_to_sqlite(tmp_path: Path) -> None:
    """database.connect() with no URL must open SQLite by default."""
    from src import database as db_module

    db_path = tmp_path / "default_sqlite.db"
    result = db_module.connect(db_path, None)

    assert result.dialect == "sqlite"


def test_database_connect_readonly_routes_to_postgresql(monkeypatch) -> None:
    """database.connect_readonly() with a PostgreSQL URL should route correctly."""
    from src import database as db_module
    from src import db_backend as backend_module

    calls: list[str] = []

    def fake_connect_postgresql_readonly(url: str) -> DatabaseConnection:
        calls.append(url)
        return DatabaseConnection(None, is_postgres=True)

    monkeypatch.setattr(
        backend_module, "connect_postgresql_readonly", fake_connect_postgresql_readonly
    )

    result = db_module.connect_readonly(
        Path("dummy.db"), "postgresql://user:pass@host/db"
    )

    assert len(calls) == 1
    assert result is not None
    assert result.is_postgres is True


def test_connect_sqlite_creates_file_and_enables_foreign_keys(tmp_path: Path) -> None:
    """SQLite connection creates the file and turns on foreign keys."""
    db_path = tmp_path / "fk_test.db"
    assert not db_path.exists()

    with connect_sqlite(db_path) as conn:
        assert db_path.exists()
        cursor = conn.execute("PRAGMA foreign_keys")
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == 1
