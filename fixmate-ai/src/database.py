"""SQLite persistence for scans and their detected issues."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "data" / "fixmate.db"


def connect(database_path: Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Open the database, creating its parent directory when necessary."""
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(database_path: Path = DEFAULT_DB_PATH) -> None:
    """Create the MVP tables if they do not already exist."""
    with connect(database_path) as connection:
        connection.executescript(
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
            );

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
            );
            """
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

