"""Default provider that performs no network or model operation."""

from __future__ import annotations

from src.llm.base import LLMMessage, LLMProvider, ProviderError, ProviderStatus


class DisabledProvider(LLMProvider):
    """Safe default used when optional AI enhancement is disabled."""

    @property
    def status(self) -> ProviderStatus:
        """Report deterministic-only operation."""
        return ProviderStatus(
            name="Disabled",
            configured=False,
            external=False,
            message="Optional AI enhancement is disabled; deterministic mode is available.",
        )

    def complete(self, messages: list[LLMMessage]) -> str:
        """Never attempt completion in disabled mode."""
        raise ProviderError("Optional AI enhancement is disabled.")

