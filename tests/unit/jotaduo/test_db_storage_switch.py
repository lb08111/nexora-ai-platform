# -*- coding: utf-8 -*-
"""Tests for Jotaduo database storage switches."""
from __future__ import annotations

import pytest

from jotaduo_ext.jotaduo import approval_requests, audit, db
from jotaduo_ext.jotaduo import governance


def test_database_enabled_requires_db_url(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv(db.DB_URL_ENV, raising=False)
    db.reset_engine_cache()

    assert not db.is_database_enabled()

    monkeypatch.setenv(db.DB_URL_ENV, "postgresql+psycopg2://u:p@db/app")
    db.reset_engine_cache()

    assert db.is_database_enabled()


def test_audit_uses_postgres_repository_when_configured(
    monkeypatch: pytest.MonkeyPatch,
):
    from jotaduo_ext.jotaduo.repositories import audit_postgres

    inserted = []
    listed = [{"id": "event-1"}]

    monkeypatch.setattr(db, "is_database_enabled", lambda: True)
    monkeypatch.setattr(
        audit_postgres,
        "insert_event",
        lambda event: inserted.append(event),
    )
    monkeypatch.setattr(
        audit_postgres,
        "list_events",
        lambda **_kwargs: listed,
    )

    event = audit.record_audit_event(actor="alice", action="login.success")

    assert inserted[0]["id"] == event["id"]
    assert audit.list_audit_events(limit=1) == listed


def test_approval_requests_use_postgres_repository_when_configured(
    monkeypatch: pytest.MonkeyPatch,
):
    from jotaduo_ext.jotaduo.repositories import approval_postgres

    stored = {}

    def create_request(item):
        stored[item["id"]] = dict(item)
        return dict(item)

    def get_request(request_id):
        return stored.get(request_id)

    def update_request(request_id, item):
        stored[request_id] = dict(item)
        return dict(item)

    monkeypatch.setattr(db, "is_database_enabled", lambda: True)
    monkeypatch.setattr(approval_postgres, "create_request", create_request)
    monkeypatch.setattr(approval_postgres, "get_request", get_request)
    monkeypatch.setattr(
        approval_postgres,
        "list_requests",
        lambda **_kwargs: list(stored.values()),
    )
    monkeypatch.setattr(approval_postgres, "update_request", update_request)

    item = approval_requests.create_approval_request(
        {
            "action": "mcp.create",
            "requester": "alice",
            "resource_type": "mcp",
            "resource_id": "prod-shell",
        },
    )
    updated = approval_requests.update_approval_request(
        item["id"],
        {"status": approval_requests.APPLIED, "approver": "bob"},
    )

    assert (
        approval_requests.get_approval_request(item["id"])["requester"]
        == "alice"
    )
    assert updated["status"] == approval_requests.APPLIED
    assert approval_requests.list_approval_requests()[0]["approver"] == "bob"


def test_governance_uses_postgres_repository_when_configured(
    monkeypatch: pytest.MonkeyPatch,
):
    from jotaduo_ext.jotaduo.repositories import governance_postgres

    resource_policies = {}
    agent_policies = {}
    approval_policies = {}

    monkeypatch.setattr(db, "is_database_enabled", lambda: True)
    monkeypatch.setattr(
        governance_postgres,
        "get_resource_policy",
        lambda policy_id: resource_policies.get(policy_id),
    )
    monkeypatch.setattr(
        governance_postgres,
        "list_resource_policies",
        lambda: list(resource_policies.values()),
    )
    monkeypatch.setattr(
        governance_postgres,
        "upsert_resource_policy",
        lambda policy: resource_policies.setdefault(
            policy["id"],
            dict(policy),
        ),
    )
    monkeypatch.setattr(
        governance_postgres,
        "delete_resource_policy",
        lambda policy_id: resource_policies.pop(policy_id, None) is not None,
    )
    monkeypatch.setattr(
        governance_postgres,
        "get_agent_policy",
        lambda policy_id: agent_policies.get(policy_id),
    )
    monkeypatch.setattr(
        governance_postgres,
        "list_agent_policies",
        lambda: list(agent_policies.values()),
    )
    monkeypatch.setattr(
        governance_postgres,
        "upsert_agent_policy",
        lambda policy: agent_policies.setdefault(policy["id"], dict(policy)),
    )
    monkeypatch.setattr(
        governance_postgres,
        "delete_agent_policy",
        lambda policy_id: agent_policies.pop(policy_id, None) is not None,
    )
    monkeypatch.setattr(
        governance_postgres,
        "get_approval_policy",
        lambda action: approval_policies.get(action),
    )
    monkeypatch.setattr(
        governance_postgres,
        "list_approval_policies",
        lambda: list(approval_policies.values()),
    )
    monkeypatch.setattr(
        governance_postgres,
        "upsert_approval_policy",
        lambda policy: approval_policies.setdefault(
            policy["action"],
            dict(policy),
        ),
    )

    policy = governance.upsert_policy(
        {
            "source": "mcp",
            "resource_id": "prod-shell",
            "allowed_agents": ["ops-agent"],
        },
    )
    agent_policy = governance.upsert_agent_policy(
        {
            "agent_id": "ops-agent",
            "allowed_roles": ["operator"],
        },
    )
    approval_policy = governance.upsert_approval_policy(
        {
            "action": "mcp.create",
            "approver_roles": ["admin"],
        },
    )

    assert (
        governance.get_resource_policy("mcp", "prod-shell")["id"]
        == policy["id"]
    )
    assert governance.list_policies()[0]["allowed_agents"] == ["ops-agent"]
    assert governance.get_agent_policy("ops-agent")["id"] == agent_policy["id"]
    assert governance.list_agent_policies()[0]["allowed_roles"] == ["operator"]
    assert (
        governance.get_approval_policy("mcp.create")["id"]
        == approval_policy["id"]
    )
    assert governance.delete_policy("mcp:prod-shell")
    assert governance.delete_agent_policy("agent:ops-agent")


def test_governance_db_migration_backfills_missing_agent_policies(
    monkeypatch: pytest.MonkeyPatch,
):
    from jotaduo_ext.jotaduo.repositories import governance_postgres

    resource_policies = {
        "skill:restart": {
            "id": "skill:restart",
            "source": "skill",
            "resource_id": "restart",
            "allowed_roles": ["ops-agent", "operator"],
            "allowed_agents": [],
            "enabled": True,
        },
    }
    agent_policies = {}

    monkeypatch.setattr(db, "is_database_enabled", lambda: True)
    monkeypatch.setattr(
        governance_postgres,
        "list_resource_policies",
        lambda: list(resource_policies.values()),
    )
    monkeypatch.setattr(
        governance_postgres,
        "upsert_resource_policy",
        lambda policy: resource_policies.__setitem__(
            policy["id"],
            dict(policy),
        )
        or dict(policy),
    )
    monkeypatch.setattr(
        governance_postgres,
        "list_agent_policies",
        lambda: list(agent_policies.values()),
    )
    monkeypatch.setattr(
        governance_postgres,
        "get_agent_policy",
        lambda policy_id: agent_policies.get(policy_id),
    )
    monkeypatch.setattr(
        governance_postgres,
        "upsert_agent_policy",
        lambda policy: agent_policies.__setitem__(policy["id"], dict(policy))
        or dict(policy),
    )

    result = governance.migrate_governance_data(
        ["ops-agent", "report-agent"],
        {"ops-agent": "Ops Agent"},
    )

    assert result == {
        "changed": True,
        "agent_policies_created": 2,
        "resource_policies_migrated": 1,
    }
    assert resource_policies["skill:restart"]["allowed_agents"] == [
        "ops-agent",
    ]
    assert agent_policies["agent:ops-agent"]["display_name"] == "Ops Agent"


def test_auth_uses_postgres_repository_when_configured(
    monkeypatch: pytest.MonkeyPatch,
):
    from jotaduo.app import auth
    from jotaduo_ext.jotaduo.repositories import auth_postgres

    stored = {"users": [], "roles": {}}
    saves = []

    def load_auth_data():
        return {
            "users": [dict(user) for user in stored["users"]],
            "roles": {
                role_id: dict(role)
                for role_id, role in stored["roles"].items()
            },
        }

    def save_auth_data(data):
        saves.append(data)
        stored["users"] = [dict(user) for user in data.get("users", [])]
        stored["roles"] = {
            role_id: dict(role)
            for role_id, role in data.get("roles", {}).items()
        }

    monkeypatch.setattr(db, "is_database_enabled", lambda: True)
    monkeypatch.setattr(auth_postgres, "load_auth_data", load_auth_data)
    monkeypatch.setattr(auth_postgres, "save_auth_data", save_auth_data)

    user = auth.create_user("db-user", "secret", ["operator"])

    assert user["username"] == "db-user"
    assert stored["users"][0]["username"] == "db-user"
    assert "operator" in stored["roles"]
    assert saves


def test_auth_db_mode_keeps_jwt_secret_file_backed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
):
    from jotaduo.app import auth
    from jotaduo_ext.jotaduo.repositories import auth_postgres

    saved_identity = []
    saved_files = []

    monkeypatch.setattr(db, "is_database_enabled", lambda: True)
    monkeypatch.setattr(auth_postgres, "save_auth_data", saved_identity.append)
    monkeypatch.setattr(auth, "AUTH_FILE", tmp_path / "auth.json")

    original_save_file = auth._save_auth_file

    def save_file(data):
        saved_files.append(dict(data))
        original_save_file(data)

    monkeypatch.setattr(auth, "_save_auth_file", save_file)

    auth._save_auth_data(
        {
            "users": [
                {
                    "id": "u1",
                    "username": "alice",
                    "password_hash": "h",
                    "password_salt": "s",
                    "roles": ["admin"],
                    "status": "active",
                    "created_at": 1,
                    "updated_at": 1,
                },
            ],
            "roles": {},
            "jwt_secret": "secret",
        },
    )

    assert saved_identity
    assert saved_identity[0]["users"][0]["username"] == "alice"
    assert saved_files == [{"jwt_secret": "secret"}]
