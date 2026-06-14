# -*- coding: utf-8 -*-
"""Jotaduo operation governance policy store.

The upstream JotaDuo pages own tool, MCP, and skill configuration.  This
extension stores only the AIops governance metadata that decides who can use a
resource, how risky it is, and whether approval/audit is required.
"""
from __future__ import annotations

import json
import os
import tempfile
import time
from collections.abc import Mapping
from typing import Literal

from fastapi import HTTPException, Request

from jotaduo.constant import SECRET_DIR
from jotaduo_ext.jotaduo import db

GOVERNANCE_FILE = SECRET_DIR / "jotaduo_governance.json"

ResourceSource = Literal[
    "builtin_tool",
    "mcp",
    "skill",
    "plugin",
    "api",
    "cli",
]
RiskLevel = Literal["low", "medium", "high", "critical"]
ApprovalAction = Literal[
    "mcp.create",
    "mcp.delete",
    "skill.create",
    "skill.delete",
    "plugin.install",
    "plugin.uninstall",
    "tool.create",
]

DEFAULT_AGENT_ALLOWED_ROLES = ("admin",)
KNOWN_ROLE_IDS = ("admin", "operator")
DEFAULT_APPROVAL_POLICIES: dict[str, dict] = {
    "mcp.create": {
        "action": "mcp.create",
        "display_name": "新增 MCP",
        "description": "新增 MCP 客户端配置进入平台前需要审批。",
        "enabled": True,
        "approver_roles": ["admin"],
        "allow_self_approval": False,
    },
    "skill.create": {
        "action": "skill.create",
        "display_name": "新增 Skill",
        "description": "创建、上传或导入 Skill 进入平台前需要审批。",
        "enabled": True,
        "approver_roles": ["admin"],
        "allow_self_approval": False,
    },
    "plugin.install": {
        "action": "plugin.install",
        "display_name": "安装插件",
        "description": "插件安装和上传风险较高，默认仅平台管理员可审批。",
        "enabled": True,
        "approver_roles": ["admin"],
        "allow_self_approval": False,
    },
    "tool.create": {
        "action": "tool.create",
        "display_name": "新增工具",
        "description": "新增工具或工具源进入平台前需要审批。",
        "enabled": True,
        "approver_roles": ["admin"],
        "allow_self_approval": False,
    },
}


def _legacy_allowed_agents_from_roles(policy: dict) -> set[str]:
    """Return agent ids saved by the old UI into allowed_roles.

    Resource permissions now belong to agents. Older governance pages briefly
    saved selected agent ids into ``allowed_roles``. Keeping this migration
    path prevents valid tool/MCP/skill assignments from disappearing after a
    restart or upgrade.
    """
    return set(policy.get("allowed_roles") or []) - set(KNOWN_ROLE_IDS)


def _chmod_best_effort(path, mode: int) -> None:
    try:
        os.chmod(path, mode)
    except OSError:
        pass


def _load_data() -> dict:
    if not GOVERNANCE_FILE.is_file():
        return {"policies": {}, "agent_policies": {}, "approval_policies": {}}
    try:
        with open(GOVERNANCE_FILE, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (json.JSONDecodeError, OSError):
        return {"policies": {}, "agent_policies": {}, "approval_policies": {}}
    if not isinstance(data, dict):
        return {"policies": {}, "agent_policies": {}, "approval_policies": {}}
    policies = data.get("policies")
    if not isinstance(policies, dict):
        data["policies"] = {}
    agent_policies = data.get("agent_policies")
    if not isinstance(agent_policies, dict):
        data["agent_policies"] = {}
    approval_policies = data.get("approval_policies")
    if not isinstance(approval_policies, dict):
        data["approval_policies"] = {}
    return data


def _save_data(data: dict) -> None:
    GOVERNANCE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _chmod_best_effort(GOVERNANCE_FILE.parent, 0o700)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{GOVERNANCE_FILE.name}.",
        suffix=".tmp",
        dir=GOVERNANCE_FILE.parent,
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
        os.replace(tmp_path, GOVERNANCE_FILE)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
    _chmod_best_effort(GOVERNANCE_FILE, 0o600)


def policy_key(source: str, resource_id: str) -> str:
    return f"{source}:{resource_id}"


def agent_policy_key(agent_id: str) -> str:
    return f"agent:{agent_id}"


def _normalize_policy(raw: dict) -> dict:
    source = raw.get("source") or "builtin_tool"
    resource_id = raw.get("resource_id") or raw.get("id") or ""
    key = raw.get("id") or policy_key(source, resource_id)
    risk_level = raw.get("risk_level") or "low"
    if risk_level not in {"low", "medium", "high", "critical"}:
        risk_level = "low"
    return {
        "id": key,
        "source": source,
        "resource_id": resource_id,
        "display_name": raw.get("display_name") or resource_id,
        "description": raw.get("description") or "",
        "risk_level": risk_level,
        "allowed_agents": list(raw.get("allowed_agents") or []),
        "allowed_roles": list(raw.get("allowed_roles") or []),
        "approval_required": bool(raw.get("approval_required", False)),
        "audit_enabled": bool(raw.get("audit_enabled", True)),
        "enabled": bool(raw.get("enabled", True)),
        "updated_at": int(raw.get("updated_at") or time.time()),
    }


def default_resource_policy(
    source: str,
    resource_id: str,
    display_name: str = "",
    description: str = "",
) -> dict:
    return _normalize_policy(
        {
            "id": policy_key(source, resource_id),
            "source": source,
            "resource_id": resource_id,
            "display_name": display_name or resource_id,
            "description": description,
            "risk_level": (
                "medium"
                if source == "builtin_tool"
                else "high"
                if source == "plugin"
                else "low"
            ),
            "allowed_agents": [],
            "allowed_roles": [],
            "approval_required": False,
            "audit_enabled": True,
            "enabled": True,
        },
    )


def get_resource_policy(
    source: str,
    resource_id: str,
    display_name: str = "",
    description: str = "",
) -> dict:
    if db.is_database_enabled():
        from jotaduo_ext.jotaduo.repositories import governance_postgres

        policy = governance_postgres.get_resource_policy(
            policy_key(source, resource_id),
        )
        if isinstance(policy, dict):
            return _normalize_policy(policy)
        return default_resource_policy(
            source,
            resource_id,
            display_name,
            description,
        )

    data = _load_data()
    policy = data.get("policies", {}).get(policy_key(source, resource_id))
    if isinstance(policy, dict):
        return _normalize_policy(policy)
    return default_resource_policy(
        source,
        resource_id,
        display_name,
        description,
    )


def list_policies() -> list[dict]:
    if db.is_database_enabled():
        from jotaduo_ext.jotaduo.repositories import governance_postgres

        return [
            _normalize_policy(policy)
            for policy in governance_postgres.list_resource_policies()
        ]

    data = _load_data()
    return [
        _normalize_policy(policy)
        for policy in data.get("policies", {}).values()
        if isinstance(policy, dict)
    ]


def upsert_policy(policy: dict) -> dict:
    normalized = _normalize_policy(
        {
            **policy,
            "id": policy_key(policy["source"], policy["resource_id"]),
            "updated_at": int(time.time()),
        },
    )
    if db.is_database_enabled():
        from jotaduo_ext.jotaduo.repositories import governance_postgres

        return _normalize_policy(
            governance_postgres.upsert_resource_policy(normalized),
        )

    data = _load_data()
    data.setdefault("policies", {})[normalized["id"]] = normalized
    _save_data(data)
    return normalized


def ensure_resource_policy(
    source: str,
    resource_id: str,
    *,
    display_name: str = "",
    description: str = "",
    allowed_agents: list[str] | tuple[str, ...] | None = None,
    risk_level: str | None = None,
) -> dict:
    """Create or update a governance policy for an approved resource.

    Existing operator choices are preserved. New allowed agents are merged so a
    resource created for a specific agent is immediately usable by that agent
    after approval, while shared resources can still stay unassigned.
    """
    if not source or not resource_id:
        raise ValueError("source and resource_id are required")

    current = get_resource_policy(
        source,
        resource_id,
        display_name,
        description,
    )
    existing = (
        current if current.get("id") == policy_key(source, resource_id) else {}
    )
    merged_agents = list(
        dict.fromkeys(
            [
                *(existing.get("allowed_agents") or []),
                *(allowed_agents or []),
            ],
        ),
    )
    policy = {
        **current,
        "display_name": existing.get("display_name")
        or display_name
        or resource_id,
        "description": existing.get("description") or description or "",
        "allowed_agents": merged_agents,
        "risk_level": risk_level or current.get("risk_level") or "low",
    }
    return upsert_policy(policy)


def delete_policy(policy_id: str) -> bool:
    if db.is_database_enabled():
        from jotaduo_ext.jotaduo.repositories import governance_postgres

        return governance_postgres.delete_resource_policy(policy_id)

    data = _load_data()
    policies = data.setdefault("policies", {})
    if policy_id not in policies:
        return False
    del policies[policy_id]
    _save_data(data)
    return True


def _normalize_agent_policy(raw: dict) -> dict:
    agent_id = raw.get("agent_id") or raw.get("id") or ""
    key = raw.get("id") or agent_policy_key(agent_id)
    return {
        "id": key,
        "agent_id": agent_id,
        "display_name": raw.get("display_name") or agent_id,
        "description": raw.get("description") or "",
        "allowed_roles": list(raw.get("allowed_roles") or []),
        "visible": bool(raw.get("visible", True)),
        "usable": bool(raw.get("usable", True)),
        "manageable": bool(raw.get("manageable", False)),
        "enabled": bool(raw.get("enabled", True)),
        "updated_at": int(raw.get("updated_at") or time.time()),
    }


def default_agent_policy(agent_id: str) -> dict:
    return _normalize_agent_policy(
        {
            "id": agent_policy_key(agent_id),
            "agent_id": agent_id,
            "display_name": agent_id,
            "allowed_roles": list(DEFAULT_AGENT_ALLOWED_ROLES),
            "visible": True,
            "usable": True,
            "manageable": False,
            "enabled": True,
        },
    )


def _normalize_approval_policy(raw: dict) -> dict:
    action = str(raw.get("action") or raw.get("id") or "")
    default = DEFAULT_APPROVAL_POLICIES.get(action, {})
    approver_roles = raw.get("approver_roles")
    if not isinstance(approver_roles, list):
        approver_roles = default.get("approver_roles", [])
    return {
        "id": action,
        "action": action,
        "display_name": raw.get("display_name")
        or default.get("display_name")
        or action,
        "description": raw.get("description")
        or default.get("description")
        or "",
        "enabled": bool(raw.get("enabled", default.get("enabled", True))),
        "approver_roles": [
            role_id
            for role_id in approver_roles
            if isinstance(role_id, str) and role_id
        ],
        "allow_self_approval": bool(
            raw.get(
                "allow_self_approval",
                default.get("allow_self_approval", False),
            ),
        ),
        "updated_at": int(raw.get("updated_at") or time.time()),
    }


def default_approval_policy(action: str) -> dict:
    default = DEFAULT_APPROVAL_POLICIES.get(
        action,
        {
            "action": action,
            "display_name": action,
            "description": "",
            "enabled": True,
            "approver_roles": ["admin"],
            "allow_self_approval": False,
        },
    )
    return _normalize_approval_policy(default)


def get_approval_policy(action: str) -> dict:
    if db.is_database_enabled():
        from jotaduo_ext.jotaduo.repositories import governance_postgres

        policy = governance_postgres.get_approval_policy(action)
        if isinstance(policy, dict):
            return _normalize_approval_policy(policy)
        return default_approval_policy(action)

    data = _load_data()
    policy = data.get("approval_policies", {}).get(action)
    if isinstance(policy, dict):
        return _normalize_approval_policy(policy)
    return default_approval_policy(action)


def list_approval_policies() -> list[dict]:
    if db.is_database_enabled():
        from jotaduo_ext.jotaduo.repositories import governance_postgres

        stored = {
            policy["action"]: policy
            for policy in governance_postgres.list_approval_policies()
        }
        actions = list(
            dict.fromkeys([*DEFAULT_APPROVAL_POLICIES.keys(), *stored.keys()]),
        )
        return [
            _normalize_approval_policy(
                stored.get(action) or default_approval_policy(action),
            )
            for action in actions
        ]

    data = _load_data()
    stored = data.get("approval_policies", {})
    actions = list(
        dict.fromkeys([*DEFAULT_APPROVAL_POLICIES.keys(), *stored.keys()]),
    )
    return [
        _normalize_approval_policy(
            stored.get(action) or default_approval_policy(action),
        )
        for action in actions
    ]


def upsert_approval_policy(policy: dict) -> dict:
    action = str(policy.get("action") or policy.get("id") or "").strip()
    if not action:
        raise ValueError("approval action is required")
    normalized = _normalize_approval_policy(
        {
            **policy,
            "action": action,
            "updated_at": int(time.time()),
        },
    )
    if db.is_database_enabled():
        from jotaduo_ext.jotaduo.repositories import governance_postgres

        return _normalize_approval_policy(
            governance_postgres.upsert_approval_policy(normalized),
        )

    data = _load_data()
    data.setdefault("approval_policies", {})[action] = normalized
    _save_data(data)
    return normalized


def role_ids_can_approve_action(
    role_ids: list[str] | tuple[str, ...],
    action: str,
    *,
    actor: str = "",
    requester: str = "",
) -> bool:
    if not _is_auth_active():
        return True
    policy = get_approval_policy(action)
    if not policy.get("enabled", True):
        return True
    if (
        actor
        and requester
        and actor == requester
        and not policy.get("allow_self_approval", False)
    ):
        return False
    roles = set(role_ids or [])
    allowed_roles = set(policy.get("approver_roles") or [])
    return bool(roles.intersection(allowed_roles))


def migrate_governance_data(
    agent_ids: list[str] | tuple[str, ...],
    agent_display_names: Mapping[str, str] | None = None,
) -> dict:
    """Backfill governance data for configured agents.

    Startup calls this as a lightweight, idempotent migration. It preserves
    existing choices, creates missing agent policies with the same conservative
    defaults as the UI, and copies legacy agent grants from ``allowed_roles``
    into ``allowed_agents`` only when they match current agent ids.
    """
    known_agent_ids = list(
        dict.fromkeys(agent_id for agent_id in agent_ids if agent_id),
    )
    known_agent_id_set = set(known_agent_ids)
    display_names = dict(agent_display_names or {})
    if db.is_database_enabled():
        resource_policies_migrated = 0
        agent_policies_created = 0
        changed = False

        for raw_policy in list_policies():
            policy = _normalize_policy(raw_policy)
            legacy_agent_ids = [
                agent_id
                for agent_id in policy.get("allowed_roles", [])
                if agent_id in known_agent_id_set
            ]
            allowed_agents = list(policy.get("allowed_agents") or [])
            merged_allowed_agents = list(
                dict.fromkeys([*allowed_agents, *legacy_agent_ids]),
            )
            if merged_allowed_agents != allowed_agents:
                policy["allowed_agents"] = merged_allowed_agents
                policy["updated_at"] = int(time.time())
                upsert_policy(policy)
                resource_policies_migrated += 1
                changed = True

        existing_agent_policy_ids = {
            policy.get("agent_id") for policy in list_agent_policies()
        }
        for agent_id in known_agent_ids:
            key = agent_policy_key(agent_id)
            if agent_id in existing_agent_policy_ids:
                existing = get_agent_policy(agent_id)
                normalized = _normalize_agent_policy(existing)
                if existing != normalized:
                    upsert_agent_policy(normalized)
                    changed = True
                continue

            policy = default_agent_policy(agent_id)
            if display_names.get(agent_id):
                policy["display_name"] = display_names[agent_id]
            upsert_agent_policy(policy)
            agent_policies_created += 1
            changed = True

        return {
            "changed": changed,
            "agent_policies_created": agent_policies_created,
            "resource_policies_migrated": resource_policies_migrated,
        }

    data = _load_data()
    policies = data.setdefault("policies", {})
    agent_policies = data.setdefault("agent_policies", {})
    changed = False
    resource_policies_migrated = 0
    agent_policies_created = 0

    for key, raw_policy in list(policies.items()):
        if not isinstance(raw_policy, dict):
            del policies[key]
            changed = True
            continue
        policy = _normalize_policy(raw_policy)
        legacy_agent_ids = [
            agent_id
            for agent_id in policy.get("allowed_roles", [])
            if agent_id in known_agent_id_set
        ]
        allowed_agents = list(policy.get("allowed_agents") or [])
        merged_allowed_agents = list(
            dict.fromkeys([*allowed_agents, *legacy_agent_ids]),
        )
        if merged_allowed_agents != allowed_agents:
            policy["allowed_agents"] = merged_allowed_agents
            policy["updated_at"] = int(time.time())
            resource_policies_migrated += 1
        if policies.get(policy["id"]) != policy:
            policies[policy["id"]] = policy
            changed = True
        if key != policy["id"]:
            del policies[key]
            changed = True

    for agent_id in known_agent_ids:
        key = agent_policy_key(agent_id)
        raw_policy = agent_policies.get(key)
        if isinstance(raw_policy, dict):
            policy = _normalize_agent_policy(raw_policy)
            if agent_policies.get(key) != policy:
                agent_policies[key] = policy
                changed = True
            continue

        policy = default_agent_policy(agent_id)
        if display_names.get(agent_id):
            policy["display_name"] = display_names[agent_id]
        agent_policies[key] = policy
        agent_policies_created += 1
        changed = True

    if changed:
        _save_data(data)

    return {
        "changed": changed,
        "agent_policies_created": agent_policies_created,
        "resource_policies_migrated": resource_policies_migrated,
    }


def get_agent_policy(agent_id: str) -> dict:
    if db.is_database_enabled():
        from jotaduo_ext.jotaduo.repositories import governance_postgres

        policy = governance_postgres.get_agent_policy(
            agent_policy_key(agent_id),
        )
        if isinstance(policy, dict):
            return _normalize_agent_policy(policy)
        return default_agent_policy(agent_id)

    data = _load_data()
    policy = data.get("agent_policies", {}).get(agent_policy_key(agent_id))
    if isinstance(policy, dict):
        return _normalize_agent_policy(policy)
    return default_agent_policy(agent_id)


def list_agent_policies() -> list[dict]:
    if db.is_database_enabled():
        from jotaduo_ext.jotaduo.repositories import governance_postgres

        return [
            _normalize_agent_policy(policy)
            for policy in governance_postgres.list_agent_policies()
        ]

    data = _load_data()
    return [
        _normalize_agent_policy(policy)
        for policy in data.get("agent_policies", {}).values()
        if isinstance(policy, dict)
    ]


def upsert_agent_policy(policy: dict) -> dict:
    normalized = _normalize_agent_policy(
        {
            **policy,
            "id": agent_policy_key(policy["agent_id"]),
            "updated_at": int(time.time()),
        },
    )
    if db.is_database_enabled():
        from jotaduo_ext.jotaduo.repositories import governance_postgres

        return _normalize_agent_policy(
            governance_postgres.upsert_agent_policy(normalized),
        )

    data = _load_data()
    data.setdefault("agent_policies", {})[normalized["id"]] = normalized
    _save_data(data)
    return normalized


def delete_agent_policy(policy_id: str) -> bool:
    if db.is_database_enabled():
        from jotaduo_ext.jotaduo.repositories import governance_postgres

        return governance_postgres.delete_agent_policy(policy_id)

    data = _load_data()
    policies = data.setdefault("agent_policies", {})
    if policy_id not in policies:
        return False
    del policies[policy_id]
    _save_data(data)
    return True


def _is_auth_active() -> bool:
    from jotaduo.app import auth

    return auth.is_auth_enabled() and auth.has_registered_users()


def agent_can_use_resource(
    agent_id: str,
    source: str,
    resource_id: str,
) -> bool:
    if not _is_auth_active():
        return True
    if not agent_id or not source or not resource_id:
        return False
    if agent_id == "__admin__":
        return True

    policy = get_resource_policy(source, resource_id)
    if not policy:
        return True
    if not policy.get("enabled", True):
        return False

    allowed_agents = set(policy.get("allowed_agents") or [])
    if not allowed_agents:
        allowed_agents.update(_legacy_allowed_agents_from_roles(policy))
    if not allowed_agents:
        return True
    return agent_id in allowed_agents


def filter_resource_ids_for_agent(
    agent_id: str,
    source: str,
    resource_ids: list[str] | tuple[str, ...],
) -> list[str]:
    """Return resource ids the agent is allowed to see/use.

    Resource authorization belongs to the agent, not directly to the user's
    role. List endpoints use this helper to avoid exposing tools, MCP clients,
    or skills that the selected agent cannot actually call.
    """
    return [
        resource_id
        for resource_id in resource_ids
        if agent_can_use_resource(agent_id, source, resource_id)
    ]


def ensure_resource_access(
    agent_id: str,
    source: str,
    resource_id: str,
) -> None:
    if agent_can_use_resource(agent_id, source, resource_id):
        return
    raise HTTPException(
        status_code=403,
        detail="Resource access denied",
    )


def _agent_id_from_path(path: str) -> str | None:
    if not path.startswith("/api/agents/"):
        return None
    parts = path.split("/")
    if len(parts) < 4 or not parts[3]:
        return None
    if parts[3] in {"order"}:
        return None
    return parts[3]


def enforce_agent_access_for_request(request: Request) -> None:
    """Delegate to authorization module for grant-based access control."""
    from jotaduo_ext.jotaduo.authorization import (
        enforce_agent_access_for_request as _enforce_v2,
    )

    _enforce_v2(request)
