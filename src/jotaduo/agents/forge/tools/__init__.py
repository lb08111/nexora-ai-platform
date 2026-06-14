# -*- coding: utf-8 -*-
"""Scaffolding tools used by the AgentForge ReActAgent."""

from .inspect_repo import inspect_repo
from .scaffold_agent import scaffold_agent
from .scaffold_plugin import scaffold_plugin
from .scaffold_skill import scaffold_skill
from .scaffold_team import scaffold_team

__all__ = [
    "inspect_repo",
    "scaffold_skill",
    "scaffold_agent",
    "scaffold_team",
    "scaffold_plugin",
    "FORGE_TOOLS",
]

FORGE_TOOLS = [
    inspect_repo,
    scaffold_skill,
    scaffold_agent,
    scaffold_team,
    scaffold_plugin,
]
