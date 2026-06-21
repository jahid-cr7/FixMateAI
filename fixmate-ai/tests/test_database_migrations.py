"""Tests for non-destructive SQLite migrations and network history."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from src.database import (
    get_network_history,
    initialize_database,
    save_network_diagnostic,
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
        # Phase 11A adds one more named, additive migration after Phases 1–3.
        assert migrations == 4


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
