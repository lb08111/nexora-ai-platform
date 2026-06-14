# -*- coding: utf-8 -*-
"""Inspect the repository to surface existing skills/agents/plugins.

Read-only. The AgentForge should call this BEFORE scaffolding to
avoid duplicating a slug.
"""

from __future__ import annotations

from pathlib import Path

from jotaduo.agents.br_team.tools._utils import json_response

from .._paths import REPO_ROOT

__all__ = ["inspect_repo"]


async def inspect_repo(area: str = "all") -> dict:
    """List things that already exist.

    Args:
        area: ``"skills"``, ``"agents"``, ``"plugins"``, ``"teams"``
            or ``"all"`` (default).
    """
    valid = {"skills", "agents", "plugins", "teams", "all"}
    if area not in valid:
        return json_response({"error": f"area inválida: {area}"})

    out: dict[str, list[str]] = {}
    if area in ("skills", "all"):
        out["skills"] = _list_skills()
    if area in ("agents", "all"):
        out["agents"] = _list_agent_packages()
    if area in ("plugins", "all"):
        out["plugins"] = _list_plugins()
    if area in ("teams", "all"):
        out["teams"] = _list_teams()
    return json_response(out)


def _list_skills() -> list[str]:
    root = REPO_ROOT / "src" / "jotaduo" / "agents" / "skills"
    if not root.exists():
        return []
    return sorted(
        p.name
        for p in root.iterdir()
        if p.is_dir() and (p / "SKILL.md").exists()
    )


def _list_agent_packages() -> list[str]:
    root = REPO_ROOT / "src" / "jotaduo" / "agents"
    if not root.exists():
        return []
    skip = {"skills", "__pycache__", "tools", "skill_system"}
    return sorted(
        p.name for p in root.iterdir() if p.is_dir() and p.name not in skip
    )


def _list_plugins() -> list[str]:
    root = REPO_ROOT / "plugins" / "bundle"
    if not root.exists():
        return []
    return sorted(
        p.name
        for p in root.iterdir()
        if p.is_dir() and (p / "plugin.json").exists()
    )


def _list_teams() -> list[str]:
    """A 'team' here is an agent package that has a prompts.py."""
    root = REPO_ROOT / "src" / "jotaduo" / "agents"
    if not root.exists():
        return []
    teams: list[str] = []
    for p in root.iterdir():
        if not p.is_dir() or p.name == "skills":
            continue
        if (p / "prompts.py").exists():
            teams.append(p.name)
    return sorted(teams)
