"""Constant-time authentication and in-memory bounded rate limiting."""

from __future__ import annotations

import secrets
import threading
import time
from collections import defaultdict, deque


def token_matches(expected: str, supplied: str) -> bool:
    """Compare local API tokens in constant time."""
    return bool(expected and supplied) and secrets.compare_digest(expected, supplied)


class InMemoryRateLimiter:
    """Simple per-client/category sliding-window limiter for local API use."""

    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(
        self,
        key: str,
        limit: int,
        window_seconds: int,
        now: float | None = None,
    ) -> bool:
        """Return whether one request fits within the configured window."""
        current = time.monotonic() if now is None else now
        cutoff = current - window_seconds
        with self._lock:
            events = self._events[key]
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= limit:
                return False
            events.append(current)
            return True

    def clear(self) -> None:
        """Clear counters, primarily for isolated tests."""
        with self._lock:
            self._events.clear()

