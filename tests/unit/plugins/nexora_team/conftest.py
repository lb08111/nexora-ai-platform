# -*- coding: utf-8 -*-
"""Conftest: ensure the plugin directory is importable."""

# flake8: noqa: E402
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[4]
_PLUGIN_PARENT = _REPO_ROOT / "plugins" / "bundle"

if str(_PLUGIN_PARENT) not in sys.path:
    sys.path.insert(0, str(_PLUGIN_PARENT))

# The plugin directory uses a dash in its name; expose it under an
# importable alias for tests.
import importlib
import importlib.util
import types


def _ensure_alias():
    target = _PLUGIN_PARENT / "nexora-team"
    if not target.exists():
        return
    if "nexora_team_plugin" in sys.modules:
        return
    init_path = target / "__init__.py"
    spec = importlib.util.spec_from_file_location(
        "nexora_team_plugin",
        init_path,
        submodule_search_locations=[str(target)],
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["nexora_team_plugin"] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)


_ensure_alias()


@pytest.fixture(autouse=True)
def _reset_store():
    from nexora_team_plugin.store import get_meeting_store  # noqa: E402

    get_meeting_store().clear()
    yield
    get_meeting_store().clear()
