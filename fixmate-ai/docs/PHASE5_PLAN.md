# Phase 5: Optional Hybrid LLM Troubleshooting Agent

Status: completed and verified.

## Design delivered

Phase 5 preserves the deterministic Phase 4 assistant as the default source of truth. Optional providers can select approved minimized read-only tools and add a labeled plain-language explanation. They cannot replace deterministic answer fields or perform actions.

The application works without an API key, internet connection, Ollama server, or model.

## Provider abstraction

`src/llm/` contains:

- A common `LLMProvider` interface and sanitized `ProviderError`
- `DisabledProvider` as the default
- An explicitly configured HTTPS chat-completions-compatible cloud provider
- A loopback-only Ollama-compatible provider
- An injectable standard-library JSON HTTP transport
- Environment-only provider factory and bounded timeout parsing

Provider status objects contain no secrets. Cloud mode requires URL, model, and API key. Ollama mode requires a model and a URL hosted on `localhost`, `127.0.0.1`, or `::1`.

## Safe tool boundary

`src/safe_agent_tools.py` exposes exactly:

- `get_latest_health_scan`
- `get_top_resource_processes`
- `get_disk_status`
- `get_network_status`
- `get_recent_issues`
- `get_issue_history`
- `get_screenshot_analysis`
- `search_knowledge_base`
- `generate_health_summary`

No arbitrary arguments are accepted. SQL, shell, file reads, process control, settings, scanning, and repair capabilities are absent. Results are minimized, bounded, and redacted. Screenshot/OCR content and process names are omitted from provider tool payloads.

## Bounded hybrid orchestration

`src/hybrid_agent.py`:

1. Always computes the deterministic answer first.
2. Stops immediately when configuration or external consent is missing.
3. Makes one structured planning call.
4. Validates at most four exact allowlisted tool requests.
5. Executes each approved duplicate tool only once.
6. Makes one final explanation call.
7. Accepts only `{\"explanation\": \"...\"}` output.
8. Rejects unsupported numbers, repair claims, commands, extra fields, excessive length, and omitted stale/missing-evidence notices.
9. Falls back to the unchanged deterministic answer after any provider or safety failure.

There are at most two provider calls and no autonomous loop.

## Privacy and consent

- External cloud evidence requires explicit session consent.
- Questions and evidence are redacted before provider use.
- Screenshots and OCR text are never sent.
- API keys are read from environment variables and never included in errors or status messages.
- Conversations remain in Streamlit session state and are not stored in SQLite.
- `.env` and variants are ignored; `.env.example` contains placeholders only.

## Streamlit changes

The Troubleshooting Assistant page now includes deterministic/AI-enhanced mode selection, provider status, external consent, payload explanation, AI-generated-content labels, deterministic fallback notifications, evidence panel, freshness, and clear-conversation behavior.

## Verification

- All provider responses are mocked and every transport is injected in tests.
- Missing credentials, consent, timeout, malformed output, forbidden tools, arguments, excessive calls, prompt injection, privacy redaction, invented metrics, unsafe repair claims, and fallback are tested.
- Phase 1–4 tests remain intact.
- All Streamlit pages and routes are validated with no LLM configuration.
- No Phase 5 schema migration or conversation persistence is added.
