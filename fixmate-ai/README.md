# FixMate AI

FixMate AI is a read-only, cross-platform IT support dashboard for Windows and Ubuntu. The MVP collects basic system metrics, detects common resource problems, stores scan history in SQLite, and displays safe troubleshooting guidance.

## MVP features

- CPU, memory, disk, operating-system, boot-time, and top-process metrics
- Detection for CPU usage above 90%, memory usage above 85%, and disk free space below 10%
- Severity, explanation, and safe recommendation for every issue
- SQLite scan history and interactive Plotly charts
- Deterministic pytest tests that use simulated values

FixMate AI never requires administrator/root access, reads no file contents, and performs no repair actions.

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

If PowerShell blocks activation, you can run the environment's Python directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
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

## Tests

```bash
python -m pytest
```

## Data and privacy

Scan history is saved locally to `data/fixmate.db`. That database is ignored by Git. Collected data is limited to performance percentages, operating-system details, boot time, and process names/PIDs/memory usage. Passwords, browser history, personal documents, and file contents are never collected.

## Project structure

- `app.py` — Streamlit user interface
- `src/collector.py` — safe cross-platform metric collection
- `src/detector.py` — pure threshold rules
- `src/database.py` — SQLite schema and persistence
- `src/health_score.py` — transparent score calculation
- `src/recommendations.py` — safe guidance text
- `tests/` — simulated rule and scoring tests

## Current limitations

This first phase uses fixed thresholds and local-only storage. It does not include authentication, OCR, an API, an external LLM, Docker, background monitoring, notifications, or automatic repairs.

