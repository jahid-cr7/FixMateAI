"""Missing-record and structured validation error tests."""

from pathlib import Path

from fastapi.testclient import TestClient

from api.main import create_app
from tests.api.conftest import make_settings


def test_missing_latest_records_return_structured_404(
    empty_database_path: Path,
) -> None:
    """Empty temporary database should return safe 404s and empty histories."""
    with TestClient(create_app(make_settings(empty_database_path))) as client:
        system = client.get("/api/v1/system/latest")
        network = client.get("/api/v1/network/latest")
        history = client.get("/api/v1/system/history")
    assert system.status_code == network.status_code == 404
    assert system.json()["error"]["code"] == "system_scan_not_found"
    assert network.json()["error"]["code"] == "network_diagnostic_not_found"
    assert history.json()["data"]["total"] == 0


def test_invalid_pagination_has_structured_422(empty_database_path: Path) -> None:
    """Pydantic validation errors should not expose internals."""
    with TestClient(create_app(make_settings(empty_database_path))) as client:
        response = client.get("/api/v1/issues?page=0")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert "traceback" not in response.text.casefold()
