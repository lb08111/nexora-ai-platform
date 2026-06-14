# -*- coding: utf-8 -*-
"""Unit tests for Nexora platform approval requests."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from qwenpaw.config.config import MCPConfig
from qwenpaw_ext.nexora import approval_requests


@pytest.fixture(autouse=True)
def _isolated_approval_requests_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        approval_requests,
        "APPROVAL_REQUESTS_FILE",
        tmp_path / "nexora_approval_requests.json",
    )


def test_create_and_update_approval_request():
    item = approval_requests.create_approval_request(
        {
            "action": "mcp.create",
            "requester": "alice",
            "resource_type": "mcp",
            "resource_id": "prod-shell",
            "resource_name": "Prod Shell",
            "payload": {"agent_id": "ops-agent"},
        },
    )

    assert item["status"] == approval_requests.PENDING
    assert item["requester"] == "alice"
    assert approval_requests.get_approval_request(item["id"])["payload"] == {
        "agent_id": "ops-agent",
    }

    updated = approval_requests.update_approval_request(
        item["id"],
        {"status": approval_requests.APPLIED, "approver": "bob"},
    )

    assert updated["status"] == approval_requests.APPLIED
    assert (
        approval_requests.list_approval_requests(
            status=approval_requests.APPLIED,
        )[0]["approver"]
        == "bob"
    )


@pytest.mark.asyncio
async def test_create_mcp_client_submits_approval_without_saving(
    monkeypatch: pytest.MonkeyPatch,
):
    import qwenpaw.app.agent_context as agent_context
    import qwenpaw.app.auth as auth
    from qwenpaw.app.routers import mcp

    saved_configs = []
    created_approvals = []

    agent = SimpleNamespace(
        agent_id="ops-agent",
        config=SimpleNamespace(mcp=MCPConfig(clients={})),
    )
    request = SimpleNamespace(state=SimpleNamespace(user="alice"))

    async def fake_get_agent_for_request(_request):
        return agent

    monkeypatch.setattr(
        agent_context, "get_agent_for_request", fake_get_agent_for_request
    )
    monkeypatch.setattr(auth, "is_auth_enabled", lambda: True)
    monkeypatch.setattr(auth, "has_registered_users", lambda: True)
    monkeypatch.setattr(
        "qwenpaw_ext.nexora.governance.get_approval_policy",
        lambda _action: {"enabled": True},
    )
    monkeypatch.setattr(
        "qwenpaw_ext.nexora.approval_requests.create_approval_request",
        lambda data: created_approvals.append(data) or {"id": "approval-1"},
    )
    monkeypatch.setattr(
        mcp,
        "save_agent_config",
        lambda *args: saved_configs.append(args),
        raising=False,
    )

    result = await mcp.create_mcp_client(
        request,  # type: ignore[arg-type]
        client_key="prod-shell",
        client=mcp.MCPClientCreateRequest(
            name="Prod Shell",
            transport="stdio",
            command="echo",
        ),
    )

    assert result.status == "pending_approval"
    assert result.approval_request_id == "approval-1"
    assert not saved_configs
    assert agent.config.mcp.clients == {}
    assert created_approvals[0]["payload"]["client_key"] == "prod-shell"


@pytest.mark.asyncio
async def test_create_skill_submits_approval_without_writing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    import qwenpaw.app.agent_context as agent_context
    import qwenpaw.app.auth as auth
    from qwenpaw.agents.skill_system import SkillService
    from qwenpaw.app.routers import skills

    created_approvals = []
    request = SimpleNamespace(state=SimpleNamespace(user="alice"))
    workspace = SimpleNamespace(
        agent_id="ops-agent",
        workspace_dir=str(tmp_path),
    )

    async def fake_get_agent_for_request(_request):
        return workspace

    def fail_create_skill(*_args, **_kwargs):
        raise AssertionError("skill should wait for approval")

    monkeypatch.setattr(
        agent_context, "get_agent_for_request", fake_get_agent_for_request
    )
    monkeypatch.setattr(auth, "is_auth_enabled", lambda: True)
    monkeypatch.setattr(auth, "has_registered_users", lambda: True)
    monkeypatch.setattr(
        "qwenpaw_ext.nexora.governance.get_approval_policy",
        lambda _action: {"enabled": True},
    )
    monkeypatch.setattr(
        "qwenpaw_ext.nexora.approval_requests.create_approval_request",
        lambda data: created_approvals.append(data)
        or {"id": "approval-skill"},
    )
    monkeypatch.setattr(SkillService, "create_skill", fail_create_skill)

    result = await skills.create_skill(
        request,  # type: ignore[arg-type]
        skills.CreateSkillRequest(name="restart_nginx", content="hello"),
    )

    assert result["status"] == "pending_approval"
    assert result["approval_request_id"] == "approval-skill"
    assert created_approvals[0]["action"] == "skill.create"
    assert created_approvals[0]["payload"]["agent_id"] == "ops-agent"


@pytest.mark.asyncio
async def test_pool_download_submits_approval_without_broadcasting(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    import qwenpaw.app.auth as auth
    from qwenpaw.agents.skill_system import SkillPoolService
    from qwenpaw.app.routers import skills

    created_approvals = []
    request = SimpleNamespace(
        state=SimpleNamespace(user="admin-user", roles=["admin"]),
    )

    def fail_download(*_args, **_kwargs):
        raise AssertionError("broadcast should wait for approval")

    monkeypatch.setattr(auth, "is_auth_enabled", lambda: True)
    monkeypatch.setattr(auth, "has_registered_users", lambda: True)
    monkeypatch.setattr(
        "qwenpaw_ext.nexora.capability_approval.requires_approval",
        lambda capability, action="add": capability == "skill"
        and action == "add",
    )
    monkeypatch.setattr(
        "qwenpaw_ext.nexora.approval_requests.create_approval_request",
        lambda data: created_approvals.append(data)
        or {"id": "approval-broadcast"},
    )
    monkeypatch.setattr(
        skills,
        "list_workspaces",
        lambda: [
            {
                "agent_id": "ops-agent",
                "agent_name": "Ops Agent",
                "workspace_dir": str(tmp_path),
            },
        ],
    )
    monkeypatch.setattr(
        SkillPoolService, "download_to_workspace", fail_download
    )

    result = await skills.download_pool_skill_to_workspaces(
        request,  # type: ignore[arg-type]
        skills.DownloadFromPoolRequest(
            skill_name="shared_skill",
            targets=[skills.PoolDownloadTarget(workspace_id="ops-agent")],
        ),
    )

    assert result["status"] == "pending_approval"
    assert result["approval_request_id"] == "approval-broadcast"
    assert created_approvals[0]["action"] == "skill.create"
    assert created_approvals[0]["payload"] == {
        "operation": "workspace.download_from_pool",
        "skill_name": "shared_skill",
        "targets": [{"workspace_id": "ops-agent"}],
        "overwrite": False,
    }


@pytest.mark.asyncio
async def test_pool_download_preview_checks_agent_access(
    monkeypatch: pytest.MonkeyPatch,
):
    import qwenpaw.app.auth as auth
    from qwenpaw.app.routers import skills

    request = SimpleNamespace(
        state=SimpleNamespace(user="alice", roles=["operator"]),
    )

    monkeypatch.setattr(auth, "is_auth_enabled", lambda: True)
    monkeypatch.setattr(auth, "has_registered_users", lambda: True)
    monkeypatch.setattr(
        skills,
        "list_workspaces",
        lambda: [
            {
                "agent_id": "ops-agent",
                "agent_name": "Ops Agent",
                "workspace_dir": "/tmp/ops-agent",
            },
        ],
    )
    monkeypatch.setattr(
        "qwenpaw_ext.nexora.agent_grants.is_user_granted",
        lambda agent_id, username: False,
    )

    with pytest.raises(Exception) as exc_info:
        await skills.download_pool_skill_to_workspaces(
            request,  # type: ignore[arg-type]
            skills.DownloadFromPoolRequest(
                skill_name="shared_skill",
                targets=[skills.PoolDownloadTarget(workspace_id="ops-agent")],
                preview_only=True,
            ),
        )

    assert getattr(exc_info.value, "status_code", None) == 403


@pytest.mark.asyncio
async def test_apply_pool_broadcast_approval_downloads_to_targets(
    monkeypatch: pytest.MonkeyPatch,
):
    from qwenpaw.app.routers import nexora, skills

    executed = []

    def fake_execute(body):
        executed.append(body)
        return {
            "downloaded": [
                {
                    "workspace_id": "ops-agent",
                    "workspace_name": "Ops Agent",
                    "name": body.skill_name,
                },
            ],
        }

    monkeypatch.setattr(skills, "_execute_pool_download", fake_execute)
    monkeypatch.setattr(
        nexora,
        "ensure_resource_policy",
        lambda source, resource_id, **kwargs: {
            "id": "policy-1",
            "source": source,
            "resource_id": resource_id,
            **kwargs,
        },
    )

    result = await nexora._apply_skill_create_approval(
        {
            "payload": {
                "operation": "workspace.download_from_pool",
                "skill_name": "shared_skill",
                "targets": [{"workspace_id": "ops-agent"}],
                "overwrite": True,
            },
        },
        SimpleNamespace(),  # type: ignore[arg-type]
    )

    assert result["operation"] == "workspace.download_from_pool"
    assert result["downloaded"][0]["workspace_id"] == "ops-agent"
    assert result["governance_policy_id"] == "policy-1"
    assert executed[0].skill_name == "shared_skill"
    assert executed[0].overwrite is True


@pytest.mark.asyncio
async def test_install_plugin_submits_approval_without_loader(
    monkeypatch: pytest.MonkeyPatch,
):
    import qwenpaw.app.auth as auth
    from qwenpaw.app.routers import plugins

    created_approvals = []
    request = SimpleNamespace(state=SimpleNamespace(user="alice"))

    monkeypatch.setattr(auth, "is_auth_enabled", lambda: True)
    monkeypatch.setattr(auth, "has_registered_users", lambda: True)
    monkeypatch.setattr(
        "qwenpaw_ext.nexora.governance.get_approval_policy",
        lambda _action: {"enabled": True},
    )
    monkeypatch.setattr(
        "qwenpaw_ext.nexora.approval_requests.create_approval_request",
        lambda data: created_approvals.append(data)
        or {"id": "approval-plugin"},
    )

    result = await plugins.install_plugin(
        plugins.InstallPluginRequest(source="/tmp/example-plugin"),
        request,  # type: ignore[arg-type]
    )

    assert result["status"] == "pending_approval"
    assert result["approval_request_id"] == "approval-plugin"
    assert created_approvals[0]["action"] == "plugin.install"
    assert created_approvals[0]["payload"]["source"] == "/tmp/example-plugin"
