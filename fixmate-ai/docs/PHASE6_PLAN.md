# Phase 6 Plan: Production-Style FastAPI Backend

## Status

Implementation complete. Validation is recorded in the final project handoff.

## Goals delivered

- Reuse Phase 1–5 collection, detection, persistence, privacy, deterministic assistant, and optional hybrid-agent services.
- Expose versioned health, system, network, issue, screenshot-analysis, and assistant endpoints.
- Keep route handlers thin through injected data, diagnostic, and assistant services.
- Provide pagination, filters, Pydantic response contracts, request IDs, UTC timestamps, and trace-free structured errors.
- Protect state-changing diagnostic and assistant requests with a configured local token, bounded request sizes, CORS restrictions, and in-memory rate limits.
- Preserve all existing Streamlit pages and SQLite records through the existing additive migrations.
- Test with temporary databases and mocked collectors/providers, requiring no internet, Tesseract, Ollama, or cloud service.

## Security boundary

The API is localhost-first and binds to `127.0.0.1` by default. It exposes no arbitrary SQL, filesystem access, shell, unrestricted model tools, process termination, network scanning, setting changes, or repair actions. POST routes require a configured `X-API-Token`; token comparison is constant-time. All returned diagnostic evidence passes through privacy redaction, while screenshot endpoints return metadata rather than filenames, screenshot bytes, or raw OCR text.

## Endpoint groups

- General: `/health`, `/api/v1/status`
- System: latest, paginated history, and authenticated scan collection
- Network: latest, paginated history, and authenticated bounded diagnostics
- Issues: paginated/filterable list and individual detail
- Screenshots: privacy-safe paginated analysis metadata
- Assistant: authenticated deterministic queries by default, with optional Phase 5 enhancement subject to provider configuration and consent

## Known operational limits

- Rate limiting is held in memory per Python process.
- Local token authentication and restricted CORS are defense-in-depth for localhost, not an internet-facing authentication platform.
- Collector requests can briefly consume CPU or network resources and are deliberately rate-limited.
- AI-enhanced assistant behavior remains optional and falls back to deterministic evidence when unavailable or unsafe.
