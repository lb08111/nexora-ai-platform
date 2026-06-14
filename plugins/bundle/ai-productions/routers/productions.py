# -*- coding: utf-8 -*-
"""HTTP API for AI productions catalog.

Endpoints
---------
GET    /api/ai-productions/productions           → list (with filters)
POST   /api/ai-productions/productions           → create a production
GET    /api/ai-productions/productions/_stats    → counts by team/type/status
GET    /api/ai-productions/productions/_types    → known production types
GET    /api/ai-productions/productions/{id}      → fetch one
PATCH  /api/ai-productions/productions/{id}      → edit fields
POST   /api/ai-productions/productions/{id}/request-approval
POST   /api/ai-productions/productions/{id}/approve
POST   /api/ai-productions/productions/{id}/reject
POST   /api/ai-productions/productions/{id}/publish
POST   /api/ai-productions/productions/{id}/archive
DELETE /api/ai-productions/productions/{id}
DELETE /api/ai-productions/productions           → clear all (admin/test)
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ..constants import (
    DEFAULT_REQUIRES_APPROVAL,
    DEFAULT_TEAM,
    NOTIFICATION_KIND_APPROVAL_REQUESTED,
    NOTIFICATION_KIND_APPROVED,
    NOTIFICATION_KIND_PRODUCTION_NEW,
    NOTIFICATION_KIND_PUBLISHED,
    NOTIFICATION_KIND_REJECTED,
    PRODUCTION_TYPE_LABELS_PT,
    PRODUCTION_TYPES,
    STATUS_APPROVED,
    STATUS_ARCHIVED,
    STATUS_DRAFT,
    STATUS_PENDING,
    STATUS_PUBLISHED,
    STATUS_REJECTED,
)
from ..store import (
    Production,
    ProductionTransitionError,
    get_notification_store,
    get_production_store,
)

logger = logging.getLogger("qwenpaw").getChild(
    "plugin.ai-productions.routers.productions",
)

router = APIRouter(prefix="", tags=["ai-productions"])


# ----------------------------------------------------------------------
# Schemas
# ----------------------------------------------------------------------
class AuditView(BaseModel):
    timestamp: float
    actor: str
    actor_kind: str
    action: str
    detail: str = ""
    from_status: str | None = None
    to_status: str | None = None


class ProductionView(BaseModel):
    id: str
    team: str
    type: str
    title: str
    agent_id: str
    agent_name: str
    summary: str
    content: str
    content_url: str | None
    payload: dict[str, Any]
    tags: list[str]
    status: str
    requires_approval: bool
    rejection_reason: str | None
    created_at: float
    updated_at: float
    history: list[AuditView]


class CreateProductionRequest(BaseModel):
    title: str = Field(..., min_length=1)
    type: str = Field(..., min_length=1)
    team: str = DEFAULT_TEAM
    agent_id: str = "unknown-agent"
    agent_name: str = ""
    summary: str = ""
    content: str = ""
    content_url: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    requires_approval: bool = DEFAULT_REQUIRES_APPROVAL
    auto_request_approval: bool = True


class EditProductionRequest(BaseModel):
    title: str | None = None
    summary: str | None = None
    content: str | None = None
    content_url: str | None = None
    tags: list[str] | None = None
    payload: dict[str, Any] | None = None
    actor: str = "human"
    actor_kind: str = "human"


class ApprovalDecisionRequest(BaseModel):
    actor: str = "human"
    actor_kind: str = "human"
    note: str = ""


class RejectRequest(ApprovalDecisionRequest):
    reason: str = Field(..., min_length=1)


class ListResponse(BaseModel):
    count: int
    items: list[ProductionView]


class StatsResponse(BaseModel):
    total: int
    by_status: dict[str, int]
    by_team: dict[str, int]
    by_type: dict[str, int]


class TypeInfo(BaseModel):
    id: str
    label_pt: str


class TypesResponse(BaseModel):
    types: list[TypeInfo]
    statuses: list[str]


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def _to_view(prod: Production) -> ProductionView:
    return ProductionView(
        id=prod.id,
        team=prod.team,
        type=prod.type,
        title=prod.title,
        agent_id=prod.agent_id,
        agent_name=prod.agent_name,
        summary=prod.summary,
        content=prod.content,
        content_url=prod.content_url,
        payload=prod.payload,
        tags=prod.tags,
        status=prod.status,
        requires_approval=prod.requires_approval,
        rejection_reason=prod.rejection_reason,
        created_at=prod.created_at,
        updated_at=prod.updated_at,
        history=[
            AuditView(
                timestamp=h.timestamp,
                actor=h.actor,
                actor_kind=h.actor_kind,
                action=h.action,
                detail=h.detail,
                from_status=h.from_status,
                to_status=h.to_status,
            )
            for h in prod.history
        ],
    )


def _notify_status(
    prod: Production,
    *,
    kind: str,
    title: str,
    body: str,
    level: str,
    actor: str,
    actor_kind: str,
) -> None:
    get_notification_store().create(
        team=prod.team,
        kind=kind,
        level=level,
        title=title,
        body=body,
        actor=actor,
        actor_kind=actor_kind,
        production_id=prod.id,
        extras={"production_type": prod.type},
    )


# ----------------------------------------------------------------------
# Discovery
# ----------------------------------------------------------------------
@router.get("/_types", response_model=TypesResponse)
def list_types() -> TypesResponse:
    return TypesResponse(
        types=[
            TypeInfo(id=t, label_pt=PRODUCTION_TYPE_LABELS_PT.get(t, t))
            for t in PRODUCTION_TYPES
        ],
        statuses=[
            STATUS_DRAFT,
            STATUS_PENDING,
            STATUS_APPROVED,
            STATUS_REJECTED,
            STATUS_PUBLISHED,
            STATUS_ARCHIVED,
        ],
    )


@router.get("/_stats", response_model=StatsResponse)
def stats() -> StatsResponse:
    s = get_production_store().stats()
    return StatsResponse(**s)


# ----------------------------------------------------------------------
# CRUD
# ----------------------------------------------------------------------
@router.get("", response_model=ListResponse)
def list_productions(
    limit: int = Query(100, ge=1, le=500),
    team: str | None = Query(None),
    type: str | None = Query(None),
    status: str | None = Query(None),
    agent_id: str | None = Query(None),
    tag: str | None = Query(None),
) -> ListResponse:
    items = get_production_store().list(
        limit=limit,
        team=team,
        type=type,
        status=status,
        agent_id=agent_id,
        tag=tag,
    )
    return ListResponse(count=len(items), items=[_to_view(p) for p in items])


@router.post("", response_model=ProductionView, status_code=201)
def create_production(body: CreateProductionRequest) -> ProductionView:
    store = get_production_store()
    initial = (
        STATUS_PENDING
        if (body.requires_approval and body.auto_request_approval)
        else STATUS_DRAFT
    )
    try:
        prod = store.create(
            team=body.team,
            type=body.type,
            title=body.title,
            agent_id=body.agent_id,
            agent_name=body.agent_name or body.agent_id,
            summary=body.summary,
            content=body.content,
            content_url=body.content_url,
            payload=body.payload,
            tags=body.tags,
            requires_approval=body.requires_approval,
            initial_status=initial,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if initial == STATUS_PENDING:
        _notify_status(
            prod,
            kind=NOTIFICATION_KIND_APPROVAL_REQUESTED,
            title=f"Aprovação pendente: {prod.title}",
            body=(
                f"O agente {prod.agent_name} enviou uma {prod.type} "
                f"para revisão no time {prod.team}."
            ),
            level="warning",
            actor=prod.agent_id,
            actor_kind="agent",
        )
    else:
        _notify_status(
            prod,
            kind=NOTIFICATION_KIND_PRODUCTION_NEW,
            title=f"Novo rascunho: {prod.title}",
            body=f"Adicionado por {prod.agent_name} ({prod.type}).",
            level="info",
            actor=prod.agent_id,
            actor_kind="agent",
        )

    return _to_view(prod)


@router.get("/{production_id}", response_model=ProductionView)
def get_production(production_id: str) -> ProductionView:
    prod = get_production_store().get(production_id)
    if prod is None:
        raise HTTPException(status_code=404, detail="Production not found")
    return _to_view(prod)


@router.patch("/{production_id}", response_model=ProductionView)
def edit_production(
    production_id: str,
    body: EditProductionRequest,
) -> ProductionView:
    try:
        prod = get_production_store().edit(
            production_id,
            actor=body.actor,
            actor_kind=body.actor_kind,
            title=body.title,
            summary=body.summary,
            content=body.content,
            content_url=body.content_url,
            tags=body.tags,
            payload=body.payload,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Production not found") from exc
    return _to_view(prod)


@router.delete("/{production_id}")
def delete_production(production_id: str) -> dict[str, Any]:
    ok = get_production_store().delete(production_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Production not found")
    return {"status": "deleted", "id": production_id}


@router.delete("")
def clear_productions() -> dict[str, str]:
    get_production_store().clear()
    return {"status": "cleared"}


# ----------------------------------------------------------------------
# Approval workflow
# ----------------------------------------------------------------------
@router.post(
    "/{production_id}/request-approval", response_model=ProductionView,
)
def request_approval_route(
    production_id: str,
    body: ApprovalDecisionRequest,
) -> ProductionView:
    try:
        prod = get_production_store().request_approval(
            production_id,
            actor=body.actor,
            actor_kind=body.actor_kind,
            note=body.note,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Production not found") from exc
    except ProductionTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    _notify_status(
        prod,
        kind=NOTIFICATION_KIND_APPROVAL_REQUESTED,
        title=f"Aprovação pendente: {prod.title}",
        body=body.note or (
            f"{body.actor} solicitou revisão de '{prod.title}'."
        ),
        level="warning",
        actor=body.actor,
        actor_kind=body.actor_kind,
    )
    return _to_view(prod)


@router.post("/{production_id}/approve", response_model=ProductionView)
def approve_route(
    production_id: str,
    body: ApprovalDecisionRequest,
) -> ProductionView:
    try:
        prod = get_production_store().change_status(
            production_id,
            new_status=STATUS_APPROVED,
            actor=body.actor,
            actor_kind=body.actor_kind,
            detail=body.note or "Aprovado",
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Production not found") from exc
    except ProductionTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    _notify_status(
        prod,
        kind=NOTIFICATION_KIND_APPROVED,
        title=f"Aprovado: {prod.title}",
        body=body.note or f"{body.actor} aprovou '{prod.title}'.",
        level="success",
        actor=body.actor,
        actor_kind=body.actor_kind,
    )
    return _to_view(prod)


@router.post("/{production_id}/reject", response_model=ProductionView)
def reject_route(
    production_id: str,
    body: RejectRequest,
) -> ProductionView:
    try:
        prod = get_production_store().change_status(
            production_id,
            new_status=STATUS_REJECTED,
            actor=body.actor,
            actor_kind=body.actor_kind,
            detail=body.note or body.reason,
            rejection_reason=body.reason,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Production not found") from exc
    except ProductionTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    _notify_status(
        prod,
        kind=NOTIFICATION_KIND_REJECTED,
        title=f"Rejeitado: {prod.title}",
        body=body.reason,
        level="error",
        actor=body.actor,
        actor_kind=body.actor_kind,
    )
    return _to_view(prod)


@router.post("/{production_id}/publish", response_model=ProductionView)
def publish_route(
    production_id: str,
    body: ApprovalDecisionRequest,
) -> ProductionView:
    try:
        prod = get_production_store().change_status(
            production_id,
            new_status=STATUS_PUBLISHED,
            actor=body.actor,
            actor_kind=body.actor_kind,
            detail=body.note or "Publicado",
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Production not found") from exc
    except ProductionTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    _notify_status(
        prod,
        kind=NOTIFICATION_KIND_PUBLISHED,
        title=f"Publicado: {prod.title}",
        body=body.note or f"{body.actor} publicou '{prod.title}'.",
        level="success",
        actor=body.actor,
        actor_kind=body.actor_kind,
    )
    return _to_view(prod)


@router.post("/{production_id}/archive", response_model=ProductionView)
def archive_route(
    production_id: str,
    body: ApprovalDecisionRequest,
) -> ProductionView:
    try:
        prod = get_production_store().change_status(
            production_id,
            new_status=STATUS_ARCHIVED,
            actor=body.actor,
            actor_kind=body.actor_kind,
            detail=body.note or "Arquivado",
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Production not found") from exc
    except ProductionTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _to_view(prod)
