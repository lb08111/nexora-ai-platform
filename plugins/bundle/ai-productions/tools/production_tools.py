# -*- coding: utf-8 -*-
"""Agent-facing tools for the ai-productions plugin.

Exposes three tools the orchestrator and specialists can call:

* ``register_production``      — publishes a new artifact into the catalog
* ``request_approval``         — flips an existing production to pending
* ``send_team_notification``   — posts a free-form notification

All tools return a ``ToolResponse`` whose payload is a JSON object so
the chat UI can render it natively.
"""

from __future__ import annotations

import logging
from typing import Any

from jotaduo.agents.br_team.tools._utils import json_response, text_response

from ..constants import (
    DEFAULT_REQUIRES_APPROVAL,
    DEFAULT_TEAM,
    NOTIFICATION_KIND_APPROVAL_REQUESTED,
    NOTIFICATION_KIND_CUSTOM,
    NOTIFICATION_KIND_PRODUCTION_NEW,
    STATUS_DRAFT,
    STATUS_PENDING,
)
from ..store import (
    ProductionTransitionError,
    get_notification_store,
    get_production_store,
)

__all__ = [
    "register_production",
    "request_approval",
    "send_team_notification",
]

logger = logging.getLogger("jotaduo").getChild(
    "plugin.ai-productions.tools",
)


async def register_production(
    title: str,
    type: str,
    *,
    team: str = DEFAULT_TEAM,
    agent_id: str = "unknown-agent",
    agent_name: str = "",
    summary: str = "",
    content: str = "",
    content_url: str | None = None,
    payload: dict[str, Any] | None = None,
    tags: list[str] | None = None,
    requires_approval: bool = DEFAULT_REQUIRES_APPROVAL,
    auto_request_approval: bool = True,
):
    """Register a new production (artifact) created by an AI agent.

    Args:
        title: Human-readable name of the artifact.
        type: One of ``post``, ``landing_page``, ``document``, ``email``,
            ``ad_creative``, ``image``, ``video``, ``script``,
            ``blog_article``, ``social_caption``, ``press_release``,
            ``newsletter``, ``report``, ``spreadsheet``,
            ``code_snippet``, ``other``.
        team: Owning team (lowercased). Defaults to ``"marketing"``.
        agent_id: ID of the agent who produced it.
        agent_name: Friendly name of the agent (optional).
        summary: One-paragraph TL;DR shown in the catalog list.
        content: Full content (text/markdown/HTML). Stored as-is.
        content_url: External link (e.g. a Google Doc, Figma, S3 URL).
        payload: Free-form structured data (e.g. design tokens, frontmatter).
        tags: Optional tag list for filtering.
        requires_approval: When True (default), the production needs a
            human ``approve`` before it can be ``publish``ed.
        auto_request_approval: When True, immediately moves the artifact
            from ``draft`` to ``pending_approval`` and fires a
            notification to the team.

    Returns:
        ``ToolResponse`` whose JSON payload contains ``{"production": {...},
        "notification": {...} | None}``.
    """
    if not title or not title.strip():
        return text_response(
            "❌ title é obrigatório para registrar uma produção.",
        )
    if not type or not type.strip():
        return text_response(
            "❌ type é obrigatório (ex.: post, landing_page, document).",
        )

    store = get_production_store()
    initial_status = (
        STATUS_PENDING
        if (requires_approval and auto_request_approval)
        else STATUS_DRAFT
    )

    try:
        prod = store.create(
            team=team,
            type=type,
            title=title,
            agent_id=agent_id,
            agent_name=agent_name or agent_id,
            summary=summary,
            content=content,
            content_url=content_url,
            payload=payload,
            tags=tags,
            requires_approval=bool(requires_approval),
            initial_status=initial_status,
        )
    except ValueError as exc:
        return text_response(f"❌ Falha ao registrar produção: {exc}")

    notif = None
    notif_store = get_notification_store()
    if initial_status == STATUS_PENDING:
        notif = notif_store.create(
            team=prod.team,
            kind=NOTIFICATION_KIND_APPROVAL_REQUESTED,
            level="warning",
            title=f"Aprovação pendente: {prod.title}",
            body=(
                f"O agente {prod.agent_name} ({prod.agent_id}) enviou "
                f"uma nova {prod.type} para aprovação no time {prod.team}."
            ),
            actor=prod.agent_id,
            actor_kind="agent",
            production_id=prod.id,
            extras={"production_type": prod.type},
        )
    else:
        notif = notif_store.create(
            team=prod.team,
            kind=NOTIFICATION_KIND_PRODUCTION_NEW,
            level="info",
            title=f"Nova produção em rascunho: {prod.title}",
            body=(
                f"O agente {prod.agent_name} adicionou uma {prod.type} "
                f"como rascunho. Use request_approval para enviar para revisão."
            ),
            actor=prod.agent_id,
            actor_kind="agent",
            production_id=prod.id,
            extras={"production_type": prod.type},
        )

    logger.info(
        "[ai-productions] registered %s (%s) by %s status=%s",
        prod.id,
        prod.type,
        prod.agent_id,
        prod.status,
    )
    return json_response(
        {
            "ok": True,
            "production": prod.to_dict(),
            "notification": notif.to_dict() if notif else None,
        },
    )


async def request_approval(
    production_id: str,
    *,
    actor: str = "unknown-agent",
    actor_kind: str = "agent",
    note: str = "",
):
    """Move an existing production from ``draft`` to ``pending_approval``.

    Also fires a ``production.approval_requested`` notification so the
    team gets pinged.

    Args:
        production_id: ID returned by ``register_production``.
        actor: Who is requesting (agent_id or user id).
        actor_kind: ``"agent"`` | ``"human"`` | ``"system"``.
        note: Optional context for the audit trail.

    Returns:
        ``ToolResponse`` JSON ``{"production": {...}, "notification": {...}}``.
    """
    if not production_id or not production_id.strip():
        return text_response("❌ production_id é obrigatório.")

    store = get_production_store()
    try:
        prod = store.request_approval(
            production_id,
            actor=actor,
            actor_kind=actor_kind,
            note=note,
        )
    except KeyError:
        return text_response(f"❌ Produção não encontrada: {production_id}")
    except ProductionTransitionError as exc:
        return text_response(f"❌ Transição inválida: {exc}")

    notif = get_notification_store().create(
        team=prod.team,
        kind=NOTIFICATION_KIND_APPROVAL_REQUESTED,
        level="warning",
        title=f"Aprovação pendente: {prod.title}",
        body=note
        or (
            f"O agente {prod.agent_name} solicitou aprovação para "
            f"a {prod.type} '{prod.title}'."
        ),
        actor=actor,
        actor_kind=actor_kind,
        production_id=prod.id,
    )

    return json_response(
        {
            "ok": True,
            "production": prod.to_dict(),
            "notification": notif.to_dict(),
        },
    )


async def send_team_notification(
    team: str,
    title: str,
    *,
    body: str = "",
    level: str = "info",
    actor: str = "unknown-agent",
    actor_kind: str = "agent",
    production_id: str | None = None,
    kind: str = NOTIFICATION_KIND_CUSTOM,
    extras: dict[str, Any] | None = None,
):
    """Send an ad-hoc notification to a team.

    Args:
        team: Target team (lowercased internally).
        title: Short headline of the notification.
        body: Optional longer text.
        level: ``info`` | ``success`` | ``warning`` | ``error``.
        actor: Who is sending it.
        actor_kind: ``"agent"`` | ``"human"`` | ``"system"``.
        production_id: Optional link back to a production.
        kind: Notification kind tag. Defaults to ``team.custom``.
        extras: Free-form metadata.

    Returns:
        ``ToolResponse`` JSON ``{"notification": {...}}``.
    """
    if not team or not team.strip():
        return text_response("❌ team é obrigatório.")
    if not title or not title.strip():
        return text_response("❌ title é obrigatório.")

    notif = get_notification_store().create(
        team=team,
        kind=kind,
        level=level,
        title=title,
        body=body,
        actor=actor,
        actor_kind=actor_kind,
        production_id=production_id,
        extras=extras,
    )
    return json_response({"ok": True, "notification": notif.to_dict()})
