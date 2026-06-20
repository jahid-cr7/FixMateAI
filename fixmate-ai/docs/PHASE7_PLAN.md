# Phase 7 Plan: Diagnostic Report Export System

## Status

Implementation complete. Automated, visual PDF, Streamlit, API, and repository-hygiene validation is recorded in the final handoff.

## Delivered architecture

- `src/report_models.py` defines five report types, four formats, selectable sections, and stable in-memory contracts.
- `src/report_builder.py` assembles deterministic evidence through existing read-only tools and applies inclusive UTC date filtering.
- `src/report_privacy.py` recursively redacts every report field and suppresses sensitive field categories.
- `src/report_exporters.py` creates CSV, JSON, standalone HTML, and ReportLab PDF bytes without writing files.
- `src/report_ui.py` provides testable date and explicitly selected conversation helpers.
- `pages/4_Reports.py` provides selection, privacy warning, preview, empty-state handling, and browser download.
- The FastAPI report service and router provide discovery and authenticated, rate-limited generation without exposing paths or database access.

## Report scopes

- System health summary
- Network diagnostics
- Screenshot error analysis metadata
- Deterministic troubleshooting assistant summary
- Full diagnostic bundle

Each scope uses only recorded FixMate AI evidence. Selected sections can contain platform details, health and resource metrics, network status, recent issues, severity counts, minimized screenshot findings, deterministic assistant guidance, evidence timestamps, limitations, and privacy notices.

## Privacy and storage boundary

Reports are generated locally in memory and are not inserted into SQLite or written to the project. Filenames are built only from allowlisted report/format enums and UTC timestamps. The API accepts no filename or output path, preventing path traversal by construction.

Existing redaction is reapplied recursively before every export. Screenshot bytes, filenames, raw OCR text, target hosts, full IP/MAC addresses, usernames, likely credentials, and sensitive user paths are excluded or redacted. Streamlit conversation text is excluded by default and minimized only after explicit selection.

## API security

- `GET /api/v1/reports/types` is read-only.
- `POST /api/v1/reports/generate` requires `X-API-Token` using the existing constant-time comparison.
- Existing body-size middleware applies before parsing.
- Report generation has an independent in-memory rate-limit category.
- Responses use existing request IDs, UTC timestamps, Pydantic schemas, CORS restrictions, and trace-free errors.

## PDF behavior

ReportLab creates landscape A4 reports with repeating headers, wrapped cells, alternating rows, page numbers, and local built-in fonts. If PDF generation fails, the exporter returns a privacy-safe HTML report with an explicit fallback warning.

## Limitations

- Exports reflect recorded evidence rather than continuous monitoring.
- Privacy redaction cannot guarantee recognition of every possible identifier.
- PDF built-in fonts replace unsupported characters for reliable cross-platform rendering.
- API report content is base64-encoded and intended for bounded localhost use.
- Rate limits are process-local rather than shared across multiple API workers.
