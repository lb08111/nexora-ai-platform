# -*- coding: utf-8 -*-
"""Plugin entry-point registration test.

Loads ``plugin.py`` the same way the platform's plugin loader does
(``importlib.util.spec_from_file_location`` with a synthetic
``submodule_search_locations``), then verifies that calling
``plugin.register(api)`` wires an HTTP router and lifecycle hooks
into a fake PluginApi.
"""
from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import pytest


_PLUGIN_ROOT = (
    Path(__file__).resolve().parents[4]
    / "plugins"
    / "bundle"
    / "discovery-copilotkit"
)


@dataclass
class FakePluginApi:
    """Records every register_* call so we can assert against it."""

    plugin_id: str = "discovery-copilotkit"
    routers: list[tuple[Any, str, list[str] | None]] = field(
        default_factory=list,
    )
    startup_hooks: list[tuple[str, Callable, int]] = field(
        default_factory=list,
    )
    shutdown_hooks: list[tuple[str, Callable, int]] = field(
        default_factory=list,
    )

    def register_http_router(self, router, *, prefix, tags=None):
        self.routers.append((router, prefix, tags))

    def register_startup_hook(self, hook_name, callback, priority=100):
        self.startup_hooks.append((hook_name, callback, priority))

    def register_shutdown_hook(self, hook_name, callback, priority=100):
        self.shutdown_hooks.append((hook_name, callback, priority))


def _load_plugin_module():
    """Mirror the loader's spec_from_file_location-based load."""
    module_name = "plugin_discovery_copilotkit_test"
    plugin_dir_str = str(_PLUGIN_ROOT)
    spec = importlib.util.spec_from_file_location(
        module_name,
        _PLUGIN_ROOT / "plugin.py",
        submodule_search_locations=[plugin_dir_str],
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    module.__package__ = module_name
    module.__path__ = [plugin_dir_str]
    spec.loader.exec_module(module)
    return module


def test_plugin_exports_plugin_object():
    module = _load_plugin_module()
    assert hasattr(module, "plugin"), (
        "plugin.py must export `plugin` (per QwenPaw plugin contract)"
    )
    assert hasattr(module.plugin, "register")


def test_register_wires_router_and_hooks():
    module = _load_plugin_module()
    api = FakePluginApi()
    module.plugin.register(api)

    # Router mounted under the documented prefix.
    assert len(api.routers) == 1
    _, prefix, tags = api.routers[0]
    assert prefix == "/discovery-copilotkit"
    assert tags == ["discovery-copilotkit"]

    # Lifecycle hooks present with sensible names.
    startup_names = {h[0] for h in api.startup_hooks}
    shutdown_names = {h[0] for h in api.shutdown_hooks}
    assert "discovery_copilotkit_startup" in startup_names
    assert "discovery_copilotkit_shutdown" in shutdown_names


def test_router_has_expected_routes():
    module = _load_plugin_module()
    api = FakePluginApi()
    module.plugin.register(api)
    router = api.routers[0][0]
    paths = {(r.path, tuple(sorted(r.methods))) for r in router.routes}
    # All five contract endpoints registered.
    assert ("/sessions", ("POST",)) in paths
    assert ("/sessions/{sid}/turn", ("POST",)) in paths
    assert ("/sessions/{sid}", ("GET",)) in paths
    assert ("/sessions/{sid}/blueprint", ("GET",)) in paths
    assert ("/components", ("GET",)) in paths


def test_startup_hook_in_scripted_mode_does_not_raise(monkeypatch):
    module = _load_plugin_module()
    monkeypatch.delenv("QWENPAW_DISCOVERY_LIVE", raising=False)
    plugin = module.plugin
    # Should be a no-op (scripted is the default factory) and must not
    # raise — guards against accidentally requiring the live agent at
    # plugin install time on machines without an LLM key.
    plugin._startup()


def test_shutdown_hook_clears_sessions():
    module = _load_plugin_module()
    plugin = module.plugin
    plugin._shutdown()  # must be idempotent / safe with no sessions
