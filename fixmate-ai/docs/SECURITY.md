# Security Model

FixMate AI is designed as a localhost-first, read-only diagnostic portfolio application. Its controls reduce risk; they do not turn it into an internet-facing security product.

## Endpoint enrollment and fleet access

Phase 11A separates endpoint ingestion from fleet administration. Agents use `X-Device-Token`; administrator reads retain `X-API-Token`. Tokens are compared in constant time, and enrollment stores only a unique salt plus PBKDF2-HMAC-SHA256 digest. Agent routes have a separate in-memory rate limit. Raw tokens are excluded from database reads, responses, and logs.

The endpoint has no command receiver, shell, repair tool, arbitrary file access, or background daemon. Use high-entropy tokens and localhost or a trusted protected network; rotate credentials after suspected exposure.

## Trust boundaries

- User questions, OCR text, database strings, knowledge-base text, uploaded image bytes, and provider output are untrusted data.
- Tesseract and optional model providers are integrations, not authorities.
- Deterministic collectors, detectors, schemas, privacy functions, and allowlists define application behavior.

## System safety

FixMate AI does not request administrator/root privileges, terminate processes, execute screenshot text, run repair commands, change settings, scan ports, capture packets, inspect browsing history, or read personal file contents.

## API controls

- Native binding defaults to `127.0.0.1`.
- Protected POST endpoints require a configured `X-API-Token`.
- Tokens use constant-time comparison and are never returned in status responses.
- Request IDs, bounded body sizes, CORS allowlists, Pydantic validation, and process-local rate limits apply.
- Errors omit internal traces.
- API routes expose no arbitrary SQL, filesystem, shell, or unrestricted tool access.

Local token authentication is not sufficient for public internet deployment. A reverse proxy, TLS, shared rate limiter, durable audit strategy, and stronger identity system would be required.

## Screenshot and OCR safety

- Uploads are limited to 5 MB and validated by Pillow from actual bytes.
- OpenCV preprocessing and Tesseract run locally.
- Uploaded image files are not saved.
- OCR text is editable but never executed or interpreted as application instructions.
- Likely credentials, email addresses, paths, usernames, IP addresses, and MAC addresses are redacted before storage.

## Assistant and provider safety

Deterministic mode is the default source of truth. Optional providers receive only minimized redacted evidence after required external consent. Tool names are validated against nine read-only tools, provider arguments are rejected, and tool/provider iterations are bounded. Unsafe, malformed, ungrounded, or repair-claiming output falls back to the deterministic answer.

Provider credentials are read from environment variables. `.env`, logs, databases, reports, virtual environments, and caches are ignored by Git and excluded from Docker images.

## Reports

Reports are built from read-only evidence and redacted again before export. Filenames come from enums and UTC timestamps. The API accepts no output path. CSV, JSON, HTML, and PDF bytes are generated in memory and are not stored by default.

## Docker and CI

- Containers run as an unprivileged `fixmate` user.
- Compose publishes ports only on host loopback.
- Secrets are supplied at runtime and are not baked into images.
- CI has read-only repository permissions and no real provider credentials.
- Tests mock network, OCR, and provider operations.

## Reporting a concern

For a public repository, use GitHub's private vulnerability reporting feature if enabled. Do not open an issue containing a real token, screenshot, database, path, username, network address, or diagnostic record.
