"""Streamlit interface for privacy-safe in-memory diagnostic report exports."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from io import BytesIO
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from src.database import DEFAULT_DB_PATH, initialize_database
from src.fleet import FleetStore
from src.report_builder import build_report
from src.report_exporters import export_report
from src.report_models import REPORT_SECTIONS, REPORT_TITLES, ReportFormat, ReportOptions, ReportType
from src.report_ui import selected_conversation_notes, utc_date_range

TYPE_LABELS = {report_type: REPORT_TITLES[report_type] for report_type in ReportType}
FLEET_REPORT_TYPES = {
    ReportType.FLEET_SUMMARY,
    ReportType.SINGLE_DEVICE,
    ReportType.OFFLINE_DEVICES,
    ReportType.HIGH_RISK_DEVICES,
}
FORMAT_LABELS = {
    ReportFormat.CSV: "CSV - tabular data",
    ReportFormat.JSON: "JSON - structured diagnostics",
    ReportFormat.HTML: "HTML - browser-readable report",
    ReportFormat.PDF: "PDF - printable handover report",
}
SECTION_LABELS = {
    "fleet": "Fleet summary",
    "devices": "Fleet devices",
    "system": "System health",
    "network": "Network diagnostics",
    "issues": "Detected issues",
    "screenshot": "Screenshot findings",
    "assistant": "Assistant summary",
    "recommendations": "Safe recommendations",
}


st.set_page_config(page_title="Reports | FixMate AI", page_icon="📄", layout="wide")
initialize_database()

st.title("📄 Diagnostic Reports")
st.caption("Generate privacy-safe IT support handover reports from collected evidence")
st.warning(
    "Reports are generated locally and are not stored by FixMate AI. Redaction is "
    "best-effort, so preview reports before sharing them. Conversation history is "
    "excluded unless you explicitly include it below."
)

left, right = st.columns([2, 1])
with left:
    report_type = st.selectbox(
        "Report type",
        options=list(ReportType),
        format_func=lambda item: TYPE_LABELS[item],
    )
    report_format = st.selectbox(
        "Export format",
        options=list(ReportFormat),
        format_func=lambda item: FORMAT_LABELS[item],
    )
    sections = st.multiselect(
        "Include sections",
        options=list(REPORT_SECTIONS),
        default=list(REPORT_SECTIONS),
        format_func=lambda item: SECTION_LABELS[item],
    )
    selected_device_id: str | None = None
    if report_type in FLEET_REPORT_TYPES:
        store = FleetStore(DEFAULT_DB_PATH)
        fleet_devices = store.list_devices()
        if not fleet_devices:
            st.info("No endpoint fleet data is available yet. Run the endpoint agent to register a device and upload heartbeats or scans.")
        if report_type == ReportType.SINGLE_DEVICE:
            if fleet_devices:
                device_options = {
                    f"{device['display_name']} ({device['device_id']})": str(device["device_id"])
                    for device in fleet_devices
                }
                selected_label = st.selectbox("Device", list(device_options))
                selected_device_id = device_options[selected_label]
            else:
                st.warning("Single-device reports require at least one registered endpoint device.")

with right:
    use_date_range = st.checkbox("Restrict evidence by date")
    selected_dates: tuple[date, ...] | list[date] = []
    if use_date_range:
        today = datetime.now(timezone.utc).date()
        selected_dates = st.date_input(
            "Evidence date range (UTC)",
            value=(today - timedelta(days=30), today),
            max_value=today,
        )
    include_conversation = st.checkbox(
        "Include current assistant conversation",
        disabled="assistant" not in sections,
        help="Only minimized text from this Streamlit session is included; it is never stored in SQLite.",
    )

if "phase7_export" not in st.session_state:
    st.session_state.phase7_export = None

if st.button("Generate report", type="primary", disabled=not sections):
    date_from, date_to = utc_date_range(list(selected_dates)) if use_date_range else (None, None)
    messages = st.session_state.get("assistant_messages", [])
    notes = selected_conversation_notes(messages) if include_conversation else ()
    options = ReportOptions(
        report_type=report_type,
        date_from=date_from,
        date_to=date_to,
        sections=tuple(sections),
        include_conversation=include_conversation,
        conversation_notes=notes,
        device_id=selected_device_id,
    )
    report = build_report(options, DEFAULT_DB_PATH)
    exported = export_report(report, report_format)
    st.session_state.phase7_export = {"report": report, "exported": exported}

result = st.session_state.phase7_export
if result is None:
    st.info("Choose a report scope and select **Generate report** to create a preview.")
else:
    report = result["report"]
    exported = result["exported"]
    if report.empty:
        st.info(
            "No diagnostic evidence matched this report type and date range. The export "
            "still contains the privacy notice, limitations, and empty-state explanation."
        )
    if exported.fallback_warning:
        st.warning(exported.fallback_warning)

    st.subheader("Preview")
    st.caption(
        f"{report.title} · generated {report.generated_at.isoformat()} · "
        f"{len(exported.content):,} bytes"
    )
    if exported.actual_format == ReportFormat.HTML:
        components.html(exported.content.decode("utf-8"), height=650, scrolling=True)
    elif exported.actual_format == ReportFormat.JSON:
        st.json(exported.content.decode("utf-8"), expanded=False)
    elif exported.actual_format == ReportFormat.CSV:
        st.dataframe(pd.read_csv(BytesIO(exported.content)), width="stretch")
    else:
        st.success("PDF generated successfully. Use the download button to review the printable report.")

    st.download_button(
        "Download report",
        data=exported.content,
        file_name=exported.filename,
        mime=exported.media_type,
        type="primary",
    )
    st.caption(
        "The generated bytes are held only in this Streamlit session. FixMate AI does not "
        "write the report to its database or project directory."
    )
