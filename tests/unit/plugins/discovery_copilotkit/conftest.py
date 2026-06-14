# -*- coding: utf-8 -*-
"""Pytest config for the discovery-copilotkit plugin tests.

Adds the plugin root to ``sys.path`` so tests can import the plugin's
flat modules (``copilotkit_adapter``, ``router``, ``eval_session``)
without depending on the platform plugin loader (which is what
production uses to load ``plugin.py``).
"""
from __future__ import annotations

import sys
from pathlib import Path

_PLUGIN_ROOT = (
    Path(__file__).resolve().parents[4]
    / "plugins"
    / "bundle"
    / "discovery-copilotkit"
)

if str(_PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(_PLUGIN_ROOT))
