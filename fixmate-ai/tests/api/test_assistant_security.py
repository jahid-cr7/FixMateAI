"""Assistant auth, fallback, rate limit, request size, and config tests."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from api.main import create_app
from src.llm.disabled import DisabledProvider
from tests.api.conftest import API_TOKEN, make_settings


def test_assistant_deterministic_default(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """Default API assistant mode remains deterministic."""
    response = client.post(
        "/api/v1/assistant/query",
        headers=auth_headers,
        json={"question": "Summarize this computer's health."},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["intent"] == "health_summary"
    assert data["ai_generated"] is False
    assert data["evidence"] and data["guidance"]


def test_ai_mode_uses_deterministic_fallback_without_provider(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch,
) -> None:
    """Missing optional provider configuration must not break the endpoint."""
    monkeypatch.setattr(
        "api.services.assistant_service.create_provider", lambda: DisabledProvider()
    )
    response = client.post(
        "/api/v1/assistant/query",
        headers=auth_headers,
        json={
            "question": "Is my disk nearly full?",
            "mode": "ai_enhanced",
            "external_consent": False,
        },
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["intent"] == "disk_status"
    assert data["fallback_used"] is True
    assert data["ai_generated"] is False


def test_missing_and_invalid_authentication(client: TestClient) -> None:
    """Assistant POST rejects missing and invalid local tokens."""
    missing = client.post(
        "/api/v1/assistant/query", json={"question": "health summary"}
    )
    invalid = client.post(
        "/api/v1/assistant/query",
        headers={"X-API-Token": "invalid"},
        json={"question": "health summary"},
    )
    assert missing.status_code == invalid.status_code == 401


def test_unconfigured_token_disables_post_endpoint(
    database_path: Path,
) -> None:
    """No configured token should produce a safe 503 rather than open access."""
    with TestClient(
        create_app(make_settings(database_path, api_token=""))
    ) as test_client:
        response = test_client.post(
            "/api/v1/assistant/query", json={"question": "health summary"}
        )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "api_token_not_configured"


def test_assistant_rate_limit(database_path: Path) -> None:
    """In-memory assistant rate limit should return 429 after the bound."""
    settings = make_settings(database_path, assistant_rate_limit=1)
    with TestClient(create_app(settings)) as test_client:
        first = test_client.post(
            "/api/v1/assistant/query",
            headers={"X-API-Token": API_TOKEN},
            json={"question": "health summary"},
        )
        second = test_client.post(
            "/api/v1/assistant/query",
            headers={"X-API-Token": API_TOKEN},
            json={"question": "health summary"},
        )
    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json()["error"]["code"] == "rate_limit_exceeded"


def test_diagnostic_rate_limit(database_path: Path, monkeypatch) -> None:
    """System/network diagnostic POSTs share the diagnostic rate bucket."""
    monkeypatch.setattr(
        "api.services.diagnostic_service.collect_system_metrics",
        lambda: {
            "collected_at": "2026-06-20T04:00:00+00:00",
            "os_name": "Ubuntu",
            "os_version": "test",
            "os_release": "24.04",
            "architecture": "x86_64",
            "boot_time": None,
            "cpu_percent": 10.0,
            "memory_percent": 20.0,
            "disk_used_percent": 30.0,
            "disk_free_percent": 70.0,
            "top_processes": [],
        },
    )
    settings = make_settings(database_path, diagnostic_rate_limit=1)
    with TestClient(create_app(settings)) as test_client:
        first = test_client.post(
            "/api/v1/system/scans", headers={"X-API-Token": API_TOKEN}
        )
        second = test_client.post(
            "/api/v1/system/scans", headers={"X-API-Token": API_TOKEN}
        )
    assert first.status_code == 201
    assert second.status_code == 429


def test_request_size_limit(database_path: Path) -> None:
    """Declared assistant bodies above the configured limit should return 413."""
    settings = make_settings(database_path, max_request_bytes=128)
    with TestClient(create_app(settings)) as test_client:
        response = test_client.post(
            "/api/v1/assistant/query",
            headers={"X-API-Token": API_TOKEN},
            json={"question": "x" * 500},
        )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "request_too_large"

