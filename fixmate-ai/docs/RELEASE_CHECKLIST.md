# v1.0.0 Release Checklist

## Code and tests

- [ ] Activate a clean Python 3.11 or 3.12 environment.
- [ ] Install `requirements.txt`.
- [ ] Run `python -m pytest -v` and record the passing result.
- [ ] Confirm GitHub Actions passes on Windows and Ubuntu.
- [ ] Confirm `src.__version__` and FastAPI metadata report `1.0.0`.

## Application startup

- [ ] Run `python -m streamlit run app.py`.
- [ ] Open every Streamlit page and check for exceptions.
- [ ] Configure a temporary local `FIXMATE_API_TOKEN`.
- [ ] Run `python -m api.main`.
- [ ] Verify `/health`, `/docs`, and `/api/v1/status`.
- [ ] Confirm native FastAPI binds to `127.0.0.1` by default.

## Synthetic demo

- [ ] Generate `data/demo_fixmate.db` with a documented seed.
- [ ] Confirm the generator refuses an existing output without `--reset-demo`.
- [ ] Set `FIXMATE_DB_PATH=data/demo_fixmate.db` before demo startup.
- [ ] Verify the UI/API shows only marked synthetic evidence.
- [ ] Remove the generated database after validation if it is no longer needed.

## Privacy and repository hygiene

- [ ] Run `git status --short` and inspect every file.
- [ ] Confirm no `.env`, `.db`, `.sqlite`, report, log, cache, virtual environment, or raw screenshot is tracked.
- [ ] Scan for API keys, tokens, usernames, user paths, real addresses, and personal data.
- [ ] Validate every README/docs link and image path.
- [ ] Review real screenshots using [SCREENSHOTS.md](SCREENSHOTS.md), or retain synthetic SVG mockups.
- [ ] Confirm report exports and conversation history are not persisted.

## Docker when available

- [ ] Run `docker compose config`.
- [ ] Run `docker compose build`.
- [ ] Run `docker compose up -d`.
- [ ] Verify both service health checks and localhost-only published ports.
- [ ] Run `docker compose down` without deleting the data volume unintentionally.

## GitHub presentation

- [ ] Configure description and topics from [GITHUB_SETUP.md](GITHUB_SETUP.md).
- [ ] Confirm the MIT License is visible.
- [ ] Enable issue templates and private vulnerability reporting.
- [ ] Confirm README badges render after publishing.
- [ ] Review CV bullets, demo script, and interview guide for truthful claims.

## Commit, push, and release

Run these commands from the repository root (the directory containing `fixmate-ai/`):

```bash
git status --short
git add .
git commit -m "chore: prepare FixMate AI v1.0.0 release"
git push origin main
git tag -a v1.0.0 -m "FixMate AI v1.0.0"
git push origin v1.0.0
```

Create a GitHub release from tag `v1.0.0`, copy the v1.0.0 changelog notes, and attach no private/generated artifacts.
