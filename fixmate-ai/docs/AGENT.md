# Endpoint Agent

The endpoint agent runs read-only diagnostics from the command line. It supports one-shot runs, dry runs, queue inspection, queue flushing, and a foreground scheduled loop. It is not a Windows Service or Linux systemd service, accepts no remote commands, and never repairs the endpoint.

## Data sent and queued

- Opaque device ID and user-selected display name
- OS/platform and agent version
- CPU, memory, disk, health score, boot time, and summarized network counters/status
- Count of active interfaces, not their names
- Redacted issue evidence, explanations, and safe guidance

It excludes hostnames, process/interface names, full IP/MAC addresses, screenshots, OCR data, browsing history, file contents, credentials, and tokens.

When a retryable upload fails, the agent stores an allowlisted endpoint and re-redacted payload in a local JSON queue. Queue files never contain the device token or request headers. The default cross-platform location is `~/.fixmate-ai/queue`; override it with `--queue-dir` or `FIXMATE_AGENT_QUEUE_DIR`.

## Run once

PowerShell:

```powershell
$env:FIXMATE_DEVICE_TOKEN = Read-Host "Enrollment token"
python -m fixmate_agent --server http://127.0.0.1:8000 --device-name "Lab Endpoint" --once
```

Ubuntu:

```bash
export FIXMATE_DEVICE_TOKEN="replace-with-private-enrollment-token"
python -m fixmate_agent --server http://127.0.0.1:8000 --device-name "Lab Endpoint" --once
```

When no interval is provided, one-shot is still the default for backward compatibility. Use `python -m fixmate_agent --dry-run` to inspect JSON locally without a token or request.

## Scheduled foreground mode

Scheduled mode is a normal foreground CLI loop. It does not install a service, create a background daemon, or make Streamlit responsible for scheduling.

```bash
python -m fixmate_agent --server http://127.0.0.1:8000 --device-name "Lab Endpoint" --interval-seconds 10 --max-iterations 3
```

Use minutes for less frequent local demos:

```bash
python -m fixmate_agent --server http://127.0.0.1:8000 --device-name "Lab Endpoint" --interval-minutes 15
```

Each cycle sends a heartbeat first, retries queued uploads, and then runs system/network diagnostics plus scan upload unless heartbeat-only mode is enabled. Press `Ctrl+C` to stop cleanly.

Heartbeat-only mode updates device presence without collecting a fresh scan:

```bash
python -m fixmate_agent --server http://127.0.0.1:8000 --device-name "Lab Endpoint" --heartbeat-only
```

For demos and tests, combine scheduled mode with `--max-iterations` so the process exits by itself.

## Safe Windows usage

Run the agent from an activated virtual environment or with the project Python executable. Keep the terminal open while scheduled mode is running; closing the terminal stops the foreground loop.

```powershell
$env:FIXMATE_DEVICE_TOKEN = Read-Host "Enrollment token"
$env:FIXMATE_AGENT_SERVER_URL = "http://127.0.0.1:8000"
python -m fixmate_agent --device-name "Lab Endpoint" --interval-seconds 60 --max-iterations 5
```

Do not run the terminal as Administrator unless your own environment requires it for Python. FixMate AI does not need elevated privileges.

## Safe Ubuntu usage

Run from the project virtual environment. Keep the shell session open while scheduled mode runs.

```bash
export FIXMATE_DEVICE_TOKEN="replace-with-private-enrollment-token"
export FIXMATE_AGENT_SERVER_URL="http://127.0.0.1:8000"
python -m fixmate_agent --device-name "Lab Endpoint" --interval-seconds 60 --max-iterations 5
```

Do not use `sudo`; the endpoint agent is designed for ordinary user permissions.

## Offline queue

Inspect queue counts and bytes without requiring a token:

```bash
python -m fixmate_agent --queue-status
```

Retry queued entries explicitly:

```bash
python -m fixmate_agent --server http://127.0.0.1:8000 --flush-queue
```

Normal one-shot runs also retry older entries before sending the new batch. Entries are processed oldest-first and deleted only after a successful response. Corrupted or unsafe files are reported and retained rather than uploaded or silently deleted. The queue is capped at 100 files by default; `--max-queue-files` can set a validated bound.

## Configuration priority

Configuration priority is CLI arguments, then environment variables, then safe defaults. Useful variables:

- `FIXMATE_AGENT_SERVER_URL`
- `FIXMATE_DEVICE_TOKEN`
- `FIXMATE_DEVICE_NAME`
- `FIXMATE_AGENT_INTERVAL_SECONDS`
- `FIXMATE_AGENT_TIMEOUT_SECONDS`
- `FIXMATE_AGENT_QUEUE_DIR`

`FIXMATE_SERVER_URL` remains supported as a backward-compatible alias, but `FIXMATE_AGENT_SERVER_URL` is clearer for endpoint use. The API and endpoint must receive the same `FIXMATE_DEVICE_TOKEN`; the token is used only in memory and is never queued.

## Current limitations

Phase 11B intentionally stops before service installation. It does not create a Windows Service, Linux systemd unit, launch agent, scheduled task, or background daemon. It also does not provide remote control, remote shell, repair actions, credential rotation UI, or fleet-aware report exports.
