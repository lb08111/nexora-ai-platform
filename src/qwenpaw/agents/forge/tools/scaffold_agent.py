# -*- coding: utf-8 -*-
"""Scaffold a single ReActAgent inside an existing or new package.

Outputs a Python module that mirrors the style of ``DiscoveryAgent``:

- module-level ``SYSTEM_PROMPT`` constant;
- class ``<Name>Agent(ReActAgent)`` with ``role`` attribute;
- function ``build_<snake_name>()`` that returns a configured instance.
"""

from __future__ import annotations

from qwenpaw.agents.br_team.tools._utils import json_response, text_response

from .._paths import slugify, write_files

__all__ = ["scaffold_agent"]


_AGENT_TEMPLATE = '''\
# -*- coding: utf-8 -*-
"""{class_name} — gerado pelo AgentForge."""

from __future__ import annotations

import logging
from typing import Callable, Iterable

from agentscope.agent import ReActAgent
from agentscope.memory import InMemoryMemory
from agentscope.tool import Toolkit

from .model_factory import create_model_and_formatter

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """{system_prompt}"""


class {class_name}(ReActAgent):
    """{description}"""

    role: str = "{role}"


def build_{snake_name}(
    name: str = "{class_name}",
    extra_tools: Iterable[Callable] | None = None,
    max_iters: int = {max_iters},
) -> {class_name}:
    """Construa uma instância configurada de :class:`{class_name}`."""
    model, formatter = create_model_and_formatter()
    innermost = model
    while hasattr(innermost, "_inner"):
        innermost = innermost._inner
    while hasattr(innermost, "_model"):
        innermost = innermost._model
    if formatter is not None and hasattr(innermost, "formatter"):
        innermost.formatter = formatter

    tool_funcs: list[Callable] = list(extra_tools or [])
    toolkit = Toolkit(tools=tool_funcs) if tool_funcs else Toolkit()

    return {class_name}(
        name=name,
        sys_prompt=SYSTEM_PROMPT,
        model=model,
        tools=toolkit.tools,
        memory=InMemoryMemory(),
        max_iters=max_iters,
    )
'''


async def scaffold_agent(
    name: str,
    role: str,
    description: str,
    system_prompt: str,
    target_dir: str = "src/qwenpaw/agents",
    max_iters: int = 12,
    dry_run: bool = True,
):
    """Create a single ReActAgent module.

    Args:
        name: Display name (used to derive class + filenames).
        role: Short role keyword (e.g. ``"reembolso"``).
        description: Docstring of the class.
        system_prompt: pt-BR persona for the agent.
        target_dir: Folder under which ``<snake>_agent.py`` is created.
        max_iters: Default ReAct loop ceiling.
        dry_run: If True, returns plan only.
    """
    if not name.strip():
        return text_response("ERROR: name vazio")
    if not system_prompt.strip():
        return text_response("ERROR: system_prompt vazio")

    snake = slugify(name, separator="_")
    class_name = "".join(part.capitalize() for part in snake.split("_"))
    if not class_name.endswith("Agent"):
        class_name = f"{class_name}Agent"

    file_path = f"{target_dir.rstrip('/')}/{snake}_agent.py"
    content = _AGENT_TEMPLATE.format(
        class_name=class_name,
        description=description.strip() or f"Agente {name}.",
        role=slugify(role),
        snake_name=snake,
        system_prompt=system_prompt.replace('"""', '\\"\\"\\"'),
        max_iters=max_iters,
    )

    plan = [{"path": file_path, "content": content}]
    payload: dict = {
        "kind": "agent",
        "class_name": class_name,
        "module": snake,
        "files": [
            {"path": entry["path"], "bytes": len(entry["content"])}
            for entry in plan
        ],
        "dry_run": dry_run,
    }
    if not dry_run:
        payload["written"] = write_files(plan)
    return json_response(payload)
