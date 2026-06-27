"""Defense-in-depth privacy handling for all exported report values."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from typing import Any

from src.privacy import redact_sensitive_text
from src.report_models import DiagnosticReport

SENSITIVE_KEYS = {
    "password",
    "passwd",
    "pwd",
    "token",
    "token_hash",
    "token_salt",
    "api_key",
    "secret",
    "username",
    "user_name",
    "target_host",
    "mac_address",
    "ip_address",
    "queue_path",
    "queue_file",
    "extracted_text",
    "raw_ocr_text",
}


def redact_report_value(value: Any, key: str | None = None) -> Any:
    """Recursively redact untrusted report evidence and sensitive fields."""
    normalized_key = (key or "").casefold().replace("-", "_").replace(" ", "_")
    if normalized_key in SENSITIVE_KEYS:
        return "[REDACTED]"
    if isinstance(value, str):
        return redact_sensitive_text(value)
    if isinstance(value, datetime):
        return value
    if isinstance(value, dict):
        return {
            redact_sensitive_text(str(item_key)): redact_report_value(item, str(item_key))
            for item_key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact_report_value(item) for item in value]
    return value


def sanitize_report(report: DiagnosticReport) -> DiagnosticReport:
    """Return a separately allocated report with every display field redacted."""
    return replace(
        report,
        title=redact_sensitive_text(report.title),
        device_summary=redact_report_value(report.device_summary),
        system=redact_report_value(report.system),
        network=redact_report_value(report.network),
        issues=redact_report_value(report.issues),
        screenshot=redact_report_value(report.screenshot),
        assistant=redact_report_value(report.assistant),
        fleet=redact_report_value(report.fleet),
        devices=redact_report_value(report.devices),
        recommendations=redact_report_value(report.recommendations),
        limitations=redact_report_value(report.limitations),
        privacy_notice=redact_sensitive_text(report.privacy_notice),
    )
