# Changelog

All notable changes to FixMate AI are documented here. The format is inspired by Keep a Changelog, and releases follow semantic versioning.

## [1.0.0] - 2026-06-21

### Added

- Cross-platform system-health collection, deterministic issue rules, health scoring, SQLite history, and Streamlit charts.
- Safe network diagnostics with active-interface, connectivity, traffic, timeout, and latency evidence.
- Local screenshot validation, OpenCV preprocessing, optional Tesseract OCR, and deterministic knowledge-base matching.
- Evidence-based deterministic troubleshooting assistant with optional bounded provider explanations and safe fallback.
- Versioned FastAPI endpoints with schemas, pagination, filters, request IDs, token-protected POST routes, CORS, limits, and privacy redaction.
- In-memory CSV, JSON, HTML, and PDF diagnostic reports.
- Non-root Docker Compose deployment and Windows/Ubuntu Python 3.11/3.12 CI.
- Deterministic marked synthetic demo data, SVG portfolio assets, architecture/security/privacy documentation, and interview material.
- Shared `FIXMATE_DB_PATH` startup override for safe demo use across Streamlit and FastAPI.
- MIT License, contribution guide, GitHub templates, screenshot workflow, repository setup guide, and release checklist.

### Security

- Read-only design with no automatic repairs, arbitrary shell/SQL/filesystem access, process termination, packet capture, or port scanning.
- Localhost API default, constant-time token checks, bounded request sizes, CORS allowlists, rate limits, and trace-free errors.
- Screenshot non-persistence, OCR/report/provider redaction, explicit external consent, and deterministic assistant authority.

### Known limitations

- Redaction and OCR are best-effort.
- SQLite and in-memory rate limits target local/single-process use.
- Docker diagnostics describe containers rather than the host.
- Local API token authentication is not sufficient for public internet deployment.
- FixMate AI does not perform autonomous repair.

