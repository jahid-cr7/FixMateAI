"""Streamlit dashboard for FixMate AI system and network health."""

from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

from src.collector import collect_system_metrics
from src.dashboard_auth import DashboardUser, authenticate, is_auth_enabled, load_dashboard_auth
from src.database import (
    get_network_history,
    get_scan_history,
    initialize_database,
    save_network_diagnostic,
    save_scan,
)
from src.detector import Issue, detect_issues
from src.health_score import calculate_health_score
from src.network_collector import NetworkDiagnostic, collect_network_diagnostic
from src.network_detector import NetworkIssue, detect_network_issues


def _format_percent(value: float | None) -> str:
    """Format an optional percentage for display."""
    return "Unavailable" if value is None else f"{value:.1f}%"


def _format_bytes(value: int | None) -> str:
    """Format an optional byte counter with a readable unit."""
    if value is None:
        return "Unavailable"
    units = ("B", "KB", "MB", "GB", "TB")
    amount = float(value)
    for unit in units:
        if amount < 1024 or unit == units[-1]:
            return f"{amount:.1f} {unit}"
        amount /= 1024
    return f"{value} B"


def _run_scan() -> tuple[dict[str, Any], list[Issue], int]:
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


def _run_network_diagnostic(
    host: str,
    port: int,
    timeout_seconds: float,
    latency_threshold_ms: float,
) -> tuple[NetworkDiagnostic, list[NetworkIssue]]:
    """Collect, evaluate, and persist one network diagnostic."""
    diagnostic = collect_network_diagnostic(
        host=host,
        port=port,
        timeout_seconds=timeout_seconds,
        latency_threshold_ms=latency_threshold_ms,
    )
    issues = detect_network_issues(diagnostic)
    save_network_diagnostic(diagnostic, issues)
    return diagnostic, issues


def _render_system_health(
    scan: dict[str, Any],
    issues: list[Issue],
    score: int,
) -> None:
    """Render the Phase 1 system-health dashboard."""
    if st.button("Run new scan", type="primary"):
        with st.spinner("Collecting system metrics..."):
            st.session_state.latest_result = _run_scan()
        scan, issues, score = st.session_state.latest_result
        st.success("System scan completed and saved.")

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
            with st.expander(
                f"{issue['severity'].upper()}: {issue['metric']}",
                expanded=True,
            ):
                st.write(issue["explanation"])
                st.markdown(f"**Safe recommendation:** {issue['recommendation']}")

    st.subheader("History")
    history = pd.DataFrame(get_scan_history())
    if history.empty:
        st.info("Historical charts will appear after a scan is saved.")
        return

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


def _render_network_diagnostics() -> None:
    """Render configuration, current results, issues, and network history."""
    st.subheader("Network Diagnostics")
    st.caption(
        "This read-only check uses one short TCP connection. It does not scan ports, "
        "capture packets, expose MAC addresses, or change network settings."
    )

    config_columns = st.columns(4)
    host = config_columns[0].text_input("Connectivity host", value="1.1.1.1")
    port = config_columns[1].number_input(
        "Port", min_value=1, max_value=65535, value=443, step=1
    )
    timeout_seconds = config_columns[2].number_input(
        "Timeout (seconds)",
        min_value=0.1,
        max_value=5.0,
        value=1.5,
        step=0.1,
    )
    latency_threshold_ms = config_columns[3].number_input(
        "High latency threshold (ms)",
        min_value=1.0,
        max_value=5000.0,
        value=150.0,
        step=10.0,
    )

    if st.button("Run new diagnostic", type="primary"):
        with st.spinner("Running a short network diagnostic..."):
            st.session_state.latest_network_result = _run_network_diagnostic(
                host,
                int(port),
                float(timeout_seconds),
                float(latency_threshold_ms),
            )
        st.success("Network diagnostic completed and saved.")

    latest = st.session_state.get("latest_network_result")
    if latest is None:
        st.info("Run a diagnostic to collect the current network status.")
    else:
        diagnostic, issues = latest
        status_columns = st.columns(4)
        status_columns[0].metric(
            "Connection status",
            "Connected" if diagnostic["connection_status"] else "Disconnected",
        )
        status_columns[1].metric(
            "Internet connectivity",
            "Online" if diagnostic["internet_connected"] else "Offline",
        )
        status_columns[2].metric(
            "Latency",
            (
                f"{diagnostic['latency_ms']:.2f} ms"
                if diagnostic["latency_ms"] is not None
                else "Unavailable"
            ),
        )
        status_columns[3].metric(
            "Active interfaces", str(len(diagnostic["active_interfaces"]))
        )

        traffic_columns = st.columns(2)
        traffic_columns[0].metric("Bytes sent", _format_bytes(diagnostic["bytes_sent"]))
        traffic_columns[1].metric(
            "Bytes received", _format_bytes(diagnostic["bytes_received"])
        )
        interfaces = diagnostic["active_interfaces"]
        st.markdown(
            "**Active interface names:** "
            + (", ".join(interfaces) if interfaces else "None detected")
        )

        st.subheader("Network issues")
        if not issues:
            st.success("No network issues were detected by the configured rules.")
        for issue in issues:
            with st.expander(
                f"{issue['severity'].upper()}: {issue['code'].replace('_', ' ').title()}",
                expanded=True,
            ):
                st.markdown(f"**Evidence:** {issue['evidence']}")
                st.write(issue["explanation"])
                st.markdown(f"**Safe recommendation:** {issue['recommendation']}")
                st.caption(f"Detected at {issue['detected_at']}")

    st.subheader("Network history")
    history = pd.DataFrame(get_network_history())
    if history.empty:
        st.info("Network history charts will appear after a diagnostic is saved.")
        return

    history["collected_at"] = pd.to_datetime(history["collected_at"])
    latency_history = history.dropna(subset=["latency_ms"])
    if latency_history.empty:
        st.info("No successful latency measurements are available yet.")
    else:
        latency_chart = px.line(
            latency_history,
            x="collected_at",
            y="latency_ms",
            markers=True,
            labels={"collected_at": "Diagnostic time", "latency_ms": "Latency (ms)"},
            title="Latency history",
        )
        st.plotly_chart(latency_chart, width="stretch")

    usage = history[["collected_at", "bytes_sent", "bytes_received"]].copy()
    usage["Sent (MB)"] = pd.to_numeric(
        usage["bytes_sent"], errors="coerce"
    ) / (1024 * 1024)
    usage["Received (MB)"] = pd.to_numeric(
        usage["bytes_received"], errors="coerce"
    ) / (1024 * 1024)
    usage = usage.melt(
        id_vars="collected_at",
        value_vars=["Sent (MB)", "Received (MB)"],
        var_name="Traffic",
        value_name="Cumulative MB",
    )
    usage_chart = px.line(
        usage,
        x="collected_at",
        y="Cumulative MB",
        color="Traffic",
        markers=True,
        labels={"collected_at": "Diagnostic time"},
        title="Network usage counters",
    )
    st.plotly_chart(usage_chart, width="stretch")


st.set_page_config(page_title="FixMate AI", page_icon="🛠️", layout="wide")
initialize_database()

_auth_config = load_dashboard_auth()

if "dashboard_user" not in st.session_state:
    st.session_state.dashboard_user = None

if _auth_config.enabled and st.session_state.dashboard_user is None:
    st.title("🛠️ FixMate AI")
    st.caption("Dashboard authentication is enabled")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log in")
        if submitted:
            user = authenticate(_auth_config, username, password)
            if user is not None:
                st.session_state.dashboard_user = user
                st.rerun()
            else:
                st.error("Invalid username or password.")
    st.stop()

_dashboard_user: DashboardUser | None = st.session_state.dashboard_user

if _dashboard_user is not None:
    with st.sidebar:
        st.write(f"**Role:** {_dashboard_user.role.title()}")
        st.write(f"**User:** {_dashboard_user.username}")
        if st.button("Log out"):
            st.session_state.dashboard_user = None
            st.rerun()

st.title("🛠️ FixMate AI")
st.caption("Read-only system and network health checks for Windows and Ubuntu")

if "latest_result" not in st.session_state:
    with st.spinner("Running the first system scan..."):
        st.session_state.latest_result = _run_scan()

system_scan, system_issues, health_score = st.session_state.latest_result
system_tab, network_tab = st.tabs(["System Health", "Network Diagnostics"])

with system_tab:
    _render_system_health(system_scan, system_issues, health_score)

with network_tab:
    _render_network_diagnostics()

st.caption(
    "FixMate AI collects basic performance and network counters only. It does not "
    "inspect file contents or browsing history, capture packets, scan ports, expose "
    "complete MAC addresses, terminate processes, or change system settings."
)
