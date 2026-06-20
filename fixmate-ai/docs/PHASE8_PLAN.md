# Phase 8 Plan: Docker, Docker Compose, and GitHub Actions CI/CD

## Status

Implementation complete. Docker daemon validation remains environment-dependent and is listed under limitations.

## Goal

Provide a reproducible, beginner-friendly container deployment and automatically test every existing FixMate AI phase on Windows and Ubuntu without making Docker mandatory for normal development.

## Implementation summary

- Added a Python 3.12 slim image that installs `requirements.txt`, copies only runtime content, runs as a non-root user, exposes ports 8501/8000, and provides a local health check.
- Added separate Streamlit and FastAPI Compose services sharing one named SQLite data volume.
- Published both host ports on `127.0.0.1`; FastAPI binds to `0.0.0.0` only inside its container.
- Added explicit Docker exclusions for secrets, databases, reports, screenshots, caches, tests, virtual environments, and Git metadata.
- Added an Ubuntu/Windows and Python 3.11/3.12 GitHub Actions matrix with pip caching and the complete pytest suite.
- Added structural deployment tests and API environment-loading tests that run without Docker.
- Preserved disabled-by-default AI, optional OCR, protected API POST routes, ephemeral reports, and existing privacy controls.

## Files changed

- `Dockerfile`
- `docker-compose.yml`
- `.dockerignore`
- `.github/workflows/ci.yml`
- `api/config.py`
- `tests/test_api_environment.py`
- `tests/test_deployment_config.py`
- `.env.example`, `README.md`, and `AGENTS.md`
- `docs/DOCKER.md` and this plan

## Run locally without Docker

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

In a second terminal, configure `FIXMATE_API_TOKEN` and run `python -m api.main`. Native FastAPI defaults to `127.0.0.1:8000`.

## Run with Docker

Configure `FIXMATE_API_TOKEN`, then run:

```bash
docker compose config
docker compose build
docker compose up
docker compose logs
docker compose down
```

The `fixmate_ai_data` volume survives ordinary `docker compose down` operations.

## Continuous integration

CI runs for pull requests and pushes to `main`. Four matrix jobs cover `ubuntu-latest` and `windows-latest` with Python 3.11 and 3.12. Each job restores pip cache, installs the production requirements, and fails if any pytest test fails. No provider credentials, OCR executable, Ollama service, or live network diagnostic is required.

## Security notes

- No secret value is present in the image or tracked deployment configuration.
- Compose receives the API token only from runtime environment substitution.
- Protected POST endpoints retain constant-time token comparison, body limits, and rate limits.
- Containers run as `fixmate`, not root.
- Host ports remain loopback-only.
- The shared volume contains SQLite records only; screenshots, conversations, and generated reports remain unpersisted.

## Limitations

- Container diagnostics measure containers rather than the Docker host.
- Tesseract is intentionally omitted to keep the image smaller; manual analyzer text remains available.
- The loopback-only Ollama provider is best used through native execution.
- In-memory API rate limits remain process-local.
- Docker build, Compose rendering, and live container health require a machine with Docker installed.
