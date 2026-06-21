"""Phase 11A endpoint-agent and fleet administration API tests."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from api.main import create_app
from tests.api.conftest import API_TOKEN, make_settings

DEVICE_TOKEN = "synthetic-enrollment-token"
DEVICE_ID = "device-api-001"


def _registration(timestamp: str) -> dict:
    return {
        "device_id": DEVICE_ID,
        "display_name": "Synthetic Endpoint",
        "operating_system": "Ubuntu",
        "platform": "Linux",
        "agent_version": "1.0.0",
        "timestamp": timestamp,
    }


def _scan(timestamp: str) -> dict:
    return {
        "device_id": DEVICE_ID,
        "timestamp": timestamp,
        "agent_version": "1.0.0",
        "health_score": 60,
        "system": {
            "operating_system": "Ubuntu",
            "platform": "linux",
            "cpu_percent": 92,
            "memory_percent": 40,
            "disk_used_percent": 50,
            "disk_free_percent": 50,
            "boot_time": None,
        },
        "network": {
            "connection_status": True,
            "internet_connected": True,
            "timed_out": False,
            "latency_ms": 20,
            "bytes_sent": 100,
            "bytes_received": 200,
            "active_interface_count": 1,
        },
        "issues": [
            {
                "source": "system",
                "code": "CPU_HIGH",
                "severity": "high",
                "evidence": "alice@example.com used 92% at C:\\Users\\Alice",
                "explanation": "CPU is above the threshold.",
                "recommendation": "Guidance: review recognized applications.",
            }
        ],
    }


def test_complete_agent_and_admin_fleet_flow(empty_database_path) -> None:
    settings = make_settings(
        empty_database_path,
        device_enrollment_token=DEVICE_TOKEN,
        agent_rate_limit=20,
    )
    now = datetime.now(timezone.utc).isoformat()
    device_headers = {"X-Device-Token": DEVICE_TOKEN}
    admin_headers = {"X-API-Token": API_TOKEN}
    with TestClient(create_app(settings)) as client:
        registration = client.post(
            "/api/v1/agent/register", json=_registration(now), headers=device_headers
        )
        assert registration.status_code == 201
        assert DEVICE_TOKEN not in registration.text

        heartbeat = client.post(
            "/api/v1/agent/heartbeat",
            json={
                "device_id": DEVICE_ID,
                "timestamp": now,
                "status": "online",
                "agent_version": "1.0.0",
            },
            headers=device_headers,
        )
        assert heartbeat.status_code == 200
        uploaded = client.post(
            "/api/v1/agent/scans", json=_scan(now), headers=device_headers
        )
        assert uploaded.status_code == 201
        assert "alice@example.com" not in uploaded.text

        listing = client.get(
            "/api/v1/devices?status=online&severity=high", headers=admin_headers
        )
        assert listing.status_code == 200
        assert len(listing.json()["data"]) == 1
        assert client.get(f"/api/v1/devices/{DEVICE_ID}", headers=admin_headers).status_code == 200
        assert client.get(f"/api/v1/devices/{DEVICE_ID}/latest", headers=admin_headers).status_code == 200
        history = client.get(
            f"/api/v1/devices/{DEVICE_ID}/history?page=1&page_size=1",
            headers=admin_headers,
        )
        assert history.status_code == 200
        assert history.json()["data"]["total"] == 1

    with sqlite3.connect(empty_database_path) as connection:
        digest = connection.execute("SELECT token_hash FROM devices").fetchone()[0]
    assert digest != DEVICE_TOKEN


def test_agent_and_admin_authentication_are_separate(empty_database_path) -> None:
    settings = make_settings(empty_database_path, device_enrollment_token=DEVICE_TOKEN)
    now = datetime.now(timezone.utc).isoformat()
    with TestClient(create_app(settings)) as client:
        assert client.post("/api/v1/agent/register", json=_registration(now)).status_code == 401
        assert client.get("/api/v1/devices").status_code == 401
        assert client.get(
            "/api/v1/devices", headers={"X-Device-Token": DEVICE_TOKEN}
        ).status_code == 401


def test_agent_validation_rate_limit_and_missing_device(empty_database_path) -> None:
    settings = make_settings(
        empty_database_path,
        device_enrollment_token=DEVICE_TOKEN,
        agent_rate_limit=1,
    )
    now = datetime.now(timezone.utc).isoformat()
    with TestClient(create_app(settings)) as client:
        first = client.post(
            "/api/v1/agent/register",
            json=_registration(now),
            headers={"X-Device-Token": DEVICE_TOKEN},
        )
        assert first.status_code == 201
        assert client.post(
            "/api/v1/agent/register",
            json={**_registration(now), "device_id": "../unsafe"},
            headers={"X-Device-Token": DEVICE_TOKEN},
        ).status_code == 429
        assert client.get(
            "/api/v1/devices/missing/latest",
            headers={"X-API-Token": API_TOKEN},
        ).status_code == 404

