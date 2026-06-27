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

## Issue Workflow

Fleet issues detected from scan uploads start as **open**. Technicians can transition them through:

- **Acknowledged** — issue seen, investigation not yet started
- **In Progress** — active investigation or remediation underway
- **Resolved** — issue addressed and confirmed fixed
- **False Positive** — issue flagged as not requiring action

Each transition records a timestamp (`acknowledged_at`, `resolved_at`, `updated_at`) and an optional **technician note**. Issues never auto-close; a human must explicitly resolve or dismiss them.

### Streamlit UI

Opening the **Device Issues** panel on the Device Fleet page shows issues for the selected device, filterable by status. Buttons allow acknowledge, mark in progress, resolve, and mark false positive with an optional note.

### API Endpoints

All fleet issue endpoints require `X-API-Token`:

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/fleet-issues` | List issues with optional `device_id` and `status` filters |
| POST | `/api/v1/fleet-issues/{id}/acknowledge` | Acknowledge an issue |
| POST | `/api/v1/fleet-issues/{id}/in-progress` | Mark issue in progress |
| POST | `/api/v1/fleet-issues/{id}/resolve` | Resolve an issue |
| POST | `/api/v1/fleet-issues/{id}/false-positive` | Mark issue as false positive |

POST endpoints accept an optional JSON body with `technician_note` (max 2000 chars). Responses never contain API keys or token digests.

### Reports

Fleet-aware reports include open, acknowledged, and in-progress issue counts where relevant. Issue status and technician notes appear in single-device reports when the `fleet` section is selected.

Fleet-aware reports are available from the **Reports** page and the reports API. Supported scopes are fleet summary, single device, offline devices, and high-risk devices. Reports include only privacy-safe read models: display names, OS/platform, agent version, first/last seen timestamps, status, health score, severity, issue counts, recent heartbeats, and recent scan batches. They never include raw device tokens, token hashes, queue file paths, or endpoint repair commands.

## Dashboard Authentication

Optional role-based dashboard authentication protects the Streamlit UI when enabled:

| Variable | Default | Purpose |
|----------|---------|---------|
| `FIXMATE_DASHBOARD_AUTH_ENABLED` | `false` | Enable or disable login |
| `FIXMATE_DASHBOARD_ADMIN_USERNAME` | `admin` | Admin username |
| `FIXMATE_DASHBOARD_ADMIN_PASSWORD` | — | Admin password (must be changed from default) |
| `FIXMATE_DASHBOARD_TECHNICIAN_USERNAME` | `technician` | Technician username |
| `FIXMATE_DASHBOARD_TECHNICIAN_PASSWORD` | — | Technician password |
| `FIXMATE_DASHBOARD_VIEWER_USERNAME` | `viewer` | Viewer username |
| `FIXMATE_DASHBOARD_VIEWER_PASSWORD` | — | Viewer password |

When disabled (default), the dashboard runs in open demo mode suitable for local portfolios. When enabled, a login form renders before any dashboard content. Viewers see read-only fleet data; technicians and admins can perform issue workflow actions (acknowledge, resolve, etc.). Passwords are hashed in server memory and never stored in SQLite, logs, or reports.
