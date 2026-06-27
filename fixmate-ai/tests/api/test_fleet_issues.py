"""Phase 12B fleet issue workflow API tests."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from api.main import create_app
from tests.api.conftest import API_TOKEN, make_settings

DEVICE_TOKEN = "synthetic-enrollment-token"
DEVICE_ID = "device-api-issue-001"


def _registration(timestamp: str) -> dict:
    return {
        "device_id": DEVICE_ID,
        "display_name": "Issue Test Endpoint",
        "operating_system": "Ubuntu",
        "platform": "Linux",
        "agent_version": "1.0.0",
        "timestamp": timestamp,
    }


def _scan_with_issues(timestamp: str) -> dict:
    return {
        "device_id": DEVICE_ID,
        "timestamp": timestamp,
        "agent_version": "1.0.0",
        "health_score": 40,
        "system": {
            "operating_system": "Ubuntu",
            "platform": "linux",
            "cpu_percent": 99,
            "memory_percent": 30,
            "disk_used_percent": 50,
            "disk_free_percent": 50,
            "boot_time": None,
        },
        "network": {
            "connection_status": True,
            "internet_connected": True,
            "timed_out": False,
            "latency_ms": 10,
            "bytes_sent": 100,
            "bytes_received": 200,
            "active_interface_count": 1,
        },
        "issues": [
            {
                "source": "system",
                "code": "CPU_HIGH",
                "severity": "high",
                "evidence": "CPU at 99%",
                "explanation": "CPU exceeded threshold.",
                "recommendation": "Guidance: review applications.",
            }
        ],
    }


def _setup_device(empty_database_path) -> TestClient:
    settings = make_settings(
        empty_database_path,
        device_enrollment_token=DEVICE_TOKEN,
        agent_rate_limit=20,
    )
    now = datetime.now(timezone.utc).isoformat()
    client = TestClient(create_app(settings))
    device_headers = {"X-Device-Token": DEVICE_TOKEN}
    client.post("/api/v1/agent/register", json=_registration(now), headers=device_headers)
    client.post("/api/v1/agent/scans", json=_scan_with_issues(now), headers=device_headers)
    return client


def test_list_fleet_issues(empty_database_path) -> None:
    client = _setup_device(empty_database_path)
    admin_headers = {"X-API-Token": API_TOKEN}
    response = client.get("/api/v1/fleet-issues", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 1
    assert data[0]["status"] == "open"
    assert data[0]["code"] == "CPU_HIGH"


def test_list_fleet_issues_with_status_filter(empty_database_path) -> None:
    client = _setup_device(empty_database_path)
    admin_headers = {"X-API-Token": API_TOKEN}
    open_resp = client.get("/api/v1/fleet-issues?status=open", headers=admin_headers)
    assert open_resp.status_code == 200
    assert len(open_resp.json()["data"]) == 1
    resolved_resp = client.get("/api/v1/fleet-issues?status=resolved", headers=admin_headers)
    assert resolved_resp.status_code == 200
    assert len(resolved_resp.json()["data"]) == 0


def test_list_fleet_issues_with_device_filter(empty_database_path) -> None:
    client = _setup_device(empty_database_path)
    admin_headers = {"X-API-Token": API_TOKEN}
    filtered = client.get(
        f"/api/v1/fleet-issues?device_id={DEVICE_ID}", headers=admin_headers
    )
    assert filtered.status_code == 200
    assert len(filtered.json()["data"]) == 1
    wrong = client.get(
        "/api/v1/fleet-issues?device_id=nonexistent", headers=admin_headers
    )
    assert wrong.status_code == 200
    assert len(wrong.json()["data"]) == 0


def test_list_fleet_issues_combined_filters(empty_database_path) -> None:
    client = _setup_device(empty_database_path)
    admin_headers = {"X-API-Token": API_TOKEN}
    resp = client.get(
        f"/api/v1/fleet-issues?device_id={DEVICE_ID}&status=open",
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert len(resp.json()["data"]) == 1
    mismatch = client.get(
        f"/api/v1/fleet-issues?device_id={DEVICE_ID}&status=resolved",
        headers=admin_headers,
    )
    assert mismatch.status_code == 200
    assert len(mismatch.json()["data"]) == 0


def test_acknowledge_fleet_issue(empty_database_path) -> None:
    client = _setup_device(empty_database_path)
    admin_headers = {"X-API-Token": API_TOKEN}
    issue_id = client.get("/api/v1/fleet-issues", headers=admin_headers).json()["data"][0]["id"]
    resp = client.post(
        f"/api/v1/fleet-issues/{issue_id}/acknowledge",
        json={"technician_note": "checking"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "acknowledged"
    assert resp.json()["data"]["technician_note"] == "checking"
    assert resp.json()["data"]["acknowledged_at"] is not None


def test_mark_in_progress_fleet_issue(empty_database_path) -> None:
    client = _setup_device(empty_database_path)
    admin_headers = {"X-API-Token": API_TOKEN}
    issue_id = client.get("/api/v1/fleet-issues", headers=admin_headers).json()["data"][0]["id"]
    resp = client.post(
        f"/api/v1/fleet-issues/{issue_id}/in-progress",
        json={"technician_note": "upgrading"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "in_progress"


def test_resolve_fleet_issue(empty_database_path) -> None:
    client = _setup_device(empty_database_path)
    admin_headers = {"X-API-Token": API_TOKEN}
    issue_id = client.get("/api/v1/fleet-issues", headers=admin_headers).json()["data"][0]["id"]
    resp = client.post(
        f"/api/v1/fleet-issues/{issue_id}/resolve",
        json={"technician_note": "fixed"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "resolved"
    assert resp.json()["data"]["resolved_at"] is not None


def test_mark_false_positive_fleet_issue(empty_database_path) -> None:
    client = _setup_device(empty_database_path)
    admin_headers = {"X-API-Token": API_TOKEN}
    issue_id = client.get("/api/v1/fleet-issues", headers=admin_headers).json()["data"][0]["id"]
    resp = client.post(
        f"/api/v1/fleet-issues/{issue_id}/false-positive",
        json={"technician_note": "expected backup load"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "false_positive"
    assert resp.json()["data"]["resolved_at"] is not None


def test_transition_no_body(empty_database_path) -> None:
    client = _setup_device(empty_database_path)
    admin_headers = {"X-API-Token": API_TOKEN}
    issue_id = client.get("/api/v1/fleet-issues", headers=admin_headers).json()["data"][0]["id"]
    resp = client.post(
        f"/api/v1/fleet-issues/{issue_id}/acknowledge",
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "acknowledged"
    assert resp.json()["data"]["technician_note"] == ""


def test_retransition_same_status_returns_200(empty_database_path) -> None:
    client = _setup_device(empty_database_path)
    admin_headers = {"X-API-Token": API_TOKEN}
    issue_id = client.get("/api/v1/fleet-issues", headers=admin_headers).json()["data"][0]["id"]
    client.post(f"/api/v1/fleet-issues/{issue_id}/acknowledge", headers=admin_headers)
    resp = client.post(
        f"/api/v1/fleet-issues/{issue_id}/acknowledge",
        json={"technician_note": "duplicate"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "acknowledged"


def test_nonexistent_fleet_issue_returns_404(empty_database_path) -> None:
    client = _setup_device(empty_database_path)
    admin_headers = {"X-API-Token": API_TOKEN}
    resp = client.post(f"/api/v1/fleet-issues/9999/acknowledge", headers=admin_headers)
    assert resp.status_code == 404


def test_fleet_issues_require_auth(empty_database_path) -> None:
    client = _setup_device(empty_database_path)
    assert client.get("/api/v1/fleet-issues").status_code == 401
    assert client.post("/api/v1/fleet-issues/1/acknowledge").status_code == 401


def test_invalid_status_query_returns_422(empty_database_path) -> None:
    client = _setup_device(empty_database_path)
    admin_headers = {"X-API-Token": API_TOKEN}
    resp = client.get("/api/v1/fleet-issues?status=invalid", headers=admin_headers)
    assert resp.status_code == 422


def test_issue_record_contains_workflow_fields(empty_database_path) -> None:
    client = _setup_device(empty_database_path)
    admin_headers = {"X-API-Token": API_TOKEN}
    data = client.get("/api/v1/fleet-issues", headers=admin_headers).json()["data"]
    issue = data[0]
    assert "status" in issue
    assert "technician_note" in issue
    assert "detected_at" in issue
    assert "acknowledged_at" in issue
    assert "resolved_at" in issue
    assert "updated_at" in issue
    assert issue["acknowledged_at"] is None
    assert issue["resolved_at"] is None


def test_no_secret_leakage_in_issue_responses(empty_database_path) -> None:
    secret = "sk-tp-super-secret-key-value"
    settings = make_settings(
        empty_database_path,
        device_enrollment_token=DEVICE_TOKEN,
        agent_rate_limit=20,
    )
    now = datetime.now(timezone.utc).isoformat()
    client = TestClient(create_app(settings))
    device_headers = {"X-Device-Token": DEVICE_TOKEN}
    client.post("/api/v1/agent/register", json=_registration(now), headers=device_headers)
    client.post(
        "/api/v1/agent/scans",
        json={
            "device_id": DEVICE_ID,
            "timestamp": now,
            "agent_version": "1.0.0",
            "health_score": 30,
            "system": {"operating_system": "Ubuntu", "platform": "linux", "cpu_percent": 99},
            "network": {
                "connection_status": True,
                "internet_connected": True,
                "timed_out": False,
                "active_interface_count": 1,
            },
            "issues": [
                {
                    "source": "system",
                    "code": "CPU_HIGH",
                    "severity": "critical",
                    "evidence": f"token={secret}",
                    "explanation": "CPU exceeded.",
                    "recommendation": "Guidance: check.",
                }
            ],
        },
        headers=device_headers,
    )
    admin_headers = {"X-API-Token": API_TOKEN}
    listing = client.get("/api/v1/fleet-issues", headers=admin_headers)
    assert secret not in listing.text
