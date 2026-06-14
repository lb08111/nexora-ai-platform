# -*- coding: utf-8 -*-
"""In-memory store for team notifications.

A *notification* is a small message dispatched when something happens
to a production (new, approval requested, approved, rejected, …) or
sent ad-hoc by an agent via ``send_team_notification``.

Notifications have a read/unread flag so the UI can show a badge.
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any

from ..constants import (
    ALL_NOTIFICATION_KINDS,
    NOTIFICATION_KIND_CUSTOM,
    NOTIFICATION_LEVELS,
)

__all__ = [
    "Notification",
    "NotificationStore",
    "get_notification_store",
]


@dataclass
class Notification:
    """A single team notification."""

    id: str
    team: str
    kind: str
    level: str  # "info" | "success" | "warning" | "error"
    title: str
    body: str = ""
    actor: str = "system"
    actor_kind: str = "system"
    production_id: str | None = None
    extras: dict[str, Any] = field(default_factory=dict)
    read: bool = False
    created_at: float = field(default_factory=time.time)
    read_at: float | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["created_at_iso"] = _iso(self.created_at)
        data["read_at_iso"] = _iso(self.read_at) if self.read_at else None
        return data


def _iso(ts: float) -> str:
    import datetime as dt

    return dt.datetime.fromtimestamp(ts, tz=dt.timezone.utc).isoformat()


class NotificationStore:
    """Thread-safe in-memory notification store with FIFO retention."""

    def __init__(self, max_items: int = 1000) -> None:
        self._items: dict[str, Notification] = {}
        self._order: list[str] = []
        self._lock = threading.RLock()
        self._max = max_items

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------
    def create(
        self,
        *,
        team: str,
        title: str,
        body: str = "",
        kind: str = NOTIFICATION_KIND_CUSTOM,
        level: str = "info",
        actor: str = "system",
        actor_kind: str = "system",
        production_id: str | None = None,
        extras: dict[str, Any] | None = None,
    ) -> Notification:
        if kind not in ALL_NOTIFICATION_KINDS:
            # Allow free-form kinds but normalize to "team.custom" prefix
            kind = kind or NOTIFICATION_KIND_CUSTOM
        if level not in NOTIFICATION_LEVELS:
            level = "info"

        nid = f"ntf-{uuid.uuid4().hex[:12]}"
        notif = Notification(
            id=nid,
            team=(team or "default").lower(),
            kind=kind,
            level=level,
            title=title.strip() or "(notificação)",
            body=body or "",
            actor=actor or "system",
            actor_kind=actor_kind or "system",
            production_id=production_id,
            extras=dict(extras or {}),
        )
        with self._lock:
            self._items[nid] = notif
            self._order.append(nid)
            self._evict_locked()
        return notif

    def mark_read(self, notification_id: str) -> Notification | None:
        with self._lock:
            notif = self._items.get(notification_id)
            if notif is None:
                return None
            if not notif.read:
                notif.read = True
                notif.read_at = time.time()
            return notif

    def mark_all_read(self, *, team: str | None = None) -> int:
        team_lc = team.lower() if team else None
        count = 0
        now = time.time()
        with self._lock:
            for notif in self._items.values():
                if team_lc and notif.team != team_lc:
                    continue
                if not notif.read:
                    notif.read = True
                    notif.read_at = now
                    count += 1
        return count

    def delete(self, notification_id: str) -> bool:
        with self._lock:
            if notification_id in self._items:
                self._items.pop(notification_id, None)
                self._order = [
                    nid for nid in self._order if nid != notification_id
                ]
                return True
        return False

    def clear(self) -> None:
        with self._lock:
            self._items.clear()
            self._order.clear()

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------
    def get(self, notification_id: str) -> Notification | None:
        with self._lock:
            return self._items.get(notification_id)

    def list(
        self,
        *,
        limit: int = 50,
        team: str | None = None,
        unread_only: bool = False,
        kind: str | None = None,
        production_id: str | None = None,
    ) -> list[Notification]:
        team_lc = team.lower() if team else None
        with self._lock:
            ids = list(reversed(self._order))
            out: list[Notification] = []
            for nid in ids:
                notif = self._items.get(nid)
                if notif is None:
                    continue
                if team_lc and notif.team != team_lc:
                    continue
                if unread_only and notif.read:
                    continue
                if kind and notif.kind != kind:
                    continue
                if production_id and notif.production_id != production_id:
                    continue
                out.append(notif)
                if len(out) >= limit:
                    break
            return out

    def unread_count(self, *, team: str | None = None) -> int:
        team_lc = team.lower() if team else None
        with self._lock:
            return sum(
                1
                for n in self._items.values()
                if not n.read and (team_lc is None or n.team == team_lc)
            )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _evict_locked(self) -> None:
        while len(self._order) > self._max:
            oldest = self._order.pop(0)
            self._items.pop(oldest, None)


_STORE: NotificationStore | None = None
_STORE_LOCK = threading.Lock()


def get_notification_store() -> NotificationStore:
    """Process-wide singleton."""
    global _STORE
    if _STORE is None:
        with _STORE_LOCK:
            if _STORE is None:
                _STORE = NotificationStore()
    return _STORE
