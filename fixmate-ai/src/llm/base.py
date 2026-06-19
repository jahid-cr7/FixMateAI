"""Common interface and safe error types for optional LLM providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TypedDict


class LLMMessage(TypedDict):
    """A provider-neutral chat message."""

    role: str
    content: str


@dataclass(frozen=True)
class ProviderStatus:
    """Non-secret provider readiness information suitable for the UI."""

    name: str
    configured: bool
    external: bool
    message: str


class ProviderError(RuntimeError):
    """A sanitized provider failure that never contains credentials."""


class LLMProvider(ABC):
    """Provider-neutral interface used by the bounded hybrid agent."""

    @property
    @abstractmethod
    def status(self) -> ProviderStatus:
        """Return safe configuration status without making a request."""

    @abstractmethod
    def complete(self, messages: list[LLMMessage]) -> str:
        """Return one text completion or raise a sanitized ProviderError."""

