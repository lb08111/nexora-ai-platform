# -*- coding: utf-8 -*-
"""In-memory transcript store for Nexora team meetings.

Production deployments should swap this for a persistent backend
(Postgres + ``MeetingRepository`` interface stays the same).
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any

__all__ = [
    "Contribution",
    "Meeting",
    "MeetingStore",
    "get_meeting_store",
]


@dataclass
class Contribution:
    """A single specialist contribution within a meeting."""

    agent_id: str
    agent_name: str
    role: str
    content: str
    elapsed_ms: int
    error: str | None = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class Meeting:
    """A multi-agent meeting transcript."""

    id: str
    topic: str
    convener: str
    participants: list[str]
    status: str = "running"
    contributions: list[Contribution] = field(default_factory=list)
    summary: str | None = None
    created_at: float = field(default_factory=time.time)
    finished_at: float | None = None
    context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["created_at_iso"] = _iso(self.created_at)
        data["finished_at_iso"] = (
            _iso(self.finished_at) if self.finished_at else None
        )
        return data


def _iso(ts: float) -> str:
    import datetime as dt

    return dt.datetime.fromtimestamp(ts, tz=dt.timezone.utc).isoformat()


class MeetingStore:
    """Thread-safe in-memory store with a fixed retention window."""

    def __init__(self, max_meetings: int = 200) -> None:
        self._meetings: dict[str, Meeting] = {}
        self._order: list[str] = []
        self._lock = threading.RLock()
        self._max = max_meetings

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------
    def create(
        self,
        topic: str,
        convener: str,
        participants: list[str],
        context: dict[str, Any] | None = None,
    ) -> Meeting:
        meeting_id = f"mtg-{uuid.uuid4().hex[:12]}"
        meeting = Meeting(
            id=meeting_id,
            topic=topic,
            convener=convener,
            participants=list(participants),
            context=dict(context or {}),
        )
        with self._lock:
            self._meetings[meeting_id] = meeting
            self._order.append(meeting_id)
            self._evict_locked()
        return meeting

    def add_contribution(
        self,
        meeting_id: str,
        contribution: Contribution,
    ) -> Meeting | None:
        with self._lock:
            meeting = self._meetings.get(meeting_id)
            if meeting is None:
                return None
            meeting.contributions.append(contribution)
            return meeting

    def finish(
        self,
        meeting_id: str,
        summary: str,
        status: str = "completed",
    ) -> Meeting | None:
        with self._lock:
            meeting = self._meetings.get(meeting_id)
            if meeting is None:
                return None
            meeting.summary = summary
            meeting.status = status
            meeting.finished_at = time.time()
            return meeting

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------
    def get(self, meeting_id: str) -> Meeting | None:
        with self._lock:
            return self._meetings.get(meeting_id)

    def list(
        self,
        limit: int = 50,
        status: str | None = None,
    ) -> list[Meeting]:
        with self._lock:
            ids = list(reversed(self._order))
            out: list[Meeting] = []
            for mid in ids:
                meeting = self._meetings.get(mid)
                if meeting is None:
                    continue
                if status and meeting.status != status:
                    continue
                out.append(meeting)
                if len(out) >= limit:
                    break
            return out

    def clear(self) -> None:
        with self._lock:
            self._meetings.clear()
            self._order.clear()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _evict_locked(self) -> None:
        while len(self._order) > self._max:
            oldest = self._order.pop(0)
            self._meetings.pop(oldest, None)


_STORE: MeetingStore | None = None
_STORE_LOCK = threading.Lock()


def get_meeting_store() -> MeetingStore:
    """Process-wide singleton."""
    global _STORE
    if _STORE is None:
        with _STORE_LOCK:
            if _STORE is None:
                _STORE = MeetingStore()
    return _STORE
