# -*- coding: utf-8 -*-
"""PostgreSQL repository for agent-user grants (multi-tenant authorization)."""
from __future__ import annotations

import time
from typing import Any

from sqlalchemy import text

from qwenpaw_ext.nexora import db


def _grant_row(row: Any) -> dict:
    return {
        "agent_id": row["agent_id"],
        "username": row["username"],
        "granted_by": row["granted_by"],
        "granted_at": row["granted_at"],
    }


def list_grants_for_agent(agent_id: str) -> list[dict]:
    db.initialize_schema()
    with db.get_engine().begin() as conn:
        rows = (
            conn.execute(
                text(
                    """
                SELECT agent_id, username, granted_by, granted_at
                FROM nexora_agent_user_grants
                WHERE agent_id = :agent_id
                ORDER BY granted_at
                """,
                ),
                {"agent_id": agent_id},
            )
            .mappings()
            .all()
        )
    return [_grant_row(r) for r in rows]


def list_grants_for_user(username: str) -> list[dict]:
    db.initialize_schema()
    with db.get_engine().begin() as conn:
        rows = (
            conn.execute(
                text(
                    """
                SELECT agent_id, username, granted_by, granted_at
                FROM nexora_agent_user_grants
                WHERE username = :username
                ORDER BY granted_at
                """,
                ),
                {"username": username},
            )
            .mappings()
            .all()
        )
    return [_grant_row(r) for r in rows]


def grant_agent_to_user(
    agent_id: str,
    username: str,
    granted_by: str,
) -> dict:
    db.initialize_schema()
    now = int(time.time() * 1000)
    with db.get_engine().begin() as conn:
        row = (
            conn.execute(
                text(
                    """
                INSERT INTO nexora_agent_user_grants
                    (agent_id, username, granted_by, granted_at)
                VALUES (:agent_id, :username, :granted_by, :granted_at)
                ON CONFLICT (agent_id, username) DO UPDATE SET
                    granted_by = EXCLUDED.granted_by,
                    granted_at = EXCLUDED.granted_at
                RETURNING agent_id, username, granted_by, granted_at
                """,
                ),
                {
                    "agent_id": agent_id,
                    "username": username,
                    "granted_by": granted_by,
                    "granted_at": now,
                },
            )
            .mappings()
            .one()
        )
    return _grant_row(row)


def revoke_agent_from_user(agent_id: str, username: str) -> bool:
    db.initialize_schema()
    with db.get_engine().begin() as conn:
        result = conn.execute(
            text(
                """
                DELETE FROM nexora_agent_user_grants
                WHERE agent_id = :agent_id AND username = :username
                """,
            ),
            {"agent_id": agent_id, "username": username},
        )
    return result.rowcount > 0


def batch_grant_agent(
    agent_id: str,
    usernames: list[str],
    granted_by: str,
) -> int:
    if not usernames:
        return 0
    db.initialize_schema()
    now = int(time.time() * 1000)
    with db.get_engine().begin() as conn:
        for username in usernames:
            conn.execute(
                text(
                    """
                    INSERT INTO nexora_agent_user_grants
                        (agent_id, username, granted_by, granted_at)
                    VALUES (:agent_id, :username, :granted_by, :granted_at)
                    ON CONFLICT (agent_id, username) DO NOTHING
                    """,
                ),
                {
                    "agent_id": agent_id,
                    "username": username,
                    "granted_by": granted_by,
                    "granted_at": now,
                },
            )
    return len(usernames)


def batch_revoke_agent(agent_id: str, usernames: list[str]) -> int:
    if not usernames:
        return 0
    db.initialize_schema()
    count = 0
    with db.get_engine().begin() as conn:
        for username in usernames:
            result = conn.execute(
                text(
                    """
                    DELETE FROM nexora_agent_user_grants
                    WHERE agent_id = :agent_id AND username = :username
                    """,
                ),
                {"agent_id": agent_id, "username": username},
            )
            count += result.rowcount
    return count


def is_user_granted(agent_id: str, username: str) -> bool:
    db.initialize_schema()
    with db.get_engine().begin() as conn:
        row = conn.execute(
            text(
                """
                SELECT 1 FROM nexora_agent_user_grants
                WHERE agent_id = :agent_id AND username = :username
                """,
            ),
            {"agent_id": agent_id, "username": username},
        ).first()
    return row is not None


def delete_all_grants() -> None:
    """Clear all grants. Intended for tests and re-initialization."""
    db.initialize_schema()
    with db.get_engine().begin() as conn:
        conn.execute(text("DELETE FROM nexora_agent_user_grants"))
