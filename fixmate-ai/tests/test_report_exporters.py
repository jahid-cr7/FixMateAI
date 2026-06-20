"""Tests for all in-memory report export formats."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from io import BytesIO, StringIO

import pytest
from pypdf import PdfReader

from src.report_builder import build_report
from src.report_exporters import export_report, make_safe_filename
from src.report_models import ReportFormat, ReportOptions, ReportType
from tests.api.conftest import populate_api_database


@pytest.fixture
def full_report(tmp_path):
    database_path = tmp_path / "export.db"
    populate_api_database(database_path)
    return build_report(
        ReportOptions(ReportType.FULL_DIAGNOSTIC),
        database_path,
        datetime(2026, 6, 20, 5, 6, 7, tzinfo=timezone.utc),
    )


@pytest.mark.parametrize("report_format", list(ReportFormat))
def test_every_export_format(report_format: ReportFormat, full_report) -> None:
    exported = export_report(full_report, report_format)
    assert exported.actual_format == report_format
    assert exported.content
    assert exported.filename.endswith(f".{report_format.value}")
    if report_format == ReportFormat.PDF:
        assert exported.content.startswith(b"%PDF-")
        reader = PdfReader(BytesIO(exported.content))
        assert len(reader.pages) >= 1
        assert "Full Diagnostic Bundle Report" in (reader.pages[0].extract_text() or "")


def test_csv_json_and_html_are_parseable_and_private(full_report) -> None:
    csv_export = export_report(full_report, ReportFormat.CSV)
    rows = list(csv.DictReader(StringIO(csv_export.content.decode("utf-8-sig"))))
    assert rows and {"section", "metric", "value"} <= set(rows[0])

    json_export = export_report(full_report, ReportFormat.JSON)
    parsed = json.loads(json_export.content)
    assert parsed["report_type"] == "full_diagnostic"

    html_export = export_report(full_report, ReportFormat.HTML)
    assert b"<!doctype html>" in html_export.content
    assert b"<script" not in html_export.content.lower()

    combined = csv_export.content + json_export.content + html_export.content
    assert b"203.0.113.10" not in combined
    assert b"AA:BB:CC:DD:EE:FF" not in combined
    assert b"alice@example.com" not in combined
    assert b"C:\\Users\\Alice" not in combined


def test_safe_filename_is_timestamped_and_rejects_traversal() -> None:
    timestamp = datetime(2026, 6, 20, 5, 6, 7, tzinfo=timezone.utc)
    filename = make_safe_filename(ReportType.SYSTEM_HEALTH, ReportFormat.PDF, timestamp)
    assert filename == "fixmate-system_health-20260620T050607Z.pdf"
    assert "/" not in filename and "\\" not in filename and ".." not in filename
    with pytest.raises(ValueError):
        make_safe_filename("../../private", ReportFormat.JSON, timestamp)
    with pytest.raises(ValueError):
        make_safe_filename(ReportType.SYSTEM_HEALTH, "../pdf", timestamp)


def test_pdf_failure_falls_back_to_html(full_report) -> None:
    def failed_renderer(_report):
        raise RuntimeError("renderer internals must not escape")

    exported = export_report(full_report, ReportFormat.PDF, pdf_renderer=failed_renderer)
    assert exported.requested_format == ReportFormat.PDF
    assert exported.actual_format == ReportFormat.HTML
    assert exported.filename.endswith(".html")
    assert b"<!doctype html>" in exported.content
    assert "renderer internals" not in (exported.fallback_warning or "")
