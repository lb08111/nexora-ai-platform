# -*- coding: utf-8 -*-
"""Scaffold a team package modelled after ``br_team``.

Generates the minimal skeleton (``__init__.py``, ``prompts.py``,
``factory.py``, ``specialists/base.py``) so the team is immediately
runnable — the user then fills in concrete tools.
"""

from __future__ import annotations

from qwenpaw.agents.br_team.tools._utils import json_response, text_response

from .._paths import slugify, write_files

__all__ = ["scaffold_team"]


_INIT = '''\
# -*- coding: utf-8 -*-
"""{title} team — gerado pelo AgentForge."""

from __future__ import annotations

__all__ = ["{registry_name}", "build_team"]


def __getattr__(name):  # pragma: no cover
    if name == "{registry_name}":
        from .factory import {registry_name}

        return {registry_name}
    if name == "build_team":
        from .factory import build_team

        return build_team
    raise AttributeError(name)
'''

_PROMPTS = '''\
# -*- coding: utf-8 -*-
"""System prompts for the {title} team."""

PROMPTS_BY_ROLE: dict[str, str] = {{
{role_entries}
}}
'''

_FACTORY = '''\
# -*- coding: utf-8 -*-
"""Factory that materialises {title} specialists."""

from __future__ import annotations

from typing import Callable

from .prompts import PROMPTS_BY_ROLE
from .specialists.base import build_specialist

{registry_name}: dict[str, Callable] = {{
    role: (lambda name=None, r=role: build_specialist(r, name))
    for role in PROMPTS_BY_ROLE
}}


def build_team(roles: list[str] | None = None) -> list:
    """Build a list of specialists for the requested roles."""
    chosen = roles or list(PROMPTS_BY_ROLE)
    return [
        {registry_name}[role]()
        for role in chosen
        if role in {registry_name}
    ]
'''

_SPECIALIST_INIT = '''\
# -*- coding: utf-8 -*-
"""Specialists for the {title} team."""

from .base import build_specialist  # noqa: F401
'''

_SPECIALIST_BASE = '''\
# -*- coding: utf-8 -*-
"""Generic specialist for the {title} team."""

from __future__ import annotations

from typing import Callable, Iterable

from agentscope.agent import ReActAgent
from agentscope.memory import InMemoryMemory
from agentscope.tool import Toolkit

from ...model_factory import create_model_and_formatter
from ..prompts import PROMPTS_BY_ROLE


class TeamSpecialistAgent(ReActAgent):
    """Generic role-based specialist for {title}."""

    role: str


def build_specialist(
    role: str,
    name: str | None = None,
    extra_tools: Iterable[Callable] | None = None,
    max_iters: int = 8,
) -> TeamSpecialistAgent:
    if role not in PROMPTS_BY_ROLE:
        raise ValueError(
            f"role desconhecido: {{role!r}}. "
            f"Válidos: {{sorted(PROMPTS_BY_ROLE)}}",
        )

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

    agent = TeamSpecialistAgent(
        name=name or f"{title_slug}_{{role}}",
        sys_prompt=PROMPTS_BY_ROLE[role],
        model=model,
        tools=toolkit.tools,
        memory=InMemoryMemory(),
        max_iters=max_iters,
    )
    agent.role = role
    return agent
'''


async def scaffold_team(
    name: str,
    roles: list[str],
    default_prompt_prefix: str = "Você é um especialista do time.",
    target_dir: str = "src/qwenpaw/agents",
    dry_run: bool = True,
):
    """Generate a new team package.

    Args:
        name: Team name (e.g. ``"saude_team"``). Folder slug derives.
        roles: List of role keywords (e.g. ``["recepcao","triagem"]``).
        default_prompt_prefix: Prefix used to stub the system prompts.
        target_dir: Parent under which the package is created.
        dry_run: If True, returns plan only.
    """
    if not name.strip():
        return text_response("ERROR: name vazio")
    if not roles:
        return text_response("ERROR: lista de roles vazia")

    slug = slugify(name)
    title = name.strip().replace("_", " ").title()
    registry_name = f"{slug.upper()}_REGISTRY"
    folder = f"{target_dir.rstrip('/')}/{slug}"

    prompt_entries = "\n".join(
        f'    "{slugify(role)}": (\n'
        f'        "{default_prompt_prefix} "\n'
        f'        "Você atua como {role}. "\n'
        f'        "Responda em português do Brasil."\n'
        f'    ),'
        for role in roles
    )

    plan = [
        {
            "path": f"{folder}/__init__.py",
            "content": _INIT.format(
                title=title,
                registry_name=registry_name,
            ),
        },
        {
            "path": f"{folder}/prompts.py",
            "content": _PROMPTS.format(
                title=title,
                role_entries=prompt_entries,
            ),
        },
        {
            "path": f"{folder}/factory.py",
            "content": _FACTORY.format(
                title=title,
                registry_name=registry_name,
            ),
        },
        {
            "path": f"{folder}/specialists/__init__.py",
            "content": _SPECIALIST_INIT.format(title=title),
        },
        {
            "path": f"{folder}/specialists/base.py",
            "content": _SPECIALIST_BASE.format(
                title=title,
                title_slug=slug,
            ),
        },
    ]

    payload: dict = {
        "kind": "team",
        "slug": slug,
        "folder": folder,
        "roles": [slugify(r) for r in roles],
        "files": [
            {"path": entry["path"], "bytes": len(entry["content"])}
            for entry in plan
        ],
        "dry_run": dry_run,
    }
    if not dry_run:
        payload["written"] = write_files(plan)
    return json_response(payload)
