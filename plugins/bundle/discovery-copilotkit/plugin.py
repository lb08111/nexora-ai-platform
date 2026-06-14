# -*- coding: utf-8 -*-
"""Plugin entry point: register the CopilotKit router with JotaDuo."""

# pylint: disable=wrong-import-position,wrong-import-order

import logging
import sys
from pathlib import Path

# ``jotaduo plugin install`` execs this file as a plain module (no
# package), so sibling modules are not reachable via relative imports
# unless the plugin directory is on sys.path before importing them.
_plugin_dir = str(Path(__file__).resolve().parent)
if _plugin_dir not in sys.path:
    sys.path.insert(0, _plugin_dir)

from router import build_router, get_session_manager  # noqa: E402

logger = logging.getLogger("jotaduo.discovery_copilotkit")


class DiscoveryCopilotKitPlugin:
    """Mount the CopilotKit-flavoured discovery router under ``/api``."""

    PREFIX = "/discovery-copilotkit"

    def register(self, api) -> None:
        logger.info("Registering discovery-copilotkit plugin")
        api.register_http_router(
            build_router(),
            prefix=self.PREFIX,
            tags=["discovery-copilotkit"],
        )
        api.register_startup_hook(
            hook_name="discovery_copilotkit_startup",
            callback=self._startup,
            priority=80,
        )
        api.register_shutdown_hook(
            hook_name="discovery_copilotkit_shutdown",
            callback=self._shutdown,
            priority=120,
        )

    def _startup(self) -> None:
        """Optionally swap the session factory to the live agent.

        Defaults to the scripted (LLM-free) session so the plugin works
        out of the box; setting ``JOTADUO_DISCOVERY_LIVE=1`` flips it to
        the real LLM-driven session — same env switch the discovery
        runner uses, so the two stay in sync.
        """
        import os

        if os.environ.get("JOTADUO_DISCOVERY_LIVE") == "1":
            try:
                from jotaduo.discovery import LiveDiscoverySession

                get_session_manager().set_factory(LiveDiscoverySession)
                logger.info(
                    "discovery-copilotkit: using LiveDiscoverySession",
                )
            except Exception:
                logger.exception(
                    "discovery-copilotkit: failed to enable live session; "
                    "falling back to scripted session",
                )
        else:
            logger.info(
                "discovery-copilotkit: using ScriptedDiscoverySession "
                "(set JOTADUO_DISCOVERY_LIVE=1 for live mode)",
            )

    def _shutdown(self) -> None:
        try:
            get_session_manager().reset()
            logger.info("discovery-copilotkit: sessions cleared")
        except Exception:
            logger.warning(
                "discovery-copilotkit: shutdown cleanup failed",
                exc_info=True,
            )


plugin = DiscoveryCopilotKitPlugin()
