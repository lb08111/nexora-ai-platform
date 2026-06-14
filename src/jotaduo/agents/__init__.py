# -*- coding: utf-8 -*-
"""JotaDuo Agents Module.

This module provides the main agent implementation and supporting utilities
for building AI agents with tools, skills, and memory management.

Public API:
- JotaDuoAgent: Main agent class
- create_model_and_formatter: Factory for creating models and formatters

Example:
    >>> from jotaduo.agents import JotaDuoAgent, create_model_and_formatter
    >>> agent = JotaDuoAgent()
    >>> # Or with custom model
    >>> model, formatter = create_model_and_formatter()
"""

# JotaDuoAgent is lazy-loaded so that importing agents.skill_system (e.g.
# from CLI init_cmd/skills_cmd) does not pull react_agent, agentscope, tools.
# pylint: disable=undefined-all-variable
__all__ = ["JotaDuoAgent", "create_model_and_formatter"]


def __getattr__(name: str):
    """Lazy load heavy imports."""
    if name == "JotaDuoAgent":
        from .react_agent import JotaDuoAgent

        return JotaDuoAgent
    if name == "create_model_and_formatter":
        from .model_factory import create_model_and_formatter

        return create_model_and_formatter
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
