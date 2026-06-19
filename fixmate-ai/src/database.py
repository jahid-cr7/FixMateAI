"""SQLite persistence for scans and their detected issues."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "data" / "fixmate.db"
PHASE_1_MIGRATION = "phase1_system_health"
PHASE_2_MIGRATION = "phase2_network_diagnostics"


def connect(database_path: Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Open the database, creating its parent directory when necessary."""
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(database_path: Path = DEFAULT_DB_PATH) -> None:
    """Apply data-preserving schema migrations required by the application."""
    with connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS scans (
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
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS issues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scan_id INTEGER NOT NULL,
                code TEXT NOT NULL,
                severity TEXT NOT NULL,
                metric TEXT NOT NULL,
                value REAL NOT NULL,
                explanation TEXT NOT NULL,
                recommendation TEXT NOT NULL,
                FOREIGN KEY (scan_id) REFERENCES scans(id) ON DELETE CASCADE
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                migration_id TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            "INSERT OR IGNORE INTO schema_migrations (migration_id) VALUES (?)",
            (PHASE_1_MIGRATION,),
        )

        migration_applied = connection.execute(
            "SELECT 1 FROM schema_migrations WHERE migration_id = ?",
            (PHASE_2_MIGRATION,),
        ).fetchone()
        if migration_applied is None:
            _apply_phase_2_migration(connection)


def _apply_phase_2_migration(connection: sqlite3.Connection) -> None:
    """Add network tables without modifying or deleting Phase 1 records."""
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS network_diagnostics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            collected_at TEXT NOT NULL,
            target_host TEXT NOT NULL,
            target_port INTEGER NOT NULL,
            timeout_seconds REAL NOT NULL,
            latency_threshold_ms REAL NOT NULL,
            active_interfaces_json TEXT NOT NULL,
            connection_status INTEGER NOT NULL,
            internet_connected INTEGER NOT NULL,
            timed_out INTEGER NOT NULL,
            latency_ms REAL,
            bytes_sent INTEGER,
            bytes_received INTEGER
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS network_issues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            diagnostic_id INTEGER NOT NULL,
            code TEXT NOT NULL,
            severity TEXT NOT NULL,
            evidence TEXT NOT NULL,
            explanation TEXT NOT NULL,
            recommendation TEXT NOT NULL,
            detected_at TEXT NOT NULL,
            FOREIGN KEY (diagnostic_id)
                REFERENCES network_diagnostics(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_network_diagnostics_collected_at
        ON network_diagnostics(collected_at)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_network_issues_diagnostic_id
        ON network_issues(diagnostic_id)
        """
    )
    connection.execute(
        "INSERT INTO schema_migrations (migration_id) VALUES (?)",
        (PHASE_2_MIGRATION,),
    )


def save_scan(
    scan: Mapping[str, Any],
    issues: Sequence[Mapping[str, Any]],
    health_score: int,
    database_path: Path = DEFAULT_DB_PATH,
) -> int:
    """Save one scan and its issues atomically, returning the new scan ID."""
    initialize_database(database_path)
    with connect(database_path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO scans (
                collected_at, os_name, os_version, os_release, architecture,
                boot_time, cpu_percent, memory_percent, disk_used_percent,
                disk_free_percent, health_score, top_processes_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                scan["collected_at"], scan["os_name"], scan["os_version"],
                scan["os_release"], scan["architecture"], scan.get("boot_time"),
                scan.get("cpu_percent"), scan.get("memory_percent"),
                scan.get("disk_used_percent"), scan.get("disk_free_percent"),
                health_score, json.dumps(scan.get("top_processes", [])),
            ),
        )
        scan_id = int(cursor.lastrowid)
        connection.executemany(
            """
            INSERT INTO issues (
                scan_id, code, severity, metric, value, explanation, recommendation
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    scan_id, issue["code"], issue["severity"], issue["metric"],
                    issue["value"], issue["explanation"], issue["recommendation"],
                )
                for issue in issues
            ],
        )
    return scan_id


def get_scan_history(
    limit: int = 100, database_path: Path = DEFAULT_DB_PATH
) -> list[dict[str, Any]]:
    """Return recent scans in chronological order for dashboard charts."""
    initialize_database(database_path)
    with connect(database_path) as connection:
        rows = connection.execute(
            """
            SELECT collected_at, cpu_percent, memory_percent, disk_used_percent,
                   disk_free_percent, health_score
            FROM scans ORDER BY id DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in reversed(rows)]


def save_network_diagnostic(
    diagnostic: Mapping[str, Any],
    issues: Sequence[Mapping[str, Any]],
    database_path: Path = DEFAULT_DB_PATH,
) -> int:
    """Save one network diagnostic and its issues atomically."""
    initialize_database(database_path)
    with connect(database_path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO network_diagnostics (
                collected_at, target_host, target_port, timeout_seconds,
                latency_threshold_ms, active_interfaces_json, connection_status,
                internet_connected, timed_out, latency_ms, bytes_sent,
                bytes_received
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                diagnostic["collected_at"],
                diagnostic["target_host"],
                diagnostic["target_port"],
                diagnostic["timeout_seconds"],
                diagnostic["latency_threshold_ms"],
                json.dumps(diagnostic.get("active_interfaces", [])),
                int(bool(diagnostic.get("connection_status"))),
                int(bool(diagnostic.get("internet_connected"))),
                int(bool(diagnostic.get("timed_out"))),
                diagnostic.get("latency_ms"),
                diagnostic.get("bytes_sent"),
                diagnostic.get("bytes_received"),
            ),
        )
        diagnostic_id = int(cursor.lastrowid)
        connection.executemany(
            """
            INSERT INTO network_issues (
                diagnostic_id, code, severity, evidence, explanation,
                recommendation, detected_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    diagnostic_id,
                    issue["code"],
                    issue["severity"],
                    issue["evidence"],
                    issue["explanation"],
                    issue["recommendation"],
                    issue["detected_at"],
                )
                for issue in issues
            ],
        )
    return diagnostic_id


def get_network_history(
    limit: int = 100,
    database_path: Path = DEFAULT_DB_PATH,
) -> list[dict[str, Any]]:
    """Return recent network records in chronological order."""
    initialize_database(database_path)
    with connect(database_path) as connection:
        rows = connection.execute(
            """
            SELECT collected_at, target_host, target_port, connection_status,
                   internet_connected, timed_out, latency_ms, bytes_sent,
                   bytes_received, active_interfaces_json
            FROM network_diagnostics
            ORDER BY id DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()

    history: list[dict[str, Any]] = []
    for row in reversed(rows):
        item = dict(row)
        item["active_interfaces"] = json.loads(item.pop("active_interfaces_json"))
        item["connection_status"] = bool(item["connection_status"])
        item["internet_connected"] = bool(item["internet_connected"])
        item["timed_out"] = bool(item["timed_out"])
        history.append(item)
    return history
