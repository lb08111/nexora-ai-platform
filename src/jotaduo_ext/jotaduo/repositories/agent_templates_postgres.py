# -*- coding: utf-8 -*-
"""PostgreSQL repository for agent initialization templates."""
from __future__ import annotations

import json
import time
import uuid
from typing import Any

from sqlalchemy import text

from jotaduo_ext.jotaduo import db


def _template_row(row: Any) -> dict:
    caps = row["capabilities"]
    if isinstance(caps, str):
        try:
            caps = json.loads(caps)
        except json.JSONDecodeError:
            caps = {}
    return {
        "template_id": row["template_id"],
        "name": row["name"],
        "description": row["description"],
        "capabilities": caps if isinstance(caps, dict) else {},
        "created_by": row["created_by"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def list_templates() -> list[dict]:
    db.initialize_schema()
    with db.get_engine().begin() as conn:
        rows = (
            conn.execute(
                text(
                    """
                SELECT template_id, name, description, capabilities,
                       created_by, created_at, updated_at
                FROM jotaduo_agent_templates
                ORDER BY created_at
                """,
                ),
            )
            .mappings()
            .all()
        )
    return [_template_row(r) for r in rows]


def get_template(template_id: str) -> dict | None:
    db.initialize_schema()
    with db.get_engine().begin() as conn:
        row = (
            conn.execute(
                text(
                    """
                SELECT template_id, name, description, capabilities,
                       created_by, created_at, updated_at
                FROM jotaduo_agent_templates
                WHERE template_id = :template_id
                """,
                ),
                {"template_id": template_id},
            )
            .mappings()
            .first()
        )
    return _template_row(row) if row else None


def create_template(template: dict) -> dict:
    db.initialize_schema()
    now = int(time.time() * 1000)
    template_id = template.get("template_id") or uuid.uuid4().hex[:12]
    caps_json = json.dumps(
        template.get("capabilities", {}),
        ensure_ascii=False,
        separators=(",", ":"),
    )
    with db.get_engine().begin() as conn:
        row = (
            conn.execute(
                text(
                    """
                INSERT INTO jotaduo_agent_templates (
                    template_id, name, description, capabilities,
                    created_by, created_at, updated_at
                )
                VALUES (
                    :template_id, :name, :description,
                    CAST(:capabilities AS JSONB),
                    :created_by, :created_at, :updated_at
                )
                RETURNING template_id, name, description, capabilities,
                          created_by, created_at, updated_at
                """,
                ),
                {
                    "template_id": template_id,
                    "name": template["name"],
                    "description": template.get("description", ""),
                    "capabilities": caps_json,
                    "created_by": template.get("created_by", "admin"),
                    "created_at": now,
                    "updated_at": now,
                },
            )
            .mappings()
            .one()
        )
    return _template_row(row)


def update_template(template_id: str, updates: dict) -> dict | None:
    db.initialize_schema()
    now = int(time.time() * 1000)
    sets = ["updated_at = :updated_at"]
    params: dict[str, Any] = {"template_id": template_id, "updated_at": now}
    if "name" in updates:
        sets.append("name = :name")
        params["name"] = updates["name"]
    if "description" in updates:
        sets.append("description = :description")
        params["description"] = updates["description"]
    if "capabilities" in updates:
        sets.append("capabilities = CAST(:capabilities AS JSONB)")
        params["capabilities"] = json.dumps(
            updates["capabilities"],
            ensure_ascii=False,
            separators=(",", ":"),
        )
    set_clause = ", ".join(sets)
    with db.get_engine().begin() as conn:
        row = (
            conn.execute(
                text(
                    f"""
                UPDATE jotaduo_agent_templates
                SET {set_clause}
                WHERE template_id = :template_id
                RETURNING template_id, name, description, capabilities,
                          created_by, created_at, updated_at
                """,
                ),
                params,
            )
            .mappings()
            .first()
        )
    return _template_row(row) if row else None


def delete_template(template_id: str) -> bool:
    db.initialize_schema()
    with db.get_engine().begin() as conn:
        result = conn.execute(
            text(
                "DELETE FROM jotaduo_agent_templates WHERE template_id = :id",
            ),
            {"id": template_id},
        )
    return result.rowcount > 0


def delete_all_templates() -> None:
    """Clear all templates. Intended for tests and re-initialization."""
    db.initialize_schema()
    with db.get_engine().begin() as conn:
        conn.execute(text("DELETE FROM jotaduo_agent_templates"))
