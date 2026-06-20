"""Stable data contracts for privacy-safe diagnostic reports."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class ReportType(str, Enum):
    """Supported evidence-focused report scopes."""

    SYSTEM_HEALTH = "system_health"
    NETWORK_DIAGNOSTICS = "network_diagnostics"
    SCREENSHOT_ANALYSIS = "screenshot_analysis"
    ASSISTANT_SUMMARY = "assistant_summary"
    FULL_DIAGNOSTIC = "full_diagnostic"


class ReportFormat(str, Enum):
    """Supported local export formats."""

    CSV = "csv"
    JSON = "json"
    HTML = "html"
    PDF = "pdf"


REPORT_TITLES = {
    ReportType.SYSTEM_HEALTH: "System Health Summary Report",
    ReportType.NETWORK_DIAGNOSTICS: "Network Diagnostics Report",
    ReportType.SCREENSHOT_ANALYSIS: "Screenshot Error Analysis Report",
    ReportType.ASSISTANT_SUMMARY: "Troubleshooting Assistant Summary Report",
    ReportType.FULL_DIAGNOSTIC: "Full Diagnostic Bundle Report",
}

REPORT_SECTIONS = (
    "system",
    "network",
    "issues",
    "screenshot",
    "assistant",
    "recommendations",
)


@dataclass(frozen=True)
class ReportOptions:
    """User-controlled report scope without any filesystem destination."""

    report_type: ReportType
    date_from: datetime | None = None
    date_to: datetime | None = None
    sections: tuple[str, ...] = REPORT_SECTIONS
    include_conversation: bool = False
    conversation_notes: tuple[str, ...] = ()


@dataclass
class DiagnosticReport:
    """Normalized report content shared by every exporter."""

    report_type: ReportType
    title: str
    generated_at: datetime
    date_from: datetime | None
    date_to: datetime | None
    device_summary: dict[str, Any] = field(default_factory=dict)
    system: dict[str, Any] | None = None
    network: dict[str, Any] | None = None
    issues: list[dict[str, Any]] = field(default_factory=list)
    severity_summary: dict[str, int] = field(default_factory=dict)
    screenshot: dict[str, Any] | None = None
    assistant: dict[str, Any] | None = None
    recommendations: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    privacy_notice: str = ""
    empty: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Return a serialization-ready representation."""
        return asdict(self)


@dataclass(frozen=True)
class ExportedReport:
    """In-memory export result; it is never persisted by the exporter."""

    requested_format: ReportFormat
    actual_format: ReportFormat
    filename: str
    media_type: str
    content: bytes
    fallback_warning: str | None = None

