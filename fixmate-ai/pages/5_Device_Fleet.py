"""Streamlit fleet overview for registered one-shot endpoint agents."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.database import DEFAULT_DB_PATH
from src.fleet import FleetStore
from src.fleet_status import filter_devices, fleet_summary

st.set_page_config(page_title="Device Fleet | FixMate AI", page_icon="🖥️", layout="wide")

store = FleetStore(DEFAULT_DB_PATH)
devices = store.list_devices()
summary = fleet_summary(devices)

st.title("🖥️ Device Fleet")
st.caption("Read-only status from registered one-shot FixMate AI endpoint agents")
st.info(
    "Fleet status reflects uploaded heartbeats and scan batches. FixMate AI does not "
    "run repairs, background services, notifications, or remote commands."
)

columns = st.columns(5)
columns[0].metric("Total devices", summary["total"])
columns[1].metric("Online", summary["online"])
columns[2].metric("Offline", summary["offline"])
columns[3].metric("Unknown", summary["unknown"])
columns[4].metric("High risk", summary["high_risk"])

if not devices:
    st.info(
        "No endpoint devices are registered yet. Run `python -m fixmate_agent "
        "--server http://127.0.0.1:8000 --dry-run` to inspect a safe payload, then "
        "configure a device token and run a one-shot upload."
    )
    st.stop()

st.subheader("Fleet filters")
filter_columns = st.columns(3)
operating_systems = sorted(
    {str(item["operating_system"]) for item in devices}, key=str.casefold
)
severities = sorted(
    {str(item.get("highest_severity") or "none") for item in devices},
    key=str.casefold,
)
with filter_columns[0]:
    os_filter = st.selectbox("Operating system", ["All", *operating_systems])
with filter_columns[1]:
    status_filter = st.selectbox("Status", ["All", "online", "offline", "unknown"])
with filter_columns[2]:
    severity_filter = st.selectbox("Latest severity", ["All", *severities])

filtered = filter_devices(
    devices,
    None if os_filter == "All" else os_filter,
    None if status_filter == "All" else status_filter,
    None if severity_filter == "All" else severity_filter,
)

st.subheader("Devices")
if not filtered:
    st.info("No devices match the selected filters.")
    st.stop()

table = pd.DataFrame(filtered).rename(
    columns={
        "display_name": "Device",
        "operating_system": "OS",
        "last_seen_at": "Last seen",
        "latest_health_score": "Health score",
        "highest_severity": "Severity",
        "issue_count": "Issues",
        "status": "Status",
    }
)
visible_columns = [
    "Device",
    "OS",
    "Status",
    "Health score",
    "Severity",
    "Issues",
    "Last seen",
]
st.dataframe(table[visible_columns], width="stretch", hide_index=True)

device_options = {item["display_name"]: item["device_id"] for item in filtered}
selected_name = st.selectbox("Selected device", list(device_options))
selected_id = device_options[selected_name]
selected = store.get_device(selected_id)
latest = store.latest_scan(selected_id)

st.subheader("Selected device detail")
if selected:
    detail_columns = st.columns(4)
    detail_columns[0].metric("Status", str(selected["status"]).title())
    detail_columns[1].metric(
        "Health score",
        selected.get("latest_health_score")
        if selected.get("latest_health_score") is not None
        else "Unavailable",
    )
    detail_columns[2].metric(
        "Severity", str(selected.get("highest_severity") or "None").title()
    )
    detail_columns[3].metric("Last seen", selected["last_seen_at"])
    st.caption(
        f"Device ID: {selected['device_id']} · OS: {selected['operating_system']} · "
        f"Platform: {selected['platform']} · Agent: {selected['agent_version']}"
    )

if latest:
    payload = latest.get("payload_summary") or {}
    system = payload.get("system") or {}
    network = payload.get("network") or {}
    metric_columns = st.columns(4)
    metric_columns[0].metric("CPU", f"{system.get('cpu_percent', 'N/A')}%")
    metric_columns[1].metric("Memory", f"{system.get('memory_percent', 'N/A')}%")
    metric_columns[2].metric("Disk free", f"{system.get('disk_free_percent', 'N/A')}%")
    metric_columns[3].metric(
        "Internet", "Online" if network.get("internet_connected") else "Offline"
    )
    issues = payload.get("issues") or []
    if issues:
        st.warning(f"Latest batch contains {len(issues)} detected issue(s).")
        st.dataframe(pd.DataFrame(issues), width="stretch", hide_index=True)
    else:
        st.success("The latest uploaded batch contains no detected issues.")
else:
    st.info("This device has not uploaded a scan batch yet.")

st.subheader("Recent scan batches")
history = store.scan_history(selected_id, page=1, page_size=20)
if history["items"]:
    history_rows = [
        {
            "Timestamp": item["timestamp"],
            "Health score": item["health_score"],
            "Severity": item.get("highest_severity") or "none",
            "Issues": item["issue_count"],
        }
        for item in history["items"]
    ]
    st.dataframe(pd.DataFrame(history_rows), width="stretch", hide_index=True)
else:
    st.info("No scan history is available for this device.")
