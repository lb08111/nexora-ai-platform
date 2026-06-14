# -*- coding: utf-8 -*-
"""JotaDuo Pet backend plugin entry point."""

# pylint: disable=wrong-import-position,wrong-import-order

import atexit
import logging
import sys
from pathlib import Path

# ``jotaduo plugin install`` execs this file as a plain module (no
# package), so sibling modules are not reachable via relative imports
# unless the plugin directory is on sys.path before importing them.
_plugin_dir = str(Path(__file__).resolve().parent)
if _plugin_dir not in sys.path:
    sys.path.insert(0, _plugin_dir)

from jotaduo.plugins.api import PluginApi  # noqa: E402

from emitter import (  # noqa: E402
    emit_pet_event,
    ensure_desktop_available,
    stop_desktop,
)
from patch_approval import (  # noqa: E402
    patch_approval_service,
    restore_approval_service,
)
from patch_runner import (  # noqa: E402
    patch_agent_runner,
    restore_agent_runner,
)
from router import build_router  # noqa: E402

# Logger uses ``jotaduo.*`` so messages appear in the project logger
# (``~/.jotaduo/jotaduo.log``).
logger = logging.getLogger("jotaduo.pet_desktop")


def _atexit_stop_pet_desktop() -> None:
    """Best-effort stop when the interpreter exits without lifespan hooks."""
    try:
        stop_desktop(force=True, aggressive=True, grace=5.0)
    except Exception:
        logger.debug(
            "JotaDuo Pet: atexit stop skipped or failed",
            exc_info=True,
        )


class JotaDuoPetPlugin:
    """Emit JotaDuo backend lifecycle events to the desktop pet."""

    def register(self, api: PluginApi):
        """Register startup/shutdown hooks and plugin HTTP routes."""
        logger.info("Registering JotaDuo Pet plugin")

        # Runtime patches (``AgentRunner`` / ``ApprovalService``) are
        # applied exclusively from the startup hook below — applying them
        # here at import time runs before JotaDuo has finished wiring up
        # the affected classes and silently swallowing the import error
        # would leave the plugin in a broken state.
        api.register_startup_hook(
            hook_name="jotaduo_pet_startup",
            callback=self._startup,
            priority=80,
        )
        api.register_shutdown_hook(
            hook_name="jotaduo_pet_shutdown",
            callback=self._shutdown,
            priority=120,
        )
        api.register_http_router(
            build_router(),
            prefix="/jotaduo-pet",
            tags=["jotaduo-pet"],
        )

        atexit.register(_atexit_stop_pet_desktop)

        logger.info("JotaDuo Pet plugin registered")

    def _startup(self):
        """Patch the runner and notify the desktop.

        Patch failures (e.g. an upstream rename of ``AgentRunner`` /
        ``ApprovalService``) surface as ``logger.exception`` so the
        plugin install system can flag them; we still attempt to keep
        the desktop autostart and ``jotaduo.startup`` emit going so the
        UI is never silently dead.
        """
        try:
            patch_agent_runner()
        except Exception:
            logger.exception(
                "JotaDuo Pet: failed to patch AgentRunner; "
                "lifecycle events will be unavailable",
            )
        try:
            patch_approval_service()
        except Exception:
            logger.exception(
                "JotaDuo Pet: failed to patch ApprovalService; "
                "approval events will be unavailable",
            )

        try:
            ensure_desktop_available()
            emit_pet_event(
                "jotaduo.startup",
                text="JotaDuo started",
                duration_ms=1500,
            )
            logger.info("JotaDuo Pet startup hook complete")
        except Exception:
            logger.exception("JotaDuo Pet startup hook failed")

    def _shutdown(self):
        """Notify the desktop, terminate it, and restore the runner patch.

        The pet desktop is treated as a child of JotaDuo: when JotaDuo
        exits, the floating window goes with it. ``stop_desktop`` only
        kills a process that this plugin instance spawned (so a desktop
        started independently via ``python -m jotaduo_pet_desktop start``
        is left alone), and the whole behaviour can be opted out of via
        ``JOTADUO_PET_STOP_ON_SHUTDOWN=0``.
        """
        try:
            emit_pet_event("jotaduo.shutdown", text="", duration_ms=500)
        except Exception:
            logger.warning(
                "JotaDuo Pet: shutdown event emit failed",
                exc_info=True,
            )

        try:
            result = stop_desktop(force=True, aggressive=True, grace=5.0)
            logger.info("JotaDuo Pet: stop_desktop result=%s", result)
        except Exception:
            logger.exception("JotaDuo Pet: failed to stop desktop process")

        try:
            restore_approval_service()
            restore_agent_runner()
        except Exception:
            logger.exception("JotaDuo Pet: failed to restore class methods")

        logger.info("JotaDuo Pet shutdown hook complete")


plugin = JotaDuoPetPlugin()
