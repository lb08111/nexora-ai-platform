# -*- coding: utf-8 -*-
"""Public re-exports for the jotaduo-team plugin."""

__all__ = ["JotaduoTeamPlugin"]


def __getattr__(name):  # pragma: no cover - lazy import
    if name == "JotaduoTeamPlugin":
        from .plugin import JotaduoTeamPlugin

        return JotaduoTeamPlugin
    raise AttributeError(name)
