"""Environment-only provider configuration without dotenv or secret logging."""

from __future__ import annotations

import os
from collections.abc import Mapping

from src.llm.base import LLMProvider
from src.llm.cloud import CloudProvider
from src.llm.disabled import DisabledProvider
from src.llm.ollama import OllamaProvider


def _timeout(environment: Mapping[str, str]) -> float:
    """Parse and clamp the optional provider timeout."""
    try:
        return max(1.0, min(float(environment.get("FIXMATE_LLM_TIMEOUT_SECONDS", "15")), 30.0))
    except ValueError:
        return 15.0


def create_provider(environment: Mapping[str, str] | None = None) -> LLMProvider:
    """Create the selected provider from environment variables only."""
    env = environment if environment is not None else os.environ
    provider_name = env.get("FIXMATE_LLM_PROVIDER", "disabled").strip().casefold()
    timeout = _timeout(env)
    if provider_name == "cloud":
        return CloudProvider(
            api_url=env.get("FIXMATE_CLOUD_API_URL", ""),
            api_key=env.get("FIXMATE_CLOUD_API_KEY", ""),
            model=env.get("FIXMATE_CLOUD_MODEL", ""),
            timeout_seconds=timeout,
        )
    if provider_name == "ollama":
        return OllamaProvider(
            api_url=env.get(
                "FIXMATE_OLLAMA_URL", "http://127.0.0.1:11434/api/chat"
            ),
            model=env.get("FIXMATE_OLLAMA_MODEL", ""),
            timeout_seconds=timeout,
        )
    return DisabledProvider()
