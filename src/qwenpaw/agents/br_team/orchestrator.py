# -*- coding: utf-8 -*-
"""NexoraOrchestrator: líder do time BR.

Usa as tools NATIVAS de coordenação inter-agente já existentes em
``qwenpaw.agents.tools.agent_management`` (``list_agents``,
``chat_with_agent``, ``submit_to_agent``, ``check_agent_task``,
``spawn_subagent``) para rotear intenções para os especialistas
brasileiros.

Esse orquestrador **não** instancia os especialistas em processo — ele
fala com eles via API local (``http://127.0.0.1:8088``), exatamente
como o padrão Hub-and-Spoke do qwenpaw. Isso permite que cada
especialista rode no seu próprio Workspace, com sua memória e seus
canais (WhatsApp, Telegram etc.).
"""

from __future__ import annotations

import logging
from typing import Optional

from agentscope.agent import ReActAgent
from agentscope.memory import InMemoryMemory
from agentscope.tool import Toolkit

from ..model_factory import create_model_and_formatter
from ..tools import (
    chat_with_agent,
    check_agent_task,
    list_agents,
    spawn_subagent,
    submit_to_agent,
)
from .prompts import ORCHESTRATOR_PROMPT
from .specialists.base import _attach_formatter

logger = logging.getLogger(__name__)


class NexoraOrchestrator(ReActAgent):
    """Orquestrador de time pt-BR.

    Propósito: receber a intenção do usuário/sistema e delegar ao
    especialista certo, retornando o resultado consolidado.
    """

    def __init__(
        self,
        name: str = "NexoraOrchestrator",
        max_iters: int = 10,
        extra_tools: Optional[list] = None,
    ) -> None:
        model, formatter = create_model_and_formatter()
        _attach_formatter(model, formatter)

        tools = [
            list_agents,
            chat_with_agent,
            submit_to_agent,
            check_agent_task,
            spawn_subagent,
        ]
        if extra_tools:
            tools.extend(extra_tools)
        toolkit = Toolkit(tools=tools)

        super().__init__(
            name=name,
            sys_prompt=ORCHESTRATOR_PROMPT,
            model=model,
            tools=toolkit.tools,
            memory=InMemoryMemory(),
            max_iters=max_iters,
        )
        logger.info(
            "NexoraOrchestrator pronto (name=%s, tools=%d)",
            name,
            len(tools),
        )
