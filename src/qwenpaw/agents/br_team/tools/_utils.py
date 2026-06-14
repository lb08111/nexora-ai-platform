# -*- coding: utf-8 -*-
"""Helpers compartilhados pelas tools BR (formato ToolResponse e logging)."""

from __future__ import annotations

import json
import logging
from typing import Any

from agentscope.message import TextBlock
from agentscope.tool import ToolResponse

logger = logging.getLogger(__name__)


def text_response(text: str) -> ToolResponse:
    """Empacota uma string em ``ToolResponse``."""
    return ToolResponse(content=[TextBlock(type="text", text=text)])


def json_response(payload: dict[str, Any]) -> ToolResponse:
    """Empacota um dict como texto JSON dentro de ``ToolResponse``."""
    return text_response(json.dumps(payload, ensure_ascii=False, indent=2))


def err(msg: str) -> ToolResponse:
    """Resposta de erro padronizada (prefixo ERROR para o ReAct loop)."""
    logger.warning("br_team tool error: %s", msg)
    return text_response(f"ERROR: {msg}")
