# Phase 4: Evidence-Based Troubleshooting Assistant

Status: completed and verified.

## Goal delivered

Phase 4 adds a local deterministic assistant that answers supported natural-language questions using only collected FixMate AI evidence. It does not use a generative AI model, external LLM, cloud API, or internet service.

## Architecture

`src/assistant_tools.py` provides independent read-only tools:

- `get_latest_health_scan`
- `get_health_scan_history`
- `get_top_resource_processes`
- `get_disk_status`
- `get_network_status`
- `get_recent_issues`
- `get_issue_history`
- `get_screenshot_analysis`
- `search_knowledge_base`
- `generate_health_summary`

The tools open the existing SQLite database using `mode=ro` and `PRAGMA query_only`. They do not initialize, migrate, insert, update, or delete data.

`src/troubleshooting_assistant.py` provides deterministic intent detection and routing. Every route returns:

- A direct evidence-bound answer
- Evidence items and their sources
- A relevant timestamp or explicit unavailability
- Severity where applicable
- Data freshness
- Safe guidance labeled as non-guaranteed
- A sufficient/inconclusive evidence flag

## Supported questions

- Why is my computer slow?
- What is using the most memory?
- Is my disk nearly full?
- Is my internet connection working?
- Why is my network slow?
- What problems were detected today?
- Explain my latest screenshot error.
- Summarize this computer's health.
- What should I fix first?

Reliable local knowledge-base queries are also supported. Unknown questions return an explicit routing limitation rather than an invented answer.

## Streamlit page

`pages/3_Troubleshooting_Assistant.py` includes chat-style messages, suggested questions, evidence panel, data-freshness indicator, clear-conversation control, privacy notice, and guidance for running fresh scans. Conversation history lives only in `st.session_state`.

## Privacy and safety

- No conversation persistence or Phase 4 database migration
- No external data transmission
- Display-time redaction for likely IP addresses, MAC addresses, credentials, emails, usernames in paths, and sensitive paths
- OCR text and user questions remain untrusted inert data
- No command execution, process termination, settings changes, or repairs

## Verification

- Every supported intent and route is tested.
- Missing, stale, and conflicting evidence is tested.
- Prompt-injection-like OCR text remains inert and is not echoed as guidance.
- Tool calls are verified not to change database file bytes.
- All Phase 1–4 tests pass without internet, Tesseract, or external AI services.
- Main dashboard, screenshot analyzer, and troubleshooting assistant pages are validated independently.
