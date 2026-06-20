# FixMate AI Interview Guide

## 60-second pitch

FixMate AI is a cross-platform, read-only IT support application I built for Windows and Ubuntu. It collects system and network health evidence, detects explicit threshold violations, stores history in SQLite, analyzes error screenshots locally with OpenCV and Tesseract, and answers supported troubleshooting questions from collected evidence. The deterministic assistant is the source of truth; optional model support can explain approved evidence but cannot access the database, filesystem, shell, or repair tools. The project includes privacy-safe reports, a versioned FastAPI backend, Streamlit UI, Docker Compose, and Windows/Ubuntu CI. I focused on trustworthy boundaries, testability, and graceful operation without internet, OCR software, or AI credentials.

## Two-minute technical explanation

Collectors use `psutil` and bounded standard-library network calls. Pure detector functions convert metrics into issues with severity, evidence, explanation, and safe guidance. Additive SQLite migrations preserve earlier records. Streamlit and FastAPI reuse the same services rather than duplicating business logic.

Screenshot analysis validates image bytes with Pillow, preprocesses images using independently testable OpenCV steps, and calls local Tesseract behind a graceful optional boundary. OCR text is treated as untrusted, redacted before storage, and matched deterministically against a curated knowledge base.

The troubleshooting assistant uses explicit intent routing and nine read-only evidence tools. Optional providers are isolated, consent-gated, redacted, iteration-limited, and validated against the deterministic result. Report exports reuse the same evidence, redact it again, and generate CSV, JSON, HTML, or PDF entirely in memory. FastAPI adds versioned schemas, request IDs, token-protected POST routes, CORS restrictions, body limits, and rate limits. Tests use temporary databases and mocked external boundaries across Windows and Ubuntu CI.

## Problems solved

- Converts scattered system metrics into understandable evidence and history.
- Distinguishes deterministic facts from optional model-generated explanation.
- Makes screenshot troubleshooting local and useful when cloud OCR is inappropriate.
- Produces support handover reports without persisting exports.
- Demonstrates one business layer reused by interactive UI and REST API.
- Provides a safe synthetic demo path without committing personal diagnostics.

## Architecture talking points

1. Pure collectors/detectors are easy to test with simulated values.
2. SQLite is appropriate for a single-user local portfolio app and supports additive migrations.
3. Streamlit and FastAPI are adapters over shared services.
4. Privacy is applied at collection/storage, display, report, and provider boundaries.
5. Docker is a reproducible deployment, but native mode is required for host diagnostics.

## Security and privacy decisions

- Read-only by design; no automatic repair path exists.
- No admin/root requirement, packet capture, port scanning, shell, arbitrary SQL, or file-content collection.
- Localhost API default and constant-time token checks for POST routes.
- Uploaded screenshots are never stored.
- Conversation history remains session-only.
- External evidence requires explicit consent and is minimized/redacted.
- Provider failures or unsafe output fall back to deterministic answers.

## Testing strategy

- Unit tests for threshold rules, scoring, redaction, image preprocessing, matching, routing, providers, reports, and demo safety.
- Temporary SQLite databases for migrations and API isolation.
- Mocked OCR, connectivity, and provider transports; tests require no internet or Tesseract.
- Endpoint tests cover authentication, validation, pagination, filtering, CORS, rate limits, privacy, and safe errors.
- Streamlit's test runtime validates every page.
- GitHub Actions covers Windows/Ubuntu and Python 3.11/3.12.

## Challenges and solutions

**How did you stop the model from becoming the source of truth?**  I generate the deterministic answer first, expose only approved minimized tools, validate provider output, and retain the deterministic evidence and guidance regardless of provider behavior.

**How did you handle cross-platform metrics?**  I favored `psutil`, Python standard-library APIs, `pathlib`, and simulated tests. OS-specific behavior is isolated and optional dependencies fail gracefully.

**How did you make reports privacy-safe?**  Reports use read-only evidence tools, recursive redaction, minimized screenshot metadata, generated filenames, in-memory bytes, and no output-path parameter.

**How did you protect demo data?**  The generator refuses the production database and existing files. Reset works only for a database carrying a synthetic marker.

## What I would improve next

- Add a UI selector for marked demo databases.
- Add stronger deployment authentication and shared rate limiting.
- Add optional PostgreSQL and structured audit events.
- Expand knowledge-base provenance and accessibility testing.
- Add Docker build validation and coverage reporting to CI.

## CV bullets

- Built a cross-platform Python diagnostics platform using Streamlit, FastAPI, SQLite, psutil, OpenCV, Tesseract, Plotly, and ReportLab.
- Designed deterministic system/network issue detection and evidence-grounded troubleshooting with privacy-safe history and reporting.
- Implemented an optional consent-gated LLM abstraction with strict read-only tool allowlists, redaction, bounded iterations, validation, and deterministic fallback.
- Delivered versioned REST endpoints with Pydantic schemas, token-protected POST routes, request IDs, CORS restrictions, rate limits, and isolated API tests.
- Added Docker Compose deployment and a Windows/Ubuntu Python 3.11/3.12 GitHub Actions matrix with offline-safe mocked tests.

## LinkedIn project post draft

I built **FixMate AI**, a local-first IT diagnostics portfolio project for Windows and Ubuntu. It combines system-health history, safe network checks, local screenshot OCR, deterministic evidence-based troubleshooting, privacy-safe report exports, and a versioned FastAPI backend.

The design constraint I cared about most was trust: optional AI can explain approved evidence, but deterministic logic remains authoritative. The app does not execute repairs, expose shell access, store screenshots, or require cloud services. It also runs without an API key, internet connection, Ollama, or Tesseract.

The project includes Streamlit, SQLite migrations, OpenCV/Tesseract, Plotly, ReportLab, Docker Compose, and automated tests on Windows and Ubuntu. The repository also contains clearly synthetic demo data tooling and privacy-safe SVG walkthroughs.

## Common interview questions

**Why SQLite?**  It is zero-configuration, cross-platform, transactional, and appropriate for local single-user history. I kept access isolated so another database can be introduced later.

**Why deterministic routing instead of an LLM first?**  Diagnostic claims need traceable evidence. Explicit routing makes supported behavior testable and provides a safe fallback.

**Is this an autonomous agent?**  No. It is a read-only troubleshooting assistant. It never claims or performs repairs.

**Why FastAPI after Streamlit?**  It demonstrates service reuse, typed contracts, integration testing, and a path for other local clients without replacing the interactive UI.

**What does Docker diagnose?**  The containers themselves. Native execution is necessary to diagnose the actual host machine.

**What is the biggest remaining risk?**  Best-effort redaction can miss novel identifiers, and localhost token authentication is not enough for public deployment. Both are documented constraints.

