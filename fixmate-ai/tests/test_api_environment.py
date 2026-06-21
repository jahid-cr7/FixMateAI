"""Environment loading tests for local and container API startup."""

from __future__ import annotations

from pathlib import Path

from api.config import ApiSettings


def test_api_defaults_remain_localhost(monkeypatch) -> None:
    monkeypatch.delenv("FIXMATE_API_HOST", raising=False)
    monkeypatch.delenv("FIXMATE_API_PORT", raising=False)
    settings = ApiSettings.from_environment()
    assert settings.host == "127.0.0.1"
    assert settings.port == 8000


def test_container_bind_and_database_environment(monkeypatch, tmp_path: Path) -> None:
    database_path = tmp_path / "container-data" / "fixmate.db"
    monkeypatch.setenv("FIXMATE_API_HOST", "0.0.0.0")
    monkeypatch.setenv("FIXMATE_API_PORT", "9000")
    monkeypatch.setenv("FIXMATE_DATABASE_PATH", str(database_path))
    settings = ApiSettings.from_environment()
    assert settings.host == "0.0.0.0"
    assert settings.port == 9000
    assert settings.database_path == database_path


def test_shared_database_override_has_priority(monkeypatch, tmp_path: Path) -> None:
    shared = tmp_path / "shared-demo.db"
    legacy = tmp_path / "legacy.db"
    monkeypatch.setenv("FIXMATE_DB_PATH", str(shared))
    monkeypatch.setenv("FIXMATE_DATABASE_PATH", str(legacy))
    settings = ApiSettings.from_environment()
    assert settings.database_path == shared


def test_unsafe_host_and_wildcard_cors_fall_back(monkeypatch) -> None:
    monkeypatch.setenv("FIXMATE_API_HOST", "public.example")
    monkeypatch.setenv("FIXMATE_API_CORS_ORIGINS", "*")
    settings = ApiSettings.from_environment()
    assert settings.host == "127.0.0.1"
    assert "*" not in settings.allowed_origins
