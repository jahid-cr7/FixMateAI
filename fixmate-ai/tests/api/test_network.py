"""Network endpoint tests with fully mocked diagnostic collection."""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.services import diagnostic_service


def test_latest_network_is_privacy_safe(client: TestClient) -> None:
    """Latest network data must omit host, interface names, IP, MAC, and email."""
    response = client.get("/api/v1/network/latest")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["active_interface_count"] == 1
    assert "target_host" not in data
    for sensitive in (
        "203.0.113.10",
        "AA:BB:CC:DD:EE:FF",
        "alice@example.com",
        "Alice VPN",
    ):
        assert sensitive not in response.text


def test_network_history_pagination(client: TestClient) -> None:
    """Network history supports the shared pagination schema."""
    response = client.get("/api/v1/network/history?page=1&page_size=1")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 1
    assert len(data["items"]) == 1


def test_network_diagnostic_request_validation_and_mocked_success(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch,
) -> None:
    """Invalid hosts fail; a mocked valid diagnostic is persisted."""
    invalid = client.post(
        "/api/v1/network/diagnostics",
        headers=auth_headers,
        json={"host": "https://not-allowed.example"},
    )
    assert invalid.status_code == 422

    monkeypatch.setattr(
        diagnostic_service,
        "collect_network_diagnostic",
        lambda **kwargs: {
            "collected_at": "2026-06-20T05:00:00+00:00",
            "target_host": kwargs["host"],
            "target_port": kwargs["port"],
            "timeout_seconds": kwargs["timeout_seconds"],
            "latency_threshold_ms": kwargs["latency_threshold_ms"],
            "active_interfaces": ["Ethernet"],
            "connection_status": True,
            "internet_connected": True,
            "timed_out": False,
            "latency_ms": 30.0,
            "bytes_sent": 3000,
            "bytes_received": 4000,
        },
    )
    response = client.post(
        "/api/v1/network/diagnostics",
        headers=auth_headers,
        json={"host": "example.test", "timeout_seconds": 0.5},
    )
    assert response.status_code == 201
    assert response.json()["data"]["latency_ms"] == 30.0

