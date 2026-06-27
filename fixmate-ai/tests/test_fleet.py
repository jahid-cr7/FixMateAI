"""Fleet persistence and deterministic device-status tests."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

from src.fleet import FleetStore
from src.fleet_status import device_online_status, filter_devices, fleet_summary


def _device(timestamp: str) -> dict:
    return {
        "device_id": "device-test-001",
        "display_name": "Synthetic Endpoint",
        "operating_system": "Ubuntu",
        "platform": "Linux",
        "agent_version": "1.0.0",
        "timestamp": timestamp,
    }


def test_registration_hashes_token_and_never_returns_it(tmp_path) -> None:
    database = tmp_path / "fleet.db"
    store = FleetStore(database)
    timestamp = datetime.now(timezone.utc).isoformat()
    result = store.register_device(_device(timestamp), "synthetic-device-token")

    assert store.token_matches_device("device-test-001", "synthetic-device-token")
    assert not store.token_matches_device("device-test-001", "wrong-token")
    assert "token" not in str(result).casefold()
    with sqlite3.connect(database) as connection:
        salt, digest = connection.execute(
            "SELECT token_salt, token_hash FROM devices"
        ).fetchone()
    assert salt and digest
    assert digest != "synthetic-device-token"


def test_heartbeat_scan_history_and_privacy_redaction(tmp_path) -> None:
    store = FleetStore(tmp_path / "fleet.db")
    now = datetime.now(timezone.utc)
    timestamp = now.isoformat()
    store.register_device(_device(timestamp), "token")
    store.record_heartbeat(
        {
            "device_id": "device-test-001",
            "timestamp": timestamp,
            "status": "online",
            "agent_version": "1.0.0",
        }
    )
    batch = store.record_scan_batch(
        {
            "device_id": "device-test-001",
            "timestamp": timestamp,
            "health_score": 55,
            "system": {"cpu_percent": 95, "operating_system": "Ubuntu"},
            "network": {"internet_connected": False},
            "issues": [
                {
                    "severity": "high",
                    "evidence": "alice@example.com C:\\Users\\Alice\\secret.txt",
                }
            ],
        }
    )

    device = store.get_device("device-test-001", now=now)
    assert device and device["status"] == "online"
    assert device["high_risk"] is True
    assert batch["highest_severity"] == "high"
    assert "alice@example.com" not in str(batch)
    assert store.scan_history("device-test-001", page_size=1)["total"] == 1


def test_fleet_status_and_filters_are_deterministic() -> None:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert device_online_status(None, now) == "unknown"
    assert device_online_status(now - timedelta(minutes=2), now) == "online"
    assert device_online_status(now - timedelta(minutes=10), now) == "offline"
    assert device_online_status(now + timedelta(hours=1), now) == "unknown"
    devices = [
        {"operating_system": "Windows", "status": "online", "high_risk": True, "highest_severity": "high"},
        {"operating_system": "Ubuntu", "status": "offline", "high_risk": False, "highest_severity": None},
    ]
    assert fleet_summary(devices) == {
        "total": 2,
        "online": 1,
        "offline": 1,
        "unknown": 0,
        "high_risk": 1,
    }
    assert filter_devices(devices, operating_system="ubuntu") == [devices[1]]


def test_stale_replay_does_not_regress_device_last_seen(tmp_path) -> None:
    store = FleetStore(tmp_path / "fleet.db")
    fresh = "2026-06-22T10:00:00+00:00"
    stale = "2026-06-21T10:00:00+00:00"
    store.register_device(_device(fresh), "token")
    store.record_heartbeat(
        {
            "device_id": "device-test-001",
            "timestamp": fresh,
            "status": "online",
            "agent_version": "1.0.0",
        }
    )
    store.record_heartbeat(
        {
            "device_id": "device-test-001",
            "timestamp": stale,
            "status": "degraded",
            "agent_version": "0.9.0",
        }
    )
    device = store.get_device("device-test-001")
    assert device and device["last_seen_at"] == fresh
    assert device["agent_version"] == "1.0.0"
