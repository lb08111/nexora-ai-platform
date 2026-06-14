# -*- coding: utf-8 -*-
"""Shared helpers for capability creation approval flows."""
from __future__ import annotations

from typing import Any

from fastapi import Request


def current_requester(request: Request) -> str:
    """Return the authenticated actor used by approval requests."""
    return str(getattr(request.state, "user", "") or "__local_admin__")


def capability_create_requires_approval(
    request: Request,
    action: str,
) -> bool:
    """Check whether creating a capability should be routed to approval."""
    from ..auth import has_registered_users, is_auth_enabled
    from qwenpaw_ext.nexora import capability_approval

    if not is_auth_enabled() or not has_registered_users():
        return False
    if current_requester(request) == "__local_admin__":
        return False

    cap_type = _action_to_capability_type(action)
    if cap_type:
        return capability_approval.requires_approval(cap_type, "add")

    from qwenpaw_ext.nexora.governance import get_approval_policy

    return bool(get_approval_policy(action).get("enabled", True))


def capability_remove_requires_approval(
    request: Request,
    action: str,
) -> tuple[bool, bool]:
    """Check whether removing a capability needs approval.

    Returns (requires_approval, auto_approve).
    """
    from ..auth import has_registered_users, is_auth_enabled
    from qwenpaw_ext.nexora import capability_approval

    if not is_auth_enabled() or not has_registered_users():
        return False, False
    if current_requester(request) == "__local_admin__":
        return False, False

    cap_type = _action_to_capability_type(action)
    if cap_type:
        needs = capability_approval.requires_approval(cap_type, "remove")
        auto = capability_approval.should_auto_approve(cap_type, "remove")
        return needs, auto
    return False, False


def _action_to_capability_type(action: str) -> str | None:
    """Map an approval action string to a capability type."""
    mapping = {
        "skill.create": "skill",
        "skill.delete": "skill",
        "mcp.create": "mcp",
        "mcp.delete": "mcp",
        "tool.create": "tool",
        "tool.delete": "tool",
        "plugin.install": "plugin",
        "plugin.uninstall": "plugin",
        "acp.create": "acp",
        "acp.delete": "acp",
    }
    return mapping.get(action)


def submit_capability_approval(
    request: Request,
    *,
    action: str,
    resource_type: str,
    resource_id: str,
    resource_name: str,
    summary: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Create a pending approval request for a capability change."""
    from qwenpaw_ext.nexora.approval_requests import create_approval_request

    return create_approval_request(
        {
            "action": action,
            "requester": current_requester(request),
            "resource_type": resource_type,
            "resource_id": resource_id,
            "resource_name": resource_name,
            "summary": summary,
            "payload": payload,
        },
    )


def record_auto_approved(
    request: Request,
    *,
    action: str,
    resource_type: str,
    resource_id: str,
    resource_name: str,
    summary: str,
    payload: dict[str, Any],
    result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Record an auto-approved action so it shows in the approval log."""
    from qwenpaw_ext.nexora.approval_requests import create_approval_request

    requester = current_requester(request)
    record = create_approval_request(
        {
            "action": action,
            "requester": requester,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "resource_name": resource_name,
            "summary": summary,
            "payload": payload,
        },
    )
    from qwenpaw_ext.nexora.approval_requests import update_approval_request

    update_approval_request(
        record["id"],
        {
            "status": "applied",
            "approver": "[auto]",
            "reason": "自动审批",
            "result": result or {},
        },
    )
    return record


def pending_approval_response(
    approval: dict[str, Any],
    message: str,
) -> dict[str, str]:
    """Return a stable response shape for pending approvals."""
    return {
        "status": "pending_approval",
        "approval_request_id": str(approval["id"]),
        "message": message,
    }
