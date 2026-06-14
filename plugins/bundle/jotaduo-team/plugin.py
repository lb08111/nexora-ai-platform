# -*- coding: utf-8 -*-
"""Jotaduo Team Plugin for JotaDuo.

Registers the Brazilian specialist team (orchestrator + 4 specialists),
ships the ``jotaduo-meeting`` skill, exposes HTTP endpoints, and
publishes the ``convene_meeting`` tool to the orchestrator.

See ``README.md`` for the install/uninstall lifecycle.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger("jotaduo").getChild("plugin.jotaduo-team")


def _init_plugin_path() -> None:
    plugin_dir = str(Path(__file__).parent)
    if plugin_dir not in sys.path:
        sys.path.insert(0, plugin_dir)


def _ensure_default_env_vars() -> None:
    """Expose plugin-related env keys in the Console."""
    from .constants import DEFAULT_ENV_KEYS, DEFAULT_ENV_VALUES

    try:
        from jotaduo.envs import load_envs, save_envs
    except ImportError:
        logger.warning(
            "Cannot import jotaduo.envs; env provisioning skipped",
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


def _register_convene_meeting_tool() -> None:
    """Expose ``convene_meeting`` so the orchestrator can call it."""
    try:
        from jotaduo.agents.tools import registry as tool_registry
    except ImportError:
        logger.debug(
            "tool registry not available; convene_meeting will be "
            "called directly via async route only.",
        )
        return

    try:
        from .tools.meeting_tools import convene_meeting

        register = getattr(tool_registry, "register_tool", None)
        if callable(register):
            register("convene_meeting", convene_meeting)
            logger.info("Registered tool: convene_meeting")
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("convene_meeting registration failed: %s", exc)


def _patch_plugin_loader_unload() -> None:
    """Hook into PluginLoader to run cleanup on uninstall."""
    try:
        from jotaduo.plugins.loader import PluginLoader
    except ImportError:
        logger.warning(
            "PluginLoader unavailable; uninstall cleanup disabled",
        )
        return

    if getattr(PluginLoader, "_jotaduo_team_patched", False):
        return

    _original = PluginLoader.unload_plugin

    async def _patched(
        self,
        plugin_id: str,
        delete_files: bool = False,
    ) -> None:
        if plugin_id == "jotaduo-team":
            logger.info("[jotaduo-team] uninstall detected, cleaning up...")
            try:
                from .agents_setup import uninstall_agents

                uninstall_agents()
            except Exception as exc:  # pylint: disable=broad-except
                logger.warning(
                    "[jotaduo-team] cleanup failed: %s",
                    exc,
                )
        return await _original(self, plugin_id, delete_files)

    PluginLoader.unload_plugin = _patched
    PluginLoader._jotaduo_team_patched = True
    logger.info("[jotaduo-team] patched PluginLoader.unload_plugin")


# ----------------------------------------------------------------------
# Plugin entry class
# ----------------------------------------------------------------------


class JotaduoTeamPlugin:
    """Jotaduo Team plugin entry point."""

    def register(self, api):
        logger.info("JotaduoTeamPlugin.register() called")
        _init_plugin_path()

        try:
            from .routers_setup import build_plugin_routers

            for router, prefix in build_plugin_routers():
                logger.info(
                    "[jotaduo-team] registering router at /api%s",
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
            hook_name="jotaduo_team_init",
            callback=self._on_startup,
            priority=50,
        )
        api.register_shutdown_hook(
            hook_name="jotaduo_team_shutdown",
            callback=self._on_shutdown,
            priority=50,
        )

        _patch_plugin_loader_unload()
        logger.info("[jotaduo-team] hooks registered")

    async def _on_startup(self):
        from .agents_setup import (
            ensure_builtin_agents,
            install_plugin_skills,
        )

        logger.info("[jotaduo-team] starting up...")
        _ensure_default_env_vars()
        install_plugin_skills()
        ensure_builtin_agents()
        _register_convene_meeting_tool()
        logger.info("[jotaduo-team] startup complete")

    async def _on_shutdown(self):
        logger.info("[jotaduo-team] shutting down")
