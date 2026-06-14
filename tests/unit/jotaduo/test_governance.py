# -*- coding: utf-8 -*-
"""Unit tests for Jotaduo governance policy behavior."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi import HTTPException

from jotaduo_ext.jotaduo import governance


@pytest.fixture(autouse=True)
def _isolated_governance_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Use a per-test governance file and force auth-aware policy behavior."""
    monkeypatch.setattr(
        governance,
        "GOVERNANCE_FILE",
        tmp_path / "jotaduo_governance.json",
    )
    monkeypatch.setattr(governance, "_is_auth_active", lambda: True)


def test_resource_access_uses_allowed_agents_not_allowed_roles():
    """When allowed_agents is explicitly set, only those agents pass."""
    governance.upsert_policy(
        {
            "source": "mcp",
            "resource_id": "prod-shell",
            "allowed_roles": ["operator"],
            "allowed_agents": [],
            "enabled": True,
        },
    )

    # Empty allowed_agents = open to all agents (new multi-tenant model)
    assert governance.agent_can_use_resource(
        "operator",
        "mcp",
        "prod-shell",
    )

    governance.upsert_policy(
        {
            "source": "mcp",
            "resource_id": "prod-shell",
            "allowed_roles": ["operator"],
            "allowed_agents": ["ops-agent"],
            "enabled": True,
        },
    )

    # Explicit allowed_agents restricts access
    assert governance.agent_can_use_resource("ops-agent", "mcp", "prod-shell")
    assert not governance.agent_can_use_resource(
        "other-agent",
        "mcp",
        "prod-shell",
    )


def test_resource_access_keeps_legacy_agent_ids_saved_in_allowed_roles():
    """Old governance data may store agent ids in allowed_roles."""
    governance.upsert_policy(
        {
            "source": "builtin_tool",
            "resource_id": "execute_shell_command",
            "allowed_roles": ["ops-agent", "operator"],
            "allowed_agents": [],
            "enabled": True,
        },
    )

    assert governance.agent_can_use_resource(
        "ops-agent",
        "builtin_tool",
        "execute_shell_command",
    )
    assert not governance.agent_can_use_resource(
        "operator",
        "builtin_tool",
        "execute_shell_command",
    )


def test_filter_resource_ids_for_agent_returns_only_agent_granted_resources():
    governance.upsert_policy(
        {
            "source": "builtin_tool",
            "resource_id": "terminal",
            "allowed_agents": ["ops-agent"],
            "enabled": True,
        },
    )
    governance.upsert_policy(
        {
            "source": "builtin_tool",
            "resource_id": "browser",
            "allowed_agents": ["other-agent"],
            "enabled": True,
        },
    )
    governance.upsert_policy(
        {
            "source": "builtin_tool",
            "resource_id": "disabled-tool",
            "allowed_agents": ["ops-agent"],
            "enabled": False,
        },
    )

    # "terminal" allowed for ops-agent, "browser" restricted to other-agent,
    # "missing-tool" has no policy so defaults to allowed, "disabled-tool" is disabled.
    assert governance.filter_resource_ids_for_agent(
        "ops-agent",
        "builtin_tool",
        ["terminal", "browser", "missing-tool", "disabled-tool"],
    ) == ["terminal", "missing-tool"]


def test_ensure_resource_access_denies_agent_not_in_allowed_list():
    governance.upsert_policy(
        {
            "source": "skill",
            "resource_id": "restart-service",
            "allowed_agents": ["other-agent"],
            "enabled": True,
        },
    )

    with pytest.raises(HTTPException) as exc_info:
        governance.ensure_resource_access(
            "ops-agent",
            "skill",
            "restart-service",
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Resource access denied"


def test_save_data_writes_valid_json_and_leaves_no_temp_files(tmp_path: Path):
    policy = governance.upsert_policy(
        {
            "source": "builtin_tool",
            "resource_id": "safe-read",
            "allowed_agents": ["ops-agent"],
        },
    )

    assert policy["id"] == "builtin_tool:safe-read"
    data = json.loads(governance.GOVERNANCE_FILE.read_text("utf-8"))
    assert data["policies"]["builtin_tool:safe-read"]["allowed_agents"] == [
        "ops-agent",
    ]
    assert not list(tmp_path.glob(".jotaduo_governance.json.*.tmp"))


def test_ensure_resource_policy_merges_approved_agent_grants():
    initial = governance.ensure_resource_policy(
        "mcp",
        "prod-shell",
        display_name="Prod Shell",
        allowed_agents=["ops-agent"],
    )

    assert initial["id"] == "mcp:prod-shell"
    assert initial["display_name"] == "Prod Shell"
    assert initial["allowed_agents"] == ["ops-agent"]
    assert governance.agent_can_use_resource(
        "ops-agent",
        "mcp",
        "prod-shell",
    )

    updated = governance.ensure_resource_policy(
        "mcp",
        "prod-shell",
        display_name="Ignored Name",
        allowed_agents=["report-agent", "ops-agent"],
    )

    assert updated["display_name"] == "Prod Shell"
    assert updated["allowed_agents"] == ["ops-agent", "report-agent"]


def test_plugin_resource_policy_defaults_to_high_risk():
    policy = governance.ensure_resource_policy(
        "plugin",
        "ssh-tools",
        display_name="SSH Tools",
    )

    assert policy["id"] == "plugin:ssh-tools"
    assert policy["risk_level"] == "high"
    assert policy["allowed_agents"] == []


def test_migrate_governance_data_backfills_agents_and_legacy_resource_grants():
    governance.upsert_policy(
        {
            "source": "skill",
            "resource_id": "restart-service",
            "allowed_roles": ["operator", "ops-agent", "deleted-agent"],
            "allowed_agents": [],
            "enabled": True,
        },
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
    assert governance.agent_can_use_resource(
        "ops-agent",
        "skill",
        "restart-service",
    )
    assert not governance.agent_can_use_resource(
        "deleted-agent",
        "skill",
        "restart-service",
    )
    assert (
        governance.get_agent_policy("ops-agent")["display_name"] == "Ops Agent"
    )
    assert governance.get_agent_policy("report-agent")["allowed_roles"] == [
        "admin",
    ]


def test_migrate_governance_data_is_idempotent():
    governance.migrate_governance_data(["ops-agent"])

    assert governance.migrate_governance_data(["ops-agent"]) == {
        "changed": False,
        "agent_policies_created": 0,
        "resource_policies_migrated": 0,
    }


def test_default_approval_policies_define_first_phase_approvers():
    policies = {
        policy["action"]: policy
        for policy in governance.list_approval_policies()
    }

    assert policies["mcp.create"]["approver_roles"] == [
        "admin",
    ]
    assert policies["skill.create"]["approver_roles"] == [
        "admin",
    ]
    assert policies["tool.create"]["approver_roles"] == [
        "admin",
    ]
    assert policies["plugin.install"]["approver_roles"] == ["admin"]
    assert not policies["mcp.create"]["allow_self_approval"]


def test_approval_policy_can_be_overridden():
    updated = governance.upsert_approval_policy(
        {
            "action": "plugin.install",
            "enabled": True,
            "approver_roles": ["admin"],
            "allow_self_approval": True,
        },
    )

    assert updated["approver_roles"] == ["admin"]
    assert updated["allow_self_approval"]
    assert governance.get_approval_policy("plugin.install")[
        "approver_roles"
    ] == ["admin"]


def test_approval_policy_checks_roles_and_self_approval():
    assert governance.role_ids_can_approve_action(
        ["admin"],
        "mcp.create",
        actor="alice",
        requester="bob",
    )
    assert not governance.role_ids_can_approve_action(
        ["operator"],
        "mcp.create",
        actor="alice",
        requester="bob",
    )
    assert not governance.role_ids_can_approve_action(
        ["admin"],
        "mcp.create",
        actor="alice",
        requester="alice",
    )

    governance.upsert_approval_policy(
        {
            "action": "mcp.create",
            "enabled": True,
            "approver_roles": ["admin"],
            "allow_self_approval": True,
        },
    )

    assert governance.role_ids_can_approve_action(
        ["admin"],
        "mcp.create",
        actor="alice",
        requester="alice",
    )


def test_disabled_approval_policy_does_not_require_approval_role():
    governance.upsert_approval_policy(
        {
            "action": "tool.create",
            "enabled": False,
            "approver_roles": ["admin"],
            "allow_self_approval": False,
        },
    )

    assert governance.role_ids_can_approve_action(
        ["operator"],
        "tool.create",
        actor="alice",
        requester="alice",
    )
