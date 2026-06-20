"""General API envelope, status, request ID, CORS, and isolation tests."""

from __future__ import annotations

import hashlib
from pathlib import Path

from fastapi.testclient import TestClient

from api.main import create_app
from src.database import DEFAULT_DB_PATH
from tests.api.conftest import make_settings


def test_health_response_schema_and_request_id(client: TestClient) -> None:
    """Health should use the common envelope and preserve a safe request ID."""
    response = client.get("/health", headers={"X-Request-ID": "test-request-123"})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "test-request-123"
    body = response.json()
    assert body["data"]["status"] == "ok"
    assert body["meta"]["api_version"] == "v1"
    assert body["meta"]["timestamp"].endswith("Z")


def test_status_has_no_secret_values(client: TestClient) -> None:
    """Status reports auth readiness without returning the token."""
    response = client.get("/api/v1/status")
    assert response.status_code == 200
    serialized = response.text
    assert response.json()["data"]["post_auth_configured"] is True
    assert "local-test-token" not in serialized


def test_openapi_contains_all_required_paths(client: TestClient) -> None:
    """Swagger schema should document every required endpoint."""
    schema = client.get("/openapi.json").json()
    required = {
        "/health",
        "/api/v1/status",
        "/api/v1/system/latest",
        "/api/v1/system/history",
        "/api/v1/system/scans",
        "/api/v1/network/latest",
        "/api/v1/network/history",
        "/api/v1/network/diagnostics",
        "/api/v1/issues",
        "/api/v1/issues/{issue_id}",
        "/api/v1/screenshot-analyses",
        "/api/v1/assistant/query",
    }
    assert required <= set(schema["paths"])


def test_cors_allows_only_configured_origin(client: TestClient) -> None:
    """Configured origin receives CORS headers; another origin does not."""
    allowed = client.options(
        "/api/v1/status",
        headers={
            "Origin": "http://allowed.test",
            "Access-Control-Request-Method": "GET",
        },
    )
    denied = client.options(
        "/api/v1/status",
        headers={
            "Origin": "http://denied.test",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert allowed.headers["access-control-allow-origin"] == "http://allowed.test"
    assert "access-control-allow-origin" not in denied.headers


def test_temporary_database_does_not_modify_real_database(tmp_path: Path) -> None:
    """API tests must remain isolated from the user's configured database."""
    before = (
        hashlib.sha256(DEFAULT_DB_PATH.read_bytes()).hexdigest()
        if DEFAULT_DB_PATH.exists()
        else None
    )
    temporary = tmp_path / "isolated.db"
    with TestClient(create_app(make_settings(temporary))) as test_client:
        assert test_client.get("/health").status_code == 200
    after = (
        hashlib.sha256(DEFAULT_DB_PATH.read_bytes()).hexdigest()
        if DEFAULT_DB_PATH.exists()
        else None
    )
    assert temporary.exists()
    assert before == after


def test_invalid_route_error_is_structured(client: TestClient) -> None:
    """Missing routes must not return internal trace information."""
    response = client.get("/does-not-exist")
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "http_error"
    assert "traceback" not in response.text.casefold()


def test_internal_errors_do_not_leak_exception_details(tmp_path: Path) -> None:
    """Unexpected failures should return a generic request-correlated response."""
    application = create_app(make_settings(tmp_path / "errors.db"))

    @application.get("/_test/unexpected-error", include_in_schema=False)
    def raise_unexpected_error() -> None:
        raise RuntimeError("private database and filesystem detail")

    with TestClient(application, raise_server_exceptions=False) as test_client:
        response = test_client.get("/_test/unexpected-error")

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    assert "private database" not in response.text
    assert "traceback" not in response.text.casefold()
