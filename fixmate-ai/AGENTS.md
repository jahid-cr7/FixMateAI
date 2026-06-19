# AGENTS.md

## Project purpose

FixMate AI is a beginner-friendly, portfolio-quality system health, network diagnostic, screenshot-analysis, and hybrid troubleshooting application for Windows and Ubuntu. Deterministic evidence remains authoritative; keep every feature read-only and safe by default.

## Commands

Run from the `fixmate-ai` directory with the virtual environment activated:

```bash
python -m pip install -r requirements.txt
python -m pytest
python -m streamlit run app.py
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

## Before submitting changes

1. Run `python -m pytest`.
2. Validate `app.py` and every file under `pages/` with Streamlit.
3. Confirm the application starts when the Tesseract executable is unavailable.
4. Confirm `data/fixmate.db` remains ignored by Git.
5. Update `README.md` and the relevant phase plan when behavior changes.
6. Run provider tests with injected transports only; automated tests must never contact cloud or Ollama endpoints.
7. Confirm the complete app works with all `FIXMATE_LLM_*` variables absent.

