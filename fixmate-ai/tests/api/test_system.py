"""System endpoint tests including pagination, auth, and collector failures."""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.services import diagnostic_service


def test_latest_system_and_privacy_redaction(client: TestClient) -> None:
    """Latest system response should validate and redact sensitive process paths."""
    response = client.get("/api/v1/system/latest")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["health_score"] == 100
    assert data["collected_at"].endswith("Z")
    assert "203.0.113" not in response.text


def test_system_history_pagination_and_date_filter(client: TestClient) -> None:
    """System history should paginate and filter by UTC date."""
    page = client.get("/api/v1/system/history?page=1&page_size=1").json()["data"]
    filtered = client.get(
        "/api/v1/system/history",
        params={"date_from": "2026-06-20T00:00:00Z"},
    ).json()["data"]
    assert page["total"] == 2
    assert len(page["items"]) == 1
    assert filtered["total"] == 1


def test_system_scan_authentication(client: TestClient) -> None:
    """System POST requires the configured local token."""
    missing = client.post("/api/v1/system/scans")
    invalid = client.post(
        "/api/v1/system/scans", headers={"X-API-Token": "wrong"}
    )
    assert missing.status_code == 401
    assert invalid.status_code == 401
    assert missing.json()["error"]["code"] == "invalid_api_token"


def test_create_system_scan_with_mocked_collector(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch,
) -> None:
    """POST should reuse mocked collector/detector/storage orchestration."""
    monkeypatch.setattr(
        diagnostic_service,
        "collect_system_metrics",
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
    response = client.post("/api/v1/system/scans", headers=auth_headers)
    assert response.status_code == 201
    assert response.json()["data"]["os_name"] == "Ubuntu"


def test_collector_failure_is_trace_free(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch,
) -> None:
    """Collector exceptions should become safe 503 errors."""
    monkeypatch.setattr(
        diagnostic_service,
        "collect_system_metrics",
        lambda: (_ for _ in ()).throw(RuntimeError("SECRET INTERNAL TRACE")),
    )
    response = client.post("/api/v1/system/scans", headers=auth_headers)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "system_scan_failed"
    assert "SECRET INTERNAL TRACE" not in response.text

