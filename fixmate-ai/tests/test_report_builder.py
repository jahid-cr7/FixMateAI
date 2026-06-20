"""Tests for deterministic privacy-safe report assembly."""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from src.database import initialize_database
from src.report_builder import build_report
from src.report_models import REPORT_SECTIONS, ReportOptions, ReportType
from src.report_ui import selected_conversation_notes, utc_date_range
from tests.api.conftest import populate_api_database


@pytest.mark.parametrize("report_type", list(ReportType))
def test_every_report_type_builds(report_type: ReportType, tmp_path) -> None:
    """All five report scopes should build from the same temporary evidence."""
    database_path = tmp_path / "reports.db"
    populate_api_database(database_path)
    report = build_report(
        ReportOptions(report_type=report_type),
        database_path,
        datetime(2026, 6, 20, 4, tzinfo=timezone.utc),
    )
    assert report.report_type == report_type
    assert report.generated_at.tzinfo == timezone.utc
    assert report.privacy_notice
    assert report.limitations
    assert report.empty is False


def test_report_type_limits_unrelated_sections(tmp_path) -> None:
    """Focused reports should not silently include unrelated evidence categories."""
    database_path = tmp_path / "scope.db"
    populate_api_database(database_path)
    system = build_report(ReportOptions(ReportType.SYSTEM_HEALTH), database_path)
    network = build_report(ReportOptions(ReportType.NETWORK_DIAGNOSTICS), database_path)
    screenshot = build_report(ReportOptions(ReportType.SCREENSHOT_ANALYSIS), database_path)
    assert system.system and not system.network and not system.screenshot
    assert all(issue["source"] == "system" for issue in system.issues)
    assert network.network and not network.system and not network.screenshot
    assert all(issue["source"] == "network" for issue in network.issues)
    assert screenshot.screenshot and screenshot.issues == []


def test_empty_database_and_date_range_have_clear_empty_state(tmp_path) -> None:
    """No data and out-of-range data should never crash or invent evidence."""
    empty_path = tmp_path / "empty.db"
    initialize_database(empty_path)
    empty = build_report(ReportOptions(ReportType.FULL_DIAGNOSTIC), empty_path)
    assert empty.empty is True
    assert empty.system is None
    assert empty.network is None
    assert empty.screenshot is None

    populated = tmp_path / "populated.db"
    populate_api_database(populated)
    future = build_report(
        ReportOptions(
            ReportType.FULL_DIAGNOSTIC,
            date_from=datetime(2030, 1, 1, tzinfo=timezone.utc),
            date_to=datetime(2030, 1, 2, tzinfo=timezone.utc),
        ),
        populated,
    )
    assert future.empty is True


def test_report_redacts_private_values_and_omits_ocr(tmp_path) -> None:
    """Every report boundary should redact paths, addresses, accounts, and secrets."""
    database_path = tmp_path / "privacy.db"
    populate_api_database(database_path)
    report = build_report(
        ReportOptions(
            ReportType.FULL_DIAGNOSTIC,
            include_conversation=True,
            conversation_notes=(
                "username=Alice token=super-secret alice@example.com 203.0.113.7 C:\\Users\\Alice\\note.txt",
            ),
        ),
        database_path,
    )
    serialized = str(report.to_dict())
    for private in ("Alice", "super-secret", "alice@example.com", "203.0.113.7", "C:\\Users"):
        assert private not in serialized
    assert "extracted_text_redacted" not in serialized
    assert "anonymized_filename" not in serialized
    assert "[REDACTED" in serialized


def test_sections_and_conversation_are_explicit(tmp_path) -> None:
    """Excluded sections and unselected chat history must remain absent."""
    database_path = tmp_path / "sections.db"
    populate_api_database(database_path)
    options = ReportOptions(
        ReportType.FULL_DIAGNOSTIC,
        sections=("system",),
        include_conversation=False,
        conversation_notes=("must not appear",),
    )
    report = build_report(options, database_path)
    assert report.system
    assert report.network is None
    assert report.assistant is None
    assert "must not appear" not in str(report.to_dict())


def test_streamlit_report_helpers_redact_and_normalize_dates() -> None:
    """UI helper inputs should be minimized before reaching report generation."""
    notes = selected_conversation_notes(
        [{"role": "user", "content": "token=secret alice@example.com"}]
    )
    assert "secret" not in notes[0]
    assert "alice@example.com" not in notes[0]
    start, end = utc_date_range([date(2026, 6, 1), date(2026, 6, 2)])
    assert start == datetime(2026, 6, 1, tzinfo=timezone.utc)
    assert end and end.date() == date(2026, 6, 2)
    assert utc_date_range([date(2026, 6, 1)]) == (None, None)


def test_invalid_date_range_is_rejected(tmp_path) -> None:
    with pytest.raises(ValueError, match="date_from"):
        build_report(
            ReportOptions(
                ReportType.SYSTEM_HEALTH,
                date_from=datetime(2026, 6, 2, tzinfo=timezone.utc),
                date_to=datetime(2026, 6, 1, tzinfo=timezone.utc),
                sections=REPORT_SECTIONS,
            ),
            tmp_path / "unused.db",
        )

