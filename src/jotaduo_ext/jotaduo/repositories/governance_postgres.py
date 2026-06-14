# -*- coding: utf-8 -*-
"""PostgreSQL repository for Jotaduo governance policies."""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy import text

from jotaduo_ext.jotaduo import db


def _json_for_db(value: list | None) -> str:
    return json.dumps(value or [], ensure_ascii=False, separators=(",", ":"))


def _list_from_db(value: Any) -> list:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return []
        return parsed if isinstance(parsed, list) else []
    return []


def _resource_row(row: Any) -> dict:
    return {
        "id": row["id"],
        "source": row["source"],
        "resource_id": row["resource_id"],
        "display_name": row["display_name"],
        "description": row["description"],
        "risk_level": row["risk_level"],
        "allowed_agents": _list_from_db(row["allowed_agents"]),
        "allowed_roles": _list_from_db(row["allowed_roles"]),
        "approval_required": row["approval_required"],
        "audit_enabled": row["audit_enabled"],
        "enabled": row["enabled"],
        "updated_at": row["updated_at"],
    }


def _agent_row(row: Any) -> dict:
    return {
        "id": row["id"],
        "agent_id": row["agent_id"],
        "display_name": row["display_name"],
        "description": row["description"],
        "allowed_roles": _list_from_db(row["allowed_roles"]),
        "visible": row["visible"],
        "usable": row["usable"],
        "manageable": row["manageable"],
        "enabled": row["enabled"],
        "updated_at": row["updated_at"],
    }


def _approval_row(row: Any) -> dict:
    return {
        "id": row["id"],
        "action": row["action"],
        "display_name": row["display_name"],
        "description": row["description"],
        "enabled": row["enabled"],
        "approver_roles": _list_from_db(row["approver_roles"]),
        "allow_self_approval": row["allow_self_approval"],
        "updated_at": row["updated_at"],
    }


def get_resource_policy(policy_id: str) -> dict | None:
    db.initialize_schema()
    with db.get_engine().begin() as conn:
        row = (
            conn.execute(
                text(
                    """
                SELECT id, source, resource_id, display_name, description,
                       risk_level, allowed_agents, allowed_roles,
                       approval_required, audit_enabled, enabled, updated_at
                FROM jotaduo_resource_policies
                WHERE id = :id
                """,
                ),
                {"id": policy_id},
            )
            .mappings()
            .first()
        )
    return _resource_row(row) if row else None


def list_resource_policies(limit: int = 1000) -> list[dict]:
    db.initialize_schema()
    limit = max(1, min(limit, 5000))
    with db.get_engine().begin() as conn:
        rows = (
            conn.execute(
                text(
                    """
                SELECT id, source, resource_id, display_name, description,
                       risk_level, allowed_agents, allowed_roles,
                       approval_required, audit_enabled, enabled, updated_at
                FROM jotaduo_resource_policies
                ORDER BY source, resource_id
                LIMIT :limit
                """,
                ),
                {"limit": limit},
            )
            .mappings()
            .all()
        )
    return [_resource_row(row) for row in rows]


def upsert_resource_policy(policy: dict) -> dict:
    db.initialize_schema()
    with db.get_engine().begin() as conn:
        row = (
            conn.execute(
                text(
                    """
                INSERT INTO jotaduo_resource_policies (
                    id, source, resource_id, display_name, description,
                    risk_level, allowed_agents, allowed_roles,
                    approval_required, audit_enabled, enabled, updated_at
                )
                VALUES (
                    :id, :source, :resource_id, :display_name, :description,
                    :risk_level, CAST(:allowed_agents AS JSONB),
                    CAST(:allowed_roles AS JSONB), :approval_required,
                    :audit_enabled, :enabled, :updated_at
                )
                ON CONFLICT (id) DO UPDATE SET
                    source = EXCLUDED.source,
                    resource_id = EXCLUDED.resource_id,
                    display_name = EXCLUDED.display_name,
                    description = EXCLUDED.description,
                    risk_level = EXCLUDED.risk_level,
                    allowed_agents = EXCLUDED.allowed_agents,
                    allowed_roles = EXCLUDED.allowed_roles,
                    approval_required = EXCLUDED.approval_required,
                    audit_enabled = EXCLUDED.audit_enabled,
                    enabled = EXCLUDED.enabled,
                    updated_at = EXCLUDED.updated_at
                RETURNING id, source, resource_id, display_name, description,
                          risk_level, allowed_agents, allowed_roles,
                          approval_required, audit_enabled, enabled, updated_at
                """,
                ),
                {
                    **policy,
                    "allowed_agents": _json_for_db(
                        policy.get("allowed_agents")
                    ),
                    "allowed_roles": _json_for_db(policy.get("allowed_roles")),
                },
            )
            .mappings()
            .one()
        )
    return _resource_row(row)


def delete_resource_policy(policy_id: str) -> bool:
    db.initialize_schema()
    with db.get_engine().begin() as conn:
        result = conn.execute(
            text("DELETE FROM jotaduo_resource_policies WHERE id = :id"),
            {"id": policy_id},
        )
    return result.rowcount > 0


def get_agent_policy(policy_id: str) -> dict | None:
    db.initialize_schema()
    with db.get_engine().begin() as conn:
        row = (
            conn.execute(
                text(
                    """
                SELECT id, agent_id, display_name, description, allowed_roles,
                       visible, usable, manageable, enabled, updated_at
                FROM jotaduo_agent_policies
                WHERE id = :id
                """,
                ),
                {"id": policy_id},
            )
            .mappings()
            .first()
        )
    return _agent_row(row) if row else None


def list_agent_policies(limit: int = 1000) -> list[dict]:
    db.initialize_schema()
    limit = max(1, min(limit, 5000))
    with db.get_engine().begin() as conn:
        rows = (
            conn.execute(
                text(
                    """
                SELECT id, agent_id, display_name, description, allowed_roles,
                       visible, usable, manageable, enabled, updated_at
                FROM jotaduo_agent_policies
                ORDER BY agent_id
                LIMIT :limit
                """,
                ),
                {"limit": limit},
            )
            .mappings()
            .all()
        )
    return [_agent_row(row) for row in rows]


def upsert_agent_policy(policy: dict) -> dict:
    db.initialize_schema()
    with db.get_engine().begin() as conn:
        row = (
            conn.execute(
                text(
                    """
                INSERT INTO jotaduo_agent_policies (
                    id, agent_id, display_name, description, allowed_roles,
                    visible, usable, manageable, enabled, updated_at
                )
                VALUES (
                    :id, :agent_id, :display_name, :description,
                    CAST(:allowed_roles AS JSONB), :visible, :usable,
                    :manageable, :enabled, :updated_at
                )
                ON CONFLICT (id) DO UPDATE SET
                    agent_id = EXCLUDED.agent_id,
                    display_name = EXCLUDED.display_name,
                    description = EXCLUDED.description,
                    allowed_roles = EXCLUDED.allowed_roles,
                    visible = EXCLUDED.visible,
                    usable = EXCLUDED.usable,
                    manageable = EXCLUDED.manageable,
                    enabled = EXCLUDED.enabled,
                    updated_at = EXCLUDED.updated_at
                RETURNING id, agent_id, display_name, description,
                          allowed_roles, visible, usable, manageable,
                          enabled, updated_at
                """,
                ),
                {
                    **policy,
                    "allowed_roles": _json_for_db(policy.get("allowed_roles")),
                },
            )
            .mappings()
            .one()
        )
    return _agent_row(row)


def delete_agent_policy(policy_id: str) -> bool:
    db.initialize_schema()
    with db.get_engine().begin() as conn:
        result = conn.execute(
            text("DELETE FROM jotaduo_agent_policies WHERE id = :id"),
            {"id": policy_id},
        )
    return result.rowcount > 0


def get_approval_policy(action: str) -> dict | None:
    db.initialize_schema()
    with db.get_engine().begin() as conn:
        row = (
            conn.execute(
                text(
                    """
                SELECT id, action, display_name, description, enabled,
                       approver_roles, allow_self_approval, updated_at
                FROM jotaduo_approval_policies
                WHERE action = :action
                """,
                ),
                {"action": action},
            )
            .mappings()
            .first()
        )
    return _approval_row(row) if row else None


def list_approval_policies(limit: int = 1000) -> list[dict]:
    db.initialize_schema()
    limit = max(1, min(limit, 5000))
    with db.get_engine().begin() as conn:
        rows = (
            conn.execute(
                text(
                    """
                SELECT id, action, display_name, description, enabled,
                       approver_roles, allow_self_approval, updated_at
                FROM jotaduo_approval_policies
                ORDER BY action
                LIMIT :limit
                """,
                ),
                {"limit": limit},
            )
            .mappings()
            .all()
        )
    return [_approval_row(row) for row in rows]


def upsert_approval_policy(policy: dict) -> dict:
    db.initialize_schema()
    with db.get_engine().begin() as conn:
        row = (
            conn.execute(
                text(
                    """
                INSERT INTO jotaduo_approval_policies (
                    id, action, display_name, description, enabled,
                    approver_roles, allow_self_approval, updated_at
                )
                VALUES (
                    :id, :action, :display_name, :description, :enabled,
                    CAST(:approver_roles AS JSONB), :allow_self_approval,
                    :updated_at
                )
                ON CONFLICT (id) DO UPDATE SET
                    action = EXCLUDED.action,
                    display_name = EXCLUDED.display_name,
                    description = EXCLUDED.description,
                    enabled = EXCLUDED.enabled,
                    approver_roles = EXCLUDED.approver_roles,
                    allow_self_approval = EXCLUDED.allow_self_approval,
                    updated_at = EXCLUDED.updated_at
                RETURNING id, action, display_name, description, enabled,
                          approver_roles, allow_self_approval, updated_at
                """,
                ),
                {
                    **policy,
                    "approver_roles": _json_for_db(
                        policy.get("approver_roles")
                    ),
                },
            )
            .mappings()
            .one()
        )
    return _approval_row(row)


def delete_all_governance_rows() -> None:
    """Clear governance rows. Intended for tests only."""
    db.initialize_schema()
    with db.get_engine().begin() as conn:
        conn.execute(text("DELETE FROM jotaduo_approval_policies"))
        conn.execute(text("DELETE FROM jotaduo_resource_policies"))
        conn.execute(text("DELETE FROM jotaduo_agent_policies"))
