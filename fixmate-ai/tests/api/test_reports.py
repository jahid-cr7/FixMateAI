"""FastAPI report discovery, generation, authentication, and rate-limit tests."""

from __future__ import annotations

import base64
import json

import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from src.report_models import ReportFormat, ReportType
from tests.api.conftest import API_TOKEN, make_settings


def test_report_types_endpoint_lists_every_type_and_format(client: TestClient) -> None:
    response = client.get("/api/v1/reports/types")
    assert response.status_code == 200
    data = response.json()["data"]
    assert {item["id"] for item in data["types"]} == {item.value for item in ReportType}
    assert set(data["types"][0]["formats"]) == {item.value for item in ReportFormat}


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

