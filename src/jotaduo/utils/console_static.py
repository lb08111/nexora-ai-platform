# -*- coding: utf-8 -*-
"""Resolve the web console static assets directory (shared by app and CLI)."""
from __future__ import annotations

import os
from pathlib import Path

from ..constant import EnvVarLoader

# Primary env key (``COPAW_CONSOLE_STATIC_DIR`` is accepted as a legacy
# fallback via :class:`~jotaduo.constant.EnvVarLoader`).
CONSOLE_STATIC_ENV = "JOTADUO_CONSOLE_STATIC_DIR"


def resolve_console_static_dir() -> str:
    """Return the directory expected to contain ``index.html`` for the console.

    Resolution order matches :mod:`jotaduo.app._app`: env override, package
    ``jotaduo/console``, repo ``console/dist``, then cwd fallbacks.
    """
    static_dir = EnvVarLoader.get_str("JOTADUO_CONSOLE_STATIC_DIR")
    if static_dir:
        return static_dir

    pkg_dir = Path(__file__).resolve().parent.parent
    candidate = pkg_dir / "console"
    if candidate.is_dir() and (candidate / "index.html").is_file():
        return str(candidate)

    repo_dir = pkg_dir.parent.parent
    candidate = repo_dir / "console" / "dist"
    if candidate.is_dir() and (candidate / "index.html").is_file():
        return str(candidate)

    cwd = Path(os.getcwd())
    for subdir in ("console/dist", "console_dist"):
        candidate = cwd / subdir
        if candidate.is_dir() and (candidate / "index.html").is_file():
            return str(candidate)

    return str(cwd / "console" / "dist")


def find_jotaduo_source_repo_root() -> Path | None:
    """Return the git checkout root if this Python
    is running from JotaDuo source.

    Looks upward from :mod:`jotaduo` for ``console/package.json``,
    ``console/package-lock.json``, and ``src/jotaduo/``
    (bundled static target).
    Returns ``None`` for a normal pip/wheel install.
    """
    try:
        import jotaduo  # noqa: PLC0415 — avoid import cycle at module load
    except Exception:  # pylint: disable=broad-exception-caught
        return None
    cur = Path(jotaduo.__file__).resolve().parent
    for _ in range(20):
        con = cur / "console"
        if (
            (con / "package.json").is_file()
            and (con / "package-lock.json").is_file()
            and (cur / "src" / "jotaduo").is_dir()
        ):
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return None
