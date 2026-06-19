"""Security tests for the exact Phase 5 read-only tool allowlist."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.safe_agent_tools import (
    ALLOWED_TOOL_NAMES,
    MAX_TOOL_CALLS,
    ToolContext,
    ToolValidationError,
    execute_safe_tool,
    execute_tool_requests,
    validate_tool_requests,
)
from tests.test_assistant_tools import populate_assistant_database


def test_allowlist_contains_only_approved_tools() -> None:
    """No SQL, shell, file, repair, or mutation capability may appear."""
    assert ALLOWED_TOOL_NAMES == {
        "get_latest_health_scan",
        "get_top_resource_processes",
        "get_disk_status",
        "get_network_status",
        "get_recent_issues",
        "get_issue_history",
        "get_screenshot_analysis",
        "search_knowledge_base",
        "generate_health_summary",
    }


@pytest.mark.parametrize(
    "name",
    ["run_shell", "execute_sql", "read_file", "kill_process", "repair_system", "scan_ports"],
)
def test_unsupported_tool_requests_are_rejected(name: str) -> None:
    """Dangerous capability names should fail before tool execution."""
    with pytest.raises(ToolValidationError, match="Unsupported"):
        validate_tool_requests([{"name": name, "arguments": {}}])


def test_provider_arguments_are_rejected() -> None:
    """Providers cannot choose paths, SQL, limits, hosts, or other arguments."""
    with pytest.raises(ToolValidationError, match="arguments"):
        validate_tool_requests(
            [{"name": "get_latest_health_scan", "arguments": {"path": "secret"}}]
        )


def test_excessive_tool_requests_are_rejected() -> None:
    """Structured plans cannot exceed the hard call limit."""
    requests = [
        {"name": "get_latest_health_scan", "arguments": {}}
        for _ in range(MAX_TOOL_CALLS + 1)
    ]
    with pytest.raises(ToolValidationError, match="limit exceeded"):
        validate_tool_requests(requests)


def test_screenshot_and_process_tools_minimize_external_payload(tmp_path: Path) -> None:
    """OCR text, screenshot IDs, and process names must not enter tool payloads."""
    database_path = tmp_path / "minimized.db"
    populate_assistant_database(database_path)
    context = ToolContext(database_path, "Explain my latest screenshot error")
    screenshot = execute_safe_tool("get_screenshot_analysis", context)
    processes = execute_safe_tool("get_top_resource_processes", context)
    serialized = f"{screenshot} {processes}"
    assert "rm -rf" not in serialized
    assert "image-1234567890abcdef" not in serialized
    assert "browser.exe" not in serialized
    assert "editor.exe" not in serialized


def test_duplicate_tool_names_execute_once(tmp_path: Path) -> None:
    """Duplicate requests should consume one result rather than loop."""
    database_path = tmp_path / "duplicate.db"
    populate_assistant_database(database_path)
    results = execute_tool_requests(
        ["get_disk_status", "get_disk_status"],
        ToolContext(database_path, "disk"),
    )
    assert list(results) == ["get_disk_status"]

