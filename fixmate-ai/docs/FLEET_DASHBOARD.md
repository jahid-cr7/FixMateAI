# Device Fleet Dashboard

Open **Device Fleet** in Streamlit after endpoints submit data. It shows total, online, offline, unknown, and high-risk counts; filters; latest summarized evidence; recent scan upload time; agent version; and scan history.

Status is deterministic:

- **Online:** latest heartbeat is within `FIXMATE_FLEET_ONLINE_MINUTES` (default 5).
- **Offline:** a valid heartbeat exists but is older than that window.
- **Unknown:** no valid heartbeat exists.
- **High risk:** the latest batch contains a high or critical issue.

The page does not poll endpoints, issue commands, schedule agents, or repair devices. Refresh the page after newer endpoint uploads arrive. Scheduled collection is started from the endpoint CLI, for example:

```bash
python -m fixmate_agent --server http://127.0.0.1:8000 --device-name "Lab Endpoint" --interval-seconds 60
```

Use `--max-iterations` for demos or testing so the process exits automatically.

Fleet-aware reports are available from the **Reports** page and the reports API. Supported scopes are fleet summary, single device, offline devices, and high-risk devices. Reports include only privacy-safe read models: display names, OS/platform, agent version, first/last seen timestamps, status, health score, severity, issue counts, recent heartbeats, and recent scan batches. They never include raw device tokens, token hashes, queue file paths, or endpoint repair commands.
