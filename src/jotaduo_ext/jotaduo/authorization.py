# -*- coding: utf-8 -*-
"""Multi-tenant agent authorization — replaces role-based agent access.

Core rule: a user can access an agent if and only if:
  1. The user is an admin (admin role bypasses all grant checks), OR
  2. The user has an explicit grant in agent_user_grants.

Resource access (tool/MCP/skill) still belongs to the agent.  If a user
has access to an agent, they can use all capabilities the agent has.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from fastapi import HTTPException

if TYPE_CHECKING:
    from fastapi import Request

logger = logging.getLogger(__name__)


def _is_auth_active() -> bool:
    from jotaduo.app import auth

    return auth.is_auth_enabled() and auth.has_registered_users()


def _is_admin(request_or_roles) -> bool:
    """Check if the request or role list includes admin."""
    if isinstance(request_or_roles, (list, tuple, set)):
        return "admin" in request_or_roles
    roles = getattr(request_or_roles, "state", None)
    if roles:
        return "admin" in (getattr(roles, "roles", None) or [])
    return False


def _get_username(request: "Request") -> str:
    return str(getattr(request.state, "user", "") or "")


def _get_roles(request: "Request") -> list[str]:
    return list(getattr(request.state, "roles", []) or [])


def user_can_access_agent(
    username: str, roles: list[str], agent_id: str
) -> bool:
    """Check if a user can access a specific agent."""
    if not _is_auth_active():
        return True
    if not agent_id:
        return False
    if "admin" in roles:
        return True
    from jotaduo_ext.jotaduo import agent_grants

    return agent_grants.is_user_granted(agent_id, username)


def filter_agent_ids_for_user(
    agent_ids: list[str],
    username: str,
    roles: list[str],
) -> list[str]:
    """Filter agent list to only those the user is authorized to see."""
    if not _is_auth_active():
        return agent_ids
    if "admin" in roles:
        return agent_ids
    from jotaduo_ext.jotaduo import agent_grants

    granted_ids = set(agent_grants.get_authorized_agent_ids(username))
    return [aid for aid in agent_ids if aid in granted_ids]


def ensure_agent_access(
    username: str,
    roles: list[str],
    agent_id: str,
) -> None:
    """Raise 403 if the user cannot access the agent."""
    if user_can_access_agent(username, roles, agent_id):
        return
    raise HTTPException(
        status_code=403,
        detail="Agent access denied",
    )


def enforce_agent_access_for_request(request: "Request") -> None:
    """Middleware-level check: extract agent_id from request path or header,
    then verify the user has access.
    """
    if not _is_auth_active():
        return

    path = request.url.path
    agent_id = _agent_id_from_path(path)
    if not agent_id:
        agent_id = request.headers.get("X-Agent-Id") or ""
    if not agent_id:
        return

    username = _get_username(request)
    roles = _get_roles(request)
    ensure_agent_access(username, roles, agent_id)


def _agent_id_from_path(path: str) -> str | None:
    """Extract agent_id from /api/agents/{agentId}/... paths."""
    if not path.startswith("/api/agents/"):
        return None
    parts = path.split("/")
    if len(parts) < 4 or not parts[3]:
        return None
    if parts[3] in {"order", "runtime"}:
        return None
    return parts[3]
