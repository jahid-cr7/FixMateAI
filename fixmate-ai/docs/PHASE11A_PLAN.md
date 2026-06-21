# Phase 11A: Multi-Device Real-World Foundation

Status: **complete**

## Delivered

- One-shot Windows/Ubuntu endpoint CLI using the existing read-only collectors and detectors
- Dry-run preview, bounded HTTP timeout, explicit configuration, and graceful offline failure
- Additive SQLite tables for devices, heartbeats, and minimized scan batches
- Salted PBKDF2 device-token hashes; raw enrollment tokens are never persisted
- Separate agent ingestion and administrator fleet APIs with rate limits and privacy-safe responses
- Streamlit Device Fleet page with totals, filters, risk state, latest evidence, and history
- Unit and API coverage with unavailable networking and isolated temporary databases

Fleet report exports are intentionally deferred. Existing reports remain unchanged, and Phase 11A does not imply remote repair or background monitoring.

