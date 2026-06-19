# FixMate AI

FixMate AI is a read-only, cross-platform IT support dashboard for Windows and Ubuntu. It collects basic system and network metrics, detects common problems, stores local history in SQLite, and displays safe troubleshooting guidance.

## Features

- CPU, memory, disk, operating-system, boot-time, and top-process metrics
- Detection for CPU usage above 90%, memory usage above 85%, and disk free space below 10%
- Active network interfaces and cumulative sent/received byte counters
- Configurable internet connectivity, timeout, and latency checks
- Severity, evidence, explanations, and safe recommendations for network issues
- SQLite history and interactive Plotly charts
- Deterministic tests using simulated system values and mocked network operations

FixMate AI never requires administrator/root access, reads no file contents, captures no packets, scans no ports, and performs no repair actions.

## Requirements

- Python 3.11 or newer
- Windows 10/11 or a current Ubuntu release

## Windows setup

Open PowerShell in the `fixmate-ai` directory:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

If PowerShell blocks activation, run the environment's Python directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

If your prompt is at `D:\FixMateAI` instead of the project directory, first run:

```powershell
cd .\fixmate-ai
```

## Ubuntu setup

Open a terminal in the `fixmate-ai` directory:

```bash
sudo apt update
sudo apt install python3.11 python3.11-venv
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

The `sudo` commands install Python only; running FixMate AI itself does not require root privileges.

## Network diagnostics

Open the **Network Diagnostics** tab and configure:

- Connectivity host (default: `1.1.1.1`)
- TCP port (default: `443`)
- Short timeout from 0.1 to 5 seconds
- High-latency threshold in milliseconds

Select **Run new diagnostic** to store a result. The dashboard shows connection and internet status, latency, active interface names, cumulative sent/received byte counters, detected issues, and historical Plotly charts.

The diagnostic performs one TCP connection to the configured host and port. It is not a port scan and does not execute `ping`, repair commands, or operating-system-specific network commands. A failed result proves only that this particular test could not connect; captive portals, firewalls, VPNs, or a blocked target may also affect it.

## Tests

```bash
python -m pytest
```

All network operations are mocked in automated tests, so tests do not require internet access.

## Data and privacy

History is saved locally to `data/fixmate.db`, which is ignored by Git. Collected data is limited to performance percentages, operating-system details, boot time, process names/PIDs/memory usage, interface names, connectivity results, latency, and byte counters.

Complete MAC addresses, passwords, browsing history, packet contents, personal documents, and file contents are never collected. Database migrations are additive and preserve existing system-health records.

## Project structure

- `app.py` — Streamlit user interface
- `src/collector.py` — safe system metric collection
- `src/detector.py` — pure system threshold rules
- `src/network_collector.py` — interface, traffic, connectivity, and latency collection
- `src/network_detector.py` — pure network issue rules
- `src/database.py` — SQLite migrations and persistence
- `src/health_score.py` — transparent score calculation
- `src/recommendations.py` — safe guidance text
- `tests/` — simulated and mocked automated tests
- `docs/PHASE3_PLAN.md` — saved design only; Phase 3 is not implemented

## Current limitations

Diagnostics run only when requested, and connectivity is inferred from one configured TCP target. Byte counters are cumulative since operating-system startup, not per-application traffic. The project does not include authentication, OCR, an API, an external LLM, Docker, background monitoring, notifications, or automatic repairs.

