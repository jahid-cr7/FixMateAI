"""In-memory CSV, JSON, HTML, and PDF exporters for diagnostic reports."""

from __future__ import annotations

import csv
import html
import json
import re
from datetime import datetime, timezone
from io import BytesIO, StringIO
from typing import Any, Callable

from src.report_models import DiagnosticReport, ExportedReport, ReportFormat, ReportType
from src.report_privacy import sanitize_report

MEDIA_TYPES = {
    ReportFormat.CSV: "text/csv; charset=utf-8",
    ReportFormat.JSON: "application/json",
    ReportFormat.HTML: "text/html; charset=utf-8",
    ReportFormat.PDF: "application/pdf",
}
SAFE_COMPONENT = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


class PdfGenerationError(RuntimeError):
    """Raised when the optional local PDF renderer cannot produce a document."""


def make_safe_filename(
    report_type: ReportType | str,
    report_format: ReportFormat | str,
    generated_at: datetime,
) -> str:
    """Create a timestamped filename while rejecting path-like components."""
    try:
        type_value = ReportType(report_type).value
        format_value = ReportFormat(report_format).value
    except ValueError as error:
        raise ValueError("Unsupported report type or format") from error
    if not SAFE_COMPONENT.fullmatch(type_value) or not SAFE_COMPONENT.fullmatch(format_value):
        raise ValueError("Unsafe report filename component")
    stamp = generated_at.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"fixmate-{type_value}-{stamp}.{format_value}"


def _json_default(value: Any) -> str:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(value, ReportType):
        return value.value
    raise TypeError(f"Unsupported report value: {type(value).__name__}")


def _display(value: Any) -> str:
    if value is None:
        return "Unavailable"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, default=_json_default, ensure_ascii=True, sort_keys=True)
    return str(value)


def report_rows(report: DiagnosticReport) -> list[dict[str, str]]:
    """Flatten report evidence into consistent tabular rows for CSV and PDF."""
    rows: list[dict[str, str]] = []

    def add(section: str, metric: str, value: Any, timestamp: Any = None, severity: Any = None, recommendation: Any = None) -> None:
        rows.append(
            {
                "section": section,
                "metric": metric,
                "value": _display(value),
                "evidence_timestamp": _display(timestamp) if timestamp else "",
                "severity": _display(severity) if severity else "",
                "recommendation": _display(recommendation) if recommendation else "",
            }
        )

    for key, value in report.device_summary.items():
        if key != "evidence_timestamp":
            add("device", key, value, report.device_summary.get("evidence_timestamp"))
    for section_name, payload in (("system", report.system), ("network", report.network), ("screenshot", report.screenshot)):
        if payload:
            evidence_time = payload.get("evidence_timestamp") or payload.get("collected_at") or payload.get("analyzed_at")
            for key, value in payload.items():
                if key not in {"issues", "evidence_timestamp", "collected_at", "analyzed_at"}:
                    add(section_name, key, value, evidence_time, payload.get("severity"))
    for issue in report.issues:
        add(
            "issues",
            str(issue.get("code") or "detected_issue"),
            issue.get("explanation") or issue.get("evidence"),
            issue.get("timestamp") or issue.get("detected_at"),
            issue.get("severity"),
            issue.get("recommendation"),
        )
    if report.assistant:
        add(
            "assistant",
            "health_summary",
            report.assistant.get("direct_answer"),
            report.assistant.get("evidence_timestamp"),
            report.assistant.get("severity"),
            report.assistant.get("guidance"),
        )
        if "explicitly_selected_conversation_notes" in report.assistant:
            add("assistant", "selected_conversation_notes", report.assistant["explicitly_selected_conversation_notes"])
    for severity, count in sorted(report.severity_summary.items()):
        add("severity_summary", severity, count)
    for index, recommendation in enumerate(report.recommendations, start=1):
        add("recommendations", f"guidance_{index}", recommendation)
    for index, limitation in enumerate(report.limitations, start=1):
        add("limitations", f"limitation_{index}", limitation)
    add("privacy", "notice", report.privacy_notice)
    return rows


def export_csv(report: DiagnosticReport) -> bytes:
    """Export all selected report data as UTF-8 CSV bytes."""
    output = StringIO(newline="")
    columns = ("section", "metric", "value", "evidence_timestamp", "severity", "recommendation")
    writer = csv.DictWriter(output, fieldnames=columns)
    writer.writeheader()
    writer.writerows(report_rows(sanitize_report(report)))
    return output.getvalue().encode("utf-8-sig")


def export_json(report: DiagnosticReport) -> bytes:
    """Export a structured, redacted JSON report."""
    safe = sanitize_report(report)
    return json.dumps(safe.to_dict(), default=_json_default, indent=2, ensure_ascii=True).encode("utf-8")


def export_html(report: DiagnosticReport) -> bytes:
    """Export a standalone, readable HTML report without external assets."""
    safe = sanitize_report(report)
    generated = _display(safe.generated_at)
    range_text = f"{_display(safe.date_from)} to {_display(safe.date_to)}" if safe.date_from or safe.date_to else "All available dates"
    rows = report_rows(safe)
    table_rows = "".join(
        "<tr>" + "".join(f"<td>{html.escape(row[column])}</td>" for column in ("section", "metric", "value", "evidence_timestamp", "severity", "recommendation")) + "</tr>"
        for row in rows
    )
    empty_notice = '<div class="empty">No diagnostic evidence matched this report scope.</div>' if safe.empty else ""
    document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(safe.title)}</title>
<style>
body{{font-family:Arial,sans-serif;color:#172033;background:#f3f6fa;margin:0;padding:32px}}main{{max-width:1100px;margin:auto;background:white;padding:36px;border-radius:12px;box-shadow:0 5px 24px #17203318}}h1{{color:#0b5cab;margin:0 0 8px}}.meta{{color:#5a677a;margin-bottom:24px}}.notice,.empty{{padding:14px;border-radius:8px;margin:18px 0}}.notice{{background:#eef6ff;border-left:4px solid #0b5cab}}.empty{{background:#fff6e5;border-left:4px solid #b36b00}}table{{border-collapse:collapse;width:100%;font-size:13px}}th{{background:#153a64;color:white;text-align:left}}th,td{{padding:9px;border:1px solid #d8e0ea;vertical-align:top;overflow-wrap:anywhere}}tr:nth-child(even){{background:#f7f9fc}}footer{{margin-top:24px;color:#667085;font-size:12px}}
</style></head><body><main><h1>{html.escape(safe.title)}</h1>
<div class="meta">Generated {html.escape(generated)} UTC | Evidence range: {html.escape(range_text)}</div>
{empty_notice}<div class="notice"><strong>Privacy notice:</strong> {html.escape(safe.privacy_notice)}</div>
<h2>Diagnostic evidence</h2><table><thead><tr><th>Section</th><th>Metric</th><th>Value</th><th>Evidence timestamp</th><th>Severity</th><th>Safe recommendation</th></tr></thead><tbody>{table_rows}</tbody></table>
<footer>Generated locally by FixMate AI. Review redaction and evidence freshness before sharing.</footer>
</main></body></html>"""
    return document.encode("utf-8")


def _pdf_ascii(value: Any) -> str:
    """Use predictable built-in PDF fonts without broken Unicode glyphs."""
    return _display(value).encode("ascii", "replace").decode("ascii")


def _export_pdf(report: DiagnosticReport) -> bytes:
    """Generate a polished PDF entirely in memory using ReportLab."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError as error:
        raise PdfGenerationError("ReportLab is not installed") from error

    safe = sanitize_report(report)
    buffer = BytesIO()
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="ReportTitle", parent=styles["Title"], textColor=colors.HexColor("#0B5CAB"), fontSize=20, leading=24, spaceAfter=8))
    styles.add(ParagraphStyle(name="Small", parent=styles["BodyText"], fontSize=8, leading=10))
    styles.add(ParagraphStyle(name="TableHeader", parent=styles["Small"], textColor=colors.white, fontName="Helvetica-Bold"))
    styles.add(ParagraphStyle(name="Privacy", parent=styles["BodyText"], backColor=colors.HexColor("#EEF6FF"), borderColor=colors.HexColor("#0B5CAB"), borderWidth=1, borderPadding=8, fontSize=9, leading=12))
    story: list[Any] = [
        Paragraph(html.escape(_pdf_ascii(safe.title)), styles["ReportTitle"]),
        Paragraph(f"Generated: {html.escape(_pdf_ascii(safe.generated_at))} UTC", styles["Small"]),
        Spacer(1, 5 * mm),
        Paragraph(f"<b>Privacy notice:</b> {html.escape(_pdf_ascii(safe.privacy_notice))}", styles["Privacy"]),
        Spacer(1, 5 * mm),
    ]
    if safe.empty:
        story.extend([Paragraph("No diagnostic evidence matched this report scope.", styles["Heading2"]), Spacer(1, 3 * mm)])
    headers = ["Section", "Metric", "Value", "Timestamp", "Severity", "Recommendation"]
    data: list[list[Any]] = [[Paragraph(item, styles["TableHeader"]) for item in headers]]
    for row in report_rows(safe):
        data.append(
            [
                Paragraph(html.escape(_pdf_ascii(row[column])), styles["Small"])
                for column in ("section", "metric", "value", "evidence_timestamp", "severity", "recommendation")
            ]
        )
    table = Table(data, repeatRows=1, colWidths=[24 * mm, 28 * mm, 61 * mm, 35 * mm, 20 * mm, 75 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#153A64")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#C5D0DC")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F9FC")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(table)

    def page_footer(canvas: Any, document: Any) -> None:
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#667085"))
        canvas.drawString(14 * mm, 8 * mm, "FixMate AI - privacy-safe diagnostic report")
        canvas.drawRightString(283 * mm, 8 * mm, f"Page {document.page}")
        canvas.restoreState()

    document = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=12 * mm,
        leftMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=14 * mm,
        title=_pdf_ascii(safe.title),
        author="FixMate AI",
    )
    try:
        document.build(story, onFirstPage=page_footer, onLaterPages=page_footer)
    except Exception as error:
        raise PdfGenerationError("Local PDF generation failed") from error
    return buffer.getvalue()


def export_report(
    report: DiagnosticReport,
    requested_format: ReportFormat,
    pdf_renderer: Callable[[DiagnosticReport], bytes] | None = None,
) -> ExportedReport:
    """Export in memory, falling back from PDF to HTML without writing files."""
    safe = sanitize_report(report)
    actual_format = requested_format
    warning: str | None = None
    if requested_format == ReportFormat.CSV:
        content = export_csv(safe)
    elif requested_format == ReportFormat.JSON:
        content = export_json(safe)
    elif requested_format == ReportFormat.HTML:
        content = export_html(safe)
    else:
        try:
            content = (pdf_renderer or _export_pdf)(safe)
            if not content.startswith(b"%PDF-"):
                raise PdfGenerationError("Renderer returned invalid PDF data")
        except Exception:
            actual_format = ReportFormat.HTML
            content = export_html(safe)
            warning = "PDF generation was unavailable; a privacy-safe HTML report was generated instead."
    return ExportedReport(
        requested_format=requested_format,
        actual_format=actual_format,
        filename=make_safe_filename(safe.report_type, actual_format, safe.generated_at),
        media_type=MEDIA_TYPES[actual_format],
        content=content,
        fallback_warning=warning,
    )
