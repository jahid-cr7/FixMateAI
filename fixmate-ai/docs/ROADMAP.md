# Roadmap

FixMate AI currently provides read-only diagnostics, deterministic troubleshooting, optional bounded explanation, reporting, FastAPI, Docker, and cross-platform CI. The roadmap deliberately avoids claiming autonomous repair.

## Phase 11A — complete

- One-shot privacy-minimized endpoint collector
- Hashed device enrollment, heartbeat and scan-batch persistence
- Authenticated ingestion/admin APIs and Streamlit fleet dashboard

## Phase 11B — complete

- Bounded local offline queue for retryable endpoint uploads
- Queue status and explicit queue flush commands
- Foreground scheduled endpoint loop with interval seconds/minutes
- Heartbeat-only mode, max-iteration demo safety, and clean Ctrl+C handling

## Phase 11C-1 — complete

- Fleet summary, single-device, offline-device, and high-risk-device reports
- CSV, JSON, HTML, and PDF export through the existing report system
- Streamlit device selection and FastAPI report generation for fleet scopes

## Optional Tencent TokenHub GLM provider — complete

- Tencent TokenHub GLM is available as an optional AI-enhanced explanation provider.
- Deterministic troubleshooting remains the default source of truth.
- Provider setup uses environment variables only and falls back safely on missing config, timeouts, auth failures, or malformed output.

Formal credential rotation and optional service-manager instructions remain candidate follow-ups.

## Phase 12B — Fleet Alert Acknowledgement Workflow — complete

- Fleet issues from scan uploads automatically start as **open**.
- Technicians can acknowledge, mark in progress, resolve, or dismiss as false positive.
- Timestamps and optional technician notes are recorded at each transition.
- Streamlit Device Fleet page shows issue status badges, filters, and action buttons.
- Authenticated API endpoints support programmatic issue management.
- Reports include open, acknowledged, and in-progress issue counts.

## Near-term

- Add a first-class Streamlit database selector for marked synthetic demo databases.
- Improve accessibility and responsive behavior across dashboard pages.
- Add downloadable redaction-review summaries before report export.
- Add coverage reporting and lightweight Ruff checks after a controlled formatting pass.
- Validate Docker builds automatically in a separate CI job with image-layer caching.
- Add optional documented recipes for Windows Task Scheduler or systemd timers without changing the agent into a remote-control service.
- Add a clearer provider-selection UX if more external providers are added.

## Medium-term

- Add PostgreSQL as an optional deployment database while retaining SQLite for local use.
- Add shared rate limiting and stronger authentication for team deployments.
- Expand the curated Windows/Ubuntu knowledge base with source/version metadata.
- Add multilingual OCR language configuration without cloud OCR.
- Add signed report metadata and optional encrypted export packages.

## Long-term research

- Evaluate carefully permissioned repair *plans* that require explicit human confirmation; execution remains out of scope until a strong sandbox, audit model, rollback design, and threat review exist.
- Add event correlation across scans without inventing causality.
- Evaluate local embedding-based retrieval against deterministic baselines.
- Package native Windows and Ubuntu desktop installers.

## Explicitly out of scope today

- Autonomous repair
- Background surveillance
- Credential collection
- Arbitrary shell or SQL access
- Packet capture, port scanning, or malware detection claims
- Public internet deployment without additional security architecture
