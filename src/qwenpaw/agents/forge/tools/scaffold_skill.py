# -*- coding: utf-8 -*-
"""Scaffold a SKILL.md in the repo-standard format.

A skill is a folder under ``src/qwenpaw/agents/skills/<kebab-name>/``
containing a single ``SKILL.md`` with YAML frontmatter.
"""

from __future__ import annotations

from qwenpaw.agents.br_team.tools._utils import json_response, text_response

from .._paths import kebab, write_files

__all__ = ["scaffold_skill"]


_TEMPLATE = """\
---
name: {name}
description: |
{description_indented}
when_to_use: |
{when_indented}
metadata:
  builtin_skill_version: "1.0"
  qwenpaw:
    emoji: "{emoji}"
    requires: {{}}
---

# Habilidade: {title}

{body}
"""


async def scaffold_skill(
    name: str,
    description: str,
    when_to_use: str = "",
    emoji: str = "🛠️",
    body_markdown: str = "",
    target_dir: str = "src/qwenpaw/agents/skills",
    dry_run: bool = True,
):
    """Create a new skill.

    Args:
        name: Human-readable name. Folder slug derives from it.
        description: Single-paragraph description shown to the agent.
        when_to_use: Multi-line guidance for when the skill triggers.
        emoji: Single emoji used in the UI.
        body_markdown: Free Markdown body appended after the frontmatter.
        target_dir: Parent directory (relative to repo root).
        dry_run: If True (default), returns the plan WITHOUT writing.

    Returns:
        ToolResponse with the file plan and write status.
    """
    if not name.strip():
        return text_response("ERROR: name vazio")
    if not description.strip():
        return text_response("ERROR: description vazio")

    slug = kebab(name)
    folder = f"{target_dir.rstrip('/')}/{slug}"
    skill_md_path = f"{folder}/SKILL.md"

    content = _TEMPLATE.format(
        name=slug,
        description_indented=_indent(description.strip(), 2),
        when_indented=_indent(
            (when_to_use or "Sem critérios específicos.").strip(),
            2,
        ),
        emoji=emoji,
        title=name.strip(),
        body=body_markdown.strip()
        or "Descreva aqui o passo a passo da habilidade.",
    )

    plan = [{"path": skill_md_path, "content": content}]
    payload: dict = {
        "kind": "skill",
        "slug": slug,
        "folder": folder,
        "files": [
            {"path": entry["path"], "bytes": len(entry["content"])}
            for entry in plan
        ],
        "dry_run": dry_run,
    }
    if not dry_run:
        payload["written"] = write_files(plan)
    return json_response(payload)


def _indent(text: str, n: int) -> str:
    pad = " " * n
    return "\n".join(f"{pad}{line}" if line else line
                     for line in text.splitlines())
