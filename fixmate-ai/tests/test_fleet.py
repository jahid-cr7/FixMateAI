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


def _register_and_scan(store: FleetStore, timestamp: str) -> int:
    store.register_device(_device(timestamp), "token")
    batch = store.record_scan_batch(
        {
            "device_id": "device-test-001",
            "timestamp": timestamp,
            "health_score": 55,
            "system": {"cpu_percent": 95, "operating_system": "Ubuntu"},
            "network": {"internet_connected": False},
            "issues": [
                {
                    "source": "system",
                    "code": "CPU_HIGH",
                    "severity": "high",
                    "evidence": "CPU at 95%",
                    "explanation": "CPU exceeded threshold.",
                    "recommendation": "Guidance: review applications.",
                }
            ],
        }
    )
    return batch["id"]


def test_fleet_issues_default_to_open(tmp_path) -> None:
    store = FleetStore(tmp_path / "fleet.db")
    now = datetime.now(timezone.utc).isoformat()
    _register_and_scan(store, now)
    issues = store.list_fleet_issues(device_id="device-test-001")
    assert len(issues) == 1
    assert issues[0]["status"] == "open"
    assert issues[0]["device_id"] == "device-test-001"
    assert issues[0]["code"] == "CPU_HIGH"
    assert issues[0]["technician_note"] == ""


def test_acknowledge_fleet_issue(tmp_path) -> None:
    store = FleetStore(tmp_path / "fleet.db")
    now = datetime.now(timezone.utc).isoformat()
    _register_and_scan(store, now)
    issue_id = store.list_fleet_issues()[0]["id"]
    result = store.update_fleet_issue(issue_id, "acknowledged", "looking into it")
    assert result is not None
    assert result["status"] == "acknowledged"
    assert result["technician_note"] == "looking into it"
    assert result["acknowledged_at"] is not None


def test_mark_fleet_issue_in_progress(tmp_path) -> None:
    store = FleetStore(tmp_path / "fleet.db")
    now = datetime.now(timezone.utc).isoformat()
    _register_and_scan(store, now)
    issue_id = store.list_fleet_issues()[0]["id"]
    result = store.update_fleet_issue(issue_id, "in_progress", "upgrading driver")
    assert result is not None
    assert result["status"] == "in_progress"
    assert result["technician_note"] == "upgrading driver"


def test_resolve_fleet_issue(tmp_path) -> None:
    store = FleetStore(tmp_path / "fleet.db")
    now = datetime.now(timezone.utc).isoformat()
    _register_and_scan(store, now)
    issue_id = store.list_fleet_issues()[0]["id"]
    result = store.update_fleet_issue(issue_id, "resolved", "driver updated")
    assert result is not None
    assert result["status"] == "resolved"
    assert result["resolved_at"] is not None
    assert result["technician_note"] == "driver updated"


def test_mark_false_positive_fleet_issue(tmp_path) -> None:
    store = FleetStore(tmp_path / "fleet.db")
    now = datetime.now(timezone.utc).isoformat()
    _register_and_scan(store, now)
    issue_id = store.list_fleet_issues()[0]["id"]
    result = store.update_fleet_issue(issue_id, "false_positive", "expected load during backup")
    assert result is not None
    assert result["status"] == "false_positive"
    assert result["resolved_at"] is not None
    assert result["technician_note"] == "expected load during backup"


def test_fleet_issue_status_filtering(tmp_path) -> None:
    store = FleetStore(tmp_path / "fleet.db")
    now = datetime.now(timezone.utc).isoformat()
    _register_and_scan(store, now)
    issue_id = store.list_fleet_issues()[0]["id"]
    store.update_fleet_issue(issue_id, "resolved")
    open_issues = store.list_fleet_issues(status="open")
    resolved_issues = store.list_fleet_issues(status="resolved")
    assert len(open_issues) == 0
    assert len(resolved_issues) == 1


def test_fleet_issue_device_filtering(tmp_path) -> None:
    store = FleetStore(tmp_path / "fleet.db")
    now = datetime.now(timezone.utc).isoformat()
    _register_and_scan(store, now)
    specific = store.list_fleet_issues(device_id="device-test-001")
    wrong = store.list_fleet_issues(device_id="nonexistent")
    assert len(specific) == 1
    assert len(wrong) == 0


def test_update_nonexistent_fleet_issue_returns_none(tmp_path) -> None:
    store = FleetStore(tmp_path / "fleet.db")
    result = store.update_fleet_issue(9999, "acknowledged")
    assert result is None


def test_no_secret_leakage_in_fleet_issue_records(tmp_path) -> None:
    store = FleetStore(tmp_path / "fleet.db")
    now = datetime.now(timezone.utc).isoformat()
    secret = "sk-tp-super-secret-key-value"
    store.register_device(
        {
            "device_id": "device-leak-test",
            "display_name": "Leak Test",
            "operating_system": "Ubuntu",
            "platform": "Linux",
            "agent_version": "1.0.0",
            "timestamp": now,
        },
        secret,
    )
    batch = store.record_scan_batch(
        {
            "device_id": "device-leak-test",
            "timestamp": now,
            "health_score": 40,
            "system": {"cpu_percent": 99},
            "network": {"internet_connected": True},
            "issues": [
                {
                    "source": "system",
                    "code": "CPU_HIGH",
                    "severity": "critical",
                    "evidence": f"token={secret}",
                    "explanation": "CPU threshold exceeded.",
                    "recommendation": "Guidance: check processes.",
                }
            ],
        }
    )
    all_issues = store.list_fleet_issues(device_id="device-leak-test")
    for issue in all_issues:
        assert secret not in str(issue)


def test_retransition_same_status_returns_unchanged(tmp_path) -> None:
    store = FleetStore(tmp_path / "fleet.db")
    now = datetime.now(timezone.utc).isoformat()
    _register_and_scan(store, now)
    issue_id = store.list_fleet_issues()[0]["id"]
    store.update_fleet_issue(issue_id, "acknowledged", "first note")
    result = store.update_fleet_issue(issue_id, "acknowledged", "second note")
    assert result is not None
    assert result["status"] == "acknowledged"
    assert result["technician_note"] == "first note"


def test_open_to_in_progress_sets_acknowledged_at(tmp_path) -> None:
    store = FleetStore(tmp_path / "fleet.db")
    now = datetime.now(timezone.utc).isoformat()
    _register_and_scan(store, now)
    issue_id = store.list_fleet_issues()[0]["id"]
    result = store.update_fleet_issue(issue_id, "in_progress")
    assert result is not None
    assert result["status"] == "in_progress"
    assert result["acknowledged_at"] is not None


def test_open_to_resolved_sets_both_timestamps(tmp_path) -> None:
    store = FleetStore(tmp_path / "fleet.db")
    now = datetime.now(timezone.utc).isoformat()
    _register_and_scan(store, now)
    issue_id = store.list_fleet_issues()[0]["id"]
    result = store.update_fleet_issue(issue_id, "resolved", "fixed driver")
    assert result is not None
    assert result["status"] == "resolved"
    assert result["acknowledged_at"] is not None
    assert result["resolved_at"] is not None


def test_open_to_false_positive_sets_both_timestamps(tmp_path) -> None:
    store = FleetStore(tmp_path / "fleet.db")
    now = datetime.now(timezone.utc).isoformat()
    _register_and_scan(store, now)
    issue_id = store.list_fleet_issues()[0]["id"]
    result = store.update_fleet_issue(issue_id, "false_positive", "backup window")
    assert result is not None
    assert result["status"] == "false_positive"
    assert result["acknowledged_at"] is not None
    assert result["resolved_at"] is not None


def test_invalid_status_returns_none(tmp_path) -> None:
    store = FleetStore(tmp_path / "fleet.db")
    now = datetime.now(timezone.utc).isoformat()
    _register_and_scan(store, now)
    issue_id = store.list_fleet_issues()[0]["id"]
    result = store.update_fleet_issue(issue_id, "invalid_status")
    assert result is None


def test_list_fleet_issues_combined_filters(tmp_path) -> None:
    store = FleetStore(tmp_path / "fleet.db")
    now = datetime.now(timezone.utc).isoformat()
    _register_and_scan(store, now)
    filtered = store.list_fleet_issues(device_id="device-test-001", status="open")
    assert len(filtered) == 1
    wrong_device = store.list_fleet_issues(device_id="nonexistent", status="open")
    assert len(wrong_device) == 0


def test_list_fleet_issues_limit_clamping(tmp_path) -> None:
    store = FleetStore(tmp_path / "fleet.db")
    now = datetime.now(timezone.utc).isoformat()
    _register_and_scan(store, now)
    huge = store.list_fleet_issues(limit=9999)
    assert len(huge) == 1
    tiny = store.list_fleet_issues(limit=0)
    assert len(tiny) == 1


def test_record_fleet_issues_returns_full_structure(tmp_path) -> None:
    store = FleetStore(tmp_path / "fleet.db")
    now = datetime.now(timezone.utc).isoformat()
    batch_id = _register_and_scan(store, now)
    results = store.record_fleet_issues(
        "device-test-001",
        batch_id,
        [{"source": "network", "code": "HIGH_LATENCY", "severity": "medium", "evidence": "220ms", "explanation": "Slow", "recommendation": "Check ISP"}],
    )
    assert len(results) == 1
    r = results[0]
    assert "acknowledged_at" in r
    assert "resolved_at" in r
    assert "updated_at" in r
    assert r["acknowledged_at"] is None
    assert r["status"] == "open"
