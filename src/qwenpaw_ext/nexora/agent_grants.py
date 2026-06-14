# -*- coding: utf-8 -*-
"""Agent-user grant management — file-backed with optional PostgreSQL.

Manages which users are authorized to use which agents.
Admin users bypass grant checks and can see all agents.
"""
from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_GRANTS_FILE = "nexora_agent_grants.json"


def _secret_dir() -> Path:
    from qwenpaw.constant import SECRET_DIR

    return Path(SECRET_DIR)


def _grants_path() -> Path:
    return _secret_dir() / _GRANTS_FILE


def _load_grants() -> dict:
    path = _grants_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        logger.exception("Failed to load agent grants from %s", path)
        return {}


def _save_grants(data: dict) -> None:
    path = _grants_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    tmp.replace(path)


def _use_pg() -> bool:
    from qwenpaw_ext.nexora import db

    return db.is_database_enabled()


def list_grants_for_agent(agent_id: str) -> list[dict]:
    if _use_pg():
        from .repositories import agent_grants_postgres as repo

        return repo.list_grants_for_agent(agent_id)
    data = _load_grants()
    return data.get(agent_id, [])


def list_grants_for_user(username: str) -> list[dict]:
    if _use_pg():
        from .repositories import agent_grants_postgres as repo

        return repo.list_grants_for_user(username)
    data = _load_grants()
    result = []
    for agent_id, grants in data.items():
        for g in grants:
            if g.get("username") == username:
                result.append({**g, "agent_id": agent_id})
    return result


def get_authorized_agent_ids(username: str) -> list[str]:
    """Return agent IDs that a user is authorized to use."""
    grants = list_grants_for_user(username)
    return [g["agent_id"] for g in grants]


def is_user_granted(agent_id: str, username: str) -> bool:
    if _use_pg():
        from .repositories import agent_grants_postgres as repo

        return repo.is_user_granted(agent_id, username)
    data = _load_grants()
    for g in data.get(agent_id, []):
        if g.get("username") == username:
            return True
    return False


def grant_agent_to_user(
    agent_id: str,
    username: str,
    granted_by: str,
) -> dict:
    if _use_pg():
        from .repositories import agent_grants_postgres as repo

        return repo.grant_agent_to_user(agent_id, username, granted_by)
    data = _load_grants()
    grants = data.setdefault(agent_id, [])
    for g in grants:
        if g.get("username") == username:
            g["granted_by"] = granted_by
            g["granted_at"] = int(time.time() * 1000)
            _save_grants(data)
            return g
    entry = {
        "agent_id": agent_id,
        "username": username,
        "granted_by": granted_by,
        "granted_at": int(time.time() * 1000),
    }
    grants.append(entry)
    _save_grants(data)
    return entry


def revoke_agent_from_user(agent_id: str, username: str) -> bool:
    if _use_pg():
        from .repositories import agent_grants_postgres as repo

        return repo.revoke_agent_from_user(agent_id, username)
    data = _load_grants()
    grants = data.get(agent_id, [])
    before = len(grants)
    data[agent_id] = [g for g in grants if g.get("username") != username]
    if len(data[agent_id]) < before:
        _save_grants(data)
        return True
    return False


def batch_grant_agent(
    agent_id: str,
    usernames: list[str],
    granted_by: str,
) -> int:
    if _use_pg():
        from .repositories import agent_grants_postgres as repo

        return repo.batch_grant_agent(agent_id, usernames, granted_by)
    count = 0
    for username in usernames:
        grant_agent_to_user(agent_id, username, granted_by)
        count += 1
    return count


def batch_revoke_agent(agent_id: str, usernames: list[str]) -> int:
    if _use_pg():
        from .repositories import agent_grants_postgres as repo

        return repo.batch_revoke_agent(agent_id, usernames)
    count = 0
    for username in usernames:
        if revoke_agent_from_user(agent_id, username):
            count += 1
    return count
