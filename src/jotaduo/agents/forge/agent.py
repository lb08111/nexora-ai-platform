# -*- coding: utf-8 -*-
"""The AgentForge ReActAgent — meta-agent that scaffolds code."""

from __future__ import annotations

import logging
from typing import Callable, Iterable

from agentscope.agent import ReActAgent
from agentscope.memory import InMemoryMemory
from agentscope.tool import Toolkit

from ..model_factory import create_model_and_formatter
from .prompts import AGENT_FORGE_PROMPT
from .tools import FORGE_TOOLS

logger = logging.getLogger(__name__)

__all__ = ["AgentForge", "build_agent_forge"]


class AgentForge(ReActAgent):
    """Meta-agente que cria agentes, times, skills e plugins."""

    role: str = "forge"


def _attach_formatter(model, formatter) -> None:
    if formatter is None:
        return
    innermost = model
    while hasattr(innermost, "_inner"):
        innermost = innermost._inner
    while hasattr(innermost, "_model"):
        innermost = innermost._model
    if hasattr(innermost, "formatter"):
        innermost.formatter = formatter


def build_agent_forge(
    name: str = "AgentForge",
    extra_tools: Iterable[Callable] | None = None,
    max_iters: int = 30,
) -> AgentForge:
    """Build a fresh AgentForge instance ready to ``reply()``."""
    model, formatter = create_model_and_formatter()
    _attach_formatter(model, formatter)

    tool_funcs: list[Callable] = list(FORGE_TOOLS)
    if extra_tools:
        tool_funcs.extend(extra_tools)
    toolkit = Toolkit(tools=tool_funcs)

    agent = AgentForge(
        name=name,
        sys_prompt=AGENT_FORGE_PROMPT,
        model=model,
        tools=toolkit.tools,
        memory=InMemoryMemory(),
        max_iters=max_iters,
    )
    return agent
