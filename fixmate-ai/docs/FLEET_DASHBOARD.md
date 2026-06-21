# Device Fleet Dashboard

Open **Device Fleet** in Streamlit after endpoints submit data. It shows total, online, offline, unknown, and high-risk counts; filters; latest summarized evidence; and scan history.

Status is deterministic:

- **Online:** latest heartbeat is within `FIXMATE_FLEET_ONLINE_MINUTES` (default 5).
- **Offline:** a valid heartbeat exists but is older than that window.
- **Unknown:** no valid heartbeat exists.
- **High risk:** the latest batch contains a high or critical issue.

The page does not poll endpoints, issue commands, or repair devices. Refresh or rerun the endpoint agent for newer evidence. Fleet-specific report exports are a future enhancement.

