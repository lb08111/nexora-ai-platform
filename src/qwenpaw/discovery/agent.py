# -*- coding: utf-8 -*-
"""Fábrica do discovery agent (AgentScope ``ReActAgent``).

``build_discovery_agent`` monta um ``ReActAgent`` com o toolkit da
``InterviewSession`` e o modelo ativo do workspace.
"""

from __future__ import annotations

from agentscope.agent import ReActAgent
from agentscope.memory import InMemoryMemory

from ..agents.model_factory import create_model_and_formatter
from .prompts import build_discovery_system_prompt
from .tools import InterviewSession


def build_discovery_agent(
    session: InterviewSession,
    max_iters: int = 6,
) -> ReActAgent:
    """Monta o ``ReActAgent`` de discovery com o toolkit da sessão e o modelo ativo.

    Args:
        session: A ``InterviewSession`` que detém o estado e expõe as tools
            ``segment_lookup`` / ``reflect`` / ``emit_blueprint``.
        max_iters: Tetos de iterações do laço ReAct por turno.

    Returns:
        Um ``agentscope.agent.ReActAgent`` pronto para ``reply()``.
    """
    model, formatter = create_model_and_formatter()
    # Mesmo attach de formatter feito pelo QwenPawAgent (react_agent.py):
    # encontra o modelo mais interno e sobrescreve o formatter padrão.
    if formatter is not None:
        innermost = model
        while hasattr(innermost, "_inner"):
            innermost = innermost._inner
        while hasattr(innermost, "_model"):
            innermost = innermost._model
        if hasattr(innermost, "formatter"):
            innermost.formatter = formatter

    agent = ReActAgent(
        name="DiscoveryAgent",
        sys_prompt=build_discovery_system_prompt(),
        model=model,
        tools=session.build_toolkit().tools,
        memory=InMemoryMemory(),
        max_iters=max_iters,
    )

    return agent
