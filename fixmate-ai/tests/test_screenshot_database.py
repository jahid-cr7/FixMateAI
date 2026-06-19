"""Tests for the additive Phase 3 migration and redacted history."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from src.database import (
    PHASE_3_MIGRATION,
    get_screenshot_analysis_history,
    initialize_database,
    save_screenshot_analysis,
)


def test_phase_3_migration_preserves_phase_1_and_2_rows(tmp_path: Path) -> None:
    """Reapplying Phase 3 must preserve existing system and network records."""
    database_path = tmp_path / "phase2.db"
    initialize_database(database_path)
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO scans (
                collected_at, os_name, os_version, os_release, architecture,
                health_score, top_processes_json
            ) VALUES ('2026-01-01', 'Windows', 'test', '11', 'AMD64', 100, '[]')
            """
        )
        connection.execute(
            """
            INSERT INTO network_diagnostics (
                collected_at, target_host, target_port, timeout_seconds,
                latency_threshold_ms, active_interfaces_json, connection_status,
                internet_connected, timed_out
            ) VALUES ('2026-01-01', '1.1.1.1', 443, 1, 150, '[]', 0, 0, 0)
            """
        )
        connection.execute("DROP TABLE screenshot_analyses")
        connection.execute(
            "DELETE FROM schema_migrations WHERE migration_id = ?",
            (PHASE_3_MIGRATION,),
        )

    initialize_database(database_path)

    with sqlite3.connect(database_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM scans").fetchone()[0] == 1
        assert connection.execute(
            "SELECT COUNT(*) FROM network_diagnostics"
        ).fetchone()[0] == 1
        assert connection.execute(
            "SELECT COUNT(*) FROM screenshot_analyses"
        ).fetchone()[0] == 0


def test_screenshot_analysis_round_trip_contains_no_image(tmp_path: Path) -> None:
    """History stores redacted text and metadata but has no image column."""
    database_path = tmp_path / "analysis.db"
    analysis_id = save_screenshot_analysis(
        analyzed_at="2026-01-01T00:00:00+00:00",
        anonymized_filename="image-1234567890abcdef.png",
        extracted_text_redacted="password=[REDACTED] access denied",
        matched_issue_id="access_denied_windows",
        confidence_score=88.0,
        database_path=database_path,
    )
    history = get_screenshot_analysis_history(database_path=database_path)
    assert analysis_id == 1
    assert history[0]["matched_issue_id"] == "access_denied_windows"
    assert history[0]["extracted_text_redacted"] == "password=[REDACTED] access denied"
    with sqlite3.connect(database_path) as connection:
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(screenshot_analyses)")
        }
    assert not {"image", "image_bytes", "image_path"} & columns
