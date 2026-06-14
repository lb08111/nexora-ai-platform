# -*- coding: utf-8 -*-
"""PostgreSQL repository for Jotaduo users, roles, and permissions."""
from __future__ import annotations

import time

from sqlalchemy import text

from jotaduo_ext.jotaduo import db


def _now() -> int:
    return int(time.time())


def _load_roles_map() -> dict[str, dict]:
    db.initialize_schema()
    with db.get_engine().begin() as conn:
        roles = (
            conn.execute(
                text(
                    """
                SELECT id, name, description, builtin
                FROM jotaduo_roles
                ORDER BY id
                """,
                ),
            )
            .mappings()
            .all()
        )
        perms = (
            conn.execute(
                text(
                    """
                SELECT role_id, permission
                FROM jotaduo_role_permissions
                ORDER BY role_id, permission
                """,
                ),
            )
            .mappings()
            .all()
        )

    permissions_by_role: dict[str, list[str]] = {}
    for row in perms:
        permissions_by_role.setdefault(row["role_id"], []).append(
            row["permission"],
        )

    return {
        row["id"]: {
            "id": row["id"],
            "name": row["name"],
            "description": row["description"],
            "permissions": permissions_by_role.get(row["id"], []),
            "builtin": bool(row["builtin"]),
        }
        for row in roles
    }


def load_auth_data() -> dict:
    db.initialize_schema()
    with db.get_engine().begin() as conn:
        users = (
            conn.execute(
                text(
                    """
                SELECT id, username, password_hash, password_salt, status,
                       created_at, updated_at
                FROM jotaduo_users
                ORDER BY username
                """,
                ),
            )
            .mappings()
            .all()
        )
        user_roles = (
            conn.execute(
                text(
                    """
                SELECT username, role_id
                FROM jotaduo_user_roles
                ORDER BY username, role_id
                """,
                ),
            )
            .mappings()
            .all()
        )

    roles_by_user: dict[str, list[str]] = {}
    for row in user_roles:
        roles_by_user.setdefault(row["username"], []).append(row["role_id"])

    return {
        "users": [
            {
                "id": row["id"],
                "username": row["username"],
                "password_hash": row["password_hash"],
                "password_salt": row["password_salt"],
                "roles": roles_by_user.get(row["username"], []),
                "status": row["status"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
            for row in users
        ],
        "roles": _load_roles_map(),
    }


def save_auth_data(data: dict) -> None:
    db.initialize_schema()
    users = [user for user in data.get("users", []) if isinstance(user, dict)]
    roles = data.get("roles") if isinstance(data.get("roles"), dict) else {}
    sync_users = "users" in data
    sync_roles = "roles" in data
    user_names = {
        user.get("username") for user in users if user.get("username")
    }
    role_ids = set(roles.keys())

    with db.get_engine().begin() as conn:
        if sync_roles:
            existing_role_ids = [
                row["id"]
                for row in conn.execute(
                    text("SELECT id FROM jotaduo_roles"),
                ).mappings()
            ]
            for role_id in existing_role_ids:
                if role_id not in role_ids:
                    conn.execute(
                        text(
                            "DELETE FROM jotaduo_role_permissions "
                            "WHERE role_id = :role_id",
                        ),
                        {"role_id": role_id},
                    )
                    conn.execute(
                        text(
                            "DELETE FROM jotaduo_user_roles "
                            "WHERE role_id = :role_id",
                        ),
                        {"role_id": role_id},
                    )
                    conn.execute(
                        text("DELETE FROM jotaduo_roles WHERE id = :role_id"),
                        {"role_id": role_id},
                    )

        if sync_users:
            existing_usernames = [
                row["username"]
                for row in conn.execute(
                    text("SELECT username FROM jotaduo_users"),
                ).mappings()
            ]
            for username in existing_usernames:
                if username not in user_names:
                    conn.execute(
                        text(
                            "DELETE FROM jotaduo_user_roles "
                            "WHERE username = :username",
                        ),
                        {"username": username},
                    )
                    conn.execute(
                        text(
                            "DELETE FROM jotaduo_users "
                            "WHERE username = :username",
                        ),
                        {"username": username},
                    )

        for role_id, role in roles.items():
            conn.execute(
                text(
                    """
                    INSERT INTO jotaduo_roles (
                        id, name, description, builtin, created_at, updated_at
                    )
                    VALUES (
                        :id, :name, :description, :builtin,
                        :created_at, :updated_at
                    )
                    ON CONFLICT (id) DO UPDATE SET
                        name = EXCLUDED.name,
                        description = EXCLUDED.description,
                        builtin = EXCLUDED.builtin,
                        updated_at = EXCLUDED.updated_at
                    """,
                ),
                {
                    "id": role_id,
                    "name": role.get("name") or role_id,
                    "description": role.get("description") or "",
                    "builtin": bool(role.get("builtin", False)),
                    "created_at": int(role.get("created_at") or _now()),
                    "updated_at": int(role.get("updated_at") or _now()),
                },
            )
            conn.execute(
                text(
                    "DELETE FROM jotaduo_role_permissions WHERE role_id = :role_id",
                ),
                {"role_id": role_id},
            )
            for permission in role.get("permissions") or []:
                conn.execute(
                    text(
                        """
                        INSERT INTO jotaduo_role_permissions (role_id, permission)
                        VALUES (:role_id, :permission)
                        ON CONFLICT DO NOTHING
                        """,
                    ),
                    {"role_id": role_id, "permission": permission},
                )

        for user in users:
            username = user.get("username")
            if not username:
                continue
            conn.execute(
                text(
                    """
                    INSERT INTO jotaduo_users (
                        id, username, password_hash, password_salt, status,
                        created_at, updated_at
                    )
                    VALUES (
                        :id, :username, :password_hash, :password_salt,
                        :status, :created_at, :updated_at
                    )
                    ON CONFLICT (username) DO UPDATE SET
                        id = EXCLUDED.id,
                        password_hash = EXCLUDED.password_hash,
                        password_salt = EXCLUDED.password_salt,
                        status = EXCLUDED.status,
                        updated_at = EXCLUDED.updated_at
                    """,
                ),
                {
                    "id": user.get("id") or "",
                    "username": username,
                    "password_hash": user.get("password_hash") or "",
                    "password_salt": user.get("password_salt") or "",
                    "status": user.get("status") or "active",
                    "created_at": int(user.get("created_at") or _now()),
                    "updated_at": int(user.get("updated_at") or _now()),
                },
            )
            conn.execute(
                text(
                    "DELETE FROM jotaduo_user_roles WHERE username = :username",
                ),
                {"username": username},
            )
            for role_id in user.get("roles") or []:
                conn.execute(
                    text(
                        """
                        INSERT INTO jotaduo_user_roles (username, role_id)
                        VALUES (:username, :role_id)
                        ON CONFLICT DO NOTHING
                        """,
                    ),
                    {"username": username, "role_id": role_id},
                )


def delete_user(username: str) -> bool:
    db.initialize_schema()
    with db.get_engine().begin() as conn:
        conn.execute(
            text("DELETE FROM jotaduo_user_roles WHERE username = :username"),
            {"username": username},
        )
        result = conn.execute(
            text("DELETE FROM jotaduo_users WHERE username = :username"),
            {"username": username},
        )
    return result.rowcount > 0


def delete_role(role_id: str) -> bool:
    db.initialize_schema()
    with db.get_engine().begin() as conn:
        conn.execute(
            text(
                "DELETE FROM jotaduo_role_permissions WHERE role_id = :role_id",
            ),
            {"role_id": role_id},
        )
        result = conn.execute(
            text("DELETE FROM jotaduo_roles WHERE id = :role_id"),
            {"role_id": role_id},
        )
    return result.rowcount > 0
