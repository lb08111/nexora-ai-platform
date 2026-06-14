# -*- coding: utf-8 -*-
"""PostgreSQL repository for Nexora audit events."""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy import text

from qwenpaw_ext.nexora import db


def _json_for_db(value: dict | None) -> str:
    return json.dumps(value or {}, ensure_ascii=False, separators=(",", ":"))


def _json_from_db(value: Any) -> dict:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def insert_event(event: dict) -> None:
    db.initialize_schema()
    engine = db.get_engine()
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO nexora_audit_events (
                    id, timestamp, actor, action, resource_type, resource_id,
                    status, ip, user_agent, detail
                )
                VALUES (
                    :id, :timestamp, :actor, :action, :resource_type,
                    :resource_id, :status, :ip, :user_agent,
                    CAST(:detail AS JSONB)
                )
                """,
            ),
            {
                "id": event["id"],
                "timestamp": event["timestamp"],
                "actor": event.get("actor") or "anonymous",
                "action": event.get("action") or "",
                "resource_type": event.get("resource_type") or "",
                "resource_id": event.get("resource_id") or "",
                "status": event.get("status") or "success",
                "ip": event.get("ip") or "",
                "user_agent": event.get("user_agent") or "",
                "detail": _json_for_db(event.get("detail")),
            },
        )


def list_events(
    *,
    limit: int = 200,
    actor: str | None = None,
    action: str | None = None,
    status: str | None = None,
    start_time: int | None = None,
    end_time: int | None = None,
) -> list[dict]:
    db.initialize_schema()
    limit = max(1, min(limit, 1000))
    filters = []
    params: dict[str, Any] = {"limit": limit}
    if actor:
        filters.append("actor ILIKE :actor")
        params["actor"] = f"%{actor}%"
    if action:
        filters.append("action ILIKE :action")
        params["action"] = f"%{action}%"
    if status:
        filters.append("status = :status")
        params["status"] = status
    if start_time is not None:
        filters.append("timestamp >= :start_time")
        params["start_time"] = start_time
    if end_time is not None:
        filters.append("timestamp <= :end_time")
        params["end_time"] = end_time
    where_sql = f"WHERE {' AND '.join(filters)}" if filters else ""
    query = text(
        f"""
        SELECT id, timestamp, actor, action, resource_type, resource_id,
               status, ip, user_agent, detail
        FROM nexora_audit_events
        {where_sql}
        ORDER BY created_at DESC, timestamp DESC
        LIMIT :limit
        """,
    )
    engine = db.get_engine()
    with engine.begin() as conn:
        rows = conn.execute(query, params).mappings().all()
    return [
        {
            "id": row["id"],
            "timestamp": row["timestamp"],
            "actor": row["actor"],
            "action": row["action"],
            "resource_type": row["resource_type"],
            "resource_id": row["resource_id"],
            "status": row["status"],
            "ip": row["ip"],
            "user_agent": row["user_agent"],
            "detail": _json_from_db(row["detail"]),
        }
        for row in rows
    ]
