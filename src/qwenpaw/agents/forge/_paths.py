# -*- coding: utf-8 -*-
"""Path guards and filename helpers for the AgentForge.

Every scaffolding tool MUST route its writes through :func:`safe_join`
so users can never escape the repository root with ``..`` or absolute
paths. ``REPO_ROOT`` is resolved relative to this file so it works
both in dev and inside packaged installs.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

# src/qwenpaw/agents/forge/_paths.py → repo root is parents[4]
REPO_ROOT = Path(__file__).resolve().parents[4]

# Allowed write roots. Anything outside these is rejected.
ALLOWED_ROOTS: tuple[Path, ...] = (
    REPO_ROOT / "src" / "qwenpaw" / "agents",
    REPO_ROOT / "src" / "qwenpaw" / "agents" / "skills",
    REPO_ROOT / "plugins" / "bundle",
    REPO_ROOT / "tests" / "unit" / "agents",
    REPO_ROOT / "tests" / "unit" / "plugins",
)


class PathGuardError(ValueError):
    """Raised when a scaffolding target escapes the allowed roots."""


def safe_join(rel_path: str | Path) -> Path:
    """Resolve ``rel_path`` against REPO_ROOT and validate the result.

    Args:
        rel_path: A path expressed relative to the repo root (e.g.
            ``"plugins/bundle/foo"`` or ``"src/qwenpaw/agents/foo"``).

    Returns:
        Absolute :class:`Path` guaranteed to live under one of the
        :data:`ALLOWED_ROOTS`.

    Raises:
        PathGuardError: if the resolved path escapes the allowed roots
            or if the caller passed an absolute path.
    """
    p = Path(rel_path)
    if p.is_absolute():
        raise PathGuardError(
            f"absolute paths are forbidden: {rel_path!r}",
        )
    resolved = (REPO_ROOT / p).resolve()
    for root in ALLOWED_ROOTS:
        try:
            resolved.relative_to(root)
            return resolved
        except ValueError:
            continue
    raise PathGuardError(
        f"target {resolved} is outside the allowed roots "
        f"({[str(r.relative_to(REPO_ROOT)) for r in ALLOWED_ROOTS]})",
    )


def slugify(text: str, *, separator: str = "_") -> str:
    """Slugify ``text`` to snake_case (or kebab-case if separator='-').

    Removes accents, lowercases, collapses non-alnum to the separator.
    """
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKD", text)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    lowered = ascii_only.lower().strip()
    cleaned = re.sub(r"[^a-z0-9]+", separator, lowered)
    return cleaned.strip(separator)


def kebab(text: str) -> str:
    """Slug with hyphen separator (good for skill/plugin folders)."""
    return slugify(text, separator="-")


def write_files(
    plan: list[dict],
    *,
    overwrite: bool = False,
) -> list[dict]:
    """Materialise a file plan returned by a scaffolder.

    Args:
        plan: List of ``{"path": <rel-path>, "content": <str>}`` dicts.
        overwrite: If False, refuses to clobber existing files.

    Returns:
        List with the same shape, augmented with ``"status"`` and
        ``"absolute_path"`` per entry.
    """
    out: list[dict] = []
    for entry in plan:
        rel = entry["path"]
        content = entry["content"]
        target = safe_join(rel)
        status = "written"
        if target.exists() and not overwrite:
            status = "skipped_exists"
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        out.append(
            {
                "path": rel,
                "absolute_path": str(target),
                "status": status,
                "bytes": len(content.encode("utf-8")),
            },
        )
    return out
