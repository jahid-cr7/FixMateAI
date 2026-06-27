"""Deployment configuration tests that do not require a Docker daemon."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent


def _read(relative_path: str) -> str:
    return (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")


def test_dockerfile_uses_slim_non_root_runtime_without_secrets() -> None:
    dockerfile = _read("Dockerfile")
    assert "FROM python:3.12-slim" in dockerfile
    assert "USER fixmate" in dockerfile
    assert "EXPOSE 8501 8000" in dockerfile
    assert "HEALTHCHECK" in dockerfile
    assert "FIXMATE_API_TOKEN=" not in dockerfile
    assert "tesseract" not in dockerfile.casefold()


def test_compose_has_two_loopback_services_and_shared_volume() -> None:
    compose = _read("docker-compose.yml")
    assert "streamlit:" in compose
    assert "api:" in compose
    assert '"127.0.0.1:8501:8501"' in compose
    assert '"127.0.0.1:8000:8000"' in compose
    assert "FIXMATE_API_HOST: 0.0.0.0" in compose
    assert "FIXMATE_API_TOKEN: ${FIXMATE_API_TOKEN:-}" in compose
    assert compose.count("fixmate_data:/app/data") == 2
    assert compose.count("FIXMATE_LLM_PROVIDER: ${FIXMATE_LLM_PROVIDER:-disabled}") == 2
    assert compose.count("TENCENT_TOKENHUB_API_KEY: ${TENCENT_TOKENHUB_API_KEY:-}") == 2
    assert compose.count("TENCENT_TOKENHUB_MODEL: ${TENCENT_TOKENHUB_MODEL:-glm-5.1}") == 2


def test_dockerignore_excludes_private_and_generated_content() -> None:
    ignored = set(_read(".dockerignore").splitlines())
    required = {
        ".git",
        ".env",
        ".env.*",
        ".venv",
        "tests",
        "reports",
        "output",
        "data/*.db",
        ".pytest_cache",
    }
    assert required <= ignored
    assert "data" not in ignored  # the local knowledge-base JSON is runtime data


def test_ci_matrix_covers_windows_ubuntu_and_supported_python() -> None:
    workflow = (REPOSITORY_ROOT / ".github/workflows/ci.yml").read_text(
        encoding="utf-8"
    )
    assert "pull_request:" in workflow
    assert "branches: [main]" in workflow
    assert "ubuntu-latest" in workflow
    assert "windows-latest" in workflow
    assert 'python-version: ["3.11", "3.12"]' in workflow
    assert "python -m pytest -v" in workflow
    assert "cache: pip" in workflow
    assert "working-directory: fixmate-ai" in workflow
    assert "cache-dependency-path: fixmate-ai/requirements.txt" in workflow
