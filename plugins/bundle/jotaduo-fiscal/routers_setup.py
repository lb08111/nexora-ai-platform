# -*- coding: utf-8 -*-
"""Builds the FastAPI routers registered by ``plugin.py``."""

from __future__ import annotations

import logging

logger = logging.getLogger("jotaduo").getChild(
    "plugin.jotaduo-fiscal.routers_setup",
)


def build_plugin_routers():
    """Return ``(router, prefix)`` tuples for ``api.register_http_router``."""
    from .routers.fiscal_router import router as fiscal_router

    return [(fiscal_router, "/fiscal")]
