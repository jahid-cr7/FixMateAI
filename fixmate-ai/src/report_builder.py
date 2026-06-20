"""Read-only evidence assembly for FixMate AI diagnostic reports."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.assistant_tools import (
    get_issue_history,
    get_latest_health_scan,
    get_network_status,
    get_screenshot_analysis,
)
from src.database import DEFAULT_DB_PATH
from src.report_models import DiagnosticReport, REPORT_TITLES, ReportOptions, ReportType
from src.report_privacy import sanitize_report
from src.troubleshooting_assistant import answer_question

PRIVACY_NOTICE = (
    "This report was generated locally from collected FixMate AI evidence. "
    "Sensitive values are redacted on a best-effort basis. No screenshot files, "
    "raw OCR text, credentials, complete IP/MAC addresses, or report files are stored."
)
DEFAULT_LIMITATIONS = [
    "Metrics describe recorded scan times and may not represent current conditions.",
    "Recommendations are safe guidance, not guaranteed fixes or completed repairs.",
    "Privacy redaction is best-effort; review the report before sharing it.",
]


def _as_utc(value: datetime | str | None) -> datetime | None:
    """Normalize aware, naive, or ISO timestamps to UTC."""
    if value is None:
        return None
    try:
        parsed = datetime.fromisoformat(value) if isinstance(value, str) else value
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _in_range(value: datetime | str | None, options: ReportOptions) -> bool:
    """Return whether evidence timestamp is inside the inclusive requested range."""
    timestamp = _as_utc(value)
    if timestamp is None:
        return options.date_from is None and options.date_to is None
    start = _as_utc(options.date_from)
    end = _as_utc(options.date_to)
    return not ((start and timestamp < start) or (end and timestamp > end))


def _allows(options: ReportOptions, section: str) -> bool:
    return section in options.sections


def _system_payload(scan: dict[str, Any]) -> dict[str, Any]:
    return {
        "evidence_timestamp": scan.get("collected_at"),
        "health_score": scan.get("health_score"),
        "cpu_percent": scan.get("cpu_percent"),
        "memory_percent": scan.get("memory_percent"),
        "disk_used_percent": scan.get("disk_used_percent"),
        "disk_free_percent": scan.get("disk_free_percent"),
        "boot_time": scan.get("boot_time"),
        "top_processes": scan.get("top_processes", []),
    }


def _device_summary(scan: dict[str, Any] | None) -> dict[str, Any]:
    if not scan:
        return {"status": "No system-health scan is available."}
    return {
        "operating_system": scan.get("os_name"),
        "release": scan.get("os_release"),
        "architecture": scan.get("architecture"),
        "evidence_timestamp": scan.get("collected_at"),
    }


def _assistant_payload(database_path: Path, now: datetime) -> dict[str, Any]:
    answer = answer_question("Summarize this computer's health.", database_path, now)
    return {
        "direct_answer": answer["direct_answer"],
        "evidence": answer["evidence"],
        "evidence_timestamp": answer["relevant_timestamp"],
        "severity": answer["severity"],
        "guidance": answer["guidance"],
        "freshness": answer["freshness"],
        "sufficient_evidence": answer["sufficient_evidence"],
    }


def _screenshot_payload(screenshot: dict[str, Any]) -> dict[str, Any]:
    """Minimize screenshot findings; never include OCR text or filenames."""
    return {
        "evidence_timestamp": screenshot.get("analyzed_at"),
        "matched_issue_id": screenshot.get("matched_issue_id"),
        "confidence_score": screenshot.get("confidence_score"),
    }


def build_report(
    options: ReportOptions,
    database_path: Path = DEFAULT_DB_PATH,
    generated_at: datetime | None = None,
) -> DiagnosticReport:
    """Build a deterministic report without changing the database or filesystem."""
    if options.date_from and options.date_to:
        if (_as_utc(options.date_from) or datetime.min.replace(tzinfo=timezone.utc)) > (
            _as_utc(options.date_to) or datetime.max.replace(tzinfo=timezone.utc)
        ):
            raise ValueError("date_from must not be later than date_to")

    now = _as_utc(generated_at) or datetime.now(timezone.utc)
    scan = get_latest_health_scan(database_path)
    if scan and not _in_range(scan.get("collected_at"), options):
        scan = None
    network = get_network_status(database_path)
    if network and not _in_range(network.get("collected_at"), options):
        network = None
    screenshot = get_screenshot_analysis(database_path)
    if screenshot and not _in_range(screenshot.get("analyzed_at"), options):
        screenshot = None
    issues = [
        issue
        for issue in get_issue_history(limit=500, database_path=database_path)
        if _in_range(issue.get("timestamp"), options)
    ]

    wanted_system = options.report_type in {ReportType.SYSTEM_HEALTH, ReportType.FULL_DIAGNOSTIC}
    wanted_network = options.report_type in {ReportType.NETWORK_DIAGNOSTICS, ReportType.FULL_DIAGNOSTIC}
    wanted_screenshot = options.report_type in {ReportType.SCREENSHOT_ANALYSIS, ReportType.FULL_DIAGNOSTIC}
    wanted_assistant = options.report_type in {ReportType.ASSISTANT_SUMMARY, ReportType.FULL_DIAGNOSTIC}

    system_payload = _system_payload(scan) if scan and wanted_system and _allows(options, "system") else None
    network_payload = network if network and wanted_network and _allows(options, "network") else None
    screenshot_payload = (
        _screenshot_payload(screenshot)
        if screenshot and wanted_screenshot and _allows(options, "screenshot")
        else None
    )
    if options.report_type == ReportType.SYSTEM_HEALTH:
        issues = [item for item in issues if item.get("source") == "system"]
    elif options.report_type == ReportType.NETWORK_DIAGNOSTICS:
        issues = [item for item in issues if item.get("source") == "network"]
    elif options.report_type == ReportType.SCREENSHOT_ANALYSIS:
        issues = []
    included_issues = issues if _allows(options, "issues") else []
    assistant_payload = (
        _assistant_payload(database_path, now)
        if wanted_assistant and _allows(options, "assistant")
        else None
    )
    if assistant_payload and not _in_range(
        assistant_payload.get("evidence_timestamp"), options
    ):
        assistant_payload = None
    if assistant_payload and options.include_conversation:
        assistant_payload["explicitly_selected_conversation_notes"] = list(
            options.conversation_notes
        )

    severity_summary: dict[str, int] = {}
    recommendations: list[str] = []
    for issue in included_issues:
        severity = str(issue.get("severity") or "unknown").casefold()
        severity_summary[severity] = severity_summary.get(severity, 0) + 1
        recommendation = issue.get("recommendation")
        if recommendation and recommendation not in recommendations:
            recommendations.append(str(recommendation))
    if assistant_payload and _allows(options, "recommendations"):
        for item in assistant_payload.get("guidance", []):
            if item not in recommendations:
                recommendations.append(str(item))
    if not _allows(options, "recommendations"):
        recommendations = []

    has_evidence = any(
        (
            system_payload,
            network_payload,
            screenshot_payload,
            included_issues,
            assistant_payload and assistant_payload.get("sufficient_evidence"),
        )
    )
    report = DiagnosticReport(
        report_type=options.report_type,
        title=REPORT_TITLES[options.report_type],
        generated_at=now,
        date_from=_as_utc(options.date_from),
        date_to=_as_utc(options.date_to),
        device_summary=_device_summary(scan),
        system=system_payload,
        network=network_payload,
        issues=included_issues,
        severity_summary=severity_summary,
        screenshot=screenshot_payload,
        assistant=assistant_payload,
        recommendations=recommendations,
        limitations=list(DEFAULT_LIMITATIONS),
        privacy_notice=PRIVACY_NOTICE,
        empty=not has_evidence,
    )
    return sanitize_report(report)
