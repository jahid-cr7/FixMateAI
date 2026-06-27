"""FastAPI report discovery, generation, authentication, and rate-limit tests."""

from __future__ import annotations

import base64
import json

import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from src.fleet import FleetStore
from src.report_models import ReportFormat, ReportType
from tests.api.conftest import API_TOKEN, make_settings


def _populate_fleet(database_path) -> None:
    store = FleetStore(database_path)
    timestamp = "2026-06-20T04:00:00+00:00"
    for device_id, name, severity in (
        ("device-api-001", "API Fleet Normal", "low"),
        ("device-api-002", "API Fleet Risk", "high"),
    ):
        store.register_device(
            {
                "device_id": device_id,
                "display_name": name,
                "operating_system": "Ubuntu",
                "platform": "Linux",
                "agent_version": "1.0.0",
                "timestamp": timestamp,
            },
            "synthetic-token",
        )
        store.record_heartbeat(
            {
                "device_id": device_id,
                "timestamp": timestamp,
                "status": "online",
                "agent_version": "1.0.0",
            }
        )
        store.record_scan_batch(
            {
                "device_id": device_id,
                "timestamp": timestamp,
                "agent_version": "1.0.0",
                "health_score": 50 if severity == "high" else 95,
                "system": {"operating_system": "Ubuntu", "platform": "Linux"},
                "network": {"internet_connected": True},
                "issues": [
                    {
                        "source": "system",
                        "code": "synthetic",
                        "severity": severity,
                        "evidence": "alice@example.com token=secret",
                        "explanation": "Synthetic fleet issue.",
                        "recommendation": "Use safe synthetic guidance.",
                    }
                ],
            }
        )


def test_report_types_endpoint_lists_every_type_and_format(client: TestClient) -> None:
    response = client.get("/api/v1/reports/types")
    assert response.status_code == 200
    data = response.json()["data"]
    assert {item["id"] for item in data["types"]} == {item.value for item in ReportType}
    assert set(data["types"][0]["formats"]) == {item.value for item in ReportFormat}
    assert "fleet_summary" in {item["id"] for item in data["types"]}


def test_report_generation_requires_valid_authentication(client: TestClient) -> None:
    payload = {"report_type": "system_health", "format": "json"}
    assert client.post("/api/v1/reports/generate", json=payload).status_code == 401
    assert client.post(
        "/api/v1/reports/generate",
        json=payload,
        headers={"X-API-Token": "incorrect"},
    ).status_code == 401


@pytest.mark.parametrize("report_format", list(ReportFormat))
def test_api_generates_every_format(
    client: TestClient,
    auth_headers: dict[str, str],
    report_format: ReportFormat,
) -> None:
    response = client.post(
        "/api/v1/reports/generate",
        headers=auth_headers,
        json={"report_type": "full_diagnostic", "format": report_format.value},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    content = base64.b64decode(data["content_base64"], validate=True)
    assert data["requested_format"] == report_format.value
    assert data["actual_format"] == report_format.value
    assert data["size_bytes"] == len(content)
    assert data["filename"].startswith("fixmate-full_diagnostic-")
    if report_format == ReportFormat.JSON:
        parsed = json.loads(content)
        serialized = json.dumps(parsed)
        assert "203.0.113.10" not in serialized
        assert "alice@example.com" not in serialized
        assert "extracted_text_redacted" not in serialized


@pytest.mark.parametrize(
    "report_type,payload_extra",
    [
        ("fleet_summary", {}),
        ("single_device", {"device_id": "device-api-002"}),
        ("offline_devices", {}),
        ("high_risk_devices", {}),
    ],
)
def test_api_generates_fleet_reports(
    empty_database_path,
    auth_headers: dict[str, str],
    report_type: str,
    payload_extra: dict,
) -> None:
    _populate_fleet(empty_database_path)
    with TestClient(create_app(make_settings(empty_database_path))) as test_client:
        response = test_client.post(
            "/api/v1/reports/generate",
            headers=auth_headers,
            json={"report_type": report_type, "format": "json", **payload_extra},
        )
    assert response.status_code == 200
    data = response.json()["data"]
    parsed = json.loads(base64.b64decode(data["content_base64"], validate=True))
    assert parsed["report_type"] == report_type
    assert "token_hash" not in json.dumps(parsed)
    assert "alice@example.com" not in json.dumps(parsed)
    if report_type == "single_device":
        assert parsed["devices"][0]["display_name"] == "API Fleet Risk"
    if report_type == "high_risk_devices":
        assert parsed["devices"][0]["highest_severity"] == "high"


@pytest.mark.parametrize(
    "payload",
    [
        {"report_type": "../../etc", "format": "json"},
        {"report_type": "system_health", "format": "exe"},
        {"report_type": "system_health", "format": "json", "sections": ["shell"]},
        {
            "report_type": "system_health",
            "format": "json",
            "date_from": "2026-06-21T00:00:00Z",
            "date_to": "2026-06-20T00:00:00Z",
        },
        {
            "report_type": "assistant_summary",
            "format": "json",
            "conversation_notes": ["implicit history"],
        },
        {"report_type": "single_device", "format": "json"},
    ],
)
def test_report_request_validation(
    client: TestClient,
    auth_headers: dict[str, str],
    payload: dict,
) -> None:
    response = client.post("/api/v1/reports/generate", headers=auth_headers, json=payload)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_report_rate_limit(database_path) -> None:
    settings = make_settings(database_path, report_rate_limit=1)
    payload = {"report_type": "system_health", "format": "json"}
    with TestClient(create_app(settings)) as test_client:
        first = test_client.post(
            "/api/v1/reports/generate",
            headers={"X-API-Token": API_TOKEN},
            json=payload,
        )
        second = test_client.post(
            "/api/v1/reports/generate",
            headers={"X-API-Token": API_TOKEN},
            json=payload,
        )
    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json()["error"]["code"] == "rate_limit_exceeded"


def test_empty_report_api_response(empty_database_path, auth_headers) -> None:
    with TestClient(create_app(make_settings(empty_database_path))) as test_client:
        response = test_client.post(
            "/api/v1/reports/generate",
            headers=auth_headers,
            json={"report_type": "full_diagnostic", "format": "html"},
        )
    assert response.status_code == 200
    assert response.json()["data"]["empty"] is True
