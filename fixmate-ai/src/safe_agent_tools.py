"""Strict allowlist of minimized read-only tools available to optional LLMs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.assistant_tools import (
    generate_health_summary,
    get_disk_status,
    get_issue_history,
    get_latest_health_scan,
    get_network_status,
    get_recent_issues,
    get_screenshot_analysis,
    get_top_resource_processes,
    search_knowledge_base,
)
from src.database import DEFAULT_DB_PATH
from src.privacy import redact_sensitive_text

MAX_TOOL_CALLS = 4
ALLOWED_TOOL_NAMES = frozenset(
    {
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
)


class ToolValidationError(ValueError):
    """Raised before any unsupported or excessive tool request can execute."""


@dataclass(frozen=True)
class ToolContext:
    """Local context supplied by application code, never by the provider."""

    database_path: Path = DEFAULT_DB_PATH
    question: str = ""


def _redact_payload(value: Any) -> Any:
    """Recursively redact strings and bound collection sizes for provider use."""
    if isinstance(value, str):
        return redact_sensitive_text(value)[:1000]
    if isinstance(value, dict):
        return {
            redact_sensitive_text(str(key))[:100]: _redact_payload(item)
            for key, item in list(value.items())[:30]
        }
    if isinstance(value, list):
        return [_redact_payload(item) for item in value[:20]]
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return redact_sensitive_text(str(value))[:1000]


def _latest_health(context: ToolContext) -> dict[str, Any] | None:
    scan = get_latest_health_scan(context.database_path)
    if scan is None:
        return None
    return {
        "collected_at": scan.get("collected_at"),
        "cpu_percent": scan.get("cpu_percent"),
        "memory_percent": scan.get("memory_percent"),
        "disk_used_percent": scan.get("disk_used_percent"),
        "disk_free_percent": scan.get("disk_free_percent"),
        "health_score": scan.get("health_score"),
    }


def _top_processes(context: ToolContext) -> dict[str, Any] | None:
    result = get_top_resource_processes(database_path=context.database_path)
    if result is None:
        return None
    return {
        "collected_at": result["collected_at"],
        "processes": [
            {"rank": index, "memory_mb": process.get("memory_mb")}
            for index, process in enumerate(result["processes"], start=1)
        ],
        "privacy_note": "Process names were omitted from provider data.",
    }


def _network(context: ToolContext) -> dict[str, Any] | None:
    result = get_network_status(context.database_path)
    if result is None:
        return None
    return {
        key: value
        for key, value in result.items()
        if key
        in {
            "collected_at",
            "latency_threshold_ms",
            "active_interface_count",
            "connection_status",
            "internet_connected",
            "timed_out",
            "latency_ms",
            "bytes_sent",
            "bytes_received",
            "issues",
        }
    }


def _screenshot(context: ToolContext) -> dict[str, Any] | None:
    result = get_screenshot_analysis(context.database_path)
    if result is None:
        return None
    return {
        "analyzed_at": result.get("analyzed_at"),
        "matched_issue_id": result.get("matched_issue_id"),
        "confidence_score": result.get("confidence_score"),
        "privacy_note": "Screenshot and OCR text were omitted from provider data.",
    }


def _summary(context: ToolContext) -> dict[str, Any]:
    summary = generate_health_summary(context.database_path)
    return {
        "latest_health": _latest_health(context),
        "network": _network(context),
        "screenshot": _screenshot(context),
        "recent_issues": summary.get("recent_issues", [])[:10],
        "latest_data_timestamp": summary.get("latest_data_timestamp"),
    }


def execute_safe_tool(name: str, context: ToolContext) -> Any:
    """Execute one exact allowlisted tool with application-owned arguments."""
    if name not in ALLOWED_TOOL_NAMES:
        raise ToolValidationError(f"Unsupported tool request: {name}")
    if name == "get_latest_health_scan":
        result = _latest_health(context)
    elif name == "get_top_resource_processes":
        result = _top_processes(context)
    elif name == "get_disk_status":
        result = get_disk_status(context.database_path)
    elif name == "get_network_status":
        result = _network(context)
    elif name == "get_recent_issues":
        result = get_recent_issues(limit=10, database_path=context.database_path)
    elif name == "get_issue_history":
        result = get_issue_history(limit=20, database_path=context.database_path)
    elif name == "get_screenshot_analysis":
        result = _screenshot(context)
    elif name == "search_knowledge_base":
        result = search_knowledge_base(context.question, limit=5)
    else:
        result = _summary(context)
    return _redact_payload(result)


def validate_tool_requests(raw_requests: Any) -> list[str]:
    """Validate structured requests and reject arguments or unknown fields."""
    if not isinstance(raw_requests, list):
        raise ToolValidationError("Tool requests must be a list.")
    if len(raw_requests) > MAX_TOOL_CALLS:
        raise ToolValidationError(
            f"Tool request limit exceeded; maximum is {MAX_TOOL_CALLS}."
        )
    names: list[str] = []
    for request in raw_requests:
        if not isinstance(request, dict):
            raise ToolValidationError("Each tool request must be an object.")
        if set(request) - {"name", "arguments"}:
            raise ToolValidationError("Tool request contains unsupported fields.")
        name = request.get("name")
        arguments = request.get("arguments", {})
        if not isinstance(name, str) or name not in ALLOWED_TOOL_NAMES:
            raise ToolValidationError(f"Unsupported tool request: {name}")
        if arguments not in ({}, None):
            raise ToolValidationError("Provider-supplied tool arguments are not allowed.")
        names.append(name)
    return names


def execute_tool_requests(
    names: list[str],
    context: ToolContext,
) -> dict[str, Any]:
    """Execute validated requests once each within the global call limit."""
    if len(names) > MAX_TOOL_CALLS:
        raise ToolValidationError(
            f"Tool request limit exceeded; maximum is {MAX_TOOL_CALLS}."
        )
    results: dict[str, Any] = {}
    for name in names:
        if name not in results:
            results[name] = execute_safe_tool(name, context)
    return results

