# -*- coding: utf-8 -*-
"""Smoke test: AgentForge package imports cleanly + tool list intact."""

from jotaduo.agents.forge import FORGE_TOOLS


def test_forge_tools_loaded():
    names = {fn.__name__ for fn in FORGE_TOOLS}
    assert names == {
        "inspect_repo",
        "scaffold_skill",
        "scaffold_agent",
        "scaffold_team",
        "scaffold_plugin",
    }


def test_forge_class_is_lazy_importable():
    from jotaduo.agents.forge import AgentForge, build_agent_forge

    assert AgentForge.__name__ == "AgentForge"
    assert callable(build_agent_forge)
