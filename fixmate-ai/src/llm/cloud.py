"""Optional OpenAI-compatible cloud provider isolated from application data tools."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from urllib.parse import urlparse

from src.llm.base import LLMMessage, LLMProvider, ProviderError, ProviderStatus
from src.llm.http_transport import post_json

Transport = Callable[[str, dict[str, Any], dict[str, str], float], dict[str, Any]]


class CloudProvider(LLMProvider):
    """Use an explicitly configured HTTPS chat-completions endpoint."""

    def __init__(
        self,
        api_url: str,
        api_key: str,
        model: str,
        timeout_seconds: float = 15.0,
        transport: Transport = post_json,
    ) -> None:
        self._api_url = api_url.strip()
        self._api_key = api_key.strip()
        self._model = model.strip()
        self._timeout_seconds = max(1.0, min(float(timeout_seconds), 30.0))
        self._transport = transport

    @property
    def status(self) -> ProviderStatus:
        """Validate required values without exposing them."""
        parsed = urlparse(self._api_url)
        valid_url = parsed.scheme == "https" and bool(parsed.netloc)
        configured = bool(valid_url and self._api_key and self._model)
        message = (
            "Cloud provider is configured. External consent is required for each session."
            if configured
            else "Cloud provider configuration is missing or invalid. HTTPS URL, model, and API key are required."
        )
        return ProviderStatus("Cloud", configured, True, message)

    def complete(self, messages: list[LLMMessage]) -> str:
        """Call the configured endpoint with no database or filesystem access."""
        if not self.status.configured:
            raise ProviderError("Cloud provider configuration is missing or invalid.")
        response = self._transport(
            self._api_url,
            {
                "model": self._model,
                "messages": messages,
                "temperature": 0,
                "response_format": {"type": "json_object"},
            },
            {"Authorization": f"Bearer {self._api_key}"},
            self._timeout_seconds,
        )
        try:
            content = response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise ProviderError("The cloud provider returned an invalid response shape.") from error
        if not isinstance(content, str):
            raise ProviderError("The cloud provider returned non-text content.")
        return content

