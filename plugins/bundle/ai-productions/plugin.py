# -*- coding: utf-8 -*-
"""AI Productions Plugin for JotaDuo / Jotaduo.

Centralizes everything AI agents produce — posts, landing pages,
documents, e-mails, ad creatives, scripts, etc. — with a built-in
human-in-the-loop approval flow and team notifications.

Endpoints (mounted under ``/api/ai-productions/``):
    productions/*       — CRUD + approval workflow
    notifications/*     — list / send / mark-as-read

Tools exposed to agents:
    register_production       — publish a new artifact
    request_approval          — flip draft → pending_approval
    send_team_notification    — post an ad-hoc team notification

See ``README.md`` for the install/uninstall lifecycle.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

logger = logging.getLogger("jotaduo").getChild("plugin.ai-productions")


def _init_plugin_path() -> None:
    plugin_dir = str(Path(__file__).parent)
    if plugin_dir not in sys.path:
        sys.path.insert(0, plugin_dir)


def _register_agent_tools() -> None:
    """Expose plugin tools so any agent can call them."""
    try:
        from jotaduo.agents.tools import registry as tool_registry
    except ImportError:
        logger.debug(
            "tool registry not available; ai-productions tools will "
            "be reachable via HTTP API only.",
        )
        return

    try:
        from .tools.production_tools import (
            register_production,
            request_approval,
            send_team_notification,
        )

        register = getattr(tool_registry, "register_tool", None)
        if not callable(register):
            logger.debug(
                "tool registry has no register_tool(); skipping tool exposure",
            )
            return

        register("register_production", register_production)
        register("request_approval", request_approval)
        register("send_team_notification", send_team_notification)
        logger.info(
            "[ai-productions] registered tools: "
            "register_production, request_approval, send_team_notification",
        )
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning(
            "[ai-productions] tool registration failed: %s",
            exc,
            exc_info=True,
        )


def _patch_plugin_loader_unload() -> None:
    """Hook into PluginLoader to clean stores on uninstall."""
    try:
        from jotaduo.plugins.loader import PluginLoader
    except ImportError:
        logger.warning(
            "PluginLoader unavailable; ai-productions uninstall cleanup disabled",
        )
        return

    if getattr(PluginLoader, "_ai_productions_patched", False):
        return

    _original = PluginLoader.unload_plugin

    async def _patched(
        self,
        plugin_id: str,
        delete_files: bool = False,
    ) -> None:
        if plugin_id == "ai-productions":
            logger.info("[ai-productions] uninstall detected, cleaning up...")
            try:
                from .store import get_notification_store, get_production_store

                get_production_store().clear()
                get_notification_store().clear()
            except Exception as exc:  # pylint: disable=broad-except
                logger.warning(
                    "[ai-productions] cleanup failed: %s",
                    exc,
                )
        return await _original(self, plugin_id, delete_files)

    PluginLoader.unload_plugin = _patched
    PluginLoader._ai_productions_patched = True
    logger.info("[ai-productions] patched PluginLoader.unload_plugin")


# ----------------------------------------------------------------------
# Plugin entry class
# ----------------------------------------------------------------------


class AIProductionsPlugin:
    """AI Productions plugin entry point."""

    def register(self, api):
        logger.info("AIProductionsPlugin.register() called")
        _init_plugin_path()

        try:
            from .routers_setup import build_plugin_routers

            for router, prefix in build_plugin_routers():
                logger.info(
                    "[ai-productions] registering router at /api%s",
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
            hook_name="ai_productions_init",
            callback=self._on_startup,
            priority=50,
        )
        api.register_shutdown_hook(
            hook_name="ai_productions_shutdown",
            callback=self._on_shutdown,
            priority=50,
        )

        _patch_plugin_loader_unload()
        logger.info("[ai-productions] hooks registered")

    async def _on_startup(self):
        logger.info("[ai-productions] starting up...")
        _register_agent_tools()
        logger.info("[ai-productions] startup complete")

    async def _on_shutdown(self):
        logger.info("[ai-productions] shutting down")
