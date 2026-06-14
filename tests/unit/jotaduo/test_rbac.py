# -*- coding: utf-8 -*-
"""Unit tests for Jotaduo RBAC policy mapping."""
from __future__ import annotations

import pytest

from jotaduo_ext.jotaduo import rbac


@pytest.fixture
def auth_data():
    return {
        "roles": rbac.default_roles(),
        "users": [
            {
                "username": "admin",
                "roles": ["admin"],
                "status": "active",
            },
            {
                "username": "operator",
                "roles": ["operator"],
                "status": "active",
            },
            {
                "username": "disabled",
                "roles": ["admin"],
                "status": "disabled",
            },
        ],
    }


@pytest.fixture(autouse=True)
def _mock_auth_store(monkeypatch: pytest.MonkeyPatch, auth_data):
    import jotaduo.app.auth as auth

    monkeypatch.setattr(auth, "_load_normalized_auth_data", lambda: auth_data)
    monkeypatch.setattr(
        auth,
        "_find_user",
        lambda data, username: next(
            (
                (idx, user)
                for idx, user in enumerate(data.get("users", []))
                if user.get("username") == username
            ),
            (-1, None),
        ),
    )


@pytest.mark.parametrize(
    ("path", "method", "permission"),
    [
        ("/api/auth/users", "POST", "users.manage"),
        ("/api/auth/users", "GET", "users.view"),
        ("/api/agents/default/messages", "GET", "agents.use"),
        ("/api/agents/default/tools", "POST", "tools.manage"),
        ("/api/jotaduo/governance/policies", "GET", "governance.view"),
        ("/api/jotaduo/governance/policies", "POST", "governance.manage"),
        ("/api/jotaduo/approval-requests", "GET", "approval.manage"),
        (
            "/api/jotaduo/approval-requests/abc/approve",
            "POST",
            "approval.manage",
        ),
        ("/api/jotaduo/audit/events", "GET", "audit.view"),
        ("/api/approval/list", "GET", "approval.manage"),
        ("/api/approval/approve", "POST", "approval.manage"),
    ],
)
def test_required_permission_mapping(path: str, method: str, permission: str):
    assert rbac.required_permission(path, method) == permission


def test_admin_role_has_every_permission():
    for permission in rbac.DEFAULT_PERMISSIONS:
        assert rbac.user_has_permission("admin", permission)


def test_operator_permission_implications_are_enforced():
    assert rbac.user_has_permission("operator", "agents.use")
    assert rbac.user_has_permission("operator", "agents.manage")
    assert rbac.user_has_permission("operator", "tools.execute")
    assert rbac.user_has_permission("operator", "tools.manage")
    assert rbac.user_has_permission("operator", "mcp.manage")
    assert not rbac.user_has_permission("operator", "system.admin")
    assert not rbac.user_has_permission("operator", "users.manage")
    assert not rbac.user_has_permission("operator", "approval.manage")
    assert not rbac.user_has_permission("operator", "audit.view")


def test_disabled_user_has_no_permission():
    assert not rbac.user_has_permission("disabled", "system.admin")


def test_auth_normalization_backfills_new_builtin_permissions(
    monkeypatch: pytest.MonkeyPatch,
):
    import jotaduo.app.auth as auth

    saved_payloads: list[dict] = []
    monkeypatch.setattr(
        auth,
        "_save_auth_data",
        lambda data: saved_payloads.append(data.copy()),
    )

    data = {
        "users": [
            {
                "username": "ops",
                "roles": ["operator"],
                "status": "active",
            },
        ],
        "roles": {
            "operator": {
                "id": "operator",
                "name": "平台操作员",
                "permissions": ["agents.use"],
                "builtin": True,
            },
        },
    }

    normalized = auth._normalize_auth_data(data)

    permissions = normalized["roles"]["operator"]["permissions"]
    assert "agents.use" in permissions
    assert "mcp.manage" in permissions
    assert saved_payloads
