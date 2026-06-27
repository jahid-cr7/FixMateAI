# Phase 11C: Fleet-Aware Reports

Status: 11C-1 implemented.

## Goal

Extend the existing privacy-safe report system so IT staff can generate handover reports for endpoint fleets collected through the Phase 11A/11B agent and fleet API.

## Implemented report types

- Fleet summary report
- Single device report
- Offline devices report
- High-risk devices report

## Evidence included

Fleet reports use only existing read-only fleet records:

- Device display name, OS/platform, and agent version
- First seen and last seen timestamps
- Deterministic online/offline/unknown status
- Latest health score, latest highest severity, and issue count
- Recent heartbeat history for single-device reports
- Recent scan batch history
- Fleet totals and high-risk counts
- Safe recommendations and privacy notice

## Export formats

Fleet reports reuse the existing in-memory exporters:

- CSV
- JSON
- HTML
- PDF

No generated report is stored by default.

## Privacy and safety

- Reports apply existing redaction at the report boundary.
- Raw device tokens, token salts, token hashes, request headers, queue paths, full IP/MAC addresses, usernames, secrets, and sensitive paths are excluded.
- Reports are read-only and never execute repairs or commands.
- Single-device reports require an explicit device ID through the API.
- Streamlit device selection is populated from privacy-safe fleet summaries.

## Validation

- Added tests for fleet summary, single-device, offline-device, and high-risk-device reports.
- Added API generation tests for all fleet report types.
- Existing report type tests continue to cover CSV, JSON, HTML, PDF, privacy redaction, empty states, and request validation.

## Limitations

- Fleet reports summarize current SQLite fleet records only.
- Offline status depends on the configured heartbeat freshness threshold.
- Report redaction is best-effort; exported files should be reviewed before sharing.
- Fleet reports do not include raw queued upload files, raw tokens, or endpoint command capability.
