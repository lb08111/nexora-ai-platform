# -*- coding: utf-8 -*-
"""Jotaduo audit log storage and helpers."""
from __future__ import annotations

import json
import logging
import os
import secrets
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from jotaduo.constant import SECRET_DIR
from jotaduo_ext.jotaduo import db

AUDIT_FILE: Path = SECRET_DIR / "jotaduo_audit.jsonl"
MAX_READ_LINES = 5000
logger = logging.getLogger(__name__)


@contextmanager
def _exclusive_file_lock(file_obj: Any):
    """Best-effort append lock for audit writes on platforms that support it."""
    try:
        import fcntl  # type: ignore

        fcntl.flock(file_obj.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(file_obj.fileno(), fcntl.LOCK_UN)
    except (ImportError, OSError):
        yield


def _chmod_best_effort(path: Path, mode: int) -> None:
    try:
        os.chmod(path, mode)
    except OSError:
        pass


def _prepare_file() -> None:
    AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)
    _chmod_best_effort(AUDIT_FILE.parent, 0o700)


def _client_ip_from_request(request: Any) -> str:
    if request is None:
        return ""
    forwarded_for = request.headers.get("x-forwarded-for", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    real_ip = request.headers.get("x-real-ip", "")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else ""


def _user_agent_from_request(request: Any) -> str:
    if request is None:
        return ""
    return request.headers.get("user-agent", "")


def safe_preview(value: Any, *, max_length: int = 2000) -> Any:
    """Return a bounded, JSON-safe preview for audit details."""
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return (
            value if len(value) <= max_length else value[:max_length] + "..."
        )
    try:
        rendered = json.dumps(value, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        rendered = str(value)
    return (
        rendered
        if len(rendered) <= max_length
        else rendered[:max_length] + "..."
    )


def record_tool_audit_event(
    *,
    actor: str,
    agent_id: str,
    tool_name: str,
    status: str,
    tool_call_id: str = "",
    session_id: str = "",
    channel: str = "",
    detail: dict | None = None,
) -> dict:
    """Record an Agent tool execution audit event."""
    payload = {
        "agent_id": agent_id,
        "tool_call_id": tool_call_id,
        "session_id": session_id,
        "channel": channel,
        **(detail or {}),
    }
    return record_audit_event(
        actor=actor or "agent",
        action="agent.tool.execute",
        resource_type="tool",
        resource_id=tool_name,
        status=status,
        detail=payload,
    )


def record_audit_event(
    *,
    actor: str,
    action: str,
    resource_type: str = "",
    resource_id: str = "",
    status: str = "success",
    detail: dict | None = None,
    request: Any = None,
) -> dict:
    """Append one audit event to the JSONL audit log."""
    event = {
        "id": secrets.token_hex(12),
        "timestamp": int(time.time()),
        "actor": actor or "anonymous",
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "status": status,
        "ip": _client_ip_from_request(request),
        "user_agent": _user_agent_from_request(request),
        "detail": detail or {},
    }
    if db.is_database_enabled():
        try:
            from jotaduo_ext.jotaduo.repositories import audit_postgres

            audit_postgres.insert_event(event)
            return event
        except Exception as exc:  # pylint: disable=broad-except
            logger.error(
                "Failed to write audit event %s to PostgreSQL, "
                "falling back to local file: %s",
                action,
                exc,
            )

    try:
        _prepare_file()
        with open(AUDIT_FILE, "a", encoding="utf-8") as fh:
            with _exclusive_file_lock(fh):
                fh.write(
                    json.dumps(
                        event, ensure_ascii=False, separators=(",", ":")
                    )
                )
                fh.write("\n")
                fh.flush()
                os.fsync(fh.fileno())
        _chmod_best_effort(AUDIT_FILE, 0o600)
    except OSError as exc:
        logger.warning("Failed to write audit event %s: %s", action, exc)
    return event


def list_audit_events(
    *,
    limit: int = 200,
    actor: str | None = None,
    action: str | None = None,
    status: str | None = None,
    start_time: int | None = None,
    end_time: int | None = None,
) -> list[dict]:
    """Return recent audit events, newest first."""
    if db.is_database_enabled():
        try:
            from jotaduo_ext.jotaduo.repositories import audit_postgres

            return audit_postgres.list_events(
                limit=limit,
                actor=actor,
                action=action,
                status=status,
                start_time=start_time,
                end_time=end_time,
            )
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Failed to list PostgreSQL audit events: %s", exc)
            return []

    if not AUDIT_FILE.is_file():
        return []

    limit = max(1, min(limit, 1000))
    lines: list[str] = []
    with open(AUDIT_FILE, "r", encoding="utf-8") as fh:
        for line in fh:
            lines.append(line)
            if len(lines) > MAX_READ_LINES:
                lines.pop(0)

    events: list[dict] = []
    for line in reversed(lines):
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if actor and actor not in str(event.get("actor", "")):
            continue
        if action and action not in str(event.get("action", "")):
            continue
        if status and status != event.get("status"):
            continue
        ts = event.get("timestamp", 0)
        if start_time is not None and ts < start_time:
            continue
        if end_time is not None and ts > end_time:
            continue
        events.append(event)
        if len(events) >= limit:
            break
    return events
