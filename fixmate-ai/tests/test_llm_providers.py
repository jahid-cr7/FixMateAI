"""Offline tests for optional provider configuration and response parsing."""

from __future__ import annotations

from typing import Any

import pytest

from src.llm.base import ProviderError
from src.llm.cloud import CloudProvider
from src.llm.disabled import DisabledProvider
from src.llm.factory import create_provider
from src.llm.ollama import OllamaProvider


def test_default_provider_is_disabled() -> None:
    """No environment configuration must keep all LLM activity disabled."""
    provider = create_provider({})
    assert isinstance(provider, DisabledProvider)
    assert provider.status.configured is False
    assert provider.status.external is False


def test_cloud_provider_requires_all_credentials() -> None:
    """Missing API URL, model, or key should fail before any request."""
    provider = CloudProvider("https://provider.example/v1/chat/completions", "", "model")
    assert provider.status.configured is False
    with pytest.raises(ProviderError, match="missing or invalid"):
        provider.complete([{"role": "user", "content": "test"}])


def test_cloud_provider_uses_injected_transport_without_exposing_key() -> None:
    """A configured cloud provider should parse mocked chat-completions output."""
    captured: dict[str, Any] = {}

    def transport(
        url: str,
        payload: dict[str, Any],
        headers: dict[str, str],
        timeout: float,
    ) -> dict[str, Any]:
        captured.update(url=url, payload=payload, headers=headers, timeout=timeout)
        return {"choices": [{"message": {"content": '{"explanation":"ok"}'}}]}

    secret = "super-secret-provider-key"
    provider = CloudProvider(
        "https://provider.example/v1/chat/completions",
        secret,
        "model-a",
        timeout_seconds=99,
        transport=transport,
    )
    result = provider.complete([{"role": "user", "content": "test"}])
    assert result == '{"explanation":"ok"}'
    assert captured["timeout"] == 30.0
    assert secret not in provider.status.message


def test_cloud_provider_rejects_malformed_response_shape() -> None:
    """Mocked non-chat output should become a sanitized provider error."""
    provider = CloudProvider(
        "https://provider.example/v1/chat/completions",
        "secret",
        "model",
        transport=lambda *args: {"unexpected": True},
    )
    with pytest.raises(ProviderError, match="invalid response shape"):
        provider.complete([{"role": "user", "content": "test"}])


def test_ollama_requires_loopback_and_model() -> None:
    """The local provider must not accept a remote Ollama-compatible URL."""
    remote = OllamaProvider("http://192.0.2.5:11434/api/chat", "model")
    missing_model = OllamaProvider(model="")
    assert remote.status.configured is False
    assert missing_model.status.configured is False


def test_ollama_parses_mocked_local_response() -> None:
    """The loopback provider should parse mocked Ollama output offline."""
    provider = OllamaProvider(
        model="local-model",
        transport=lambda *args: {"message": {"content": '{"tool_requests":[]}' }},
    )
    assert provider.status.configured is True
    assert provider.status.external is False
    assert provider.complete([{"role": "user", "content": "test"}]) == '{"tool_requests":[]}'


def test_factory_validates_invalid_provider_name_as_disabled() -> None:
    """Unknown provider names should never trigger a network-capable provider."""
    provider = create_provider({"FIXMATE_LLM_PROVIDER": "not-real"})
    assert isinstance(provider, DisabledProvider)

