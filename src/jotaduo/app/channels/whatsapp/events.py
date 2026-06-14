# -*- coding: utf-8 -*-
"""Lightweight event bus for WhatsApp channel observers."""

from __future__ import annotations

import inspect
import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List

logger = logging.getLogger(__name__)


@dataclass
class WhatsAppMessageEvent:
    direction: str
    agent_id: str
    session_id: str
    user_id: str
    text: str
    channel_meta: Dict[str, Any] = field(default_factory=dict)
    should_process: bool = True
    handled_by: List[str] = field(default_factory=list)


WhatsAppEventHandler = Callable[
    [WhatsAppMessageEvent],
    bool | None | Awaitable[bool | None],
]

_handlers: Dict[str, WhatsAppEventHandler] = {}


def register_handler(name: str, handler: WhatsAppEventHandler) -> None:
    _handlers[name] = handler


def unregister_handler(name: str) -> None:
    _handlers.pop(name, None)


async def publish(event: WhatsAppMessageEvent) -> WhatsAppMessageEvent:
    for name, handler in list(_handlers.items()):
        try:
            result = handler(event)
            if inspect.isawaitable(result):
                result = await result
            if result is False:
                event.should_process = False
            event.handled_by.append(name)
        except Exception:
            logger.exception("whatsapp event handler failed: %s", name)
    return event


__all__ = [
    "WhatsAppMessageEvent",
    "register_handler",
    "unregister_handler",
    "publish",
]
