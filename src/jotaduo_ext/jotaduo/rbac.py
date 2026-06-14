# -*- coding: utf-8 -*-
"""Jotaduo role-based access control extension.

This module keeps the platform-specific RBAC policy away from JotaDuo core
modules.  Core auth still owns password/token persistence; this extension owns
roles, permissions, user management, and API permission mapping.
"""
from __future__ import annotations

import secrets
from typing import Optional

DEFAULT_PERMISSIONS: tuple[str, ...] = (
    "system.admin",
    "users.manage",
    "users.view",
    "agents.manage",
    "agents.use",
    "tools.manage",
    "tools.execute",
    "models.manage",
    "mcp.manage",
    "governance.manage",
    "governance.view",
    "approval.manage",
    "audit.view",
)

MENU_PERMISSIONS: tuple[str, ...] = (
    "system.admin",
    "users.manage",
    "users.view",
    "agents.manage",
    "tools.manage",
    "models.manage",
    "mcp.manage",
    "governance.manage",
    "governance.view",
    "audit.view",
)

CAPABILITY_PERMISSIONS: tuple[str, ...] = (
    "agents.use",
    "tools.execute",
)

PERMISSION_GROUPS: dict[str, tuple[str, ...]] = {
    "menu": MENU_PERMISSIONS,
    "capability": CAPABILITY_PERMISSIONS,
}

PERMISSION_IMPLICATIONS: dict[str, tuple[str, ...]] = {
    "users.view": ("users.manage",),
    "agents.use": ("agents.manage",),
    "tools.execute": ("tools.manage",),
    "governance.view": ("governance.manage",),
}

ROLE_DEFINITIONS: dict[str, dict] = {
    "admin": {
        "name": "平台管理员",
        "permissions": list(DEFAULT_PERMISSIONS),
    },
    "operator": {
        "name": "平台操作员",
        "permissions": [
            "agents.manage",
            "agents.use",
            "tools.manage",
            "tools.execute",
            "mcp.manage",
        ],
    },
}

MUTATING_METHODS: frozenset[str] = frozenset(
    {"POST", "PUT", "PATCH", "DELETE"},
)

API_PERMISSION_PREFIXES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("MUTATE", "users.manage", ("/api/auth/users", "/api/auth/roles")),
    (
        "*",
        "users.view",
        ("/api/auth/users", "/api/auth/roles", "/api/auth/permissions"),
    ),
    ("*", "models.manage", ("/api/local-models",)),
    ("MUTATE", "models.manage", ("/api/models",)),
    ("*", "mcp.manage", ("/api/mcp",)),
    ("*", "tools.manage", ("/api/tools",)),
    (
        "MUTATE",
        "governance.manage",
        ("/api/jotaduo/governance",),
    ),
    ("*", "governance.view", ("/api/jotaduo/governance",)),
    ("*", "approval.manage", ("/api/jotaduo/approval-requests",)),
    ("*", "audit.view", ("/api/jotaduo/audit",)),
    ("MUTATE", "agents.manage", ("/api/agents",)),
    ("*", "agents.use", ("/api/agents",)),
    ("MUTATE", "agents.manage", ("/api/workspace",)),
    ("*", "agents.use", ("/api/workspace",)),
    ("*", "agents.manage", ("/api/config", "/api/envs")),
    ("*", "approval.manage", ("/api/approval",)),
    ("*", "system.admin", ("/api/plugins", "/api/backups")),
    ("*", "system.admin", ("/api/settings",)),
    ("*", "system.admin", ("/api/plan",)),
    ("*", "agents.manage", ("/api/cron",)),
    ("*", "system.admin", ("/api/security",)),
    ("*", "audit.view", ("/api/token-usage", "/api/agent-stats")),
    ("*", "agents.use", ("/api/console", "/api/chats", "/api/messages")),
    ("*", "agents.use", ("/api/files", "/api/skills")),
)


def default_roles() -> dict[str, dict]:
    return {
        role_id: {
            "id": role_id,
            "name": role["name"],
            "description": role.get("description", ""),
            "permissions": list(role["permissions"]),
            "builtin": True,
        }
        for role_id, role in ROLE_DEFINITIONS.items()
    }


def list_permissions() -> list[str]:
    return list(DEFAULT_PERMISSIONS)


def list_roles() -> list[dict]:
    from jotaduo.app import auth

    data = auth._load_normalized_auth_data()
    roles = data.get("roles") or default_roles()
    return [
        {
            "id": role_id,
            "name": role.get("name", role_id),
            "description": role.get("description", ""),
            "permissions": list(role.get("permissions") or []),
            "builtin": bool(role.get("builtin", False)),
        }
        for role_id, role in roles.items()
    ]


def role_permissions(role_ids: list[str]) -> set[str]:
    from jotaduo.app import auth

    data = auth._load_normalized_auth_data()
    roles = data.get("roles") or default_roles()
    permissions: set[str] = set()
    for role_id in role_ids:
        role = roles.get(role_id)
        if role:
            permissions.update(role["permissions"])
    return permissions


def user_has_permission(username: str, permission: str) -> bool:
    from jotaduo.app import auth

    data = auth._load_normalized_auth_data()
    _, user = auth._find_user(data, username)
    if not user or user.get("status") != "active":
        return False
    roles = list(user.get("roles") or [])
    if "admin" in roles:
        return True
    permissions = role_permissions(roles)
    return permission in permissions or any(
        implied_by in permissions
        for implied_by in PERMISSION_IMPLICATIONS.get(permission, ())
    )


def require_permission(username: str, permission: str) -> None:
    if not user_has_permission(username, permission):
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="Permission denied")


def _role_exists(data: dict, role_id: str) -> bool:
    roles = data.get("roles") or default_roles()
    return role_id in roles


def _valid_role_ids(data: dict, role_ids: list[str]) -> list[str]:
    return [role_id for role_id in role_ids if _role_exists(data, role_id)]


def create_role(
    role_id: str,
    name: str,
    permissions: list[str],
    description: str = "",
) -> dict | None:
    from jotaduo.app import auth

    data = auth._load_normalized_auth_data()
    role_id = role_id.strip()
    if not role_id or not name.strip():
        return None
    if role_id in (data.get("roles") or {}):
        return None
    allowed_permissions = set(DEFAULT_PERMISSIONS)
    role = {
        "id": role_id,
        "name": name.strip(),
        "description": description.strip(),
        "permissions": [
            item for item in permissions if item in allowed_permissions
        ],
        "builtin": False,
    }
    data.setdefault("roles", default_roles())[role_id] = role
    auth._save_auth_data(data)
    return role


def update_role(
    role_id: str,
    name: Optional[str] = None,
    permissions: Optional[list[str]] = None,
    description: Optional[str] = None,
) -> dict | None:
    from jotaduo.app import auth

    data = auth._load_normalized_auth_data()
    roles = data.get("roles") or default_roles()
    role = roles.get(role_id)
    if not role:
        return None
    if name is not None and name.strip():
        role["name"] = name.strip()
    if description is not None:
        role["description"] = description.strip()
    if permissions is not None:
        allowed_permissions = set(DEFAULT_PERMISSIONS)
        role["permissions"] = [
            item for item in permissions if item in allowed_permissions
        ]
    roles[role_id] = role
    data["roles"] = roles
    auth._save_auth_data(data)
    return {
        "id": role_id,
        "name": role.get("name", role_id),
        "description": role.get("description", ""),
        "permissions": list(role.get("permissions") or []),
        "builtin": bool(role.get("builtin", False)),
    }


def delete_role(role_id: str) -> bool:
    from jotaduo.app import auth

    data = auth._load_normalized_auth_data()
    roles = data.get("roles") or default_roles()
    role = roles.get(role_id)
    if not role or role.get("builtin"):
        return False
    for user in data.get("users", []):
        if role_id in (user.get("roles") or []):
            return False
    del roles[role_id]
    data["roles"] = roles
    auth._save_auth_data(data)
    return True


def list_users() -> list[dict]:
    from jotaduo.app import auth

    data = auth._load_normalized_auth_data()
    return [auth._public_user(user) for user in data.get("users", [])]


def get_user(username: str) -> dict | None:
    from jotaduo.app import auth

    data = auth._load_normalized_auth_data()
    _, user = auth._find_user(data, username)
    return auth._public_user(user) if user else None


def create_user(
    username: str,
    password: str,
    roles: Optional[list[str]] = None,
) -> dict | None:
    from jotaduo.app import auth

    data = auth._load_normalized_auth_data()
    if data.get("_auth_load_error"):
        return None
    username = username.strip()
    if not username or not password.strip():
        return None
    if auth._find_user(data, username)[1] is not None:
        return None

    valid_roles = _valid_role_ids(data, roles or ["operator"]) or ["operator"]
    pw_hash, salt = auth._hash_password(password)
    ts = auth._now()
    user = {
        "id": secrets.token_hex(8),
        "username": username,
        "password_hash": pw_hash,
        "password_salt": salt,
        "roles": valid_roles,
        "status": "active",
        "created_at": ts,
        "updated_at": ts,
    }
    data.setdefault("users", []).append(user)
    auth._save_auth_data(data)
    return auth._public_user(user)


def update_user(
    username: str,
    roles: Optional[list[str]] = None,
    status: Optional[str] = None,
    password: Optional[str] = None,
) -> dict | None:
    from jotaduo.app import auth

    data = auth._load_normalized_auth_data()
    idx, user = auth._find_user(data, username)
    if user is None:
        return None

    if roles is not None:
        valid_roles = _valid_role_ids(data, roles)
        user["roles"] = valid_roles or ["operator"]

    if status is not None:
        if status not in ("active", "disabled"):
            return None
        user["status"] = status

    if password is not None and password.strip():
        pw_hash, salt = auth._hash_password(password)
        user["password_hash"] = pw_hash
        user["password_salt"] = salt
        data["jwt_secret"] = secrets.token_hex(32)

    user["updated_at"] = auth._now()
    data["users"][idx] = user
    auth._save_auth_data(data)
    return auth._public_user(user)


def delete_user(username: str) -> bool:
    from jotaduo.app import auth

    data = auth._load_normalized_auth_data()
    users = data.get("users", [])
    idx, user = auth._find_user(data, username)
    if user is None:
        return False

    active_admins = [
        item
        for item in users
        if item.get("status") == "active"
        and "admin" in (item.get("roles") or [])
    ]
    if "admin" in (user.get("roles") or []) and len(active_admins) <= 1:
        return False

    del users[idx]
    data["users"] = users
    auth._save_auth_data(data)
    return True


def _agent_scoped_permission(path: str, method: str) -> str | None:
    if not path.startswith("/api/agents/"):
        return None
    parts = path.split("/")
    if len(parts) < 5:
        if method in MUTATING_METHODS:
            return "agents.manage"
        return "agents.use"

    scope = parts[4]
    if scope in {
        "agent-status",
        "chats",
        "console",
        "files",
        "messages",
    }:
        return "agents.use"
    if scope == "mcp":
        return "mcp.manage"
    if scope in {"skills", "tools"}:
        return "tools.manage"
    if scope in {"agent-stats", "token-usage"}:
        return "audit.view"
    if scope in {"backups", "config", "envs", "plugins", "settings"}:
        return "system.admin"
    if scope in {"cron", "plan", "workspace"}:
        return "agents.manage"
    return "agents.use"


def required_permission(path: str, method: str) -> str | None:
    method = method.upper()
    scoped_permission = _agent_scoped_permission(path, method)
    if scoped_permission:
        return scoped_permission
    for mode, permission, prefixes in API_PERMISSION_PREFIXES:
        if mode == "MUTATE" and method not in MUTATING_METHODS:
            continue
        if any(path.startswith(prefix) for prefix in prefixes):
            return permission
    return None
