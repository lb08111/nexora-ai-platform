# -*- coding: utf-8 -*-
from types import SimpleNamespace

import pytest
from agentscope_runtime.engine.schemas.exception import ConfigurationException

from jotaduo.app import multi_agent_manager as manager_module
from jotaduo.app.multi_agent_manager import MultiAgentManager


class FakeTaskTracker:
    def __init__(self) -> None:
        self.active_tasks: list[str] = []

    async def has_active_tasks(self) -> bool:
        return bool(self.active_tasks)

    async def list_active_tasks(self) -> list[str]:
        return list(self.active_tasks)


class FakeWorkspace:
    stopped_agents: list[str] = []

    def __init__(self, agent_id: str, workspace_dir: str) -> None:
        self.agent_id = agent_id
        self.workspace_dir = workspace_dir
        self.task_tracker = FakeTaskTracker()
        self.manager = None
        self.started = False

    async def start(self) -> None:
        self.started = True

    async def stop(self, final: bool = True) -> None:
        FakeWorkspace.stopped_agents.append(self.agent_id)

    def set_manager(self, manager) -> None:
        self.manager = manager


@pytest.fixture(autouse=True)
def fake_workspace(monkeypatch):
    FakeWorkspace.stopped_agents = []
    monkeypatch.setattr(manager_module, "Workspace", FakeWorkspace)


def _fake_config(*agent_ids: str):
    profiles = {
        agent_id: SimpleNamespace(
            id=agent_id,
            workspace_dir=f"/tmp/{agent_id}",
            enabled=True,
        )
        for agent_id in agent_ids
    }
    return SimpleNamespace(agents=SimpleNamespace(profiles=profiles))


def _patch_config(monkeypatch, *agent_ids: str) -> None:
    monkeypatch.setattr(
        manager_module,
        "load_config",
        lambda: _fake_config(*agent_ids),
    )


@pytest.mark.asyncio
async def test_get_agent_tracks_runtime_status(monkeypatch):
    _patch_config(monkeypatch, "alpha")
    manager = MultiAgentManager(max_active_agents=20, idle_ttl_seconds=3600)

    instance = await manager.get_agent("alpha")
    status = await manager.list_runtime_agents()

    assert instance.started is True
    assert status["loaded_agent_count"] == 1
    assert status["agents"][0]["agent_id"] == "alpha"
    assert status["agents"][0]["active_task_count"] == 0
    assert status["agents"][0]["last_access_at"] is not None


@pytest.mark.asyncio
async def test_cleanup_idle_agents_unloads_inactive_agents(monkeypatch):
    _patch_config(monkeypatch, "alpha")
    manager = MultiAgentManager(max_active_agents=20, idle_ttl_seconds=1)

    await manager.get_agent("alpha")
    manager._last_access["alpha"] -= 10

    unloaded = await manager.cleanup_idle_agents()

    assert unloaded == ["alpha"]
    assert manager.list_loaded_agents() == []
    assert FakeWorkspace.stopped_agents == ["alpha"]


@pytest.mark.asyncio
async def test_cleanup_idle_agents_preserves_active_agents(monkeypatch):
    _patch_config(monkeypatch, "alpha")
    manager = MultiAgentManager(max_active_agents=20, idle_ttl_seconds=1)

    instance = await manager.get_agent("alpha")
    instance.task_tracker.active_tasks = ["run-1"]
    manager._last_access["alpha"] -= 10

    unloaded = await manager.cleanup_idle_agents()

    assert unloaded == []
    assert manager.list_loaded_agents() == ["alpha"]
    assert FakeWorkspace.stopped_agents == []


@pytest.mark.asyncio
async def test_max_active_agents_unloads_lru_idle_agent(monkeypatch):
    _patch_config(monkeypatch, "alpha", "bravo", "charlie")
    manager = MultiAgentManager(max_active_agents=2, idle_ttl_seconds=0)

    await manager.get_agent("alpha")
    await manager.get_agent("bravo")
    manager._last_access["alpha"] = 1.0
    manager._last_access["bravo"] = 2.0

    await manager.get_agent("charlie")

    assert set(manager.list_loaded_agents()) == {"bravo", "charlie"}
    assert FakeWorkspace.stopped_agents == ["alpha"]


@pytest.mark.asyncio
async def test_max_active_agents_raises_when_loaded_agents_are_active(
    monkeypatch,
):
    _patch_config(monkeypatch, "alpha", "bravo", "charlie")
    manager = MultiAgentManager(max_active_agents=2, idle_ttl_seconds=0)

    alpha = await manager.get_agent("alpha")
    bravo = await manager.get_agent("bravo")
    alpha.task_tracker.active_tasks = ["run-alpha"]
    bravo.task_tracker.active_tasks = ["run-bravo"]

    with pytest.raises(ConfigurationException):
        await manager.get_agent("charlie")

    assert set(manager.list_loaded_agents()) == {"alpha", "bravo"}
    assert FakeWorkspace.stopped_agents == []
