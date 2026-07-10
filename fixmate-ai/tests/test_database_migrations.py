"""Tests for non-destructive SQLite migrations and network history."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import pytest

from src.database import (
    get_network_history,
    initialize_database,
    save_network_diagnostic,
    _table_exists,
)


def _create_legacy_database(path: Path) -> None:
    """Create the Phase 1 schema and one record as migration test input."""
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE scans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                collected_at TEXT NOT NULL,
                os_name TEXT NOT NULL,
                os_version TEXT NOT NULL,
                os_release TEXT NOT NULL,
                architecture TEXT NOT NULL,
                boot_time TEXT,
                cpu_percent REAL,
                memory_percent REAL,
                disk_used_percent REAL,
                disk_free_percent REAL,
                health_score INTEGER NOT NULL,
                top_processes_json TEXT NOT NULL
            );
            CREATE TABLE issues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scan_id INTEGER NOT NULL,
                code TEXT NOT NULL,
                severity TEXT NOT NULL,
                metric TEXT NOT NULL,
                value REAL NOT NULL,
                explanation TEXT NOT NULL,
                recommendation TEXT NOT NULL,
                FOREIGN KEY (scan_id) REFERENCES scans(id) ON DELETE CASCADE
            );
            INSERT INTO scans (
                collected_at, os_name, os_version, os_release, architecture,
                health_score, top_processes_json
            ) VALUES (
                '2026-01-01T00:00:00+00:00', 'Windows', 'test', '11',
                'AMD64', 100, '[]'
            );
            """
        )


def test_phase_2_migration_preserves_legacy_records(tmp_path: Path) -> None:
    """Adding network tables must not delete or rewrite Phase 1 scan data."""
    database_path = tmp_path / "legacy.db"
    _create_legacy_database(database_path)

    initialize_database(database_path)
    initialize_database(database_path)

    with sqlite3.connect(database_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM scans").fetchone()[0] == 1
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        assert {
            "schema_migrations",
            "network_diagnostics",
            "network_issues",
            "screenshot_analyses",
        } <= tables
        migrations = connection.execute(
            "SELECT COUNT(*) FROM schema_migrations"
        ).fetchone()[0]
        # Phase 11A, 12B, and 12D each add one named, additive migration after Phases 1–3.
        assert migrations == 6


def test_network_diagnostic_round_trip(tmp_path: Path) -> None:
    """Saved network fields should be available to historical charts."""
    database_path = tmp_path / "history.db"
    diagnostic = {
        "collected_at": "2026-01-01T00:00:00+00:00",
        "target_host": "1.1.1.1",
        "target_port": 443,
        "timeout_seconds": 1.0,
        "latency_threshold_ms": 150.0,
        "active_interfaces": ["Ethernet"],
        "connection_status": True,
        "internet_connected": True,
        "timed_out": False,
        "latency_ms": 25.0,
        "bytes_sent": 1000,
        "bytes_received": 2000,
    }
    issue = {
        "code": "HIGH_LATENCY",
        "severity": "medium",
        "evidence": "Simulated evidence",
        "explanation": "Simulated explanation",
        "recommendation": "Simulated safe recommendation",
        "detected_at": "2026-01-01T00:00:00+00:00",
    }

    diagnostic_id = save_network_diagnostic(
        diagnostic, [issue], database_path=database_path
    )
    history = get_network_history(database_path=database_path)

    assert diagnostic_id == 1
    assert history[0]["active_interfaces"] == ["Ethernet"]
    assert history[0]["internet_connected"] is True
    assert history[0]["latency_ms"] == 25.0
    with sqlite3.connect(database_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM network_issues").fetchone()[0] == 1


def test_postgresql_migration_sql_avoids_sqlite_only_syntax() -> None:
    """Migrations for PostgreSQL must not use SQLite-only syntax."""
    from src import database as db_module

    captured_sql: list[str] = []

    class FakeCursor:
        def fetchone(self) -> Any:
            return None

        def fetchall(self) -> list[Any]:
            return []

    class FakeConnection:
        dialect = "postgresql"

        def execute(self, sql: str, params: Any = ()) -> FakeCursor:
            captured_sql.append(sql)
            return FakeCursor()

        def __enter__(self) -> "FakeConnection":
            return self

        def __exit__(self, *args: Any) -> None:
            pass

    conn = FakeConnection()

    db_module._apply_phase_2_migration(conn, "postgresql")
    db_module._apply_phase_3_migration(conn, "postgresql")
    db_module._apply_phase_11a_migration(conn, "postgresql")
    db_module._apply_phase_12b_migration(conn, "postgresql")
    db_module._apply_phase_12d_migration(conn, "postgresql")

    all_sql = " ".join(captured_sql).upper()
    assert "AUTOINCREMENT" not in all_sql
    assert "PRAGMA" not in all_sql
    assert "SQLITE_" not in all_sql
    assert "BIGSERIAL" in all_sql


def test_sqlite_migration_uses_autoincrement() -> None:
    """SQLite migrations use INTEGER PRIMARY KEY AUTOINCREMENT."""
    from src import database as db_module

    captured_sql: list[str] = []

    class FakeCursor:
        def fetchone(self) -> Any:
            return None

        def fetchall(self) -> list[Any]:
            return []

    class FakeConnection:
        dialect = "sqlite"

        def execute(self, sql: str, params: Any = ()) -> FakeCursor:
            captured_sql.append(sql)
            return FakeCursor()

        def __enter__(self) -> "FakeConnection":
            return self

        def __exit__(self, *args: Any) -> None:
            pass

    conn = FakeConnection()

    db_module._apply_phase_2_migration(conn, "sqlite")
    db_module._apply_phase_3_migration(conn, "sqlite")

    all_sql = " ".join(captured_sql).upper()
    assert "AUTOINCREMENT" in all_sql
    assert "BIGSERIAL" not in all_sql


def test_table_exists_sqlite(tmp_path: Path) -> None:
    """_table_exists returns True for existing tables in SQLite."""
    from src.database import connect_sqlite

    db_path = tmp_path / "exists.db"
    with connect_sqlite(db_path) as conn:
        conn.execute("CREATE TABLE test_table (id INTEGER PRIMARY KEY)")
        assert _table_exists(conn, "test_table") is True
        assert _table_exists(conn, "nonexistent") is False


def test_table_exists_postgresql() -> None:
    """_table_exists queries information_schema in PostgreSQL."""
    captured: list[tuple[str, tuple[Any, ...]]] = []

    class FakeCursor:
        def fetchone(self) -> tuple[Any, ...] | None:
            return (1,)

    class FakeConnection:
        dialect = "postgresql"

        def execute(self, sql: str, params: Any = ()) -> FakeCursor:
            captured.append((sql, params))
            return FakeCursor()

    result = _table_exists(FakeConnection(), "scans")
    assert result is True
    assert "information_schema.tables" in captured[0][0]
    assert captured[0][1] == ("scans",)


def test_migration_error_redacts_database_url(monkeypatch, tmp_path: Path) -> None:
    """Migration errors must not leak database credentials."""
    secret_url = "postgresql://user:secret_password@localhost:5432/fixmate"

    class FakeConnection:
        dialect = "postgresql"

        def execute(self, sql: str, params: Any = ()) -> Any:
            raise RuntimeError(f"connection to {secret_url} failed")

        def __enter__(self) -> "FakeConnection":
            return self

        def __exit__(self, *args: Any) -> None:
            pass

    from src import database as db_module

    monkeypatch.setattr(
        db_module, "connect", lambda path, url: FakeConnection()
    )

    with pytest.raises(RuntimeError) as exc_info:
        db_module.initialize_database(tmp_path / "dummy.db", secret_url)

    assert "secret_password" not in str(exc_info.value)
    assert "***" in str(exc_info.value)
