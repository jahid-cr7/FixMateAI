"""Deterministic read-only status rules for endpoint devices."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

RISK_SEVERITIES = {"high", "critical"}
ISSUE_STATUSES = {"open", "acknowledged", "in_progress", "resolved", "false_positive"}


def parse_utc(value: str | datetime | None) -> datetime | None:
    """Parse a timestamp and normalize it to aware UTC."""
    if value is None:
        return None
    try:
        parsed = datetime.fromisoformat(value) if isinstance(value, str) else value
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def device_online_status(
    last_heartbeat: str | datetime | None,
    now: datetime | None = None,
    recent_minutes: int = 5,
) -> str:
    """Classify a device as online, offline, or unknown from its heartbeat."""
    heartbeat = parse_utc(last_heartbeat)
    if heartbeat is None:
        return "unknown"
    current = parse_utc(now) or datetime.now(timezone.utc)
    window = timedelta(minutes=max(1, recent_minutes))
    if heartbeat > current + timedelta(minutes=1):
        return "unknown"
    return "online" if current - heartbeat <= window else "offline"


def is_high_risk(severity: str | None) -> bool:
    """Return whether the latest known severity needs high-risk attention."""
    return str(severity or "").casefold() in RISK_SEVERITIES


def fleet_summary(devices: list[dict]) -> dict[str, int]:
    """Count fleet status and risk categories for dashboard cards."""
    return {
        "total": len(devices),
        "online": sum(item.get("status") == "online" for item in devices),
        "offline": sum(item.get("status") == "offline" for item in devices),
        "unknown": sum(item.get("status") == "unknown" for item in devices),
        "high_risk": sum(bool(item.get("high_risk")) for item in devices),
    }


def filter_devices(
    devices: list[dict],
    operating_system: str | None = None,
    status: str | None = None,
    severity: str | None = None,
) -> list[dict]:
    """Apply case-insensitive fleet filters without mutating records."""
    filtered = devices
    if operating_system:
        filtered = [
            item
            for item in filtered
            if str(item.get("operating_system", "")).casefold()
            == operating_system.casefold()
        ]
    if status:
        filtered = [item for item in filtered if item.get("status") == status]
    if severity:
        filtered = [
            item
            for item in filtered
            if str(item.get("highest_severity") or "none").casefold()
            == severity.casefold()
        ]
    return filtered
