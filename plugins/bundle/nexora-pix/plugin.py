# -*- coding: utf-8 -*-
"""Nexora Pix Plugin for QwenPaw.

Registers the ``nexora-cobranca`` agent, exposes Pix billing tools,
and mounts HTTP routes for webhooks, health checks, and charge lookup.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger("qwenpaw").getChild("plugin.nexora-pix")


def _init_plugin_path() -> None:
    plugin_dir = str(Path(__file__).parent)
    if plugin_dir not in sys.path:
        sys.path.insert(0, plugin_dir)


def _ensure_default_env_vars() -> None:
    """Expose plugin-related env keys in the Console."""
    from .constants import DEFAULT_ENV_KEYS, DEFAULT_ENV_VALUES

    try:
        from qwenpaw.envs import load_envs, save_envs
    except ImportError:
        logger.warning(
            "Cannot import qwenpaw.envs; env provisioning skipped",
        )
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
        logger.info(
            "Provisioned default env keys: %s",
            list(DEFAULT_ENV_KEYS),
        )


def _register_pix_tools() -> None:
    """Expose Pix tools to the platform tool registry."""
    try:
        from qwenpaw.agents.tools import registry as tool_registry
    except ImportError:
        logger.debug(
            "tool registry not available; Pix tools remain importable only.",
        )
        return

    try:
        from .constants import PIX_TOOL_NAMES
        from .tools import pix_tools

        register = getattr(tool_registry, "register_tool", None)
        if not callable(register):
            return
        for name in PIX_TOOL_NAMES:
            register(name, getattr(pix_tools, name))
            logger.info("Registered tool: %s", name)
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("Pix tool registration failed: %s", exc)


def _patch_plugin_loader_unload() -> None:
    """Hook into PluginLoader to run cleanup on uninstall."""
    try:
        from qwenpaw.plugins.loader import PluginLoader
    except ImportError:
        logger.warning(
            "PluginLoader unavailable; uninstall cleanup disabled",
        )
        return

    if getattr(PluginLoader, "_nexora_pix_patched", False):
        return

    _original = PluginLoader.unload_plugin

    async def _patched(
        self,
        plugin_id: str,
        delete_files: bool = False,
    ) -> None:
        if plugin_id == "nexora-pix":
            logger.info("[nexora-pix] uninstall detected, cleaning up...")
            try:
                from .agents_setup import uninstall_agents

                uninstall_agents()
            except Exception as exc:  # pylint: disable=broad-except
                logger.warning(
                    "[nexora-pix] cleanup failed: %s",
                    exc,
                )
        return await _original(self, plugin_id, delete_files)

    PluginLoader.unload_plugin = _patched
    PluginLoader._nexora_pix_patched = True
    logger.info("[nexora-pix] patched PluginLoader.unload_plugin")


class NexoraPixPlugin:
    """Nexora Pix plugin entry point."""

    def register(self, api):
        logger.info("NexoraPixPlugin.register() called")
        _init_plugin_path()

        try:
            from .routers_setup import build_plugin_routers

            for router, prefix in build_plugin_routers():
                logger.info(
                    "[nexora-pix] registering router at /api%s",
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
            hook_name="nexora_pix_init",
            callback=self._on_startup,
            priority=50,
        )
        api.register_shutdown_hook(
            hook_name="nexora_pix_shutdown",
            callback=self._on_shutdown,
            priority=50,
        )

        _patch_plugin_loader_unload()
        logger.info("[nexora-pix] hooks registered")

    async def _on_startup(self):
        from .agents_setup import ensure_builtin_agents
        from .store.db import init_db

        logger.info("[nexora-pix] starting up...")
        _ensure_default_env_vars()
        await init_db()
        ensure_builtin_agents()
        _register_pix_tools()
        logger.info("[nexora-pix] startup complete")

    async def _on_shutdown(self):
        logger.info("[nexora-pix] shutting down")
