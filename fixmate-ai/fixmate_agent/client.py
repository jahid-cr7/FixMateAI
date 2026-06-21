"""Small standard-library HTTP client for authenticated agent submissions."""

from __future__ import annotations

import json
import socket
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class AgentClientError(RuntimeError):
    """Safe client error that excludes tokens and response internals."""


class AgentClient:
    """POST JSON payloads with a device token and bounded timeout."""

    def __init__(
        self,
        server_url: str,
        token: str,
        timeout_seconds: float,
        opener: Callable[..., Any] = urlopen,
    ) -> None:
        self.server_url = server_url.rstrip("/")
        self._token = token
        self.timeout_seconds = timeout_seconds
        self._opener = opener

    def post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Submit one authenticated JSON request and parse its response."""
        request = Request(
            f"{self.server_url}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-Device-Token": self._token,
            },
            method="POST",
        )
        try:
            response = self._opener(request, timeout=self.timeout_seconds)
            body = response.read()
            close = getattr(response, "close", None)
            if callable(close):
                close()
            decoded = json.loads(body.decode("utf-8")) if body else {}
            return decoded if isinstance(decoded, dict) else {}
        except HTTPError as error:
            raise AgentClientError(
                f"Server rejected the agent request with HTTP {error.code}."
            ) from None
        except (URLError, TimeoutError, socket.timeout, OSError, ValueError):
            raise AgentClientError(
                "FixMate AI server is unavailable or returned an invalid response."
            ) from None
