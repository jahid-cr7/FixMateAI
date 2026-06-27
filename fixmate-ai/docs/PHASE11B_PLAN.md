# Phase 11B: Scheduled Agent and Offline Queue

Status: implemented and validated.

## Goal

Phase 11B turns the Phase 11A endpoint agent into a more realistic managed-endpoint collector while keeping it read-only and safe. It adds a bounded local offline upload queue and a foreground scheduled runner without installing a Windows Service, Linux systemd unit, background daemon, remote command channel, or repair capability.

## Implemented capabilities

- One-shot mode remains the default when no interval is supplied.
- Dry-run mode still prints the privacy-minimized payload locally and requires no token.
- Scheduled foreground mode supports `--interval-seconds` and `--interval-minutes`.
- `--max-iterations` safely bounds scheduled mode for tests and demonstrations.
- `--heartbeat-only` updates endpoint presence without collecting a fresh scan.
- `Ctrl+C` exits scheduled mode cleanly.
- Retryable heartbeat, registration, and scan upload failures are written to a bounded local JSON queue.
- Queue entries store only allowlisted endpoint paths and redacted payloads.
- Queue files never store raw device tokens or request headers.
- Queue status and explicit queue flush commands are available.
- Queued uploads are retried oldest-first and deleted only after successful upload.
- Corrupted or unsafe queue files are reported and retained rather than uploaded or silently deleted.

## Commands

One-shot upload:

```bash
python -m fixmate_agent --server http://127.0.0.1:8000 --device-name "Lab Endpoint" --once
```

Dry-run payload preview:

```bash
python -m fixmate_agent --dry-run
```

Scheduled demo loop:

```bash
python -m fixmate_agent --server http://127.0.0.1:8000 --device-name "Lab Endpoint" --interval-seconds 10 --max-iterations 3
```

Heartbeat-only mode:

```bash
python -m fixmate_agent --server http://127.0.0.1:8000 --device-name "Lab Endpoint" --heartbeat-only
```

Offline queue:

```bash
python -m fixmate_agent --queue-status
python -m fixmate_agent --server http://127.0.0.1:8000 --flush-queue
```

## Environment variables

Configuration priority is CLI arguments, environment variables, then safe defaults.

- `FIXMATE_AGENT_SERVER_URL`
- `FIXMATE_SERVER_URL` as a backward-compatible alias
- `FIXMATE_DEVICE_TOKEN`
- `FIXMATE_DEVICE_ID`
- `FIXMATE_DEVICE_NAME`
- `FIXMATE_AGENT_INTERVAL_SECONDS`
- `FIXMATE_AGENT_TIMEOUT_SECONDS`
- `FIXMATE_AGENT_QUEUE_DIR`
- `FIXMATE_API_AGENT_RATE_LIMIT`
- `FIXMATE_FLEET_ONLINE_MINUTES`

## Safety boundaries

- No administrator/root privileges are required.
- No service installation is performed.
- No remote commands are accepted.
- No repairs, process termination, shell commands, port scans, or packet capture are performed.
- No screenshots, OCR text, personal document contents, browsing history, raw hostnames, full addresses, or raw tokens are sent by the endpoint agent.
- Scheduled mode is a foreground CLI process controlled by the user or terminal.

## Validation summary

- Full pytest suite passed after implementation.
- Focused agent/fleet/API tests cover one-shot, dry-run, queue status, queue flush, scheduled mode, heartbeat-only mode, failure resilience, queue retry, configuration priority, and stale replay protection.
- Manual scheduled-mode validation confirmed that unavailable-server uploads are queued without crashing and that `--max-iterations` exits automatically.

## Known limitations

- Phase 11B does not install or manage a Windows Service or Linux systemd service.
- Queue files are redacted and token-free but not encrypted.
- Queue redaction is best-effort and should be treated as local diagnostic data.
- Rate limiting is still process-local.
- Fleet reports and credential rotation remain future work.
