# -*- coding: utf-8 -*-
"""PostgreSQL repository for Jotaduo approval requests."""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy import text

from jotaduo_ext.jotaduo import db


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


def _row_to_request(row: Any) -> dict:
    return {
        "id": row["id"],
        "action": row["action"],
        "status": row["status"],
        "requester": row["requester"],
        "approver": row["approver"],
        "resource_type": row["resource_type"],
        "resource_id": row["resource_id"],
        "resource_name": row["resource_name"],
        "summary": row["summary"],
        "reason": row["reason"],
        "payload": _json_from_db(row["payload"]),
        "result": _json_from_db(row["result"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def create_request(item: dict) -> dict:
    db.initialize_schema()
    engine = db.get_engine()
    with engine.begin() as conn:
        row = (
            conn.execute(
                text(
                    """
                INSERT INTO jotaduo_approval_requests (
                    id, action, status, requester, approver, resource_type,
                    resource_id, resource_name, summary, reason, payload,
                    result, created_at, updated_at
                )
                VALUES (
                    :id, :action, :status, :requester, :approver,
                    :resource_type, :resource_id, :resource_name, :summary,
                    :reason, CAST(:payload AS JSONB), CAST(:result AS JSONB),
                    :created_at, :updated_at
                )
                RETURNING id, action, status, requester, approver,
                          resource_type, resource_id, resource_name, summary,
                          reason, payload, result, created_at, updated_at
                """,
                ),
                {
                    **item,
                    "payload": _json_for_db(item.get("payload")),
                    "result": _json_for_db(item.get("result")),
                },
            )
            .mappings()
            .one()
        )
    return _row_to_request(row)


def get_request(request_id: str) -> dict | None:
    db.initialize_schema()
    engine = db.get_engine()
    with engine.begin() as conn:
        row = (
            conn.execute(
                text(
                    """
                SELECT id, action, status, requester, approver, resource_type,
                       resource_id, resource_name, summary, reason, payload,
                       result, created_at, updated_at
                FROM jotaduo_approval_requests
                WHERE id = :id
                """,
                ),
                {"id": request_id},
            )
            .mappings()
            .first()
        )
    return _row_to_request(row) if row is not None else None


def list_requests(
    status: str | None = None,
    action: str | None = None,
    limit: int = 1000,
) -> list[dict]:
    db.initialize_schema()
    limit = max(1, min(limit, 5000))
    filters = []
    params: dict[str, Any] = {"limit": limit}
    if status:
        filters.append("status = :status")
        params["status"] = status
    if action:
        filters.append("action = :action")
        params["action"] = action
    where_sql = f"WHERE {' AND '.join(filters)}" if filters else ""
    query = text(
        f"""
        SELECT id, action, status, requester, approver, resource_type,
               resource_id, resource_name, summary, reason, payload, result,
               created_at, updated_at
        FROM jotaduo_approval_requests
        {where_sql}
        ORDER BY created_at DESC
        LIMIT :limit
        """,
    )
    engine = db.get_engine()
    with engine.begin() as conn:
        rows = conn.execute(query, params).mappings().all()
    return [_row_to_request(row) for row in rows]


def update_request(request_id: str, item: dict) -> dict | None:
    db.initialize_schema()
    engine = db.get_engine()
    with engine.begin() as conn:
        row = (
            conn.execute(
                text(
                    """
                UPDATE jotaduo_approval_requests
                SET action = :action,
                    status = :status,
                    requester = :requester,
                    approver = :approver,
                    resource_type = :resource_type,
                    resource_id = :resource_id,
                    resource_name = :resource_name,
                    summary = :summary,
                    reason = :reason,
                    payload = CAST(:payload AS JSONB),
                    result = CAST(:result AS JSONB),
                    created_at = :created_at,
                    updated_at = :updated_at
                WHERE id = :id
                RETURNING id, action, status, requester, approver,
                          resource_type, resource_id, resource_name, summary,
                          reason, payload, result, created_at, updated_at
                """,
                ),
                {
                    **item,
                    "id": request_id,
                    "payload": _json_for_db(item.get("payload")),
                    "result": _json_for_db(item.get("result")),
                },
            )
            .mappings()
            .first()
        )
    return _row_to_request(row) if row is not None else None
