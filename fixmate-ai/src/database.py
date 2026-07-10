"""SQLite and optional PostgreSQL persistence for scans and their detected issues."""

from __future__ import annotations

import json
import os
import sqlite3
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from src.db_backend import (
    DatabaseConnection,
    connect_postgresql,
    connect_sqlite,
)
from src.db_url import (
    BUILTIN_DB_PATH,
    classify_backend,
    redact_database_url,
    resolve_database_config,
)


def configured_database_path(environment: Mapping[str, str] | None = None) -> Path:
    """Resolve an optional startup database override without changing the default."""
    source = os.environ if environment is None else environment
    configured = (
        source.get("FIXMATE_DB_PATH", "").strip()
        or source.get("FIXMATE_DATABASE_PATH", "").strip()
    )
    return Path(configured).expanduser() if configured else BUILTIN_DB_PATH


_sqlite_path, _database_url, _backend = resolve_database_config()
DEFAULT_DB_PATH = _sqlite_path
DEFAULT_DATABASE_URL = _database_url
DEFAULT_BACKEND = _backend

PHASE_1_MIGRATION = "phase1_system_health"
PHASE_2_MIGRATION = "phase2_network_diagnostics"
PHASE_3_MIGRATION = "phase3_screenshot_analyzer"
PHASE_11A_MIGRATION = "phase11a_multi_device_foundation"
PHASE_12B_MIGRATION = "phase12b_fleet_issue_workflow"
PHASE_12D_MIGRATION = "phase12d_database_url_support"


def connect(
    database_path: Path = DEFAULT_DB_PATH,
    database_url: str | None = DEFAULT_DATABASE_URL,
) -> DatabaseConnection:
    """Open the database, creating its parent directory when necessary (SQLite)."""
    backend = classify_backend(database_url)
    if backend == "postgresql":
        if not database_url:
            raise ValueError("PostgreSQL backend selected but FIXMATE_DATABASE_URL is empty")
        return connect_postgresql(database_url)
    return connect_sqlite(database_path)


def connect_readonly(
    database_path: Path = DEFAULT_DB_PATH,
    database_url: str | None = DEFAULT_DATABASE_URL,
) -> DatabaseConnection | None:
    """Open an existing database in enforced read-only mode."""
    from src.db_backend import connect_postgresql_readonly, connect_sqlite_readonly

    backend = classify_backend(database_url)
    if backend == "postgresql":
        if not database_url:
            return None
        return connect_postgresql_readonly(database_url)
    return connect_sqlite_readonly(database_path)


def _auto_inc(dialect: str) -> str:
    if dialect == "postgresql":
        return "BIGSERIAL PRIMARY KEY"
    return "INTEGER PRIMARY KEY AUTOINCREMENT"


def _fmt_pct(dialect: str, col: str) -> str:
    if dialect == "postgresql":
        return f"TO_CHAR({col}, 'FM990.0') || '%'"
    return f"printf('%.1f%%', {col})"


def initialize_database(
    database_path: Path = DEFAULT_DB_PATH,
    database_url: str | None = DEFAULT_DATABASE_URL,
) -> None:
    """Apply data-preserving schema migrations required by the application."""
    try:
        with connect(database_path, database_url) as connection:
            dialect = connection.dialect
            ai = _auto_inc(dialect)

            connection.execute(
                f"""
                CREATE TABLE IF NOT EXISTS scans (
                    id {ai},
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
                f"""
                CREATE TABLE IF NOT EXISTS issues (
                    id {ai},
                    scan_id BIGINT NOT NULL,
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
            _record_migration(connection, PHASE_1_MIGRATION)

            if not _migration_applied(connection, dialect, PHASE_2_MIGRATION):
                _apply_phase_2_migration(connection, dialect)

            if not _migration_applied(connection, dialect, PHASE_3_MIGRATION):
                _apply_phase_3_migration(connection, dialect)

            if not _migration_applied(connection, dialect, PHASE_11A_MIGRATION):
                _apply_phase_11a_migration(connection, dialect)

            if not _migration_applied(connection, dialect, PHASE_12B_MIGRATION):
                _apply_phase_12b_migration(connection, dialect)

            if not _migration_applied(connection, dialect, PHASE_12D_MIGRATION):
                _apply_phase_12d_migration(connection, dialect)
    except Exception as exc:
        if database_url:
            from src.db_backend import _redact_exc

            raise _redact_exc(exc, database_url) from None
        raise


def _migration_applied(
    connection: DatabaseConnection, dialect: str, migration_id: str
) -> bool:
    placeholder = "%s" if dialect == "postgresql" else "?"
    row = connection.execute(
        f"SELECT 1 FROM schema_migrations WHERE migration_id = {placeholder}",
        (migration_id,),
    ).fetchone()
    return row is not None


def _record_migration(connection: DatabaseConnection, migration_id: str) -> None:
    dialect = connection.dialect
    placeholder = "%s" if dialect == "postgresql" else "?"
    connection.execute(
        f"INSERT INTO schema_migrations (migration_id) VALUES ({placeholder}) ON CONFLICT (migration_id) DO NOTHING",
        (migration_id,),
    )


def _table_exists(connection: DatabaseConnection, table_name: str) -> bool:
    """Return True if *table_name* exists in the current database."""
    dialect = connection.dialect
    if dialect == "postgresql":
        row = connection.execute(
            "SELECT 1 FROM information_schema.tables WHERE table_name = %s",
            (table_name,),
        ).fetchone()
    else:
        row = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table_name,),
        ).fetchone()
    return row is not None


def _boolean_type(dialect: str) -> str:
    """Return the backend-specific boolean column type."""
    return "BOOLEAN" if dialect == "postgresql" else "INTEGER"


def _apply_phase_2_migration(connection: DatabaseConnection, dialect: str) -> None:
    """Add network tables without modifying or deleting Phase 1 records."""
    ai = _auto_inc(dialect)
    connection.execute(
        f"""
        CREATE TABLE IF NOT EXISTS network_diagnostics (
            id {ai},
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
        f"""
        CREATE TABLE IF NOT EXISTS network_issues (
            id {ai},
            diagnostic_id BIGINT NOT NULL,
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
    _record_migration(connection, PHASE_2_MIGRATION)


def _apply_phase_3_migration(connection: DatabaseConnection, dialect: str) -> None:
    """Add screenshot-analysis history without altering prior phase records."""
    ai = _auto_inc(dialect)
    connection.execute(
        f"""
        CREATE TABLE IF NOT EXISTS screenshot_analyses (
            id {ai},
            analyzed_at TEXT NOT NULL,
            anonymized_filename TEXT NOT NULL,
            extracted_text_redacted TEXT NOT NULL,
            matched_issue_id TEXT,
            confidence_score REAL,
            CHECK (confidence_score IS NULL OR
                   (confidence_score >= 0 AND confidence_score <= 100))
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_screenshot_analyses_analyzed_at
        ON screenshot_analyses(analyzed_at)
        """
    )
    _record_migration(connection, PHASE_3_MIGRATION)


def _apply_phase_11a_migration(connection: DatabaseConnection, dialect: str) -> None:
    """Add fleet tables without altering existing single-device records."""
    ai = _auto_inc(dialect)
    scripts = [
        f"""
        CREATE TABLE IF NOT EXISTS devices (
            device_id TEXT PRIMARY KEY,
            display_name TEXT NOT NULL,
            operating_system TEXT NOT NULL,
            platform TEXT NOT NULL,
            agent_version TEXT NOT NULL,
            first_seen_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL,
            status TEXT NOT NULL,
            notes TEXT NOT NULL DEFAULT '',
            token_salt TEXT NOT NULL,
            token_hash TEXT NOT NULL
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS device_heartbeats (
            id {ai},
            device_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            status TEXT NOT NULL,
            agent_version TEXT NOT NULL,
            FOREIGN KEY (device_id) REFERENCES devices(device_id) ON DELETE CASCADE
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS device_scan_batches (
            id {ai},
            device_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            payload_summary TEXT NOT NULL,
            health_score INTEGER NOT NULL,
            highest_severity TEXT,
            issue_count INTEGER NOT NULL,
            FOREIGN KEY (device_id) REFERENCES devices(device_id) ON DELETE CASCADE,
            CHECK (health_score >= 0 AND health_score <= 100),
            CHECK (issue_count >= 0)
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_device_heartbeats_device_timestamp
        ON device_heartbeats(device_id, timestamp DESC)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_device_scan_batches_device_timestamp
        ON device_scan_batches(device_id, timestamp DESC)
        """,
    ]
    for stmt in scripts:
        connection.execute(stmt)
    _record_migration(connection, PHASE_11A_MIGRATION)


def _apply_phase_12b_migration(connection: DatabaseConnection, dialect: str) -> None:
    """Add fleet issue workflow table without altering existing records."""
    ai = _auto_inc(dialect)
    scripts = [
        f"""
        CREATE TABLE IF NOT EXISTS fleet_issues (
            id {ai},
            device_id TEXT NOT NULL,
            batch_id BIGINT NOT NULL,
            source TEXT NOT NULL,
            code TEXT NOT NULL,
            severity TEXT NOT NULL,
            evidence TEXT NOT NULL DEFAULT '',
            explanation TEXT NOT NULL DEFAULT '',
            recommendation TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'open'
                CHECK (status IN ('open','acknowledged','in_progress','resolved','false_positive')),
            technician_note TEXT NOT NULL DEFAULT '',
            detected_at TEXT NOT NULL,
            acknowledged_at TEXT,
            resolved_at TEXT,
            updated_at TEXT,
            FOREIGN KEY (device_id) REFERENCES devices(device_id) ON DELETE CASCADE,
            FOREIGN KEY (batch_id) REFERENCES device_scan_batches(id) ON DELETE CASCADE
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_fleet_issues_device_status
        ON fleet_issues(device_id, status)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_fleet_issues_status
        ON fleet_issues(status)
        """,
    ]
    for stmt in scripts:
        connection.execute(stmt)
    _record_migration(connection, PHASE_12B_MIGRATION)


def _apply_phase_12d_migration(connection: DatabaseConnection, dialect: str) -> None:
    """Record Phase 12D migration for database URL support."""
    _record_migration(connection, PHASE_12D_MIGRATION)


def save_scan(
    scan: Mapping[str, Any],
    issues: Sequence[Mapping[str, Any]],
    health_score: int,
    database_path: Path = DEFAULT_DB_PATH,
    database_url: str | None = DEFAULT_DATABASE_URL,
) -> int:
    """Save one scan and its issues atomically, returning the new scan ID."""
    initialize_database(database_path, database_url)
    with connect(database_path, database_url) as connection:
        cursor = connection.execute(
            """
            INSERT INTO scans (
                collected_at, os_name, os_version, os_release, architecture,
                boot_time, cpu_percent, memory_percent, disk_used_percent,
                disk_free_percent, health_score, top_processes_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING id
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
    limit: int = 100,
    database_path: Path = DEFAULT_DB_PATH,
    database_url: str | None = DEFAULT_DATABASE_URL,
) -> list[dict[str, Any]]:
    """Return recent scans in chronological order for dashboard charts."""
    initialize_database(database_path, database_url)
    with connect(database_path, database_url) as connection:
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
    database_url: str | None = DEFAULT_DATABASE_URL,
) -> int:
    """Save one network diagnostic and its issues atomically."""
    initialize_database(database_path, database_url)
    with connect(database_path, database_url) as connection:
        cursor = connection.execute(
            """
            INSERT INTO network_diagnostics (
                collected_at, target_host, target_port, timeout_seconds,
                latency_threshold_ms, active_interfaces_json, connection_status,
                internet_connected, timed_out, latency_ms, bytes_sent,
                bytes_received
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING id
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
    database_url: str | None = DEFAULT_DATABASE_URL,
) -> list[dict[str, Any]]:
    """Return recent network records in chronological order."""
    initialize_database(database_path, database_url)
    with connect(database_path, database_url) as connection:
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


def save_screenshot_analysis(
    analyzed_at: str,
    anonymized_filename: str,
    extracted_text_redacted: str,
    matched_issue_id: str | None,
    confidence_score: float | None,
    database_path: Path = DEFAULT_DB_PATH,
    database_url: str | None = DEFAULT_DATABASE_URL,
) -> int:
    """Store redacted analysis metadata without storing uploaded image data."""
    initialize_database(database_path, database_url)
    with connect(database_path, database_url) as connection:
        cursor = connection.execute(
            """
            INSERT INTO screenshot_analyses (
                analyzed_at, anonymized_filename, extracted_text_redacted,
                matched_issue_id, confidence_score
            ) VALUES (?, ?, ?, ?, ?)
            RETURNING id
            """,
            (
                analyzed_at,
                anonymized_filename,
                extracted_text_redacted,
                matched_issue_id,
                confidence_score,
            ),
        )
    return int(cursor.lastrowid)


def get_screenshot_analysis_history(
    limit: int = 50,
    database_path: Path = DEFAULT_DB_PATH,
    database_url: str | None = DEFAULT_DATABASE_URL,
) -> list[dict[str, Any]]:
    """Return recent screenshot analyses without any image content."""
    initialize_database(database_path, database_url)
    with connect(database_path, database_url) as connection:
        rows = connection.execute(
            """
            SELECT analyzed_at, anonymized_filename, extracted_text_redacted,
                   matched_issue_id, confidence_score
            FROM screenshot_analyses
            ORDER BY id DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]
