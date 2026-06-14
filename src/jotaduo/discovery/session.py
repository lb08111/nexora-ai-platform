# -*- coding: utf-8 -*-
"""Seam between the discovery interview and the AG-UI/A2UI transport.

A DiscoverySession advances one turn at a time. The router feeds the
user's message (None to start) and gets back the agent's next question +
current state, or the final blueprint. The real LLM-driven runner
(layer 1) and the scripted session for this cycle both implement this
Protocol.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass
class TurnResult:
    """Outcome of advancing the interview by one turn."""

    state: dict[str, Any] = field(default_factory=dict)
    question: str | None = None  # next agent question (None when done)
    blueprint: dict[str, Any] | None = None  # set on the final turn
    done: bool = False


@runtime_checkable
class DiscoverySession(Protocol):
    async def next_turn(self, user_message: str | None) -> TurnResult:
        """Advance one turn. ``user_message`` is None on the opening turn."""
        raise NotImplementedError
