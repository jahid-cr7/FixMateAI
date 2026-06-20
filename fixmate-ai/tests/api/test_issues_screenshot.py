"""Issue filtering/detail and screenshot privacy endpoint tests."""

from fastapi.testclient import TestClient


def test_issue_pagination_severity_type_and_date_filters(client: TestClient) -> None:
    """Unified issue endpoint supports every approved filter."""
    all_issues = client.get("/api/v1/issues?page=1&page_size=1").json()["data"]
    high = client.get("/api/v1/issues?severity=high").json()["data"]
    network = client.get("/api/v1/issues?issue_type=network").json()["data"]
    recent = client.get(
        "/api/v1/issues", params={"date_from": "2026-06-20T00:00:00Z"}
    ).json()["data"]
    assert all_issues["total"] == 2
    assert len(all_issues["items"]) == 1
    assert high["total"] == 1 and high["items"][0]["issue_type"] == "system"
    assert network["total"] == 1 and network["items"][0]["issue_type"] == "network"
    assert recent["total"] == 1


def test_issue_detail_and_missing_record(client: TestClient) -> None:
    """Namespaced issue IDs return detail or a structured 404."""
    listing = client.get("/api/v1/issues?issue_type=system").json()["data"]
    issue_id = listing["items"][0]["id"]
    found = client.get(f"/api/v1/issues/{issue_id}")
    missing = client.get("/api/v1/issues/system:99999")
    assert found.status_code == 200
    assert found.json()["data"]["id"] == issue_id
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "issue_not_found"


def test_issue_response_redacts_private_values(client: TestClient) -> None:
    """Unified issues must apply the existing privacy redactor."""
    response = client.get("/api/v1/issues?issue_type=network")
    for sensitive in (
        "203.0.113.10",
        "AA:BB:CC:DD:EE:FF",
        "alice@example.com",
        "C:\\Users\\Alice",
    ):
        assert sensitive not in response.text


def test_screenshot_history_never_returns_image_filename_or_ocr(client: TestClient) -> None:
    """Screenshot endpoint exposes only safe analysis metadata."""
    response = client.get("/api/v1/screenshot-analyses")
    assert response.status_code == 200
    item = response.json()["data"]["items"][0]
    assert set(item) == {"id", "analyzed_at", "matched_issue_id", "confidence_score"}
    assert "password" not in response.text.casefold()
    assert "image-1234567890abcdef" not in response.text

