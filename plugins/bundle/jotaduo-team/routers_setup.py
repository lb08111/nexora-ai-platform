# -*- coding: utf-8 -*-
"""Builds the FastAPI routers registered by ``plugin.py``."""

import logging

logger = logging.getLogger("jotaduo").getChild(
    "plugin.jotaduo-team.routers_setup",
)


def build_plugin_routers():
    """Return ``(router, prefix)`` tuples for ``api.register_http_router``."""
    from .routers.meeting import router as meeting_router
    from .routers.team import router as team_router

    return [
        (team_router, "/jotaduo-team/team"),
        (meeting_router, "/jotaduo-team/meeting"),
    ]
