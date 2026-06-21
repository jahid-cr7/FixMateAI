# Roadmap

FixMate AI currently provides read-only diagnostics, deterministic troubleshooting, optional bounded explanation, reporting, FastAPI, Docker, and cross-platform CI. The roadmap deliberately avoids claiming autonomous repair.

## Phase 11A — complete

- One-shot privacy-minimized endpoint collector
- Hashed device enrollment, heartbeat and scan-batch persistence
- Authenticated ingestion/admin APIs and Streamlit fleet dashboard

Fleet-aware report exports and a formal credential-rotation workflow remain candidate follow-ups.

## Near-term

- Add a first-class Streamlit database selector for marked synthetic demo databases.
- Improve accessibility and responsive behavior across dashboard pages.
- Add downloadable redaction-review summaries before report export.
- Add coverage reporting and lightweight Ruff checks after a controlled formatting pass.
- Validate Docker builds automatically in a separate CI job with image-layer caching.

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
