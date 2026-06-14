# -*- coding: utf-8 -*-
"""Nexora Fiscal Plugin for QwenPaw/Nexora AI Platform."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger("qwenpaw").getChild("plugin.nexora-fiscal")


def _init_plugin_path() -> None:
    plugin_dir = str(Path(__file__).parent)
    if plugin_dir not in sys.path:
        sys.path.insert(0, plugin_dir)


def _ensure_default_env_vars() -> None:
    """Expose fiscal env keys in the Console with safe defaults."""
    from .constants import DEFAULT_ENV_KEYS, DEFAULT_ENV_VALUES

    try:
        from qwenpaw.envs import load_envs, save_envs
    except ImportError:
        logger.warning("Cannot import qwenpaw.envs; env provisioning skipped")
        return

    envs = load_envs()
    changed = False
    for key in DEFAULT_ENV_KEYS:
        if key not in envs:
            fallback = DEFAULT_ENV_VALUES.get(key, "")
            envs[key] = os.environ.get(key, fallback)
            changed = True
    if changed:
        save_envs(envs)
        logger.info("Provisioned default env keys: %s", list(DEFAULT_ENV_KEYS))


def _register_fiscal_tools(api: Any | None = None) -> None:
    """Register fiscal tools with PluginApi and the builtin registry."""
    from .constants import FISCAL_TOOL_CONFIGS, FISCAL_TOOL_NAMES
    from .tools import fiscal_tools

    register_api = getattr(api, "register_tool", None) if api else None
    for tool_name in FISCAL_TOOL_NAMES:
        tool_func = getattr(fiscal_tools, tool_name)
        spec = FISCAL_TOOL_CONFIGS[tool_name]
        if callable(register_api):
            try:
                register_api(
                    tool_name=tool_name,
                    tool_func=tool_func,
                    description=spec["description"],
                    icon=spec.get("icon", "🧾"),
                )
                logger.info("Registered fiscal tool via PluginApi: %s", tool_name)
            except Exception as exc:  # pylint: disable=broad-except
                logger.warning("PluginApi tool registration failed: %s", exc)

    try:
        from qwenpaw.agents.tools import registry as tool_registry
    except ImportError:
        logger.debug("tool registry unavailable; PluginApi registration only")
        return

    register = getattr(tool_registry, "register_tool", None)
    if not callable(register):
        return
    for tool_name in FISCAL_TOOL_NAMES:
        try:
            register(tool_name, getattr(fiscal_tools, tool_name))
            logger.info("Registered fiscal tool in registry: %s", tool_name)
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Registry tool registration failed for %s: %s", tool_name, exc)


def _patch_plugin_loader_unload() -> None:
    """Hook into PluginLoader to run cleanup on uninstall."""
    try:
        from qwenpaw.plugins.loader import PluginLoader
    except ImportError:
        logger.warning("PluginLoader unavailable; uninstall cleanup disabled")
        return

    if getattr(PluginLoader, "_nexora_fiscal_patched", False):
        return

    _original = PluginLoader.unload_plugin

    async def _patched(
        self,
        plugin_id: str,
        delete_files: bool = False,
    ) -> None:
        if plugin_id == "nexora-fiscal":
            logger.info("[nexora-fiscal] uninstall detected, cleaning up...")
            try:
                from .agents_setup import uninstall_agents

                uninstall_agents()
            except Exception as exc:  # pylint: disable=broad-except
                logger.warning("[nexora-fiscal] cleanup failed: %s", exc)
        return await _original(self, plugin_id, delete_files)

    PluginLoader.unload_plugin = _patched
    PluginLoader._nexora_fiscal_patched = True
    logger.info("[nexora-fiscal] patched PluginLoader.unload_plugin")


class NexoraFiscalPlugin:
    """Nexora Fiscal plugin entry point."""

    def __init__(self) -> None:
        self._api: Any | None = None

    def register(self, api: Any) -> None:
        logger.info("NexoraFiscalPlugin.register() called")
        self._api = api
        _init_plugin_path()

        try:
            from .routers_setup import build_plugin_routers

            for router, prefix in build_plugin_routers():
                logger.info(
                    "[nexora-fiscal] registering router at /api%s",
                    prefix,
                )
                api.register_http_router(router, prefix=prefix)
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning(
                "Failed to register HTTP routers: %s",
                exc,
                exc_info=True,
            )

        api.register_startup_hook(
            hook_name="nexora_fiscal_init",
            callback=self._on_startup,
            priority=50,
        )
        api.register_shutdown_hook(
            hook_name="nexora_fiscal_shutdown",
            callback=self._on_shutdown,
            priority=50,
        )

        _patch_plugin_loader_unload()
        logger.info("[nexora-fiscal] hooks registered")

    async def _on_startup(self) -> None:
        from .agents_setup import ensure_builtin_agents

        logger.info("[nexora-fiscal] starting up...")
        _ensure_default_env_vars()
        ensure_builtin_agents()
        _register_fiscal_tools(self._api)
        logger.info("[nexora-fiscal] startup complete")

    async def _on_shutdown(self) -> None:
        logger.info("[nexora-fiscal] shutting down")


plugin = NexoraFiscalPlugin()
