"""Privacy-safe SQLite persistence and read models for managed devices."""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.database import DEFAULT_DB_PATH, connect, initialize_database
from src.fleet_status import device_online_status, is_high_risk
from src.privacy import redact_sensitive_text

TOKEN_ITERATIONS = 120_000
SEVERITY_ORDER = {"critical": 4, "high": 3, "medium": 2, "low": 1}


def _token_digest(token: str, salt_hex: str) -> str:
    """Derive a one-way device-token digest using a per-device salt."""
    return hashlib.pbkdf2_hmac(
        "sha256",
        token.encode("utf-8"),
        bytes.fromhex(salt_hex),
        TOKEN_ITERATIONS,
    ).hex()


def highest_severity(issues: list[dict[str, Any]]) -> str | None:
    """Return the highest recognized severity from uploaded issues."""
    values = [str(item.get("severity") or "").casefold() for item in issues]
    return max(values, key=lambda value: SEVERITY_ORDER.get(value, 0), default=None)


def _redact(value: Any) -> Any:
    if isinstance(value, str):
        return redact_sensitive_text(value)
    if isinstance(value, dict):
        return {str(key): _redact(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


class FleetStore:
    """Fleet persistence boundary with no raw token or unrestricted payload access."""

    def __init__(self, database_path: Path = DEFAULT_DB_PATH) -> None:
        self.database_path = database_path
        initialize_database(database_path)

    def register_device(self, device: dict[str, Any], token: str) -> dict[str, Any]:
        """Create or refresh a device and store only a salted token digest."""
        timestamp = str(device["timestamp"])
        salt = secrets.token_hex(16)
        digest = _token_digest(token, salt)
        safe = _redact(device)
        with closing(connect(self.database_path)) as connection:
            connection.execute(
                """
                INSERT INTO devices (
                    device_id, display_name, operating_system, platform,
                    agent_version, first_seen_at, last_seen_at, status,
                    notes, token_salt, token_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'unknown', '', ?, ?)
                ON CONFLICT(device_id) DO UPDATE SET
                    display_name = excluded.display_name,
                    operating_system = excluded.operating_system,
                    platform = excluded.platform,
                    agent_version = excluded.agent_version,
                    last_seen_at = MAX(devices.last_seen_at, excluded.last_seen_at),
                    token_salt = excluded.token_salt,
                    token_hash = excluded.token_hash
                """,
                (
                    safe["device_id"],
                    safe["display_name"],
                    safe["operating_system"],
                    safe["platform"],
                    safe["agent_version"],
                    timestamp,
                    timestamp,
                    salt,
                    digest,
                ),
            )
            connection.commit()
        return self.get_device(str(safe["device_id"])) or {}

    def token_matches_device(self, device_id: str, token: str) -> bool:
        """Verify a supplied token against stored digest using constant time."""
        with closing(connect(self.database_path)) as connection:
            row = connection.execute(
                "SELECT token_salt, token_hash FROM devices WHERE device_id = ?",
                (device_id,),
            ).fetchone()
        if row is None or not token:
            return False
        supplied = _token_digest(token, str(row["token_salt"]))
        return hmac.compare_digest(str(row["token_hash"]), supplied)

    def record_heartbeat(self, heartbeat: dict[str, Any]) -> dict[str, Any]:
        """Store one heartbeat and update non-secret device recency fields."""
        safe = _redact(heartbeat)
        with closing(connect(self.database_path)) as connection:
            connection.execute(
                """
                INSERT INTO device_heartbeats
                    (device_id, timestamp, status, agent_version)
                VALUES (?, ?, ?, ?)
                """,
                (
                    safe["device_id"],
                    safe["timestamp"],
                    safe["status"],
                    safe["agent_version"],
                ),
            )
            connection.execute(
                """
                UPDATE devices SET
                    last_seen_at = MAX(last_seen_at, ?),
                    status = CASE WHEN ? >= last_seen_at THEN ? ELSE status END,
                    agent_version = CASE
                        WHEN ? >= last_seen_at THEN ? ELSE agent_version END
                WHERE device_id = ?
                """,
                (
                    safe["timestamp"],
                    safe["timestamp"],
                    safe["status"],
                    safe["timestamp"],
                    safe["agent_version"],
                    safe["device_id"],
                ),
            )
            connection.commit()
        return {
            "device_id": safe["device_id"],
            "timestamp": safe["timestamp"],
            "status": safe["status"],
            "agent_version": safe["agent_version"],
        }

    def record_scan_batch(self, scan: dict[str, Any]) -> dict[str, Any]:
        """Store one minimized scan summary rather than unrestricted raw data."""
        safe = _redact(scan)
        issues = list(safe.get("issues") or [])
        severity = highest_severity(issues)
        summary = {
            "system": safe.get("system"),
            "network": safe.get("network"),
            "issues": issues,
        }
        with closing(connect(self.database_path)) as connection:
            cursor = connection.execute(
                """
                INSERT INTO device_scan_batches (
                    device_id, timestamp, payload_summary, health_score,
                    highest_severity, issue_count
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    safe["device_id"],
                    safe["timestamp"],
                    json.dumps(summary, sort_keys=True),
                    safe["health_score"],
                    severity,
                    len(issues),
                ),
            )
            connection.execute(
                "UPDATE devices SET last_seen_at = MAX(last_seen_at, ?) WHERE device_id = ?",
                (safe["timestamp"], safe["device_id"]),
            )
            connection.commit()
            batch_id = int(cursor.lastrowid)
        if issues:
            self.record_fleet_issues(safe["device_id"], batch_id, issues)
        return {
            "id": batch_id,
            "device_id": safe["device_id"],
            "timestamp": safe["timestamp"],
            "health_score": safe["health_score"],
            "highest_severity": severity,
            "issue_count": len(issues),
            "payload_summary": summary,
        }

    def _device_rows(self) -> list[sqlite3.Row]:
        with closing(connect(self.database_path)) as connection:
            return connection.execute(
                """
                SELECT d.device_id, d.display_name, d.operating_system, d.platform,
                       d.agent_version, d.first_seen_at, d.last_seen_at, d.notes,
                       (SELECT h.timestamp FROM device_heartbeats h
                        WHERE h.device_id = d.device_id
                        ORDER BY h.id DESC LIMIT 1) AS last_heartbeat_at,
                       (SELECT b.health_score FROM device_scan_batches b
                        WHERE b.device_id = d.device_id
                        ORDER BY b.id DESC LIMIT 1) AS latest_health_score,
                       (SELECT b.highest_severity FROM device_scan_batches b
                        WHERE b.device_id = d.device_id
                        ORDER BY b.id DESC LIMIT 1) AS highest_severity,
                       (SELECT b.issue_count FROM device_scan_batches b
                        WHERE b.device_id = d.device_id
                        ORDER BY b.id DESC LIMIT 1) AS issue_count
                FROM devices d ORDER BY d.display_name COLLATE NOCASE, d.device_id
                """
            ).fetchall()

    def list_devices(
        self,
        recent_minutes: int = 5,
        now: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Return privacy-safe device summaries with computed fleet status."""
        results: list[dict[str, Any]] = []
        for row in self._device_rows():
            item = _redact(dict(row))
            item["status"] = device_online_status(
                item.pop("last_heartbeat_at"), now, recent_minutes
            )
            item["high_risk"] = is_high_risk(item.get("highest_severity"))
            item["issue_count"] = int(item.get("issue_count") or 0)
            results.append(item)
        return results

    def get_device(
        self,
        device_id: str,
        recent_minutes: int = 5,
        now: datetime | None = None,
    ) -> dict[str, Any] | None:
        """Return one privacy-safe device summary without token columns."""
        return next(
            (
                item
                for item in self.list_devices(recent_minutes, now)
                if item["device_id"] == device_id
            ),
            None,
        )

    def latest_scan(self, device_id: str) -> dict[str, Any] | None:
        """Return the latest minimized scan batch for one device."""
        with closing(connect(self.database_path)) as connection:
            row = connection.execute(
                """
                SELECT id, device_id, timestamp, payload_summary, health_score,
                       highest_severity, issue_count
                FROM device_scan_batches WHERE device_id = ?
                ORDER BY id DESC LIMIT 1
                """,
                (device_id,),
            ).fetchone()
        return self._batch_dict(row) if row else None

    def heartbeat_history(
        self, device_id: str, limit: int = 25
    ) -> list[dict[str, Any]]:
        """Return recent heartbeat records for one device without token data."""
        safe_limit = max(1, min(int(limit), 100))
        with closing(connect(self.database_path)) as connection:
            rows = connection.execute(
                """
                SELECT device_id, timestamp, status, agent_version
                FROM device_heartbeats WHERE device_id = ?
                ORDER BY id DESC LIMIT ?
                """,
                (device_id, safe_limit),
            ).fetchall()
        return [_redact(dict(row)) for row in rows]

    def recent_scan_batches(self, limit: int = 25) -> list[dict[str, Any]]:
        """Return recent minimized scan batches across the fleet."""
        safe_limit = max(1, min(int(limit), 100))
        with closing(connect(self.database_path)) as connection:
            rows = connection.execute(
                """
                SELECT b.id, b.device_id, d.display_name, b.timestamp,
                       b.payload_summary, b.health_score, b.highest_severity,
                       b.issue_count
                FROM device_scan_batches b
                LEFT JOIN devices d ON d.device_id = b.device_id
                ORDER BY b.id DESC LIMIT ?
                """,
                (safe_limit,),
            ).fetchall()
        return [_redact(self._batch_dict(row)) for row in rows]

    def scan_history(
        self, device_id: str, page: int = 1, page_size: int = 25
    ) -> dict[str, Any]:
        """Return paginated minimized scan history newest first."""
        offset = (page - 1) * page_size
        with closing(connect(self.database_path)) as connection:
            total = int(
                connection.execute(
                    "SELECT COUNT(*) FROM device_scan_batches WHERE device_id = ?",
                    (device_id,),
                ).fetchone()[0]
            )
            rows = connection.execute(
                """
                SELECT id, device_id, timestamp, payload_summary, health_score,
                       highest_severity, issue_count
                FROM device_scan_batches WHERE device_id = ?
                ORDER BY id DESC LIMIT ? OFFSET ?
                """,
                (device_id, page_size, offset),
            ).fetchall()
        return {
            "items": [self._batch_dict(row) for row in rows],
            "page": page,
            "page_size": page_size,
            "total": total,
        }

    @staticmethod
    def _batch_dict(row: sqlite3.Row) -> dict[str, Any]:
        item = dict(row)
        try:
            item["payload_summary"] = json.loads(item["payload_summary"])
        except (json.JSONDecodeError, TypeError):
            item["payload_summary"] = {}
        return _redact(item)

    def record_fleet_issues(
        self, device_id: str, batch_id: int, issues: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Insert detected issues from a scan batch; each starts as open."""
        now = datetime.now(timezone.utc).isoformat()
        results: list[dict[str, Any]] = []
        with closing(connect(self.database_path)) as connection:
            for issue in issues:
                safe = _redact(issue)
                cursor = connection.execute(
                    """
                    INSERT INTO fleet_issues (
                        device_id, batch_id, source, code, severity,
                        evidence, explanation, recommendation,
                        status, technician_note, detected_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'open', '', ?, ?)
                    """,
                    (
                        device_id,
                        batch_id,
                        safe.get("source", ""),
                        safe.get("code", ""),
                        safe.get("severity", ""),
                        safe.get("evidence", ""),
                        safe.get("explanation", ""),
                        safe.get("recommendation", ""),
                        safe.get("detected_at") or now,
                        now,
                    ),
                )
                results.append(
                    {
                        "id": int(cursor.lastrowid),
                        "device_id": device_id,
                        "batch_id": batch_id,
                        "source": safe.get("source", ""),
                        "code": safe.get("code", ""),
                        "severity": safe.get("severity", ""),
                        "evidence": safe.get("evidence", ""),
                        "explanation": safe.get("explanation", ""),
                        "recommendation": safe.get("recommendation", ""),
                        "status": "open",
                        "technician_note": "",
                        "detected_at": safe.get("detected_at") or now,
                        "acknowledged_at": None,
                        "resolved_at": None,
                        "updated_at": now,
                    }
                )
            connection.commit()
        return _redact(results)

    def list_fleet_issues(
        self,
        device_id: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Return privacy-safe fleet issues with optional filters."""
        safe_limit = max(1, min(int(limit), 200))
        clauses: list[str] = []
        params: list[Any] = []
        if device_id:
            clauses.append("device_id = ?")
            params.append(device_id)
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        with closing(connect(self.database_path)) as connection:
            rows = connection.execute(
                f"""
                SELECT id, device_id, batch_id, source, code, severity,
                       evidence, explanation, recommendation,
                       status, technician_note,
                       detected_at, acknowledged_at, resolved_at, updated_at
                FROM fleet_issues{where}
                ORDER BY id DESC LIMIT ?
                """,
                (*params, safe_limit),
            ).fetchall()
        return [_redact(dict(row)) for row in rows]

    def update_fleet_issue(
        self,
        issue_id: int,
        status: str,
        technician_note: str = "",
    ) -> dict[str, Any] | None:
        """Transition a fleet issue and record timestamps."""
        now = datetime.now(timezone.utc).isoformat()
        note_clause = "technician_note = ?" if technician_note else "technician_note = technician_note"
        timestamp_map: dict[str, str] = {
            "acknowledged": "acknowledged_at = ?",
            "in_progress": "acknowledged_at = COALESCE(acknowledged_at, ?)",
            "resolved": "resolved_at = ?, acknowledged_at = COALESCE(acknowledged_at, ?)",
            "false_positive": "resolved_at = ?, acknowledged_at = COALESCE(acknowledged_at, ?)",
        }
        ts_clause = timestamp_map.get(status, "")
        if not ts_clause:
            return None
        sets = [f"status = ?", ts_clause, f"updated_at = ?", note_clause]
        params_list: list[Any] = [status]
        if status == "acknowledged":
            params_list.extend([now, now])
        elif status in ("in_progress",):
            params_list.extend([now, now])
        elif status in ("resolved", "false_positive"):
            params_list.extend([now, now, now])
        if technician_note:
            params_list.append(technician_note)
        params_list.append(issue_id)
        with closing(connect(self.database_path)) as connection:
            cursor = connection.execute(
                f"UPDATE fleet_issues SET {', '.join(sets)} WHERE id = ? AND status != ?",
                (*params_list, status),
            )
            if cursor.rowcount == 0:
                row = connection.execute(
                    "SELECT status FROM fleet_issues WHERE id = ?", (issue_id,)
                ).fetchone()
                if row is None:
                    return None
            connection.commit()
            row = connection.execute(
                """
                SELECT id, device_id, batch_id, source, code, severity,
                       evidence, explanation, recommendation,
                       status, technician_note,
                       detected_at, acknowledged_at, resolved_at, updated_at
                FROM fleet_issues WHERE id = ?
                """,
                (issue_id,),
            ).fetchone()
        return _redact(dict(row)) if row else None
