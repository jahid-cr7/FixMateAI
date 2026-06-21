# Contributing to FixMate AI

Thank you for considering a contribution. FixMate AI is a read-only, local-first diagnostic portfolio project; changes must preserve those safety boundaries.

## Before opening an issue

- Search existing issues and documentation.
- Remove usernames, paths, addresses, tokens, screenshots, databases, logs, and diagnostic evidence.
- Use synthetic values in reproduction steps.
- Report security concerns privately through GitHub private vulnerability reporting when available. Do not publish a real secret or private record.

## Development setup

Windows PowerShell:

```powershell
cd .\fixmate-ai
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pytest -v
```

Ubuntu:

```bash
cd fixmate-ai
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pytest -v
```

Tesseract, Docker, Ollama, internet access, and external AI credentials are not required for the automated suite.

## Contribution rules

- Support Python 3.11+ on Windows and Ubuntu.
- Use type hints and docstrings for public functions.
- Keep collectors, rules, persistence, privacy, services, and UI separate.
- Use `pathlib` and parameterized SQLite queries.
- Mock OCR, provider, and network operations in tests.
- Never add automatic repairs, shell execution, unrestricted SQL/filesystem access, packet capture, port scanning, or credential collection.
- Treat questions, OCR text, database values, and provider output as untrusted data.
- Preserve deterministic behavior as the source of truth.
- Do not commit `.env`, databases, reports, logs, screenshots containing private data, caches, or virtual environments.

## Pull requests

1. Keep the change focused.
2. Add or update tests for behavior changes.
3. Run `python -m pytest -v` from `fixmate-ai/`.
4. Validate Streamlit and FastAPI when relevant.
5. Update documentation and phase plans when behavior changes.
6. Complete the repository pull-request template.

By contributing, you agree that your contribution is provided under the repository's MIT License.
