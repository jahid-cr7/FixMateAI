"""Paginated, privacy-safe database queries for API v1."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.database import _fmt_pct, connect
from src.privacy import redact_sensitive_text


def to_utc(value: str | None) -> datetime | None:
    """Convert a stored ISO timestamp to an aware UTC datetime."""
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _redact(value: Any) -> Any:
    """Recursively apply the existing privacy utility to response strings."""
    if isinstance(value, str):
        return redact_sensitive_text(value)
    if isinstance(value, dict):
        return {str(key): _redact(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


def _json_list(value: str | None) -> list[Any]:
    """Safely decode a stored JSON list."""
    try:
        result = json.loads(value or "[]")
        return result if isinstance(result, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


class DataService:
    """Database-backed read service injected into API route handlers."""

    def __init__(self, database_path: Path, database_url: str | None = None) -> None:
        self.database_path = database_path
        self.database_url = database_url

    def _connect(self):
        return connect(self.database_path, self.database_url)

    def database_available(self) -> bool:
        """Return whether the configured database can be opened and queried."""
        try:
            with self._connect() as connection:
                connection.execute("SELECT 1").fetchone()
            return True
        except Exception:
            return False

    def latest_system(self) -> dict[str, Any] | None:
        """Return latest scan and attached issues."""
        with self._connect() as connection:
            dialect = connection.dialect
            fmt = _fmt_pct(dialect, "i.value")
            row = connection.execute("SELECT * FROM scans ORDER BY id DESC LIMIT 1").fetchone()
            if row is None:
                return None
            issue_rows = connection.execute(
                "SELECT * FROM issues WHERE scan_id = ? ORDER BY id", (row["id"],)
            ).fetchall()
        scan = dict(row)
        result = {
            "id": scan["id"],
            "collected_at": to_utc(scan["collected_at"]),
            "os_name": scan["os_name"],
            "os_release": scan["os_release"],
            "architecture": scan["architecture"],
            "boot_time": to_utc(scan["boot_time"]),
            "cpu_percent": scan["cpu_percent"],
            "memory_percent": scan["memory_percent"],
            "disk_used_percent": scan["disk_used_percent"],
            "disk_free_percent": scan["disk_free_percent"],
            "health_score": scan["health_score"],
            "top_processes": _json_list(scan["top_processes_json"]),
            "issues": [
                {
                    "id": f"system:{issue['id']}",
                    "code": issue["code"],
                    "severity": issue["severity"],
                    "evidence": f"{issue['metric']}: {_fmt_pct(dialect, str(issue['value']))}",
                    "explanation": issue["explanation"],
                    "recommendation": issue["recommendation"],
                    "detected_at": to_utc(scan["collected_at"]),
                }
                for issue in issue_rows
            ],
        }
        return _redact(result)

    def system_history(
        self,
        page: int,
        page_size: int,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> dict[str, Any]:
        """Return filtered paginated system history."""
        conditions: list[str] = []
        parameters: list[Any] = []
        if date_from:
            conditions.append("collected_at >= ?")
            parameters.append(date_from.astimezone(timezone.utc).isoformat())
        if date_to:
            conditions.append("collected_at <= ?")
            parameters.append(date_to.astimezone(timezone.utc).isoformat())
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        offset = (page - 1) * page_size
        with self._connect() as connection:
            total = connection.execute(
                f"SELECT COUNT(*) FROM scans {where}", parameters
            ).fetchone()[0]
            rows = connection.execute(
                f"""
                SELECT id, collected_at, cpu_percent, memory_percent,
                       disk_used_percent, disk_free_percent, health_score
                FROM scans {where} ORDER BY id DESC LIMIT ? OFFSET ?
                """,
                [*parameters, page_size, offset],
            ).fetchall()
        items = [dict(row) for row in rows]
        for item in items:
            item["collected_at"] = to_utc(item["collected_at"])
        return {"items": _redact(items), "page": page, "page_size": page_size, "total": total}

    def latest_network(self) -> dict[str, Any] | None:
        """Return latest network result without target host or interface names."""
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM network_diagnostics ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if row is None:
                return None
            issue_rows = connection.execute(
                "SELECT * FROM network_issues WHERE diagnostic_id = ? ORDER BY id",
                (row["id"],),
            ).fetchall()
        diagnostic = dict(row)
        interfaces = _json_list(diagnostic["active_interfaces_json"])
        result = {
            "id": diagnostic["id"],
            "collected_at": to_utc(diagnostic["collected_at"]),
            "connection_status": bool(diagnostic["connection_status"]),
            "internet_connected": bool(diagnostic["internet_connected"]),
            "timed_out": bool(diagnostic["timed_out"]),
            "latency_ms": diagnostic["latency_ms"],
            "latency_threshold_ms": diagnostic["latency_threshold_ms"],
            "active_interface_count": len(interfaces),
            "bytes_sent": diagnostic["bytes_sent"],
            "bytes_received": diagnostic["bytes_received"],
            "issues": [
                {
                    "id": f"network:{issue['id']}",
                    "code": issue["code"],
                    "severity": issue["severity"],
                    "evidence": issue["evidence"],
                    "explanation": issue["explanation"],
                    "recommendation": issue["recommendation"],
                    "detected_at": to_utc(issue["detected_at"]),
                }
                for issue in issue_rows
            ],
        }
        return _redact(result)

    def network_history(
        self,
        page: int,
        page_size: int,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> dict[str, Any]:
        """Return filtered paginated network history."""
        conditions: list[str] = []
        parameters: list[Any] = []
        if date_from:
            conditions.append("collected_at >= ?")
            parameters.append(date_from.astimezone(timezone.utc).isoformat())
        if date_to:
            conditions.append("collected_at <= ?")
            parameters.append(date_to.astimezone(timezone.utc).isoformat())
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        offset = (page - 1) * page_size
        with self._connect() as connection:
            total = connection.execute(
                f"SELECT COUNT(*) FROM network_diagnostics {where}", parameters
            ).fetchone()[0]
            rows = connection.execute(
                f"""
                SELECT id, collected_at, connection_status, internet_connected,
                       timed_out, latency_ms, bytes_sent, bytes_received
                FROM network_diagnostics {where}
                ORDER BY id DESC LIMIT ? OFFSET ?
                """,
                [*parameters, page_size, offset],
            ).fetchall()
        items = [dict(row) for row in rows]
        for item in items:
            item["collected_at"] = to_utc(item["collected_at"])
            item["connection_status"] = bool(item["connection_status"])
            item["internet_connected"] = bool(item["internet_connected"])
            item["timed_out"] = bool(item["timed_out"])
        return {"items": _redact(items), "page": page, "page_size": page_size, "total": total}

    def issues(
        self,
        page: int,
        page_size: int,
        severity: str | None = None,
        issue_type: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> dict[str, Any]:
        """Return unified filtered issue records."""
        with self._connect() as connection:
            dialect = connection.dialect
            fmt_pct = _fmt_pct(dialect, "i.value")
            system_rows = connection.execute(
                f"""
                SELECT 'system:' || i.id AS id, 'system' AS issue_type, i.code,
                       i.severity, i.metric || ': ' || {fmt_pct} AS evidence,
                       i.explanation, i.recommendation, s.collected_at AS detected_at
                FROM issues i JOIN scans s ON s.id = i.scan_id
                """
            ).fetchall()
            network_rows = connection.execute(
                """
                SELECT 'network:' || id AS id, 'network' AS issue_type, code,
                       severity, evidence, explanation, recommendation, detected_at
                FROM network_issues
                """
            ).fetchall()
        records = [dict(row) for row in [*system_rows, *network_rows]]
        filtered: list[dict[str, Any]] = []
        for record in records:
            timestamp = to_utc(record["detected_at"])
            if severity and record["severity"] != severity:
                continue
            if issue_type and record["issue_type"] != issue_type:
                continue
            if date_from and timestamp and timestamp < date_from.astimezone(timezone.utc):
                continue
            if date_to and timestamp and timestamp > date_to.astimezone(timezone.utc):
                continue
            record["detected_at"] = timestamp
            filtered.append(record)
        filtered.sort(key=lambda item: item["detected_at"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        total = len(filtered)
        offset = (page - 1) * page_size
        return {
            "items": _redact(filtered[offset : offset + page_size]),
            "page": page,
            "page_size": page_size,
            "total": total,
        }

    def issue_by_id(self, issue_id: str) -> dict[str, Any] | None:
        """Return one unified issue by namespaced ID."""
        if ":" not in issue_id:
            return None
        issue_type, raw_id = issue_id.split(":", maxsplit=1)
        if issue_type not in {"system", "network"} or not raw_id.isdigit():
            return None
        page = self.issues(1, 10_000, issue_type=issue_type)
        return next((item for item in page["items"] if item["id"] == issue_id), None)

    def screenshot_analyses(
        self,
        page: int,
        page_size: int,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> dict[str, Any]:
        """Return analysis metadata only—never image, filename, or OCR text."""
        conditions: list[str] = []
        parameters: list[Any] = []
        if date_from:
            conditions.append("analyzed_at >= ?")
            parameters.append(date_from.astimezone(timezone.utc).isoformat())
        if date_to:
            conditions.append("analyzed_at <= ?")
            parameters.append(date_to.astimezone(timezone.utc).isoformat())
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        offset = (page - 1) * page_size
        with self._connect() as connection:
            total = connection.execute(
                f"SELECT COUNT(*) FROM screenshot_analyses {where}", parameters
            ).fetchone()[0]
            rows = connection.execute(
                f"""
                SELECT id, analyzed_at, matched_issue_id, confidence_score
                FROM screenshot_analyses {where}
                ORDER BY id DESC LIMIT ? OFFSET ?
                """,
                [*parameters, page_size, offset],
            ).fetchall()
        items = [dict(row) for row in rows]
        for item in items:
            item["analyzed_at"] = to_utc(item["analyzed_at"])
        return {"items": _redact(items), "page": page, "page_size": page_size, "total": total}
