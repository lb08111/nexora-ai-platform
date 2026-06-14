# -*- coding: utf-8 -*-
"""Tauri sidecar environment variable helpers.

Keep this dependency-light: the Tauri entry imports it before jotaduo.constant
has read import-time environment variables.
"""

import os

DESKTOP_APP_ENV = "JOTADUO_DESKTOP_APP"
DESKTOP_CORS_ORIGINS_ENV = "JOTADUO_CORS_ORIGINS"
DESKTOP_READY_PREFIX = "JOTADUO_BACKEND_READY"

DESKTOP_CORS_ORIGINS = (
    "tauri://localhost",
    "https://tauri.localhost",
    "http://tauri.localhost",
)


def ensure_desktop_cors_origins() -> None:
    origins = [
        origin.strip()
        for origin in os.environ.get(DESKTOP_CORS_ORIGINS_ENV, "").split(",")
        if origin.strip()
    ]
    for origin in DESKTOP_CORS_ORIGINS:
        if origin not in origins:
            origins.append(origin)
    os.environ[DESKTOP_CORS_ORIGINS_ENV] = ",".join(origins)
