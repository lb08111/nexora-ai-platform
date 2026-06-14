# -*- coding: utf-8 -*-
"""Public re-exports for the nexora-team plugin."""

__all__ = ["NexoraTeamPlugin"]


def __getattr__(name):  # pragma: no cover - lazy import
    if name == "NexoraTeamPlugin":
        from .plugin import NexoraTeamPlugin

        return NexoraTeamPlugin
    raise AttributeError(name)
