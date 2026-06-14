# -*- coding: utf-8 -*-
"""Tiny in-process sliding-window rate limiter.

Used to throttle abuse-prone public endpoints (e.g. tenant self-signup).
In-memory and per-process — good enough for a single-node install; a
multi-node deployment behind a shared store would need a distributed
limiter. Thread-safe.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock
from typing import Deque, Dict, Optional


class SlidingWindowRateLimiter:
    """Allow at most ``max_events`` per ``window_seconds`` per key."""

    def __init__(self, max_events: int, window_seconds: float) -> None:
        self.max_events = max(1, int(max_events))
        self.window_seconds = float(window_seconds)
        self._events: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str, now: Optional[float] = None) -> bool:
        """Record an event for ``key``; return False if over the limit.

        ``now`` can be injected for deterministic tests.
        """
        ts = time.time() if now is None else now
        cutoff = ts - self.window_seconds
        with self._lock:
            bucket = self._events[key]
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            if len(bucket) >= self.max_events:
                return False
            bucket.append(ts)
            return True

    def reset(self) -> None:
        """Clear all recorded events (used by tests)."""
        with self._lock:
            self._events.clear()
