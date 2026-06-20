# FixMate AI

FixMate AI is a read-only, cross-platform IT support dashboard for Windows and Ubuntu. It combines system health checks, network diagnostics, a local error-screenshot analyzer, and a deterministic evidence-based troubleshooting assistant.

## Features

- CPU, memory, disk, operating-system, boot-time, and top-process metrics
- Threshold-based system issue detection and health scoring
- Active network interfaces, traffic counters, connectivity, and latency diagnostics
- SQLite history with additive, non-destructive migrations
- Local PNG/JPG/JPEG screenshot analysis up to 5 MB
- OpenCV grayscale, contrast, denoising, and optional threshold preprocessing
- Local Tesseract OCR with editable extracted text
- Deterministic matching against 15 curated Windows and Ubuntu problems
- Confidence scores, matching evidence, and safe troubleshooting steps
- Privacy redaction before OCR text is stored
- Deterministic natural-language question routing over collected local evidence
- Chat-style troubleshooting answers with timestamps, severity, evidence, freshness, and safe guidance
- Versioned, localhost-first FastAPI endpoints with OpenAPI documentation

FixMate AI never requires administrator/root access, executes repairs, scans ports, captures packets, runs screenshot text, or stores uploaded screenshot files.

Deterministic mode remains the default source of truth. Phase 5 can optionally add a labeled LLM explanation, but the application works normally without an API key, internet, Ollama, or any model.

## Running Streamlit and FastAPI

Start the dashboard and API in separate terminals from the `fixmate-ai` directory:

```powershell
# Terminal 1
python -m streamlit run app.py

# Terminal 2: create a private token for this shell only
$env:FIXMATE_API_TOKEN = Read-Host "Enter a local API token"
python -m api.main
```

On Ubuntu, use `export FIXMATE_API_TOKEN="your-private-random-token"` before `python -m api.main`. The API binds to `127.0.0.1:8000` by default. Open `http://127.0.0.1:8000/docs` for interactive Swagger documentation. Never place a real token in `.env.example` or commit it.

GET routes are read-only and do not require authentication. POST routes require the token in the `X-API-Token` header; when no token is configured, POST routes are intentionally unavailable. Example:

```powershell
Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/api/v1/system/scans `
  -Headers @{ "X-API-Token" = $env:FIXMATE_API_TOKEN }
```

The API provides `/health`, `/api/v1/status`, system scan/history, network diagnostic/history, filtered issues, privacy-safe screenshot-analysis metadata, and deterministic or optional consent-gated assistant queries. History uses `page` and `page_size`; issue records also support date, severity, and type filters. CORS origins, request size, rate limits, host, port, database path, and token are configured through the documented `FIXMATE_API_*` environment variables in `.env.example`.

## Requirements

- Python 3.11 or newer
- Windows 10/11 or a current Ubuntu release
- Tesseract OCR is optional but required for automatic text extraction

The main system-health and network dashboard works normally without Tesseract. The analyzer still permits manual error-text entry when OCR is unavailable.

## Windows setup

Open PowerShell in the `fixmate-ai` directory:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

If your prompt is at `D:\FixMateAI`, first run:

```powershell
cd .\fixmate-ai
```

### Windows Tesseract installation

1. Install a trusted current Windows build of Tesseract OCR.
2. During installation, note the executable path. A common location is:

   ```text
   C:\Program Files\Tesseract-OCR\tesseract.exe
   ```

3. Add the Tesseract directory to `PATH`, or set the explicit command location:

   ```powershell
   setx TESSERACT_CMD "C:\Program Files\Tesseract-OCR\tesseract.exe"
   ```

4. Open a new PowerShell window and verify:

   ```powershell
   tesseract --version
   ```

`TESSERACT_CMD` is useful when Tesseract is installed but intentionally not added to the global `PATH`.

## Ubuntu setup

```bash
sudo apt update
sudo apt install python3.11 python3.11-venv tesseract-ocr
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Verify OCR installation with:

```bash
tesseract --version
```

The `sudo` commands install system packages only; running FixMate AI does not require root privileges.

## Using the Error Screenshot Analyzer

1. Open **Error Screenshot Analyzer** from Streamlit's page navigation.
2. Review the privacy warning and upload a PNG, JPG, or JPEG no larger than 5 MB.
3. Compare the original and processed previews. Disable thresholding if colored text becomes less readable.
4. Select **Extract text with local OCR**, or type the message manually if Tesseract is unavailable.
5. Correct OCR mistakes in the editable text box.
6. Select **Analyze error text** to view ranked reliable matches.

If no result reaches the 60% confidence threshold, the page displays **No reliable match found** and does not invent a solution.

## Network diagnostics

Open the **Network Diagnostics** tab to configure a host, TCP port, short timeout, and high-latency threshold. The test performs one TCP connection; it is not a port scan. Traffic counters are cumulative operating-system counters.

## Troubleshooting Assistant

Open **Troubleshooting Assistant** from Streamlit's page navigation. It supports these question categories:

- Why is my computer slow?
- What is using the most memory?
- Is my disk nearly full?
- Is my internet connection working?
- Why is my network slow?
- What problems were detected today?
- Explain my latest screenshot error.
- Summarize this computer's health.
- What should I fix first?

Each answer provides a direct conclusion, the evidence used, its relevant timestamp and freshness, severity where applicable, and explicitly labeled guidance. When data is missing, stale, or conflicting, the assistant says so instead of inventing a cause.

Questions and conversation history are held only in Streamlit session state and are not stored in SQLite. Deterministic mode sends nothing externally; cloud AI mode may send the current redacted question and minimized evidence only after explicit consent. Use **Clear conversation** to remove the current session's messages.

## Optional AI-enhanced mode

The Troubleshooting Assistant offers two modes:

- **Deterministic** — default, fully local, and based only on explicit Phase 4 routing.
- **AI-enhanced (optional)** — keeps the deterministic answer authoritative and adds a labeled plain-language explanation from a configured provider.

The optional model can request only nine approved read-only tools. It cannot access arbitrary SQL, files, the shell, processes, operating-system settings, network scanning, or repairs. It cannot replace the deterministic direct answer, evidence, timestamps, severity, freshness, or recommendations.

Provider output is rejected and replaced with the deterministic answer when it is malformed, ungrounded, unsafe, excessive, stale-obscuring, or unavailable.

### Configuration

FixMate AI reads configuration from environment variables. It does not automatically load `.env` files. See `.env.example` for safe placeholders.

The default requires no configuration:

```powershell
$env:FIXMATE_LLM_PROVIDER="disabled"
```

Optional HTTPS cloud provider using a chat-completions-compatible endpoint:

```powershell
$env:FIXMATE_LLM_PROVIDER="cloud"
$env:FIXMATE_CLOUD_API_URL="https://your-provider.example/v1/chat/completions"
$env:FIXMATE_CLOUD_MODEL="your-model-name"
$env:FIXMATE_CLOUD_API_KEY = Read-Host "Enter the provider API key for this shell session"
$env:FIXMATE_LLM_TIMEOUT_SECONDS="15"
streamlit run app.py
```

Cloud mode requires checking the external-data consent box before any question or minimized evidence is sent.

Optional loopback-only Ollama-compatible provider:

```powershell
$env:FIXMATE_LLM_PROVIDER="ollama"
$env:FIXMATE_OLLAMA_URL="http://127.0.0.1:11434/api/chat"
$env:FIXMATE_OLLAMA_MODEL="your-installed-local-model"
streamlit run app.py
```

The Ollama-compatible URL must use `localhost`, `127.0.0.1`, or `::1`. Installing, downloading, and running a local model is separate from FixMate AI.

On Ubuntu, use equivalent `export FIXMATE_...="value"` commands before starting Streamlit.

### External privacy and cost

With explicit cloud consent, FixMate AI may send the redacted question, deterministic answer fields, timestamps, metrics, severity, and minimized approved-tool results. It excludes screenshots, OCR text, API keys, usernames identified by redaction, process names in tool output, complete IP/MAC addresses, and sensitive paths.

Redaction is best-effort. Review questions before using a cloud provider. Cloud providers may retain requests or charge per token according to their own policies; FixMate AI cannot control those policies or costs. Local Ollama-compatible inference avoids cloud transmission but uses local CPU, memory, disk, and power.

## Tests

```bash
python -m pytest
```

Tests generate images in memory and mock OCR and network operations. They require neither Tesseract nor internet access.

## Data and privacy

History is stored locally in `data/fixmate.db`, which is ignored by Git. Screenshot files and image bytes are never written to the database or filesystem.

The troubleshooting assistant opens SQLite in read-only mode and creates no conversation table. Evidence is redacted again before display, including likely IP addresses, MAC addresses, email addresses, credentials, usernames contained in paths, and sensitive paths.

Optional providers never receive database handles or direct access to SQLite. A bounded agent executes at most four validated tool requests and two provider calls per question. Screenshot files and OCR text are never included in provider payloads.

Before OCR text is stored, FixMate AI redacts likely:

- Passwords, API keys, tokens, and bearer values
- Email addresses
- Windows and Linux user-specific paths

Redaction is best-effort and cannot guarantee that every personal detail will be recognized. Crop or redact screenshots before upload and avoid screenshots containing secrets. Processing is local, but the editable text remains visible in the current Streamlit session.

## Missing OCR troubleshooting

If the analyzer reports that Tesseract is unavailable:

1. Confirm `tesseract --version` works in a new terminal.
2. Restart Streamlit after installing Tesseract or changing `PATH`.
3. On Windows, set `TESSERACT_CMD` to the complete executable path.
4. Continue by entering the error message manually; the rest of the analyzer does not depend on Tesseract.

## Project structure

- `app.py` — Phase 1 and Phase 2 Streamlit dashboard
- `api/` — Phase 6 FastAPI application, routers, schemas, security, and services
- `pages/2_Error_Screenshot_Analyzer.py` — Phase 3 analyzer page
- `pages/3_Troubleshooting_Assistant.py` — Phase 4 deterministic chat page
- `src/assistant_tools.py` — read-only evidence tools
- `src/troubleshooting_assistant.py` — intent routing and answer generation
- `src/safe_agent_tools.py` — strict minimized read-only provider tool allowlist
- `src/hybrid_agent.py` — bounded explanation orchestration and deterministic fallback
- `src/llm/` — isolated disabled, cloud, and loopback Ollama providers
- `.env.example` — credential-free optional configuration template
- `src/image_processing.py` — validation and OpenCV preprocessing
- `src/ocr.py` — optional local Tesseract integration
- `src/error_matcher.py` — deterministic confidence-ranked matching
- `src/knowledge_base.py` — trusted JSON loader
- `src/privacy.py` — anonymization and redaction
- `data/error_knowledge_base.json` — curated local troubleshooting entries
- `src/database.py` — additive migrations and persistence for all phases
- `tests/` — simulated, generated, and mocked automated tests
- `tests/api/` — isolated FastAPI endpoint, security, filtering, and failure tests

## Current limitations

- OCR accuracy depends on screenshot resolution, font, contrast, language, and Tesseract quality.
- The knowledge base covers common errors but is not a general diagnostic engine.
- Confidence is deterministic heuristic evidence, not a statistical probability.
- Redaction is best-effort; users should remove sensitive information before uploading.
- Connectivity represents one configured TCP target, and network byte counters are cumulative.
- Intent detection recognizes supported wording and reliable knowledge-base matches, not arbitrary questions.
- Recommendations are guidance rather than guaranteed fixes.
- The assistant cannot infer events that were not captured in a scan or diagnostic.
- Freshness labels do not make old evidence current; run new diagnostics when conditions change.
- Optional model explanations can be inaccurate and are always secondary to deterministic evidence.
- Cloud configuration and pricing depend on the selected compatible provider.
- Local models require separate installation and may be slow on modest hardware.
- FixMate AI is not autonomous and never claims to have repaired the computer.
- The in-memory API rate limiter is process-local; multi-worker deployments need a shared limiter.
- Local token authentication protects POST routes but is not a replacement for TLS or an internet-facing identity system. The API is designed for localhost use.
