# Safe Screenshot Workflow

The README currently uses editable SVG mockups from `docs/assets/`. They are clearly labeled `SYNTHETIC DEMO` and remain the safe fallback until reviewed real application screenshots are intentionally added.

Use only synthetic/demo records. Never capture a normal personal database or live private desktop state.

## Preparation

1. Generate a marked demo database with `scripts/generate_demo_data.py`.
2. Set `FIXMATE_DB_PATH=data/demo_fixmate.db` before starting Streamlit and FastAPI.
3. Use a temporary API token that is not visible anywhere on screen.
4. Close unrelated applications and disable desktop/browser notifications.
5. Inspect the full window for usernames, hostnames, paths, addresses, tokens, open tabs, bookmarks, and account avatars.
6. Capture only the application content—not the taskbar, terminal, browser profile, or desktop.

PowerShell demo startup:

```powershell
python scripts/generate_demo_data.py --output data/demo_fixmate.db --seed 2026 --days 14
$env:FIXMATE_DB_PATH="data/demo_fixmate.db"
python -m streamlit run app.py
```

Ubuntu:

```bash
python scripts/generate_demo_data.py --output data/demo_fixmate.db --seed 2026 --days 14
export FIXMATE_DB_PATH="data/demo_fixmate.db"
python -m streamlit run app.py
```

## Required captures

### System Health dashboard

- Show the `SYNTHETIC DEMO` dataset only.
- Include health score, CPU/memory/disk cards, synthetic top processes, issues, and history.
- Crop operating-system fields if they reveal real host information.

### Network Diagnostics

- Do not run a live diagnostic for the screenshot.
- Show stored synthetic `.invalid` target evidence and synthetic interface labels.
- Verify that no real IP, MAC, Wi-Fi name, VPN name, or adapter identifier appears.

### Error Screenshot Analyzer

- Use a generated image containing a synthetic error message.
- Do not upload a real desktop screenshot.
- Confirm OCR text contains no username, path, email, account, token, hostname, or private filename.

### Troubleshooting Assistant

- Use deterministic mode.
- Ask a supported question about synthetic evidence.
- Show evidence timestamps, severity, freshness, and guidance.
- Do not display an external provider key, prompt, or private conversation.

### Reports page

- Generate from synthetic evidence.
- Preview without displaying a filesystem save dialog or private download path.
- Confirm conversation history is excluded unless synthetic and intentionally selected.

### FastAPI Swagger

- Open `/docs` on localhost.
- Collapse request sections that could contain tokens.
- Never enter or expose `X-API-Token` in the screenshot.
- Show endpoint groups and schemas only.

## Review checklist

- [ ] Synthetic/demo data only
- [ ] No usernames, account avatars, hostnames, or personal system names
- [ ] No real IP addresses, MAC addresses, interface names, or wireless identifiers
- [ ] No Windows/Linux user paths or private filenames
- [ ] No API tokens, provider keys, `.env` contents, or terminal history
- [ ] No personal notifications, browser tabs, bookmarks, or desktop content
- [ ] No raw personal screenshots, databases, reports, or logs
- [ ] Caption states that the data is synthetic

Store approved images under `docs/assets/screenshots/`. Before committing, review each image at full resolution. Update README references only after every image has passed this checklist; otherwise keep the existing SVG mockups.

