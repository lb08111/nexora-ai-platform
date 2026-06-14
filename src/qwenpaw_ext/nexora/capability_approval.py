# -*- coding: utf-8 -*-
"""Per-capability-type approval configuration — file-backed with optional PG.

Controls whether adding/removing capabilities (skill, mcp, tool, acp, plugin)
requires approval.

Policy values:
  - "none"     — no approval, no record
  - "log"      — auto-approve and record (remove only)
  - "approval" — requires human approval
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)

_CONFIG_FILE = "nexora_capability_approval.json"

CAPABILITY_TYPES = ("skill", "mcp", "tool", "acp", "plugin")

ADD_POLICIES = ("none", "approval")
REMOVE_POLICIES = ("none", "log", "approval")

DEFAULT_CONFIGS: list[dict] = [
    {
        "capability_type": "skill",
        "add_policy": "approval",
        "remove_policy": "log",
        "approver_roles": ["admin"],
    },
    {
        "capability_type": "mcp",
        "add_policy": "approval",
        "remove_policy": "log",
        "approver_roles": ["admin"],
    },
    {
        "capability_type": "tool",
        "add_policy": "none",
        "remove_policy": "log",
        "approver_roles": ["admin"],
    },
    {
        "capability_type": "acp",
        "add_policy": "approval",
        "remove_policy": "log",
        "approver_roles": ["admin"],
    },
    {
        "capability_type": "plugin",
        "add_policy": "approval",
        "remove_policy": "log",
        "approver_roles": ["admin"],
    },
]


def _secret_dir() -> Path:
    from qwenpaw.constant import SECRET_DIR

    return Path(SECRET_DIR)


def _config_path() -> Path:
    return _secret_dir() / _CONFIG_FILE


def _load_configs() -> list[dict]:
    path = _config_path()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        logger.exception("Failed to load capability approval config")
        return []


def _migrate_legacy(config: dict) -> dict:
    """Convert old bool fields to new policy strings."""
    if "add_policy" not in config and "add_approval" in config:
        config["add_policy"] = (
            "approval" if config.pop("add_approval") else "none"
        )
    if "remove_policy" not in config:
        remove = config.pop("remove_approval", True)
        auto = config.pop("auto_approve_remove", True)
        if not remove:
            config["remove_policy"] = "none"
        elif auto:
            config["remove_policy"] = "log"
        else:
            config["remove_policy"] = "approval"
    config.pop("add_approval", None)
    config.pop("remove_approval", None)
    config.pop("auto_approve_remove", None)
    return config


def _save_configs(configs: list[dict]) -> None:
    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(configs, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    tmp.replace(path)


def _use_pg() -> bool:
    from qwenpaw_ext.nexora import db

    return db.is_database_enabled()


def ensure_default_configs() -> None:
    """Initialize default configs if none exist."""
    existing = list_configs()
    existing_types = {c["capability_type"] for c in existing}
    for default in DEFAULT_CONFIGS:
        if default["capability_type"] not in existing_types:
            upsert_config(default)


def list_configs() -> list[dict]:
    if _use_pg():
        from .repositories import capability_approval_postgres as repo

        return [_migrate_legacy(c) for c in repo.list_configs()]
    configs = _load_configs()
    return [_migrate_legacy(c) for c in configs]


def get_config(capability_type: str) -> dict | None:
    if _use_pg():
        from .repositories import capability_approval_postgres as repo

        c = repo.get_config(capability_type)
        return _migrate_legacy(c) if c else None
    for c in _load_configs():
        if c.get("capability_type") == capability_type:
            return _migrate_legacy(c)
    return None


def upsert_config(config: dict) -> dict:
    config = _migrate_legacy(config)
    if _use_pg():
        from .repositories import capability_approval_postgres as repo

        return repo.upsert_config(config)
    configs = _load_configs()
    configs = [_migrate_legacy(c) for c in configs]
    now = int(time.time() * 1000)
    config["updated_at"] = now
    for i, c in enumerate(configs):
        if c.get("capability_type") == config["capability_type"]:
            configs[i] = config
            _save_configs(configs)
            return config
    configs.append(config)
    _save_configs(configs)
    return config


def partial_update_config(capability_type: str, updates: dict) -> dict:
    """Atomically update only the provided fields for a capability type."""
    if not updates:
        config = get_config(capability_type)
        if config is None:
            ensure_default_configs()
            config = get_config(capability_type) or {}
        return config
    if _use_pg():
        from .repositories import capability_approval_postgres as repo

        existing = repo.get_config(capability_type)
        if not existing:
            ensure_default_configs()
        return repo.partial_update(capability_type, updates)
    existing = get_config(capability_type)
    if not existing:
        ensure_default_configs()
        existing = get_config(capability_type) or {}
    existing.update(updates)
    return upsert_config(existing)


def requires_approval(capability_type: str, action: str = "add") -> bool:
    config = get_config(capability_type)
    if config is None:
        return True
    if action == "remove":
        return config.get("remove_policy", "approval") != "none"
    return config.get("add_policy", "approval") == "approval"


def should_auto_approve(capability_type: str, action: str = "add") -> bool:
    if action == "add":
        return False
    config = get_config(capability_type)
    if config is None:
        return True
    return config.get("remove_policy", "log") == "log"


def get_approver_roles(capability_type: str) -> list[str]:
    config = get_config(capability_type)
    if config is None:
        return ["admin"]
    return config.get("approver_roles", ["admin"])
