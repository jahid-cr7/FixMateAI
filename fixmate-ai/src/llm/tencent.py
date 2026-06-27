"""Optional Tencent TokenHub GLM provider using the OpenAI-compatible client."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from urllib.parse import urlparse

from src.llm.base import LLMMessage, LLMProvider, ProviderError, ProviderStatus

DEFAULT_TENCENT_MODEL = "glm-5.1"


class TencentTokenHubProvider(LLMProvider):
    """Use Tencent TokenHub GLM through OpenAI-compatible chat completions."""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str = DEFAULT_TENCENT_MODEL,
        timeout_seconds: float = 15.0,
        client_factory: Callable[..., Any] | None = None,
    ) -> None:
        self._api_key = api_key.strip()
        self._base_url = base_url.strip().rstrip("/")
        self._model = (model.strip() or DEFAULT_TENCENT_MODEL)
        self._timeout_seconds = max(1.0, min(float(timeout_seconds), 30.0))
        self._client_factory = client_factory

    @property
    def status(self) -> ProviderStatus:
        """Return safe readiness information without exposing credentials."""
        if not self._api_key:
            return ProviderStatus(
                "Tencent TokenHub GLM",
                False,
                True,
                "Tencent TokenHub GLM is missing API key (TENCENT_TOKENHUB_API_KEY).",
            )
        if not self._base_url:
            return ProviderStatus(
                "Tencent TokenHub GLM",
                False,
                True,
                "Tencent TokenHub GLM is missing base URL (TENCENT_TOKENHUB_BASE_URL).",
            )
        parsed = urlparse(self._base_url)
        if parsed.scheme != "https" or not parsed.netloc:
            return ProviderStatus(
                "Tencent TokenHub GLM",
                False,
                True,
                "Tencent TokenHub GLM requires a valid HTTPS base URL.",
            )
        return ProviderStatus(
            "Tencent TokenHub GLM",
            True,
            True,
            f"Tencent TokenHub GLM is configured with model {self._model}. External consent is required for each session.",
        )

    def _client(self) -> Any:
        """Create the OpenAI-compatible client lazily."""
        if self._client_factory is not None:
            return self._client_factory(
                api_key=self._api_key,
                base_url=self._base_url,
                timeout=self._timeout_seconds,
            )
        try:
            from openai import OpenAI
        except ImportError as error:
            raise ProviderError("The OpenAI-compatible client is not installed.") from error
        return OpenAI(
            api_key=self._api_key,
            base_url=self._base_url,
            timeout=self._timeout_seconds,
        )

    @staticmethod
    def _extract_content(response: Any) -> str:
        """Extract chat-completion text from SDK objects or mocked dicts."""
        try:
            if isinstance(response, dict):
                content = response["choices"][0]["message"]["content"]
            else:
                content = response.choices[0].message.content
        except (AttributeError, KeyError, IndexError, TypeError) as error:
            raise ProviderError(
                "Tencent TokenHub GLM returned an invalid response shape."
            ) from error
        if not isinstance(content, str):
            raise ProviderError("Tencent TokenHub GLM returned non-text content.")
        return content

    def complete(self, messages: list[LLMMessage]) -> str:
        """Call Tencent TokenHub with bounded timeout and sanitized errors."""
        if not self.status.configured:
            raise ProviderError(self.status.message)
        try:
            response = self._client().chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=0,
                response_format={"type": "json_object"},
            )
        except TimeoutError as error:
            raise ProviderError("Tencent TokenHub GLM timed out.") from error
        except Exception as error:
            error_name = type(error).__name__.casefold()
            if "timeout" in error_name:
                raise ProviderError("Tencent TokenHub GLM timed out.") from error
            if "auth" in error_name or "permission" in error_name:
                raise ProviderError(
                    "Tencent TokenHub GLM authentication failed."
                ) from error
            raise ProviderError("Tencent TokenHub GLM request failed.") from error
        return self._extract_content(response)
