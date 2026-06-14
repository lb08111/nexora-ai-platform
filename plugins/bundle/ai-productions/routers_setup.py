# -*- coding: utf-8 -*-
"""Builds the FastAPI routers registered by ``plugin.py``."""

import logging

logger = logging.getLogger("jotaduo").getChild(
    "plugin.ai-productions.routers_setup",
)


def build_plugin_routers():
    """Return ``(router, prefix)`` tuples for ``api.register_http_router``."""
    from .routers.notifications import router as notifications_router
    from .routers.productions import router as productions_router

    return [
        (productions_router, "/ai-productions/productions"),
        (notifications_router, "/ai-productions/notifications"),
    ]
