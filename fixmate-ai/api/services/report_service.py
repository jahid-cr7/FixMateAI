"""API-facing orchestration for read-only in-memory report generation."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

from api.schemas.reports import GenerateReportRequest
from src.report_builder import build_report
from src.report_exporters import export_report
from src.report_models import ReportOptions


class ReportService:
    """Build and export reports without exposing database or filesystem access."""

    def __init__(
        self,
        database_path: Path,
        fleet_online_minutes: int = 5,
        database_url: str | None = None,
    ) -> None:
        self.database_path = database_path
        self.fleet_online_minutes = fleet_online_minutes
        self.database_url = database_url

    def generate(self, request: GenerateReportRequest) -> dict[str, Any]:
        """Return privacy-safe report bytes encoded for the JSON API envelope."""
        options = ReportOptions(
            report_type=request.report_type,
            date_from=request.date_from,
            date_to=request.date_to,
            sections=tuple(dict.fromkeys(request.sections)),
            include_conversation=request.include_conversation,
            conversation_notes=tuple(request.conversation_notes),
            device_id=request.device_id,
            fleet_online_minutes=self.fleet_online_minutes,
        )
        report = build_report(options, self.database_path, self.database_url)
        exported = export_report(report, request.format)
        return {
            "report_type": report.report_type,
            "requested_format": exported.requested_format,
            "actual_format": exported.actual_format,
            "filename": exported.filename,
            "media_type": exported.media_type,
            "generated_at": report.generated_at,
            "size_bytes": len(exported.content),
            "empty": report.empty,
            "content_base64": base64.b64encode(exported.content).decode("ascii"),
            "fallback_warning": exported.fallback_warning,
        }
