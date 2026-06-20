"""Pydantic contracts for report discovery and in-memory generation."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.report_models import REPORT_SECTIONS, REPORT_TITLES, ReportFormat, ReportType


class ReportTypeInfo(BaseModel):
    """One supported report type and its human-readable title."""

    id: ReportType
    title: str
    formats: list[ReportFormat]


class ReportTypesResult(BaseModel):
    """Available report types, formats, and optional sections."""

    types: list[ReportTypeInfo]
    sections: list[str]


class GenerateReportRequest(BaseModel):
    """Bounded report request with no destination path or arbitrary filename."""

    report_type: ReportType
    format: ReportFormat
    date_from: datetime | None = None
    date_to: datetime | None = None
    sections: list[str] = Field(default_factory=lambda: list(REPORT_SECTIONS), max_length=6)
    include_conversation: bool = False
    conversation_notes: list[str] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def validate_scope(self) -> "GenerateReportRequest":
        """Reject invalid ranges, unknown sections, and implicit conversations."""
        if self.date_from and self.date_to:
            start = self.date_from
            end = self.date_to
            if start.tzinfo is None:
                start = start.replace(tzinfo=timezone.utc)
            if end.tzinfo is None:
                end = end.replace(tzinfo=timezone.utc)
            if start.astimezone(timezone.utc) > end.astimezone(timezone.utc):
                raise ValueError("date_from must not be later than date_to")
        if not self.sections or any(section not in REPORT_SECTIONS for section in self.sections):
            raise ValueError("sections must contain supported report sections")
        if self.conversation_notes and not self.include_conversation:
            raise ValueError("conversation_notes require include_conversation=true")
        if any(len(note) > 2000 for note in self.conversation_notes):
            raise ValueError("conversation notes must be 2000 characters or fewer")
        return self

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "report_type": "full_diagnostic",
                    "format": "pdf",
                    "sections": list(REPORT_SECTIONS),
                    "include_conversation": False,
                }
            ]
        }
    )


class GeneratedReportResult(BaseModel):
    """Download metadata and base64 report bytes returned without persistence."""

    report_type: ReportType
    requested_format: ReportFormat
    actual_format: ReportFormat
    filename: str
    media_type: str
    generated_at: datetime
    size_bytes: int = Field(ge=0)
    empty: bool
    content_base64: str
    fallback_warning: str | None = None


def report_types_result() -> ReportTypesResult:
    """Build the deterministic report discovery response."""
    formats = list(ReportFormat)
    return ReportTypesResult(
        types=[
            ReportTypeInfo(id=report_type, title=REPORT_TITLES[report_type], formats=formats)
            for report_type in ReportType
        ],
        sections=list(REPORT_SECTIONS),
    )
