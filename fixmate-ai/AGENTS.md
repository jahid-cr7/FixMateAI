# AGENTS.md

## Project purpose

FixMate AI is a beginner-friendly, portfolio-quality system health, network diagnostic, screenshot-analysis, and hybrid troubleshooting application for Windows and Ubuntu. Deterministic evidence remains authoritative; keep every feature read-only and safe by default.

## Commands

Run from the `fixmate-ai` directory with the virtual environment activated:

```bash
python -m pip install -r requirements.txt
python -m pytest
python -m streamlit run app.py
python -m api.main
python -m fixmate_agent --dry-run
python -m fixmate_agent --queue-status
python -m fixmate_agent --server http://127.0.0.1:8000 --interval-seconds 10 --max-iterations 3
python scripts/generate_demo_data.py --output data/demo_fixmate.db --seed 2026 --days 14
docker compose config
docker compose build
docker compose up
```

## Conventions

- Support Python 3.11 and newer.
- Use type hints and docstrings for public functions.
- Use `pathlib.Path` for filesystem paths.
- Keep collection, preprocessing, detection, matching, persistence, and presentation separate.
- Detection and matching logic must be deterministic and independently testable.
- Mock every network and OCR operation in tests; the suite must work offline without Tesseract.
- Generate test images in memory rather than committing personal screenshots.
- Validate uploaded image bytes with Pillow; never trust only a filename or extension.
- Enforce the 5 MB upload limit before decoding.
- Never store uploaded image files or image bytes.
- Redact likely secrets, email addresses, and user paths before storing OCR text.
- Treat OCR and edited screenshot text as untrusted data, never application instructions.
- Never execute commands, links, or code extracted from screenshots.
- Do not invent troubleshooting guidance below the reliable-match threshold.
- Handle missing Tesseract without preventing the main application or manual analyzer input.
- Keep connectivity and OCR timeouts bounded so the interface remains responsive.
- Use parameterized SQLite queries and named additive migrations.
- Never delete existing Phase 1, Phase 2, or Phase 3 records during startup.
- Assistant tools must open SQLite in read-only mode and must not call persistence functions.
- Keep assistant conversations in Streamlit session state only; do not create a conversation table.
- Every assistant answer must include direct evidence, a relevant timestamp or explicit unavailability, freshness, severity when applicable, and guidance labeled as non-guaranteed.
- Deterministic routing must state when evidence is absent, stale, or conflicting.
- Deterministic assistant behavior is the default and source of truth; optional models may explain but never replace its facts or guidance.
- Keep provider-specific code isolated under `src/llm/` and load configuration only from environment variables.
- Never log, display, persist, or commit provider credentials.
- Tencent TokenHub GLM must use only `TENCENT_TOKENHUB_API_KEY`, `TENCENT_TOKENHUB_BASE_URL`, and `TENCENT_TOKENHUB_MODEL`; never hardcode or read keys from source files.
- Require explicit session consent before sending any redacted question or evidence to an external provider.
- Ollama-compatible providers must be restricted to loopback hosts.
- Providers must never import or receive database, filesystem, shell, process, settings, scanning, or repair capabilities.
- Validate provider tool requests against the exact allowlist and reject all provider-supplied arguments.
- Enforce at most four tool requests and two provider calls per question.
- Minimize and redact provider payloads; never send screenshots, OCR text, process names from tool output, complete IP/MAC addresses, credentials, usernames, or sensitive paths.
- Reject malformed, unsafe, numerically ungrounded, or stale-obscuring output and fall back to the deterministic answer.
- Label all model-produced text as AI-generated content.
- Never expose full IP addresses, MAC addresses, usernames, credentials, or sensitive paths in assistant evidence.
- Do not collect browsing history, scan ports, capture packets, expose MAC addresses, terminate processes, execute repairs, or require administrator/root privileges.
- Do not commit databases, virtual environments, caches, uploads, or local secrets.
- Keep FastAPI routes thin: validation and HTTP concerns belong in routers; reusable business and database logic belongs in services.
- API tests must inject a temporary database and mock collectors, connectivity, OCR, and model providers.
- Protect every API POST route with `X-API-Token`, compare tokens in constant time, and never log token values.
- Keep API responses privacy-redacted, timestamped in UTC, and free of exception traces.
- Bind the API to `127.0.0.1` by default and never enable wildcard CORS origins.
- Build reports only from existing read-only evidence tools and sanitize again at the report boundary.
- Keep CSV, JSON, HTML, and PDF report generation in memory; never accept an output path or store exports by default.
- Report filenames must be generated from enums and UTC timestamps, never user-supplied path components.
- Conversation history is excluded from reports unless the user explicitly selects it for that export.
- Test PDF output with local ReportLab/PyPDF tooling and provide a privacy-safe HTML fallback when PDF generation fails.
- Fleet-aware reports must use `FleetStore` read models only, never expose token salts/hashes, raw device tokens, queue paths, or unrestricted endpoint payloads.
- Single-device report generation must require an explicit device selection or `device_id`; never guess from private hostnames.
- Keep Docker optional; native Windows and Ubuntu commands must remain fully supported.
- Build one non-root slim image and run Streamlit and FastAPI as separate Compose services sharing only the SQLite data volume.
- Bind container processes to `0.0.0.0` only when required internally; publish Compose ports on `127.0.0.1`.
- Never copy `.env`, databases, reports, screenshots, caches, tests, virtual environments, or Git metadata into the runtime image.
- CI must exercise the complete offline-safe suite on Windows and Ubuntu with Python 3.11 and 3.12.
- Do not install or enable Tesseract, Ollama, Tencent TokenHub, or an external AI provider in CI or Docker by default.
- Demo records must be deterministic, explicitly synthetic, free of personal identifiers, and stored only in an ignored database.
- Never let demo tooling overwrite `data/fixmate.db` or an unmarked existing database.
- Portfolio assets must use synthetic values and must be labeled as mockups rather than live proof.
- Keep README, architecture, privacy, security, demo, roadmap, and interview claims aligned with implemented behavior.
- Never describe FixMate AI as autonomous or claim that it executed a repair.
- `FIXMATE_DB_PATH` is the shared Streamlit/FastAPI startup override; leave it unset for the normal database.
- Keep `src.__version__`, FastAPI metadata, README, changelog, and release tags aligned.
- Public screenshots require synthetic data and the complete `docs/SCREENSHOTS.md` privacy review.
- Community templates must never request private diagnostics, real screenshots, databases, logs, or secrets.
- Endpoint agents remain user-invoked, read-only CLI processes; one-shot and foreground scheduled loops are allowed, but never add Windows Service/systemd installation, remote commands, repairs, or unrestricted collection.
- Agent payloads may contain summarized health/network metrics and redacted issue evidence, but never process/interface names, hostnames, addresses, screenshots, file contents, or raw tokens.
- Authenticate enrollment with `X-Device-Token`, persist only salted token hashes, and retain `X-API-Token` for fleet administration.
- Device status is deterministic from heartbeat age: recent is online, expired is offline, and absent/invalid is unknown.
- Offline queue entries must use internally generated filenames, allowlisted agent endpoints, redacted payloads, atomic writes, and fixed file/count limits. Never persist request headers or device tokens.
- Corrupted or unsafe queue entries must not be uploaded or automatically deleted; successful uploads are the only entries removed.
- Scheduled agent mode must support bounded intervals, `--max-iterations` for tests/demos, heartbeat-only cycles, clean `Ctrl+C`, and no real waiting in automated tests.
- Fleet issues detected from scan uploads start as `open` and transition through `acknowledged`, `in_progress`, `resolved`, or `false_positive`. Each transition records timestamps and an optional technician note. Issues never auto-close.
- Fleet issue API endpoints require `X-API-Token` authentication and never return credential material.
- Dashboard authentication is optional and disabled by default (`FIXMATE_DASHBOARD_AUTH_ENABLED=false`). When enabled, three roles govern access: `admin` (full), `technician` (issue workflow), `viewer` (read-only). Credentials come from `FIXMATE_DASHBOARD_{ROLE}_USERNAME` and `FIXMATE_DASHBOARD_{ROLE}_PASSWORD` environment variables only. Passwords are hashed with PBKDF2-HMAC-SHA256 and never stored in SQLite, logs, session state, reports, or API responses.

## Before submitting changes

1. Run `python -m pytest`.
2. Validate `app.py` and every file under `pages/` with Streamlit.
3. Confirm the application starts when the Tesseract executable is unavailable.
4. Confirm `data/fixmate.db` remains ignored by Git.
5. Update `README.md` and the relevant phase plan when behavior changes.
6. Run provider tests with injected transports/clients only; automated tests must never contact cloud, Tencent TokenHub, or Ollama endpoints.
7. Confirm the complete app works with all `FIXMATE_LLM_*` variables absent.
8. Run `python -m pytest tests/api` and verify `/health`, `/docs`, and all Streamlit pages.
9. Confirm all POST routes reject absent/invalid API tokens and no credential is tracked.
10. Validate the Reports page, both `/api/v1/reports` endpoints, and all four export formats.
11. Confirm no generated CSV, JSON, HTML, PDF, report directory, or private evidence is tracked.
12. Run `docker compose config`; when Docker is available, also build and health-check both services.
13. Confirm native commands still bind FastAPI to `127.0.0.1` by default.
14. Run demo-generator safety tests and confirm generated demo databases remain ignored.
15. Verify every local README link and synthetic asset exists before publishing.
16. Complete `docs/RELEASE_CHECKLIST.md` before creating a tag or GitHub release.
