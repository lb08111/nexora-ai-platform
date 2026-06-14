# -*- coding: utf-8 -*-
"""PostgreSQL repository for per-capability-type approval configuration."""
from __future__ import annotations

import json
import time
from typing import Any

from sqlalchemy import text

from qwenpaw_ext.nexora import db


def _config_row(row: Any) -> dict:
    return {
        "capability_type": row["capability_type"],
        "add_policy": row["add_policy"],
        "remove_policy": row["remove_policy"],
        "approver_roles": (
            row["approver_roles"]
            if isinstance(row["approver_roles"], list)
            else []
        ),
        "updated_at": row["updated_at"],
    }


def list_configs() -> list[dict]:
    db.initialize_schema()
    with db.get_engine().begin() as conn:
        rows = (
            conn.execute(
                text(
                    """
                SELECT capability_type, add_policy, remove_policy,
                       approver_roles, updated_at
                FROM nexora_capability_approval_config
                ORDER BY capability_type
                """,
                ),
            )
            .mappings()
            .all()
        )
    return [_config_row(r) for r in rows]


def get_config(capability_type: str) -> dict | None:
    db.initialize_schema()
    with db.get_engine().begin() as conn:
        row = (
            conn.execute(
                text(
                    """
                SELECT capability_type, add_policy, remove_policy,
                       approver_roles, updated_at
                FROM nexora_capability_approval_config
                WHERE capability_type = :capability_type
                """,
                ),
                {"capability_type": capability_type},
            )
            .mappings()
            .first()
        )
    return _config_row(row) if row else None


def upsert_config(config: dict) -> dict:
    db.initialize_schema()
    now = int(time.time() * 1000)
    approver_roles = json.dumps(
        config.get("approver_roles", ["admin"]),
        ensure_ascii=False,
        separators=(",", ":"),
    )
    with db.get_engine().begin() as conn:
        row = (
            conn.execute(
                text(
                    """
                INSERT INTO nexora_capability_approval_config (
                    capability_type, add_policy, remove_policy,
                    approver_roles, updated_at
                )
                VALUES (
                    :capability_type, :add_policy, :remove_policy,
                    CAST(:approver_roles AS JSONB), :updated_at
                )
                ON CONFLICT (capability_type) DO UPDATE SET
                    add_policy = EXCLUDED.add_policy,
                    remove_policy = EXCLUDED.remove_policy,
                    approver_roles = EXCLUDED.approver_roles,
                    updated_at = EXCLUDED.updated_at
                RETURNING capability_type, add_policy, remove_policy,
                          approver_roles, updated_at
                """,
                ),
                {
                    "capability_type": config["capability_type"],
                    "add_policy": config.get("add_policy", "approval"),
                    "remove_policy": config.get("remove_policy", "log"),
                    "approver_roles": approver_roles,
                    "updated_at": now,
                },
            )
            .mappings()
            .one()
        )
    return _config_row(row)


def partial_update(capability_type: str, updates: dict) -> dict:
    """Atomically update only the specified fields using SQL SET clauses."""
    db.initialize_schema()
    now = int(time.time() * 1000)
    set_clauses = ["updated_at = :updated_at"]
    params: dict[str, Any] = {
        "capability_type": capability_type,
        "updated_at": now,
    }
    if "add_policy" in updates:
        set_clauses.append("add_policy = :add_policy")
        params["add_policy"] = updates["add_policy"]
    if "remove_policy" in updates:
        set_clauses.append("remove_policy = :remove_policy")
        params["remove_policy"] = updates["remove_policy"]
    if "approver_roles" in updates:
        set_clauses.append("approver_roles = CAST(:approver_roles AS JSONB)")
        params["approver_roles"] = json.dumps(
            updates["approver_roles"],
            ensure_ascii=False,
            separators=(",", ":"),
        )
    set_sql = ", ".join(set_clauses)
    with db.get_engine().begin() as conn:
        row = (
            conn.execute(
                text(
                    f"""
                UPDATE nexora_capability_approval_config
                SET {set_sql}
                WHERE capability_type = :capability_type
                RETURNING capability_type, add_policy, remove_policy,
                          approver_roles, updated_at
                """,
                ),
                params,
            )
            .mappings()
            .first()
        )
    if row is None:
        return upsert_config(
            {
                "capability_type": capability_type,
                **updates,
            }
        )
    return _config_row(row)


def delete_all_configs() -> None:
    """Clear all configs. Intended for tests and re-initialization."""
    db.initialize_schema()
    with db.get_engine().begin() as conn:
        conn.execute(text("DELETE FROM nexora_capability_approval_config"))
