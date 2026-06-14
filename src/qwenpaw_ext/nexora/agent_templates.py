# -*- coding: utf-8 -*-
"""Agent initialization templates — file-backed with optional PostgreSQL.

Templates define a preset collection of capabilities (skills, tools, MCPs, etc.)
that can be applied when an admin creates a new agent.
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)

_TEMPLATES_FILE = "nexora_agent_templates.json"

BUILTIN_TEMPLATES: list[dict] = [
    {
        "template_id": "ops-basic",
        "name": "运维基础包",
        "description": "系统监控、日志查询、告警处理等运维工具",
        "capabilities": {
            "skills": [],
            "tools": ["read_file", "write_file", "execute_command"],
            "mcps": [],
            "plugins": [],
        },
        "builtin": True,
        "created_by": "system",
    },
    {
        "template_id": "dev-assistant",
        "name": "开发助手包",
        "description": "代码生成、代码审查、Git 操作等开发工具",
        "capabilities": {
            "skills": [],
            "tools": [
                "read_file",
                "write_file",
                "edit_file",
                "execute_command",
            ],
            "mcps": [],
            "plugins": [],
        },
        "builtin": True,
        "created_by": "system",
    },
    {
        "template_id": "readonly-query",
        "name": "只读查询包",
        "description": "只有查询类能力，不能执行写操作",
        "capabilities": {
            "skills": [],
            "tools": ["read_file"],
            "mcps": [],
            "plugins": [],
        },
        "builtin": True,
        "created_by": "system",
    },
    {
        "template_id": "office-assistant",
        "name": "办公助手包",
        "description": "文档处理、日程管理、信息检索等办公工具",
        "capabilities": {
            "skills": [],
            "tools": ["read_file", "write_file"],
            "mcps": [],
            "plugins": [],
        },
        "builtin": True,
        "created_by": "system",
    },
]


def _secret_dir() -> Path:
    from qwenpaw.constant import SECRET_DIR

    return Path(SECRET_DIR)


def _templates_path() -> Path:
    return _secret_dir() / _TEMPLATES_FILE


def _load_templates() -> list[dict]:
    path = _templates_path()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        logger.exception("Failed to load agent templates from %s", path)
        return []


def _save_templates(templates: list[dict]) -> None:
    path = _templates_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(templates, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    tmp.replace(path)


def _use_pg() -> bool:
    from qwenpaw_ext.nexora import db

    return db.is_database_enabled()


def ensure_builtin_templates() -> None:
    """Initialize built-in templates if they don't exist."""
    existing = list_templates()
    existing_ids = {t["template_id"] for t in existing}
    for builtin in BUILTIN_TEMPLATES:
        if builtin["template_id"] not in existing_ids:
            create_template(builtin)


def list_templates() -> list[dict]:
    if _use_pg():
        from .repositories import agent_templates_postgres as repo

        return repo.list_templates()
    return _load_templates()


def get_template(template_id: str) -> dict | None:
    if _use_pg():
        from .repositories import agent_templates_postgres as repo

        return repo.get_template(template_id)
    for t in _load_templates():
        if t.get("template_id") == template_id:
            return t
    return None


def create_template(template: dict) -> dict:
    if _use_pg():
        from .repositories import agent_templates_postgres as repo

        return repo.create_template(template)
    templates = _load_templates()
    now = int(time.time() * 1000)
    entry = {
        "template_id": template.get("template_id") or uuid.uuid4().hex[:12],
        "name": template["name"],
        "description": template.get("description", ""),
        "capabilities": template.get("capabilities", {}),
        "builtin": template.get("builtin", False),
        "created_by": template.get("created_by", "admin"),
        "created_at": now,
        "updated_at": now,
    }
    templates.append(entry)
    _save_templates(templates)
    return entry


def update_template(template_id: str, updates: dict) -> dict | None:
    if _use_pg():
        from .repositories import agent_templates_postgres as repo

        return repo.update_template(template_id, updates)
    templates = _load_templates()
    now = int(time.time() * 1000)
    for i, t in enumerate(templates):
        if t.get("template_id") == template_id:
            for key in ("name", "description", "capabilities"):
                if key in updates:
                    t[key] = updates[key]
            t["updated_at"] = now
            _save_templates(templates)
            return t
    return None


def delete_template(template_id: str) -> bool:
    if _use_pg():
        from .repositories import agent_templates_postgres as repo

        return repo.delete_template(template_id)
    templates = _load_templates()
    before = len(templates)
    templates = [t for t in templates if t.get("template_id") != template_id]
    if len(templates) < before:
        _save_templates(templates)
        return True
    return False
