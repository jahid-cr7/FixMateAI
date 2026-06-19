"""Small injectable JSON HTTP transport used only by optional providers."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from src.llm.base import ProviderError


def post_json(
    url: str,
    payload: Mapping[str, Any],
    headers: Mapping[str, str],
    timeout_seconds: float,
) -> dict[str, Any]:
    """POST JSON with a bounded timeout and sanitized failure messages."""
    request_headers = {"Content-Type": "application/json", **dict(headers)}
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=request_headers,
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
            body = response.read(1_000_001)
    except TimeoutError as error:
        raise ProviderError("The optional AI provider timed out.") from error
    except HTTPError as error:
        raise ProviderError(
            f"The optional AI provider returned HTTP status {error.code}."
        ) from error
    except URLError as error:
        reason = getattr(error, "reason", None)
        if isinstance(reason, TimeoutError):
            raise ProviderError("The optional AI provider timed out.") from error
        raise ProviderError("The optional AI provider could not be reached.") from error
    except OSError as error:
        raise ProviderError("The optional AI provider request failed.") from error
    if len(body) > 1_000_000:
        raise ProviderError("The optional AI provider response was too large.")
    try:
        decoded = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ProviderError("The optional AI provider returned invalid JSON.") from error
    if not isinstance(decoded, dict):
        raise ProviderError("The optional AI provider returned an invalid response shape.")
    return decoded

