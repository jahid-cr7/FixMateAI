"""Release version and shared database configuration tests."""

from __future__ import annotations

from pathlib import Path

from src import __version__
from src.database import BUILTIN_DB_PATH, configured_database_path


def test_release_version_is_stable() -> None:
    assert __version__ == "1.0.0"


def test_database_path_defaults_and_shared_override(tmp_path: Path) -> None:
    assert configured_database_path({}) == BUILTIN_DB_PATH
    demo = tmp_path / "demo_fixmate.db"
    assert configured_database_path({"FIXMATE_DB_PATH": str(demo)}) == demo


def test_shared_override_precedes_legacy_alias(tmp_path: Path) -> None:
    shared = tmp_path / "shared.db"
    legacy = tmp_path / "legacy.db"
    resolved = configured_database_path(
        {
            "FIXMATE_DB_PATH": str(shared),
            "FIXMATE_DATABASE_PATH": str(legacy),
        }
    )
    assert resolved == shared
