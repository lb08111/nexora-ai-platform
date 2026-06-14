# -*- coding: utf-8 -*-
"""AgentForge — meta-agente que cria agentes, times, skills e plugins.

API pública (lazy):

* :class:`AgentForge` — ``ReActAgent`` especialista em scaffolding.
* :func:`build_agent_forge` — fábrica padrão.
* :data:`FORGE_TOOLS` — funções de scaffolding (também usáveis fora do
  loop ReAct, por exemplo em testes ou CLI).
"""

from __future__ import annotations

__all__ = [
    "AgentForge",
    "build_agent_forge",
    "FORGE_TOOLS",
]


def __getattr__(name):  # pragma: no cover - lazy import
    if name in ("AgentForge", "build_agent_forge"):
        from .agent import AgentForge, build_agent_forge

        return {
            "AgentForge": AgentForge,
            "build_agent_forge": build_agent_forge,
        }[name]
    if name == "FORGE_TOOLS":
        from .tools import FORGE_TOOLS

        return FORGE_TOOLS
    raise AttributeError(name)
