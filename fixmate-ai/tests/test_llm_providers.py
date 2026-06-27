"""Offline tests for optional provider configuration and response parsing."""

from __future__ import annotations

from typing import Any

import pytest

from src.llm.base import ProviderError
from src.llm.cloud import CloudProvider
from src.llm.disabled import DisabledProvider
from src.llm.factory import create_provider
from src.llm.ollama import OllamaProvider
from src.llm.tencent import DEFAULT_TENCENT_MODEL, TencentTokenHubProvider


class FakeTencentClient:
    """Tiny OpenAI-compatible fake for offline Tencent provider tests."""

    def __init__(self, responses: list[Any]) -> None:
        self.responses = list(responses)
        self.calls: list[dict[str, Any]] = []
        self.chat = self
        self.completions = self

    def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


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


def test_tencent_provider_reports_missing_api_key_and_base_url() -> None:
    """Tencent setup should identify missing fields without exposing secrets."""
    missing_key = TencentTokenHubProvider(
        api_key="",
        base_url="https://api.lkeap.cloud.tencent.com/plan/v3",
    )
    assert missing_key.status.configured is False
    assert "API key" in missing_key.status.message
    with pytest.raises(ProviderError, match="API key"):
        missing_key.complete([{"role": "user", "content": "test"}])

    missing_url = TencentTokenHubProvider(api_key="secret", base_url="")
    assert missing_url.status.configured is False
    assert "base URL" in missing_url.status.message
    assert "secret" not in missing_url.status.message


def test_factory_creates_tencent_provider_from_environment() -> None:
    """Tencent TokenHub should be selectable by environment only."""
    provider = create_provider(
        {
            "FIXMATE_LLM_PROVIDER": "tencent",
            "TENCENT_TOKENHUB_API_KEY": "placeholder-tokenhub-test-key",
            "TENCENT_TOKENHUB_BASE_URL": "https://api.lkeap.cloud.tencent.com/plan/v3",
            "TENCENT_TOKENHUB_MODEL": "",
        }
    )
    assert isinstance(provider, TencentTokenHubProvider)
    assert provider.status.configured is True
    assert provider.status.external is True
    assert DEFAULT_TENCENT_MODEL in provider.status.message
    assert "placeholder-tokenhub-test-key" not in provider.status.message


def test_tencent_provider_uses_openai_compatible_client_without_leaking_key() -> None:
    """A mocked OpenAI-compatible client should receive safe chat-completion args."""
    fake = FakeTencentClient(
        [{"choices": [{"message": {"content": '{"tool_requests":[]}'}}]}]
    )
    captured: dict[str, Any] = {}

    def factory(**kwargs: Any) -> FakeTencentClient:
        captured.update(kwargs)
        return fake

    secret = "placeholder-tokenhub-test-key"
    provider = TencentTokenHubProvider(
        api_key=secret,
        base_url="https://api.lkeap.cloud.tencent.com/plan/v3",
        model="glm-5.1",
        timeout_seconds=2,
        client_factory=factory,
    )
    result = provider.complete([{"role": "user", "content": "test"}])
    assert result == '{"tool_requests":[]}'
    assert captured["api_key"] == secret
    assert captured["base_url"] == "https://api.lkeap.cloud.tencent.com/plan/v3"
    assert captured["timeout"] == 2
    assert fake.calls[0]["model"] == "glm-5.1"
    assert fake.calls[0]["response_format"] == {"type": "json_object"}
    assert secret not in provider.status.message


def test_tencent_provider_sanitizes_timeout_auth_and_malformed_response() -> None:
    """Provider failures should produce generic safe ProviderError messages."""
    class AuthenticationError(Exception):
        pass

    secret = "placeholder-tokenhub-test-key"
    for response, expected in (
        (TimeoutError(f"timeout {secret}"), "timed out"),
        (AuthenticationError(f"auth failed {secret}"), "authentication failed"),
        ({"unexpected": True}, "invalid response shape"),
    ):
        provider = TencentTokenHubProvider(
            api_key=secret,
            base_url="https://api.lkeap.cloud.tencent.com/plan/v3",
            client_factory=lambda **_: FakeTencentClient([response]),
        )
        with pytest.raises(ProviderError) as error:
            provider.complete([{"role": "user", "content": "test"}])
        assert expected in str(error.value)
        assert secret not in str(error.value)


def test_list_provider_options_includes_deterministic_by_default() -> None:
    """Empty environment must always offer Deterministic only."""
    from src.llm.factory import list_provider_options

    options = list_provider_options({})
    assert options[0][0] == "Deterministic only"
    assert isinstance(options[0][1], DisabledProvider)


def test_list_provider_options_shows_tencent_configured() -> None:
    """Tencent should appear without warning when credentials are present."""
    from src.llm.factory import list_provider_options

    options = list_provider_options(
        {
            "TENCENT_TOKENHUB_API_KEY": "test-key",
            "TENCENT_TOKENHUB_BASE_URL": "https://api.lkeap.cloud.tencent.com/plan/v3",
        }
    )
    tencent_labels = [l for l, _ in options if "Tencent" in l]
    assert len(tencent_labels) == 1
    assert "missing" not in tencent_labels[0].casefold()


def test_list_provider_options_shows_tencent_missing_key() -> None:
    """Tencent should indicate missing API key when only base URL is set."""
    from src.llm.factory import list_provider_options

    options = list_provider_options(
        {
            "TENCENT_TOKENHUB_BASE_URL": "https://api.lkeap.cloud.tencent.com/plan/v3",
        }
    )
    tencent_labels = [l for l, _ in options if "Tencent" in l]
    assert len(tencent_labels) == 1
    assert "missing API key" in tencent_labels[0]


def test_list_provider_options_shows_tencent_missing_url() -> None:
    """Tencent should indicate missing base URL when only API key is set."""
    from src.llm.factory import list_provider_options

    options = list_provider_options(
        {
            "TENCENT_TOKENHUB_API_KEY": "test-key",
        }
    )
    tencent_labels = [l for l, _ in options if "Tencent" in l]
    assert len(tencent_labels) == 1
    assert "missing base URL" in tencent_labels[0]


def test_list_provider_options_default_env_provider() -> None:
    """When FIXMATE_LLM_PROVIDER is set, Default option should appear."""
    from src.llm.factory import list_provider_options

    options = list_provider_options(
        {
            "FIXMATE_LLM_PROVIDER": "tencent",
            "TENCENT_TOKENHUB_API_KEY": "test-key",
            "TENCENT_TOKENHUB_BASE_URL": "https://api.lkeap.cloud.tencent.com/plan/v3",
        }
    )
    default_labels = [l for l, _ in options if l.startswith("Default")]
    assert len(default_labels) == 1
    assert "Tencent" in default_labels[0]


def test_list_provider_options_does_not_leak_secret() -> None:
    """No label or provider status should contain the API key."""
    from src.llm.factory import list_provider_options

    secret = "super-secret-key-abc123"
    options = list_provider_options(
        {
            "TENCENT_TOKENHUB_API_KEY": secret,
            "TENCENT_TOKENHUB_BASE_URL": "https://api.lkeap.cloud.tencent.com/plan/v3",
        }
    )
    for label, provider in options:
        assert secret not in label
        assert secret not in provider.status.message


def test_list_provider_options_shows_cloud_if_configured() -> None:
    """Cloud should appear only when fully configured."""
    from src.llm.factory import list_provider_options

    options = list_provider_options(
        {
            "FIXMATE_CLOUD_API_URL": "https://provider.example/v1/chat/completions",
            "FIXMATE_CLOUD_API_KEY": "cloud-key",
            "FIXMATE_CLOUD_MODEL": "model-a",
        }
    )
    cloud_labels = [l for l, _ in options if "Cloud" in l]
    assert len(cloud_labels) == 1


def test_list_provider_options_hides_unconfigured_cloud() -> None:
    """Cloud should not appear when configuration is incomplete."""
    from src.llm.factory import list_provider_options

    options = list_provider_options(
        {
            "FIXMATE_CLOUD_API_URL": "",
            "FIXMATE_CLOUD_API_KEY": "",
            "FIXMATE_CLOUD_MODEL": "",
        }
    )
    cloud_labels = [l for l, _ in options if "Cloud" in l]
    assert len(cloud_labels) == 0


def test_list_provider_options_shows_ollama_if_configured() -> None:
    """Ollama should appear only when a local model is set."""
    from src.llm.factory import list_provider_options

    options = list_provider_options(
        {
            "FIXMATE_OLLAMA_MODEL": "local-model",
        }
    )
    ollama_labels = [l for l, _ in options if "Ollama" in l]
    assert len(ollama_labels) == 1
