"""Temporary database and TestClient fixtures for API tests."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.config import ApiSettings
from api.main import create_app
from src.database import (
    initialize_database,
    save_network_diagnostic,
    save_scan,
    save_screenshot_analysis,
)

API_TOKEN = "local-test-token"


def populate_api_database(database_path: Path) -> None:
    """Create deterministic Phase 1–3 records inside a temporary database."""
    first_scan = {
        "collected_at": "2026-06-19T08:00:00+00:00",
        "os_name": "Windows",
        "os_version": "test",
        "os_release": "11",
        "architecture": "AMD64",
        "boot_time": "2026-06-19T07:00:00+00:00",
        "cpu_percent": 95.0,
        "memory_percent": 70.0,
        "disk_used_percent": 80.0,
        "disk_free_percent": 20.0,
        "top_processes": [
            {
                "pid": 10,
                "name": "C:\\Users\\Alice\\private.exe",
                "memory_mb": 500.0,
            }
        ],
    }
    issue = {
        "code": "CPU_HIGH",
        "severity": "high",
        "metric": "CPU usage",
        "value": 95.0,
        "explanation": "CPU usage exceeded the configured threshold.",
        "recommendation": "Review only applications you recognize.",
    }
    save_scan(first_scan, [issue], 75, database_path)

    second_scan = {
        **first_scan,
        "collected_at": "2026-06-20T01:00:00+00:00",
        "cpu_percent": 25.0,
        "memory_percent": 55.0,
        "top_processes": [
            {"pid": 20, "name": "browser.exe", "memory_mb": 800.0}
        ],
    }
    save_scan(second_scan, [], 100, database_path)

    diagnostic = {
        "collected_at": "2026-06-20T02:00:00+00:00",
        "target_host": "203.0.113.10",
        "target_port": 443,
        "timeout_seconds": 1.0,
        "latency_threshold_ms": 150.0,
        "active_interfaces": ["Alice VPN"],
        "connection_status": True,
        "internet_connected": True,
        "timed_out": False,
        "latency_ms": 220.0,
        "bytes_sent": 1000,
        "bytes_received": 2000,
    }
    network_issue = {
        "code": "HIGH_LATENCY",
        "severity": "medium",
        "evidence": (
            "203.0.113.10 AA:BB:CC:DD:EE:FF alice@example.com "
            "C:\\Users\\Alice\\network.txt"
        ),
        "explanation": "Latency exceeded the threshold.",
        "recommendation": "Retry the diagnostic when the problem occurs.",
        "detected_at": "2026-06-20T02:00:00+00:00",
    }
    save_network_diagnostic(diagnostic, [network_issue], database_path)

    save_screenshot_analysis(
        analyzed_at="2026-06-20T03:00:00+00:00",
        anonymized_filename="image-1234567890abcdef.png",
        extracted_text_redacted="password=[REDACTED] access denied",
        matched_issue_id="access_denied_windows",
        confidence_score=88.0,
        database_path=database_path,
    )


@pytest.fixture
def database_path(tmp_path: Path) -> Path:
    """Return a populated temporary SQLite path."""
    path = tmp_path / "api.db"
    populate_api_database(path)
    return path


@pytest.fixture
def empty_database_path(tmp_path: Path) -> Path:
    """Return an initialized database with no records."""
    path = tmp_path / "empty-api.db"
    initialize_database(path)
    return path


def make_settings(database_path: Path, **overrides: object) -> ApiSettings:
    """Create deterministic API settings for tests."""
    values = {
        "database_path": database_path,
        "api_token": API_TOKEN,
        "allowed_origins": ("http://allowed.test",),
        "max_request_bytes": 4096,
        "diagnostic_rate_limit": 20,
        "assistant_rate_limit": 20,
        "rate_window_seconds": 60,
        "host": "127.0.0.1",
        "port": 8000,
    }
    values.update(overrides)
    return ApiSettings(**values)  # type: ignore[arg-type]


@pytest.fixture
def client(database_path: Path) -> Iterator[TestClient]:
    """Yield a client whose app can access only the temporary database."""
    with TestClient(create_app(make_settings(database_path))) as test_client:
        yield test_client


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Return valid local POST authentication headers."""
    return {"X-API-Token": API_TOKEN}

