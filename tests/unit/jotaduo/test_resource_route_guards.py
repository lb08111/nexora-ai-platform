# -*- coding: utf-8 -*-
"""Regression tests for resource-level route guards."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from jotaduo.config.config import MCPConfig
from jotaduo_ext.jotaduo import governance


@pytest.fixture(autouse=True)
def _isolated_governance_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        governance,
        "GOVERNANCE_FILE",
        tmp_path / "jotaduo_governance.json",
    )
    monkeypatch.setattr(governance, "_is_auth_active", lambda: True)


def _request() -> SimpleNamespace:
    return SimpleNamespace(state=SimpleNamespace(user="alice"))


def _patch_workspace(monkeypatch: pytest.MonkeyPatch, workspace) -> None:
    import jotaduo.app.agent_context as agent_context

    async def fake_get_agent_for_request(_request):
        return workspace

    monkeypatch.setattr(
        agent_context,
        "get_agent_for_request",
        fake_get_agent_for_request,
    )


def _restrict_resource(source: str, resource_id: str, allowed_agent: str):
    """Create a policy that restricts a resource to a specific agent."""
    governance.upsert_policy(
        {
            "source": source,
            "resource_id": resource_id,
            "allowed_agents": [allowed_agent],
            "enabled": True,
        },
    )


@pytest.mark.asyncio
async def test_tool_config_denies_resource_not_granted_to_agent(
    monkeypatch: pytest.MonkeyPatch,
):
    from jotaduo.app.routers import tools

    _patch_workspace(
        monkeypatch,
        SimpleNamespace(agent_id="ops-agent"),
    )

    _restrict_resource("builtin_tool", "execute_shell_command", "other-agent")

    with pytest.raises(HTTPException) as exc_info:
        await tools.get_tool_config(
            "execute_shell_command",
            _request(),  # type: ignore[arg-type]
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Resource access denied"


@pytest.mark.asyncio
async def test_mcp_detail_denies_resource_not_granted_to_agent(
    monkeypatch: pytest.MonkeyPatch,
):
    from jotaduo.app.routers import mcp

    agent = SimpleNamespace(
        agent_id="ops-agent",
        config=SimpleNamespace(
            mcp=MCPConfig(
                clients={
                    "prod-shell": mcp.MCPClientConfig(
                        name="Prod Shell",
                        transport="stdio",
                        command="echo",
                    ),
                },
            ),
        ),
    )
    _patch_workspace(monkeypatch, agent)

    _restrict_resource("mcp", "prod-shell", "other-agent")

    with pytest.raises(HTTPException) as exc_info:
        await mcp.get_mcp_client(
            _request(),  # type: ignore[arg-type]
            "prod-shell",
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Resource access denied"


@pytest.mark.asyncio
async def test_skill_config_denies_resource_not_granted_to_agent(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    from jotaduo.app.routers import skills

    _patch_workspace(
        monkeypatch,
        SimpleNamespace(
            agent_id="ops-agent",
            workspace_dir=str(tmp_path),
        ),
    )

    _restrict_resource("skill", "restart-service", "other-agent")

    with pytest.raises(HTTPException) as exc_info:
        await skills.get_skill_config_endpoint(
            _request(),  # type: ignore[arg-type]
            "restart-service",
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Resource access denied"


def test_proactive_builtin_tools_use_agent_resource_governance():
    from jotaduo.agents.memory.proactive import proactive_responder

    # No policy = allowed (multi-tenant default)
    assert proactive_responder._agent_can_use_proactive_builtin_tool(
        "ops-agent",
        "execute_shell_command",
    )

    # Restrict to other-agent => ops-agent denied
    _restrict_resource("builtin_tool", "execute_shell_command", "other-agent")

    assert not proactive_responder._agent_can_use_proactive_builtin_tool(
        "ops-agent",
        "execute_shell_command",
    )

    # Grant to ops-agent => allowed
    governance.upsert_policy(
        {
            "source": "builtin_tool",
            "resource_id": "execute_shell_command",
            "allowed_agents": ["ops-agent"],
            "enabled": True,
        },
    )

    assert proactive_responder._agent_can_use_proactive_builtin_tool(
        "ops-agent",
        "execute_shell_command",
    )


def test_memory_summary_tools_use_agent_resource_governance():
    from jotaduo.agents.memory import reme_light_memory_manager
    from jotaduo.agents.memory.base_memory_manager import BaseMemoryManager

    manager = object.__new__(
        reme_light_memory_manager.ReMeLightMemoryManager,
    )
    BaseMemoryManager.__init__(
        manager,
        working_dir="/tmp/jotaduo-test-memory",
        agent_id="ops-agent",
    )

    # No policy = allowed (multi-tenant default)
    assert manager._agent_can_use_summary_tool("write_file")

    # Restrict to other-agent => ops-agent denied
    _restrict_resource("builtin_tool", "write_file", "other-agent")

    assert not manager._agent_can_use_summary_tool("write_file")

    # Grant to ops-agent => allowed
    governance.upsert_policy(
        {
            "source": "builtin_tool",
            "resource_id": "write_file",
            "allowed_agents": ["ops-agent"],
            "enabled": True,
        },
    )

    assert manager._agent_can_use_summary_tool("write_file")
