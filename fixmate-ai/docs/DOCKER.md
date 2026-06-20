# Running FixMate AI with Docker

Docker support is optional and intended for reproducible demos, portfolio review, and local service deployment. Use native Python when you want FixMate AI to measure the actual Windows or Ubuntu computer; containers can observe only their own resource and network namespaces.

## Prerequisites

- Docker Desktop on Windows, or Docker Engine with the Compose plugin on Ubuntu
- Ports `8501` and `8000` available on local loopback
- A private API token for protected POST endpoints

Verify the installation:

```bash
docker --version
docker compose version
```

## Start both services

PowerShell:

```powershell
$env:FIXMATE_API_TOKEN = Read-Host "Enter a local API token"
docker compose config
docker compose build
docker compose up
```

Ubuntu:

```bash
export FIXMATE_API_TOKEN="replace-with-a-private-random-token"
docker compose config
docker compose build
docker compose up
```

Streamlit is available at `http://127.0.0.1:8501`; FastAPI is available at `http://127.0.0.1:8000`, with Swagger at `/docs`.

Use detached mode with `docker compose up -d`. Inspect health and logs with:

```bash
docker compose ps
docker compose logs --follow
```

Stop services without deleting history:

```bash
docker compose down
```

The optional `docker compose down --volumes` also removes the named SQLite volume and its records.

## Architecture

The same Python 3.12 slim image runs two commands:

- `streamlit` serves the dashboard on container port 8501.
- `api` serves FastAPI on container port 8000.

Both mount `fixmate_ai_data` at `/app/data`. Streamlit initializes the shared database first; the API waits for Streamlit's health check before starting. Container processes run as the unprivileged `fixmate` user.

FastAPI binds to `0.0.0.0` inside its container so Docker can forward traffic. Compose publishes both ports as `127.0.0.1:host-port:container-port`, preserving localhost-only host access. Native `python -m api.main` continues to default to `127.0.0.1`.

## Environment and secrets

Compose reads `FIXMATE_API_TOKEN` from the invoking environment or an untracked local `.env` file. Never place a real token in `.env.example`, `docker-compose.yml`, or the Dockerfile.

Optional cloud-provider variables can also be supplied from the environment, but `FIXMATE_LLM_PROVIDER` defaults to `disabled`. External consent checks and deterministic fallback remain unchanged. The image does not include Tesseract or Ollama, and neither is required for startup.

## Privacy

- SQLite stays in a local Docker volume.
- Uploaded screenshots and report exports are not persisted.
- Conversation history remains in Streamlit session memory.
- `.dockerignore` excludes credentials, databases, reports, caches, tests, virtual environments, and Git metadata.
- No repair, shell, packet capture, port scan, or unrestricted agent capability is added.

## Troubleshooting

- If a POST endpoint returns 503, configure `FIXMATE_API_TOKEN` and recreate the API container.
- If a port is in use, stop the conflicting local service before starting Compose.
- If health checks fail, run `docker compose logs streamlit api`.
- If OCR reports Tesseract missing, enter the error text manually or run FixMate AI natively with local Tesseract installed.
- Local Ollama on the host is not reached through container loopback; use native FixMate AI for the loopback-only Ollama provider.
