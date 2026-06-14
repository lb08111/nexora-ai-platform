#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Migrate first-phase Jotaduo files into PostgreSQL.

Requires JOTADUO_DB_URL to point at the target PostgreSQL database.
The script is idempotent for existing primary keys: duplicate rows are skipped.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _ensure_src_on_path() -> None:
    src = _repo_root() / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))


def _iter_jsonl(path: Path):
    if not path.is_file():
        return
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict):
                yield item


def _load_approval_requests(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text("utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    requests = data.get("requests") if isinstance(data, dict) else None
    if not isinstance(requests, dict):
        return []
    return [item for item in requests.values() if isinstance(item, dict)]


def _load_json_dict(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text("utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def _load_auth_identity(path: Path) -> dict:
    data = _load_json_dict(path)
    ts = int(time.time())

    users = data.get("users")
    if not isinstance(users, list):
        legacy_user = data.get("user")
        if isinstance(legacy_user, dict) and legacy_user.get("username"):
            users = [
                {
                    "id": legacy_user.get("id")
                    or f"legacy-{legacy_user['username']}",
                    "username": legacy_user.get("username", ""),
                    "password_hash": legacy_user.get("password_hash", ""),
                    "password_salt": legacy_user.get("password_salt", ""),
                    "roles": legacy_user.get("roles") or ["admin"],
                    "status": legacy_user.get("status") or "active",
                    "created_at": legacy_user.get("created_at") or ts,
                    "updated_at": legacy_user.get("updated_at") or ts,
                },
            ]
        else:
            users = []

    roles = data.get("roles") if isinstance(data.get("roles"), dict) else {}
    return {
        "users": [user for user in users if isinstance(user, dict)],
        "roles": roles,
    }


def _migrate_runtime_config(working_dir: Path) -> dict[str, int]:
    """Import config.json and per-agent agent.json into PostgreSQL."""
    from jotaduo_ext.jotaduo.repositories import config_postgres

    result: dict[str, int] = {"global_config": 0, "agent_configs": 0}

    config_file = working_dir / "config.json"
    if config_file.is_file():
        data = _load_json_dict(config_file)
        if data:
            config_postgres.save_global_config(data)
            result["global_config"] = 1

    workspaces_dir = working_dir / "workspaces"
    if workspaces_dir.is_dir():
        for agent_dir in sorted(workspaces_dir.iterdir()):
            agent_json = agent_dir / "agent.json"
            if agent_json.is_file():
                agent_data = _load_json_dict(agent_json)
                if agent_data:
                    config_postgres.save_agent_config(
                        agent_dir.name,
                        agent_data,
                    )
                    result["agent_configs"] += 1

    return result


def migrate(
    secret_dir: Path,
    working_dir: Path | None = None,
) -> dict[str, int]:
    _ensure_src_on_path()

    from sqlalchemy.exc import IntegrityError

    from jotaduo_ext.jotaduo import db
    from jotaduo_ext.jotaduo.approval_requests import _normalize_request
    from jotaduo_ext.jotaduo.governance import (
        _normalize_agent_policy,
        _normalize_approval_policy,
        _normalize_policy,
    )
    from jotaduo_ext.jotaduo.repositories import (
        approval_postgres,
        audit_postgres,
        auth_postgres,
        governance_postgres,
    )
    from jotaduo_ext.jotaduo.rbac import default_roles

    if not db.is_database_enabled():
        raise RuntimeError("JOTADUO_DB_URL is not configured")

    db.initialize_schema()

    audit_inserted = 0
    audit_skipped = 0
    audit_file = secret_dir / "jotaduo_audit.jsonl"
    for event in _iter_jsonl(audit_file) or []:
        try:
            audit_postgres.insert_event(event)
            audit_inserted += 1
        except IntegrityError:
            audit_skipped += 1

    approval_inserted = 0
    approval_skipped = 0
    approval_file = secret_dir / "jotaduo_approval_requests.json"
    for raw in _load_approval_requests(approval_file):
        try:
            approval_postgres.create_request(_normalize_request(raw))
            approval_inserted += 1
        except IntegrityError:
            approval_skipped += 1

    governance_file = secret_dir / "jotaduo_governance.json"
    resource_policies = 0
    agent_policies = 0
    approval_policies = 0
    if governance_file.is_file():
        governance_data = _load_json_dict(governance_file)
        if isinstance(governance_data, dict):
            for raw in (governance_data.get("policies") or {}).values():
                if isinstance(raw, dict):
                    governance_postgres.upsert_resource_policy(
                        _normalize_policy(raw),
                    )
                    resource_policies += 1
            for raw in (governance_data.get("agent_policies") or {}).values():
                if isinstance(raw, dict):
                    governance_postgres.upsert_agent_policy(
                        _normalize_agent_policy(raw),
                    )
                    agent_policies += 1
            for raw in (
                governance_data.get("approval_policies") or {}
            ).values():
                if isinstance(raw, dict):
                    governance_postgres.upsert_approval_policy(
                        _normalize_approval_policy(raw),
                    )
                    approval_policies += 1

    auth_data = _load_auth_identity(secret_dir / "auth.json")
    default_role_data = default_roles()
    roles = auth_data.get("roles") or {}
    for role_id, role in default_role_data.items():
        if role_id not in roles:
            roles[role_id] = role
        else:
            existing_permissions = list(
                roles[role_id].get("permissions") or [],
            )
            roles[role_id]["permissions"] = list(
                dict.fromkeys(
                    [*existing_permissions, *role.get("permissions", [])],
                ),
            )
            roles[role_id]["builtin"] = True
    auth_data["roles"] = roles
    auth_postgres.save_auth_data(auth_data)

    result = {
        "audit_inserted": audit_inserted,
        "audit_skipped": audit_skipped,
        "approval_inserted": approval_inserted,
        "approval_skipped": approval_skipped,
        "resource_policies_upserted": resource_policies,
        "agent_policies_upserted": agent_policies,
        "approval_policies_upserted": approval_policies,
        "users_upserted": len(auth_data.get("users") or []),
        "roles_upserted": len(auth_data.get("roles") or {}),
    }

    # -- Multi-tenant: agent grants, capability approval, templates --
    from jotaduo_ext.jotaduo.repositories import (
        agent_grants_postgres,
        capability_approval_postgres,
        agent_templates_postgres,
    )
    from jotaduo_ext.jotaduo.capability_approval import _migrate_legacy

    grants_file = secret_dir / "jotaduo_agent_grants.json"
    grants_imported = 0
    if grants_file.is_file():
        grants_data = _load_json_dict(grants_file)
        for agent_id, grant_list in grants_data.items():
            if not isinstance(grant_list, list):
                continue
            for entry in grant_list:
                if isinstance(entry, dict) and "username" in entry:
                    try:
                        agent_grants_postgres.grant_agent_to_user(
                            agent_id=entry.get("agent_id", agent_id),
                            username=entry["username"],
                            granted_by=entry.get("granted_by", "[migration]"),
                        )
                        grants_imported += 1
                    except IntegrityError:
                        pass
                elif isinstance(entry, str):
                    try:
                        agent_grants_postgres.grant_agent_to_user(
                            agent_id=agent_id,
                            username=entry,
                            granted_by="[migration]",
                        )
                        grants_imported += 1
                    except IntegrityError:
                        pass
    result["agent_grants_imported"] = grants_imported

    cap_file = secret_dir / "jotaduo_capability_approval.json"
    cap_imported = 0
    if cap_file.is_file():
        try:
            cap_data = json.loads(cap_file.read_text("utf-8"))
        except (json.JSONDecodeError, OSError):
            cap_data = []
        if isinstance(cap_data, list):
            for config in cap_data:
                if isinstance(config, dict) and "capability_type" in config:
                    config = _migrate_legacy(config)
                    capability_approval_postgres.upsert_config(config)
                    cap_imported += 1
    result["capability_approval_imported"] = cap_imported

    tpl_file = secret_dir / "jotaduo_agent_templates.json"
    tpl_imported = 0
    if tpl_file.is_file():
        try:
            tpl_data = json.loads(tpl_file.read_text("utf-8"))
        except (json.JSONDecodeError, OSError):
            tpl_data = []
        if isinstance(tpl_data, list):
            for tpl in tpl_data:
                if isinstance(tpl, dict) and "template_id" in tpl:
                    try:
                        agent_templates_postgres.create_template(tpl)
                        tpl_imported += 1
                    except IntegrityError:
                        pass
    result["agent_templates_imported"] = tpl_imported

    if working_dir is not None:
        runtime_result = _migrate_runtime_config(working_dir)
        result.update(runtime_result)

    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--secret-dir",
        default=os.environ.get("JOTADUO_SECRET_DIR")
        or str(Path.home() / ".jotaduo.secret"),
        help="Directory containing Jotaduo JSON/JSONL files.",
    )
    parser.add_argument(
        "--working-dir",
        default=os.environ.get("JOTADUO_WORKING_DIR"),
        help="JotaDuo working directory containing config.json and workspaces/. "
        "When provided, global config and per-agent configs are also imported.",
    )
    args = parser.parse_args()
    wd = (
        Path(args.working_dir).expanduser().resolve()
        if args.working_dir
        else None
    )
    result = migrate(
        Path(args.secret_dir).expanduser().resolve(),
        working_dir=wd,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
