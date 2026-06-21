# Endpoint Agent

The Phase 11A agent runs one read-only diagnostic, submits a minimized result, and exits. It is not a service, accepts no remote commands, and never repairs the endpoint.

## Data sent

- Opaque device ID and user-selected display name
- OS/platform and agent version
- CPU, memory, disk, health score, boot time, and summarized network counters/status
- Count of active interfaces (not their names)
- Redacted issue evidence, explanations, and safe guidance

It excludes hostnames, process/interface names, full IP/MAC addresses, screenshots, OCR data, browsing history, file contents, credentials, and tokens.

## Run

PowerShell:

```powershell
$env:FIXMATE_DEVICE_TOKEN = Read-Host "Enrollment token"
python -m fixmate_agent --server http://127.0.0.1:8000 --device-name "Lab Endpoint"
```

Ubuntu:

```bash
export FIXMATE_DEVICE_TOKEN="replace-with-private-enrollment-token"
python -m fixmate_agent --server http://127.0.0.1:8000 --device-name "Lab Endpoint"
```

Use `python -m fixmate_agent --dry-run` to inspect JSON locally without a token or request. Optional flags include `--device-id`, `--timeout`, `--network-host`, and `--network-port`. The bounded connectivity target is one host/port, not a port scan.

The API and endpoint must receive the same `FIXMATE_DEVICE_TOKEN` during enrollment. The API stores only a salted hash. Rotate the token by changing it and intentionally re-registering endpoints.

