# -*- coding: utf-8 -*-
"""Public re-exports for the ai-productions plugin."""

__all__ = ["AIProductionsPlugin"]


def __getattr__(name):  # pragma: no cover - lazy import
    if name == "AIProductionsPlugin":
        from .plugin import AIProductionsPlugin

        return AIProductionsPlugin
    raise AttributeError(name)
