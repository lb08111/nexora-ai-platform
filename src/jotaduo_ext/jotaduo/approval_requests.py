# -*- coding: utf-8 -*-
"""Persistent approval requests for platform capability changes."""
from __future__ import annotations

import json
import os
import tempfile
import time
import uuid

from jotaduo.constant import SECRET_DIR
from jotaduo_ext.jotaduo import db

APPROVAL_REQUESTS_FILE = SECRET_DIR / "jotaduo_approval_requests.json"

PENDING = "pending"
APPROVED = "approved"
REJECTED = "rejected"
APPLIED = "applied"
FAILED = "failed"
TERMINAL_STATUSES = {REJECTED, APPLIED}


def _chmod_best_effort(path, mode: int) -> None:
    try:
        os.chmod(path, mode)
    except OSError:
        pass


def _load_data() -> dict:
    if not APPROVAL_REQUESTS_FILE.is_file():
        return {"requests": {}}
    try:
        with open(APPROVAL_REQUESTS_FILE, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (json.JSONDecodeError, OSError):
        return {"requests": {}}
    if not isinstance(data, dict):
        return {"requests": {}}
    requests = data.get("requests")
    if not isinstance(requests, dict):
        data["requests"] = {}
    return data


def _save_data(data: dict) -> None:
    APPROVAL_REQUESTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _chmod_best_effort(APPROVAL_REQUESTS_FILE.parent, 0o700)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{APPROVAL_REQUESTS_FILE.name}.",
        suffix=".tmp",
        dir=APPROVAL_REQUESTS_FILE.parent,
        text=True,
    )
    tmp_path = os.fspath(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        _chmod_best_effort(tmp_path, 0o600)
        os.replace(tmp_path, APPROVAL_REQUESTS_FILE)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
    _chmod_best_effort(APPROVAL_REQUESTS_FILE, 0o600)


def _normalize_request(raw: dict) -> dict:
    now = int(time.time())
    return {
        "id": str(raw.get("id") or uuid.uuid4()),
        "action": str(raw.get("action") or ""),
        "status": str(raw.get("status") or PENDING),
        "requester": str(raw.get("requester") or ""),
        "approver": str(raw.get("approver") or ""),
        "resource_type": str(raw.get("resource_type") or ""),
        "resource_id": str(raw.get("resource_id") or ""),
        "resource_name": str(raw.get("resource_name") or ""),
        "summary": str(raw.get("summary") or ""),
        "reason": str(raw.get("reason") or ""),
        "payload": raw.get("payload")
        if isinstance(raw.get("payload"), dict)
        else {},
        "result": raw.get("result")
        if isinstance(raw.get("result"), dict)
        else {},
        "created_at": int(raw.get("created_at") or now),
        "updated_at": int(raw.get("updated_at") or now),
    }


def create_approval_request(request_data: dict) -> dict:
    """Create a pending platform capability approval request."""
    item = _normalize_request({**request_data, "status": PENDING})
    if db.is_database_enabled():
        from jotaduo_ext.jotaduo.repositories import approval_postgres

        return approval_postgres.create_request(item)

    data = _load_data()
    data.setdefault("requests", {})[item["id"]] = item
    _save_data(data)
    return item


def get_approval_request(request_id: str) -> dict | None:
    """Return a single approval request by id."""
    if db.is_database_enabled():
        from jotaduo_ext.jotaduo.repositories import approval_postgres

        return approval_postgres.get_request(request_id)

    item = _load_data().get("requests", {}).get(request_id)
    if not isinstance(item, dict):
        return None
    return _normalize_request(item)


def list_approval_requests(
    status: str | None = None,
    action: str | None = None,
) -> list[dict]:
    """List approval requests, newest first."""
    if db.is_database_enabled():
        from jotaduo_ext.jotaduo.repositories import approval_postgres

        return approval_postgres.list_requests(status=status, action=action)

    requests = [
        _normalize_request(item)
        for item in _load_data().get("requests", {}).values()
        if isinstance(item, dict)
    ]
    if status:
        requests = [item for item in requests if item["status"] == status]
    if action:
        requests = [item for item in requests if item["action"] == action]
    return sorted(requests, key=lambda item: item["created_at"], reverse=True)


def update_approval_request(request_id: str, changes: dict) -> dict | None:
    """Patch a request and persist it."""
    if db.is_database_enabled():
        from jotaduo_ext.jotaduo.repositories import approval_postgres

        existing = approval_postgres.get_request(request_id)
        if not isinstance(existing, dict):
            return None
        item = _normalize_request(
            {**existing, **changes, "updated_at": int(time.time())},
        )
        return approval_postgres.update_request(request_id, item)

    data = _load_data()
    existing = data.get("requests", {}).get(request_id)
    if not isinstance(existing, dict):
        return None
    item = _normalize_request(
        {**existing, **changes, "updated_at": int(time.time())},
    )
    data.setdefault("requests", {})[request_id] = item
    _save_data(data)
    return item
