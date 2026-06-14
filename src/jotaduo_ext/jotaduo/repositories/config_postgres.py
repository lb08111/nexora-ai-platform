# -*- coding: utf-8 -*-
"""PostgreSQL repository for JotaDuo runtime configuration."""
from __future__ import annotations

import json
import time
from typing import Any, Optional

from sqlalchemy import text

from jotaduo_ext.jotaduo import db


def _json_for_db(value: Any) -> str:
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


# ---------------------------------------------------------------------------
# Global config (single-row table, id=1)
# ---------------------------------------------------------------------------


def load_global_config() -> Optional[dict]:
    """Load global config from PG.  Returns None when no row exists."""
    engine = db.get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT data, updated_at FROM jotaduo_global_config WHERE id = 1"
            ),
        ).first()
    if row is None:
        return None
    return _json_from_db(row[0])


def save_global_config(data: dict) -> None:
    """Upsert global config with row-level locking."""
    engine = db.get_engine()
    payload = _json_for_db(data)
    now = int(time.time())
    with engine.begin() as conn:
        existing = conn.execute(
            text(
                "SELECT id FROM jotaduo_global_config WHERE id = 1 FOR UPDATE",
            ),
        ).first()
        if existing:
            conn.execute(
                text(
                    "UPDATE jotaduo_global_config "
                    "SET data = CAST(:data AS JSONB), updated_at = :ts "
                    "WHERE id = 1",
                ),
                {"data": payload, "ts": now},
            )
        else:
            conn.execute(
                text(
                    "INSERT INTO jotaduo_global_config (id, data, updated_at) "
                    "VALUES (1, CAST(:data AS JSONB), :ts)",
                ),
                {"data": payload, "ts": now},
            )


def get_global_config_version() -> Optional[int]:
    """Return the updated_at timestamp used for cache invalidation."""
    engine = db.get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT updated_at FROM jotaduo_global_config WHERE id = 1"),
        ).first()
    return row[0] if row else None


# ---------------------------------------------------------------------------
# Per-agent config (keyed by agent_id)
# ---------------------------------------------------------------------------


def load_agent_config(agent_id: str) -> Optional[dict]:
    """Load a single agent config from PG.  Returns None when not found."""
    engine = db.get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT data, updated_at FROM jotaduo_agent_configs "
                "WHERE agent_id = :aid",
            ),
            {"aid": agent_id},
        ).first()
    if row is None:
        return None
    return _json_from_db(row[0])


def save_agent_config(agent_id: str, data: dict) -> None:
    """Upsert agent config with row-level locking."""
    engine = db.get_engine()
    payload = _json_for_db(data)
    now = int(time.time())
    with engine.begin() as conn:
        existing = conn.execute(
            text(
                "SELECT agent_id FROM jotaduo_agent_configs "
                "WHERE agent_id = :aid FOR UPDATE",
            ),
            {"aid": agent_id},
        ).first()
        if existing:
            conn.execute(
                text(
                    "UPDATE jotaduo_agent_configs "
                    "SET data = CAST(:data AS JSONB), updated_at = :ts "
                    "WHERE agent_id = :aid",
                ),
                {"aid": agent_id, "data": payload, "ts": now},
            )
        else:
            conn.execute(
                text(
                    "INSERT INTO jotaduo_agent_configs (agent_id, data, updated_at) "
                    "VALUES (:aid, CAST(:data AS JSONB), :ts)",
                ),
                {"aid": agent_id, "data": payload, "ts": now},
            )


def delete_agent_config(agent_id: str) -> None:
    """Remove an agent config row."""
    engine = db.get_engine()
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM jotaduo_agent_configs WHERE agent_id = :aid"),
            {"aid": agent_id},
        )


def get_agent_config_version(agent_id: str) -> Optional[int]:
    """Return updated_at for cache invalidation."""
    engine = db.get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT updated_at FROM jotaduo_agent_configs WHERE agent_id = :aid",
            ),
            {"aid": agent_id},
        ).first()
    return row[0] if row else None


def list_agent_ids() -> list[str]:
    """Return all agent_id values stored in PG."""
    engine = db.get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT agent_id FROM jotaduo_agent_configs ORDER BY agent_id"
            ),
        ).fetchall()
    return [r[0] for r in rows]
