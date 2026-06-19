"""Optional local Ollama-compatible provider."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from urllib.parse import urlparse

from src.llm.base import LLMMessage, LLMProvider, ProviderError, ProviderStatus
from src.llm.http_transport import post_json

Transport = Callable[[str, dict[str, Any], dict[str, str], float], dict[str, Any]]
LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}


class OllamaProvider(LLMProvider):
    """Use a loopback-only Ollama-compatible chat endpoint."""

    def __init__(
        self,
        api_url: str = "http://127.0.0.1:11434/api/chat",
        model: str = "",
        timeout_seconds: float = 15.0,
        transport: Transport = post_json,
    ) -> None:
        self._api_url = api_url.strip()
        self._model = model.strip()
        self._timeout_seconds = max(1.0, min(float(timeout_seconds), 30.0))
        self._transport = transport

    @property
    def status(self) -> ProviderStatus:
        """Require a model and a loopback-only HTTP(S) endpoint."""
        parsed = urlparse(self._api_url)
        local_url = parsed.scheme in {"http", "https"} and parsed.hostname in LOCAL_HOSTS
        configured = bool(local_url and self._model)
        message = (
            "Local Ollama-compatible provider is configured."
            if configured
            else "Local provider needs a model and a loopback Ollama-compatible URL."
        )
        return ProviderStatus("Ollama", configured, False, message)

    def complete(self, messages: list[LLMMessage]) -> str:
        """Call only the configured loopback endpoint."""
        if not self.status.configured:
            raise ProviderError("Local Ollama-compatible provider is not configured.")
        response = self._transport(
            self._api_url,
            {
                "model": self._model,
                "messages": messages,
                "stream": False,
                "format": "json",
                "options": {"temperature": 0},
            },
            {},
            self._timeout_seconds,
        )
        try:
            content = response["message"]["content"]
        except (KeyError, TypeError) as error:
            raise ProviderError("The local provider returned an invalid response shape.") from error
        if not isinstance(content, str):
            raise ProviderError("The local provider returned non-text content.")
        return content

