"""Environment-only provider configuration without dotenv or secret logging."""

from __future__ import annotations

import os
from collections.abc import Mapping

from src.llm.base import LLMProvider
from src.llm.cloud import CloudProvider
from src.llm.disabled import DisabledProvider
from src.llm.ollama import OllamaProvider
from src.llm.tencent import DEFAULT_TENCENT_MODEL, TencentTokenHubProvider


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
    if provider_name in {"tencent", "tokenhub", "tencent_tokenhub", "glm"}:
        return TencentTokenHubProvider(
            api_key=env.get("TENCENT_TOKENHUB_API_KEY", ""),
            base_url=env.get("TENCENT_TOKENHUB_BASE_URL", ""),
            model=env.get("TENCENT_TOKENHUB_MODEL", DEFAULT_TENCENT_MODEL),
            timeout_seconds=timeout,
        )
    return DisabledProvider()


def list_provider_options(
    environment: Mapping[str, str] | None = None,
) -> list[tuple[str, LLMProvider]]:
    """Return selectable (label, provider) pairs for the assistant UI."""
    env = environment if environment is not None else os.environ
    timeout = _timeout(env)

    options: list[tuple[str, LLMProvider]] = [
        ("Deterministic only", DisabledProvider()),
    ]

    env_provider = create_provider(env)
    if not isinstance(env_provider, DisabledProvider):
        options.append((f"Default \u2014 {env_provider.status.name}", env_provider))

    tencent = TencentTokenHubProvider(
        api_key=env.get("TENCENT_TOKENHUB_API_KEY", ""),
        base_url=env.get("TENCENT_TOKENHUB_BASE_URL", ""),
        model=env.get("TENCENT_TOKENHUB_MODEL", DEFAULT_TENCENT_MODEL),
        timeout_seconds=timeout,
    )
    ts = tencent.status
    if ts.configured:
        options.append(("Tencent TokenHub / GLM", tencent))
    elif "API key" in ts.message:
        options.append(("Tencent TokenHub / GLM \u2014 missing API key", tencent))
    elif "base URL" in ts.message:
        options.append(("Tencent TokenHub / GLM \u2014 missing base URL", tencent))
    else:
        options.append(("Tencent TokenHub / GLM \u2014 not configured", tencent))

    cloud = CloudProvider(
        api_url=env.get("FIXMATE_CLOUD_API_URL", ""),
        api_key=env.get("FIXMATE_CLOUD_API_KEY", ""),
        model=env.get("FIXMATE_CLOUD_MODEL", ""),
        timeout_seconds=timeout,
    )
    if cloud.status.configured:
        options.append(("Cloud", cloud))

    ollama = OllamaProvider(
        api_url=env.get("FIXMATE_OLLAMA_URL", "http://127.0.0.1:11434/api/chat"),
        model=env.get("FIXMATE_OLLAMA_MODEL", ""),
        timeout_seconds=timeout,
    )
    if ollama.status.configured:
        options.append(("Ollama (local)", ollama))

    return options
