# FixMate AI Demo Guide

The demo generator creates a separate SQLite database containing clearly labeled synthetic records. It never collects live metrics, contacts the internet, creates screenshots, or modifies the normal `data/fixmate.db` database.

## Generate demo data

Run from the project root:

```bash
python scripts/generate_demo_data.py --output data/demo_fixmate.db --seed 2026 --days 14
```

The same command works in PowerShell and Ubuntu shells. Generated `.db` files are ignored by Git.

Generation is deterministic for a given seed and day count. Timestamps use a fixed UTC anchor so two runs can be compared reliably. Records use reserved `.invalid` hostnames, synthetic interface/process names, and an explicit `SYNTHETIC DEMO DATA - NOT A REAL DEVICE` marker.

## Safety behavior

- The script refuses `data/fixmate.db` even when explicitly supplied.
- It refuses every existing output file by default.
- `--reset-demo` replaces only a database carrying the generator's synthetic marker.
- It refuses an existing unmarked SQLite database, even with `--reset-demo`.
- It accepts only `.db`, `.sqlite`, and `.sqlite3` outputs.
- It creates no screenshots, reports, credentials, usernames, IP addresses, or MAC addresses.

Regenerate a known demo database:

```bash
python scripts/generate_demo_data.py --output data/demo_fixmate.db --seed 2026 --days 14 --reset-demo
```

## Run the application against demo data

Set the shared `FIXMATE_DB_PATH` override before application startup. It works for both Streamlit and FastAPI and leaves the normal `data/fixmate.db` untouched.

PowerShell:

```powershell
$env:FIXMATE_DB_PATH="data/demo_fixmate.db"
python -m streamlit run app.py
```

Ubuntu:

```bash
export FIXMATE_DB_PATH="data/demo_fixmate.db"
python -m streamlit run app.py
```

For FastAPI, keep the same variable set, configure a temporary `FIXMATE_API_TOKEN`, and run `python -m api.main`. Restart processes after changing database variables. Do not commit the generated database.

## Suggested five-minute demonstration

1. Explain that all displayed records are synthetic and local.
2. Show system and network history through the API or a controlled Streamlit demo database.
3. Explain deterministic issue thresholds and evidence timestamps.
4. Show screenshot matching using typed synthetic error text rather than a personal screenshot.
5. Ask the deterministic assistant, “What should I fix first?”
6. Generate a privacy-safe HTML or PDF diagnostic report.
7. Open Swagger and highlight token-protected POST endpoints.
8. End with the test matrix and Docker architecture.

## Capture your own portfolio screenshots

The SVG files in `docs/assets/` are safe mockups, not proof of live execution. Follow [SCREENSHOTS.md](SCREENSHOTS.md) for real screenshots.

1. Generate or prepare only synthetic data.
2. Check the screen for usernames, paths, IP addresses, browser tabs, notifications, and tokens.
3. Capture only the application window.
4. Crop and inspect the image before adding it to Git.
5. Label it as synthetic demo data in the caption.
