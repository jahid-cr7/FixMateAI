# Privacy Guide

FixMate AI processes diagnostic evidence locally by default. This document describes what it collects, what it deliberately excludes, and the limits of automated redaction.

## Managed endpoint payloads

The one-shot endpoint agent sends opaque identity metadata, summarized CPU/memory/disk/network values, health score, interface count, and redacted issue evidence. It omits hostname, process/interface names, addresses, screenshots, OCR text, browsing history, file contents, credentials, and raw tokens. Fleet records remain in the configured SQLite database.

## Collected locally

- CPU, memory, and disk percentages
- Operating-system and boot-time information
- Top process names, IDs, and memory usage
- Active interface names/counts, cumulative traffic counters, connectivity result, and latency
- Detected issue evidence and safe recommendations
- Redacted OCR text and deterministic match metadata

## Not collected

- Passwords or tokens by design
- Browser history
- Personal document contents
- Packet captures or port scans
- Raw screenshot files after processing
- Assistant conversations in SQLite
- Generated reports by default

## Redaction

FixMate AI applies pattern-based redaction to likely secrets, bearer values, email addresses, explicit usernames, Windows/Linux user paths, IPv4/IPv6 addresses, and MAC addresses. Reports and external-provider payloads receive additional minimization/redaction.

Pattern matching is best-effort and cannot recognize every personal detail. Before uploading a screenshot or sharing a report:

1. Crop unrelated applications and notifications.
2. Remove credentials, account identifiers, private filenames, and contact details.
3. Review editable OCR text.
4. Preview the final report.
5. Share only with an intended support recipient.

## Optional external providers

Deterministic mode sends nothing externally. Cloud AI enhancement requires configuration and explicit session consent. The minimized payload can include the redacted question, deterministic answer fields, evidence values, severity, and timestamps. It excludes screenshots, OCR text, process names from tool output, credentials, complete IP/MAC addresses, usernames, and sensitive paths.

The provider may have independent retention, training, location, and billing policies. Local Ollama-compatible mode avoids cloud transmission but requires a separately managed local model.

## Demo data

The portfolio generator creates only marked synthetic data. `.invalid` hostnames are reserved for examples and do not represent real systems. Generated databases are ignored by Git and should be deleted when no longer required.
