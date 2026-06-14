# -*- coding: utf-8 -*-
"""HTTP API for team notifications.

Endpoints
---------
GET    /api/ai-productions/notifications           → list (with filters)
POST   /api/ai-productions/notifications           → send a new notification
GET    /api/ai-productions/notifications/_unread   → counter
POST   /api/ai-productions/notifications/_read_all → mark everything read
POST   /api/ai-productions/notifications/{id}/read → mark one read
DELETE /api/ai-productions/notifications/{id}      → delete one
DELETE /api/ai-productions/notifications           → clear all (admin/test)
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ..constants import (
    ALL_NOTIFICATION_KINDS,
    DEFAULT_TEAM,
    NOTIFICATION_KIND_CUSTOM,
    NOTIFICATION_LEVELS,
)
from ..store import Notification, get_notification_store

logger = logging.getLogger("qwenpaw").getChild(
    "plugin.ai-productions.routers.notifications",
)

router = APIRouter(prefix="", tags=["ai-productions-notifications"])


class NotificationView(BaseModel):
    id: str
    team: str
    kind: str
    level: str
    title: str
    body: str
    actor: str
    actor_kind: str
    production_id: str | None
    extras: dict[str, Any]
    read: bool
    created_at: float
    read_at: float | None


class CreateNotificationRequest(BaseModel):
    team: str = DEFAULT_TEAM
    title: str = Field(..., min_length=1)
    body: str = ""
    kind: str = NOTIFICATION_KIND_CUSTOM
    level: str = "info"
    actor: str = "system"
    actor_kind: str = "system"
    production_id: str | None = None
    extras: dict[str, Any] = Field(default_factory=dict)


class ListResponse(BaseModel):
    count: int
    items: list[NotificationView]


class UnreadResponse(BaseModel):
    unread: int


class MarkAllResponse(BaseModel):
    updated: int


def _to_view(n: Notification) -> NotificationView:
    return NotificationView(
        id=n.id,
        team=n.team,
        kind=n.kind,
        level=n.level,
        title=n.title,
        body=n.body,
        actor=n.actor,
        actor_kind=n.actor_kind,
        production_id=n.production_id,
        extras=n.extras,
        read=n.read,
        created_at=n.created_at,
        read_at=n.read_at,
    )


@router.get("", response_model=ListResponse)
def list_notifications(
    limit: int = Query(50, ge=1, le=500),
    team: str | None = Query(None),
    unread_only: bool = Query(False),
    kind: str | None = Query(None),
    production_id: str | None = Query(None),
) -> ListResponse:
    items = get_notification_store().list(
        limit=limit,
        team=team,
        unread_only=unread_only,
        kind=kind,
        production_id=production_id,
    )
    return ListResponse(count=len(items), items=[_to_view(n) for n in items])


@router.get("/_unread", response_model=UnreadResponse)
def unread_count(team: str | None = Query(None)) -> UnreadResponse:
    return UnreadResponse(unread=get_notification_store().unread_count(team=team))


@router.post("", response_model=NotificationView, status_code=201)
def create_notification(body: CreateNotificationRequest) -> NotificationView:
    if body.level not in NOTIFICATION_LEVELS:
        raise HTTPException(
            status_code=400,
            detail=f"level deve ser um de {list(NOTIFICATION_LEVELS)}",
        )
    if body.kind not in ALL_NOTIFICATION_KINDS:
        # Allow it but log
        logger.info("[ai-productions] free-form notification kind: %s", body.kind)
    notif = get_notification_store().create(
        team=body.team,
        kind=body.kind,
        level=body.level,
        title=body.title,
        body=body.body,
        actor=body.actor,
        actor_kind=body.actor_kind,
        production_id=body.production_id,
        extras=body.extras,
    )
    return _to_view(notif)


@router.post("/{notification_id}/read", response_model=NotificationView)
def mark_read(notification_id: str) -> NotificationView:
    notif = get_notification_store().mark_read(notification_id)
    if notif is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    return _to_view(notif)


@router.post("/_read_all", response_model=MarkAllResponse)
def mark_all_read(team: str | None = Query(None)) -> MarkAllResponse:
    updated = get_notification_store().mark_all_read(team=team)
    return MarkAllResponse(updated=updated)


@router.delete("/{notification_id}")
def delete_notification(notification_id: str) -> dict[str, Any]:
    ok = get_notification_store().delete(notification_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"status": "deleted", "id": notification_id}


@router.delete("")
def clear_notifications() -> dict[str, str]:
    get_notification_store().clear()
    return {"status": "cleared"}
