# -*- coding: utf-8 -*-
"""Builds the FastAPI routers registered by ``plugin.py``."""

from __future__ import annotations

import logging

logger = logging.getLogger("qwenpaw").getChild(
    "plugin.nexora-pix.routers_setup",
)


def build_plugin_routers():
    """Return ``(router, prefix)`` tuples for ``api.register_http_router``."""
    from .routers.pix_router import router as pix_router

    return [
        (pix_router, "/pix"),
    ]
