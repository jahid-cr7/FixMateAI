"""Safety, determinism, and privacy tests for the portfolio demo generator."""

from __future__ import annotations

import hashlib
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from scripts.generate_demo_data import (
    DEMO_MARKER,
    DemoDataSafetyError,
    generate_demo_database,
    is_demo_database,
)
from src.database import DEFAULT_DB_PATH


def _database_fingerprint(database_path: Path) -> str:
    """Hash ordered logical content rather than SQLite page-level bytes."""
    with closing(sqlite3.connect(database_path)) as connection:
        tables = [
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
            if row[0] != "schema_migrations"
        ]
        content = []
        for table in tables:
            content.append((table, connection.execute(f'SELECT * FROM "{table}" ORDER BY rowid').fetchall()))
    return hashlib.sha256(repr(content).encode("utf-8")).hexdigest()


def test_demo_generation_is_deterministic_and_marked(tmp_path: Path) -> None:
    first = tmp_path / "first.db"
    second = tmp_path / "second.db"
    first_summary = generate_demo_database(first, seed=77, days=10)
    second_summary = generate_demo_database(second, seed=77, days=10)
    assert first_summary.system_scans == 10
    assert first_summary.network_diagnostics == 10
    assert is_demo_database(first)
    assert _database_fingerprint(first) == _database_fingerprint(second)
    with closing(sqlite3.connect(first)) as connection:
        marker = connection.execute("SELECT marker FROM demo_metadata").fetchone()[0]
    assert marker == DEMO_MARKER


def test_existing_files_are_never_silently_overwritten(tmp_path: Path) -> None:
    demo_path = tmp_path / "demo.db"
    generate_demo_database(demo_path, days=2)
    before = demo_path.read_bytes()
    with pytest.raises(DemoDataSafetyError, match="already exists"):
        generate_demo_database(demo_path, days=2)
    assert demo_path.read_bytes() == before

    user_path = tmp_path / "user.db"
    with closing(sqlite3.connect(user_path)) as connection:
        connection.execute("CREATE TABLE personal_records (value TEXT)")
        connection.execute("INSERT INTO personal_records VALUES ('preserve me')")
        connection.commit()
    with pytest.raises(DemoDataSafetyError, match="synthetic demo marker"):
        generate_demo_database(user_path, days=2, reset_demo=True)
    with closing(sqlite3.connect(user_path)) as connection:
        assert connection.execute("SELECT value FROM personal_records").fetchone()[0] == "preserve me"


def test_reset_replaces_only_a_marked_demo(tmp_path: Path) -> None:
    output = tmp_path / "resettable.db"
    generate_demo_database(output, seed=1, days=2)
    first_hash = _database_fingerprint(output)
    generate_demo_database(output, seed=2, days=3, reset_demo=True)
    assert is_demo_database(output)
    assert _database_fingerprint(output) != first_hash


def test_demo_content_contains_no_obvious_private_values(tmp_path: Path) -> None:
    output = tmp_path / "privacy.db"
    generate_demo_database(output, days=14)
    with closing(sqlite3.connect(output)) as connection:
        dump = "\n".join(connection.iterdump()).casefold()
    forbidden = (
        "@gmail.",
        "@outlook.",
        "c:\\users\\",
        "/home/",
        "api_key=",
        "password=",
        "bearer ",
        "aa:bb:cc:dd:ee:ff",
        "192.168.",
        "10.0.0.",
    )
    assert all(value not in dump for value in forbidden)
    assert "synthetic demo" in dump
    assert ".invalid" in dump


def test_generator_refuses_normal_database_and_invalid_ranges(tmp_path: Path) -> None:
    with pytest.raises(DemoDataSafetyError, match="normal FixMate AI database"):
        generate_demo_database(DEFAULT_DB_PATH, days=2)
    with pytest.raises(ValueError, match="between 1 and 365"):
        generate_demo_database(tmp_path / "bad.db", days=0)
    with pytest.raises(DemoDataSafetyError, match="must use"):
        generate_demo_database(tmp_path / "bad.txt", days=2)
