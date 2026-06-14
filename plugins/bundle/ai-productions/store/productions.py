# -*- coding: utf-8 -*-
"""In-memory store for AI-agent productions (artifacts).

A *production* is anything an agent produced and the team should see:
posts, landing pages, documents, e-mails, ad creatives, scripts, etc.
Each production carries:

* metadata    — id, team, type, title, agent_id, created_at, tags
* payload     — the content itself (text, URL, structured dict, …)
* lifecycle   — draft → pending_approval → approved → published, with
                rejection and archival
* audit       — every status change records who did it and why

Production deployments should swap the in-memory backend for a
persistent one (Postgres, Redis, …). The ``ProductionStore`` interface
stays the same.
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any

from ..constants import (
    ALLOWED_TRANSITIONS,
    ALL_STATUSES,
    STATUS_DRAFT,
    STATUS_PENDING,
)

__all__ = [
    "AuditEntry",
    "Production",
    "ProductionStore",
    "ProductionTransitionError",
    "get_production_store",
]


class ProductionTransitionError(ValueError):
    """Raised when a status change is not allowed."""


@dataclass
class AuditEntry:
    """One row in the audit trail of a production."""

    timestamp: float
    actor: str  # agent_id or human user id
    actor_kind: str  # "agent" | "human" | "system"
    action: str  # "created" | "status_changed" | "edited" | ...
    detail: str = ""
    from_status: str | None = None
    to_status: str | None = None


@dataclass
class Production:
    """An artifact produced by an AI agent."""

    id: str
    team: str
    type: str
    title: str
    agent_id: str
    agent_name: str
    summary: str = ""
    content: str = ""
    content_url: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    status: str = STATUS_DRAFT
    requires_approval: bool = True
    rejection_reason: str | None = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    history: list[AuditEntry] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["created_at_iso"] = _iso(self.created_at)
        data["updated_at_iso"] = _iso(self.updated_at)
        return data


def _iso(ts: float) -> str:
    import datetime as dt

    return dt.datetime.fromtimestamp(ts, tz=dt.timezone.utc).isoformat()


class ProductionStore:
    """Thread-safe in-memory production store with FIFO retention."""

    def __init__(self, max_items: int = 2000) -> None:
        self._items: dict[str, Production] = {}
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
        type: str,
        title: str,
        agent_id: str,
        agent_name: str,
        summary: str = "",
        content: str = "",
        content_url: str | None = None,
        payload: dict[str, Any] | None = None,
        tags: list[str] | None = None,
        requires_approval: bool = True,
        initial_status: str = STATUS_DRAFT,
    ) -> Production:
        if initial_status not in ALL_STATUSES:
            raise ValueError(f"invalid initial_status: {initial_status}")

        prod_id = f"prod-{uuid.uuid4().hex[:12]}"
        now = time.time()
        prod = Production(
            id=prod_id,
            team=team.strip().lower() or "default",
            type=type.strip().lower() or "other",
            title=title.strip() or "(sem título)",
            agent_id=agent_id,
            agent_name=agent_name or agent_id,
            summary=summary or "",
            content=content or "",
            content_url=content_url,
            payload=dict(payload or {}),
            tags=[t.strip() for t in (tags or []) if t and t.strip()],
            status=initial_status,
            requires_approval=requires_approval,
            created_at=now,
            updated_at=now,
        )
        prod.history.append(
            AuditEntry(
                timestamp=now,
                actor=agent_id,
                actor_kind="agent",
                action="created",
                detail=f"Production created in status {initial_status}",
                to_status=initial_status,
            ),
        )
        with self._lock:
            self._items[prod_id] = prod
            self._order.append(prod_id)
            self._evict_locked()
        return prod

    def change_status(
        self,
        production_id: str,
        *,
        new_status: str,
        actor: str,
        actor_kind: str = "human",
        detail: str = "",
        rejection_reason: str | None = None,
    ) -> Production:
        if new_status not in ALL_STATUSES:
            raise ValueError(f"invalid new_status: {new_status}")
        with self._lock:
            prod = self._items.get(production_id)
            if prod is None:
                raise KeyError(production_id)

            allowed = ALLOWED_TRANSITIONS.get(prod.status, set())
            if new_status != prod.status and new_status not in allowed:
                raise ProductionTransitionError(
                    f"Cannot move production from {prod.status!r} to "
                    f"{new_status!r}. Allowed: {sorted(allowed) or '∅'}",
                )

            now = time.time()
            from_status = prod.status
            prod.status = new_status
            prod.updated_at = now
            if rejection_reason is not None:
                prod.rejection_reason = rejection_reason
            prod.history.append(
                AuditEntry(
                    timestamp=now,
                    actor=actor,
                    actor_kind=actor_kind,
                    action="status_changed",
                    detail=detail,
                    from_status=from_status,
                    to_status=new_status,
                ),
            )
            return prod

    def request_approval(
        self,
        production_id: str,
        *,
        actor: str,
        actor_kind: str = "agent",
        note: str = "",
    ) -> Production:
        """Shortcut: move draft → pending_approval (idempotent)."""
        with self._lock:
            prod = self._items.get(production_id)
            if prod is None:
                raise KeyError(production_id)
            if prod.status == STATUS_PENDING:
                return prod
        return self.change_status(
            production_id,
            new_status=STATUS_PENDING,
            actor=actor,
            actor_kind=actor_kind,
            detail=note or "Approval requested",
        )

    def edit(
        self,
        production_id: str,
        *,
        actor: str,
        actor_kind: str = "human",
        title: str | None = None,
        summary: str | None = None,
        content: str | None = None,
        content_url: str | None = None,
        tags: list[str] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> Production:
        with self._lock:
            prod = self._items.get(production_id)
            if prod is None:
                raise KeyError(production_id)
            changes: list[str] = []
            if title is not None and title != prod.title:
                prod.title = title.strip() or prod.title
                changes.append("title")
            if summary is not None and summary != prod.summary:
                prod.summary = summary
                changes.append("summary")
            if content is not None and content != prod.content:
                prod.content = content
                changes.append("content")
            if content_url is not None and content_url != prod.content_url:
                prod.content_url = content_url
                changes.append("content_url")
            if tags is not None:
                cleaned = [t.strip() for t in tags if t and t.strip()]
                if cleaned != prod.tags:
                    prod.tags = cleaned
                    changes.append("tags")
            if payload is not None:
                merged = dict(prod.payload)
                merged.update(payload)
                if merged != prod.payload:
                    prod.payload = merged
                    changes.append("payload")
            if not changes:
                return prod
            now = time.time()
            prod.updated_at = now
            prod.history.append(
                AuditEntry(
                    timestamp=now,
                    actor=actor,
                    actor_kind=actor_kind,
                    action="edited",
                    detail="changed: " + ", ".join(changes),
                ),
            )
            return prod

    def delete(self, production_id: str) -> bool:
        with self._lock:
            if production_id in self._items:
                self._items.pop(production_id, None)
                self._order = [
                    pid for pid in self._order if pid != production_id
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
    def get(self, production_id: str) -> Production | None:
        with self._lock:
            return self._items.get(production_id)

    def list(
        self,
        *,
        limit: int = 100,
        team: str | None = None,
        type: str | None = None,
        status: str | None = None,
        agent_id: str | None = None,
        tag: str | None = None,
    ) -> list[Production]:
        team_lc = team.lower() if team else None
        type_lc = type.lower() if type else None
        with self._lock:
            ids = list(reversed(self._order))
            out: list[Production] = []
            for pid in ids:
                prod = self._items.get(pid)
                if prod is None:
                    continue
                if team_lc and prod.team != team_lc:
                    continue
                if type_lc and prod.type != type_lc:
                    continue
                if status and prod.status != status:
                    continue
                if agent_id and prod.agent_id != agent_id:
                    continue
                if tag and tag not in prod.tags:
                    continue
                out.append(prod)
                if len(out) >= limit:
                    break
            return out

    def stats(self) -> dict[str, Any]:
        with self._lock:
            by_status: dict[str, int] = {}
            by_team: dict[str, int] = {}
            by_type: dict[str, int] = {}
            for prod in self._items.values():
                by_status[prod.status] = by_status.get(prod.status, 0) + 1
                by_team[prod.team] = by_team.get(prod.team, 0) + 1
                by_type[prod.type] = by_type.get(prod.type, 0) + 1
            return {
                "total": len(self._items),
                "by_status": by_status,
                "by_team": by_team,
                "by_type": by_type,
            }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _evict_locked(self) -> None:
        while len(self._order) > self._max:
            oldest = self._order.pop(0)
            self._items.pop(oldest, None)


_STORE: ProductionStore | None = None
_STORE_LOCK = threading.Lock()


def get_production_store() -> ProductionStore:
    """Process-wide singleton."""
    global _STORE
    if _STORE is None:
        with _STORE_LOCK:
            if _STORE is None:
                _STORE = ProductionStore()
    return _STORE
