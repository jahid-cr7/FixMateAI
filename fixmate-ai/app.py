"""Streamlit dashboard for the FixMate AI MVP."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from src.collector import collect_system_metrics
from src.database import get_scan_history, initialize_database, save_scan
from src.detector import Issue, detect_issues
from src.health_score import calculate_health_score


def _format_percent(value: float | None) -> str:
    """Format an optional percentage for display."""
    return "Unavailable" if value is None else f"{value:.1f}%"


def _run_scan() -> tuple[dict[str, object], list[Issue], int]:
    """Collect, evaluate, and persist one system scan."""
    scan = collect_system_metrics()
    issues = detect_issues(
        scan.get("cpu_percent"),
        scan.get("memory_percent"),
        scan.get("disk_free_percent"),
    )
    score = calculate_health_score(issues)
    save_scan(scan, issues, score)
    return scan, issues, score


st.set_page_config(page_title="FixMate AI", page_icon="🛠️", layout="wide")
initialize_database()

st.title("🛠️ FixMate AI")
st.caption("Read-only system health checks for Windows and Ubuntu")

if "latest_result" not in st.session_state:
    with st.spinner("Running the first system scan..."):
        st.session_state.latest_result = _run_scan()

if st.button("Run new scan", type="primary"):
    with st.spinner("Collecting system metrics..."):
        st.session_state.latest_result = _run_scan()
    st.success("System scan completed and saved.")

scan, issues, score = st.session_state.latest_result

st.subheader("System information")
info_columns = st.columns(4)
info_columns[0].metric("Operating system", f"{scan['os_name']} {scan['os_release']}")
info_columns[1].metric("Architecture", str(scan["architecture"]))
info_columns[2].metric("Boot time", str(scan.get("boot_time") or "Unavailable"))
info_columns[3].metric("Health score", f"{score}/100")

st.subheader("Current metrics")
metric_columns = st.columns(3)
metric_columns[0].metric("CPU usage", _format_percent(scan.get("cpu_percent")))
metric_columns[1].metric("Memory usage", _format_percent(scan.get("memory_percent")))
metric_columns[2].metric("Disk usage", _format_percent(scan.get("disk_used_percent")))

left, right = st.columns([1, 1])
with left:
    st.subheader("Top processes by memory")
    processes = pd.DataFrame(scan.get("top_processes", []))
    if processes.empty:
        st.info("Process metrics are unavailable on this system.")
    else:
        st.dataframe(processes, hide_index=True, width="stretch")

with right:
    st.subheader("Detected issues")
    if not issues:
        st.success("No threshold-based issues were detected.")
    for issue in issues:
        with st.expander(f"{issue['severity'].upper()}: {issue['metric']}", expanded=True):
            st.write(issue["explanation"])
            st.markdown(f"**Safe recommendation:** {issue['recommendation']}")

st.subheader("History")
history = pd.DataFrame(get_scan_history())
if history.empty:
    st.info("Historical charts will appear after a scan is saved.")
else:
    history["collected_at"] = pd.to_datetime(history["collected_at"])
    percentages = history.melt(
        id_vars="collected_at",
        value_vars=["cpu_percent", "memory_percent", "disk_used_percent"],
        var_name="Metric",
        value_name="Percent",
    )
    percentages["Metric"] = percentages["Metric"].map(
        {
            "cpu_percent": "CPU usage",
            "memory_percent": "Memory usage",
            "disk_used_percent": "Disk usage",
        }
    )
    chart = px.line(
        percentages,
        x="collected_at",
        y="Percent",
        color="Metric",
        markers=True,
        labels={"collected_at": "Scan time"},
        range_y=[0, 100],
    )
    st.plotly_chart(chart, width="stretch")

    score_chart = px.line(
        history,
        x="collected_at",
        y="health_score",
        markers=True,
        labels={"collected_at": "Scan time", "health_score": "Health score"},
        range_y=[0, 100],
    )
    st.plotly_chart(score_chart, width="stretch")

st.caption(
    "FixMate AI reads basic performance counters only. It does not inspect file contents, "
    "collect personal data, terminate processes, or change system settings."
)
