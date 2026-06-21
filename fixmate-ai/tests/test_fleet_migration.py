"""Non-destructive Phase 11A SQLite migration tests."""

from __future__ import annotations

import sqlite3

from src.database import PHASE_11A_MIGRATION, initialize_database, save_scan


def test_phase_11a_migration_preserves_existing_records(tmp_path) -> None:
    database = tmp_path / "migration.db"
    initialize_database(database)
    save_scan(
        {
            "collected_at": "2026-01-01T00:00:00+00:00",
            "os_name": "Synthetic OS",
            "os_version": "1",
            "os_release": "1",
            "architecture": "x64",
            "boot_time": None,
            "cpu_percent": 10,
            "memory_percent": 20,
            "disk_used_percent": 30,
            "disk_free_percent": 70,
            "top_processes": [],
        },
        [],
        100,
        database,
    )
    with sqlite3.connect(database) as connection:
        connection.execute("DROP TABLE device_scan_batches")
        connection.execute("DROP TABLE device_heartbeats")
        connection.execute("DROP TABLE devices")
        connection.execute(
            "DELETE FROM schema_migrations WHERE migration_id = ?",
            (PHASE_11A_MIGRATION,),
        )
        connection.commit()

    initialize_database(database)
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT COUNT(*) FROM scans").fetchone()[0] == 1
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        assert {"devices", "device_heartbeats", "device_scan_batches"} <= tables
