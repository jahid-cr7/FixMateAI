"""Read-only data tools for the deterministic troubleshooting assistant."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from src.database import DEFAULT_DATABASE_URL, DEFAULT_DB_PATH, _fmt_pct, connect_readonly
from src.error_matcher import rank_error_matches, reliable_matches
from src.knowledge_base import KnowledgeEntry, load_knowledge_base
from src.privacy import redact_sensitive_text


def _connect_readonly(
    database_path: Path = DEFAULT_DB_PATH,
    database_url: str | None = DEFAULT_DATABASE_URL,
) -> Any:
    """Open an existing database in enforced read-only mode."""

    return connect_readonly(database_path, database_url)


def _parse_json_list(value: str | None) -> list[Any]:
    """Decode a stored JSON list without allowing malformed data to crash a tool."""
    try:
        decoded = json.loads(value or "[]")
        return decoded if isinstance(decoded, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def _parse_timestamp(value: str | None) -> datetime | None:
    """Parse an ISO timestamp for local filtering and freshness checks."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def get_latest_health_scan(
    database_path: Path = DEFAULT_DB_PATH,
    database_url: str | None = DEFAULT_DATABASE_URL,
) -> dict[str, Any] | None:
    """Return the latest system scan with decoded process data."""
    connection = _connect_readonly(database_path, database_url)
    if connection is None:
        return None
    try:
        row = connection.execute("SELECT * FROM scans ORDER BY id DESC LIMIT 1").fetchone()
    except Exception:
        row = None
    finally:
        connection.close()
    if row is None:
        return None
    scan = dict(row)
    scan["top_processes"] = _parse_json_list(scan.pop("top_processes_json", "[]"))
    return scan


def get_health_scan_history(
    limit: int = 20,
    database_path: Path = DEFAULT_DB_PATH,
    database_url: str | None = DEFAULT_DATABASE_URL,
) -> list[dict[str, Any]]:
    """Return recent system scans newest first."""
    connection = _connect_readonly(database_path, database_url)
    if connection is None:
        return []
    try:
        rows = connection.execute(
            """
            SELECT collected_at, cpu_percent, memory_percent, disk_used_percent,
                   disk_free_percent, health_score
            FROM scans ORDER BY id DESC LIMIT ?
            """,
            (max(1, limit),),
        ).fetchall()
    except Exception:
        rows = []
    finally:
        connection.close()
    return [dict(row) for row in rows]


def get_top_resource_processes(
    limit: int = 5,
    database_path: Path = DEFAULT_DB_PATH,
    database_url: str | None = DEFAULT_DATABASE_URL,
) -> dict[str, Any] | None:
    """Return top memory processes from the latest recorded system scan."""
    scan = get_latest_health_scan(database_path, database_url)
    if scan is None:
        return None
    processes = [item for item in scan.get("top_processes", []) if isinstance(item, dict)]
    processes.sort(key=lambda item: float(item.get("memory_mb") or 0), reverse=True)
    return {
        "collected_at": scan["collected_at"],
        "processes": processes[: max(1, limit)],
    }


def get_disk_status(
    database_path: Path = DEFAULT_DB_PATH,
    database_url: str | None = DEFAULT_DATABASE_URL,
) -> dict[str, Any] | None:
    """Return latest disk usage and free-space evidence."""
    scan = get_latest_health_scan(database_path, database_url)
    if scan is None:
        return None
    return {
        "collected_at": scan["collected_at"],
        "disk_used_percent": scan.get("disk_used_percent"),
        "disk_free_percent": scan.get("disk_free_percent"),
        "nearly_full": (
            scan.get("disk_free_percent") is not None
            and float(scan["disk_free_percent"]) < 10
        ),
    }


def get_network_status(
    database_path: Path = DEFAULT_DB_PATH,
    database_url: str | None = DEFAULT_DATABASE_URL,
) -> dict[str, Any] | None:
    """Return latest network status without exposing the configured target address."""
    connection = _connect_readonly(database_path, database_url)
    if connection is None:
        return None
    try:
        row = connection.execute(
            """
            SELECT id, collected_at, latency_threshold_ms, active_interfaces_json,
                   connection_status, internet_connected, timed_out, latency_ms,
                   bytes_sent, bytes_received
            FROM network_diagnostics ORDER BY id DESC LIMIT 1
            """
        ).fetchone()
        if row is None:
            return None
        issues = connection.execute(
            """
            SELECT code, severity, evidence, explanation, recommendation, detected_at
            FROM network_issues WHERE diagnostic_id = ? ORDER BY id
            """,
            (row["id"],),
        ).fetchall()
    except Exception:
        return None
    finally:
        connection.close()

    result = dict(row)
    result.pop("id", None)
    active_interfaces = _parse_json_list(result.pop("active_interfaces_json", "[]"))
    result["active_interface_count"] = len(active_interfaces)
    result["connection_status"] = bool(result["connection_status"])
    result["internet_connected"] = bool(result["internet_connected"])
    result["timed_out"] = bool(result["timed_out"])
    result["issues"] = [
        {
            key: redact_sensitive_text(str(value)) if isinstance(value, str) else value
            for key, value in dict(issue).items()
        }
        for issue in issues
    ]
    return result


def get_recent_issues(
    since: datetime | None = None,
    limit: int = 50,
    database_path: Path = DEFAULT_DB_PATH,
    database_url: str | None = DEFAULT_DATABASE_URL,
) -> list[dict[str, Any]]:
    """Return recent system and network issues newest first."""
    connection = _connect_readonly(database_path, database_url)
    if connection is None:
        return []
    try:
        dialect = connection.dialect
        fmt_pct = _fmt_pct(dialect, "i.value")
        system_rows = connection.execute(
            f"""
            SELECT s.collected_at AS timestamp, 'system' AS source, i.code,
                   i.severity, i.metric || ': ' || {fmt_pct} AS evidence,
                   i.explanation, i.recommendation
            FROM issues i JOIN scans s ON s.id = i.scan_id
            """
        ).fetchall()
        network_rows = connection.execute(
            """
            SELECT ni.detected_at AS timestamp, 'network' AS source, ni.code,
                   ni.severity, ni.evidence, ni.explanation, ni.recommendation
            FROM network_issues ni
            """
        ).fetchall()
    except Exception:
        return []
    finally:
        connection.close()

    issues = [dict(row) for row in [*system_rows, *network_rows]]
    if since is not None:
        issues = [
            issue
            for issue in issues
            if (parsed := _parse_timestamp(issue.get("timestamp"))) is not None
            and (
                parsed >= since
                if parsed.tzinfo == since.tzinfo
                else parsed.replace(tzinfo=None) >= since.replace(tzinfo=None)
            )
        ]
    issues.sort(key=lambda issue: str(issue.get("timestamp") or ""), reverse=True)
    redacted: list[dict[str, Any]] = []
    for issue in issues[: max(1, limit)]:
        redacted.append(
            {
                key: redact_sensitive_text(str(value)) if isinstance(value, str) else value
                for key, value in issue.items()
            }
        )
    return redacted


def get_issue_history(
    limit: int = 100,
    database_path: Path = DEFAULT_DB_PATH,
    database_url: str | None = DEFAULT_DATABASE_URL,
) -> list[dict[str, Any]]:
    """Return combined historical issues without modifying stored records."""
    return get_recent_issues(since=None, limit=limit, database_path=database_path, database_url=database_url)


def get_screenshot_analysis(
    database_path: Path = DEFAULT_DB_PATH,
    database_url: str | None = DEFAULT_DATABASE_URL,
) -> dict[str, Any] | None:
    """Return the latest redacted screenshot-analysis record."""
    connection = _connect_readonly(database_path, database_url)
    if connection is None:
        return None
    try:
        row = connection.execute(
            """
            SELECT analyzed_at, anonymized_filename, extracted_text_redacted,
                   matched_issue_id, confidence_score
            FROM screenshot_analyses ORDER BY id DESC LIMIT 1
            """
        ).fetchone()
    except Exception:
        row = None
    finally:
        connection.close()
    if row is None:
        return None
    result = dict(row)
    result["extracted_text_redacted"] = redact_sensitive_text(
        str(result["extracted_text_redacted"])
    )
    return result


def search_knowledge_base(
    query: str,
    limit: int = 5,
    entries: list[KnowledgeEntry] | None = None,
) -> list[dict[str, Any]]:
    """Return reliable deterministic knowledge-base matches for a query."""
    knowledge = entries if entries is not None else load_knowledge_base()
    matches = reliable_matches(rank_error_matches(query, knowledge))
    return [
        {
            "issue": match["issue"],
            "confidence": match["confidence"],
            "evidence": match["evidence"],
        }
        for match in matches[: max(1, limit)]
    ]


def generate_health_summary(
    database_path: Path = DEFAULT_DB_PATH,
    database_url: str | None = DEFAULT_DATABASE_URL,
) -> dict[str, Any]:
    """Collect a read-only snapshot for assistant summary and freshness views."""
    latest_health = get_latest_health_scan(database_path, database_url)
    network = get_network_status(database_path, database_url)
    screenshot = get_screenshot_analysis(database_path, database_url)
    issues = get_recent_issues(limit=20, database_path=database_path, database_url=database_url)
    timestamps = [
        value
        for value in (
            latest_health.get("collected_at") if latest_health else None,
            network.get("collected_at") if network else None,
            screenshot.get("analyzed_at") if screenshot else None,
        )
        if value
    ]
    return {
        "latest_health": latest_health,
        "network": network,
        "screenshot": screenshot,
        "recent_issues": issues,
        "latest_data_timestamp": max(timestamps) if timestamps else None,
    }
