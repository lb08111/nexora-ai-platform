# -*- coding: utf-8 -*-
"""Classe base e fábrica de especialistas brasileiros.

Cada especialista é um ``ReActAgent`` configurado com:
- system prompt pt-BR do papel (``prompts.PROMPTS_BY_ROLE``);
- toolkit do papel (subset de ``br_team.tools``);
- modelo ativo do workspace (``create_model_and_formatter``);
- memória em memória (`InMemoryMemory`).

Mantemos uma única classe ``BRSpecialistAgent`` em vez de uma classe
por papel para reduzir boilerplate — o que muda é prompt e tools, não
o comportamento do loop ReAct.
"""

from __future__ import annotations

import logging
from typing import Callable, Iterable

from agentscope.agent import ReActAgent
from agentscope.memory import InMemoryMemory
from agentscope.tool import Toolkit

from ...model_factory import create_model_and_formatter
from ..prompts import PROMPTS_BY_ROLE
from ..tools import (
    book_appointment,
    check_slot_availability,
    consultar_cep,
    consultar_cnpj,
    consultar_status_pagamento,
    gerar_cobranca_pix,
    gerar_link_pagamento,
    list_available_slots,
    send_appointment_reminder,
    send_whatsapp_image,
    send_whatsapp_message,
    send_whatsapp_template,
    validar_cpf,
)

logger = logging.getLogger(__name__)


# Toolkit por papel: subset deliberado, não 'tudo para todos'.
TOOLS_BY_ROLE: dict[str, list[Callable]] = {
    "atendente": [
        send_whatsapp_message,
        send_whatsapp_image,
        consultar_cep,
        validar_cpf,
    ],
    "agendamento": [
        list_available_slots,
        check_slot_availability,
        book_appointment,
        send_appointment_reminder,
        send_whatsapp_template,
        send_whatsapp_message,
    ],
    "vendas": [
        send_whatsapp_message,
        send_whatsapp_template,
        send_whatsapp_image,
        gerar_link_pagamento,
        gerar_cobranca_pix,
        consultar_status_pagamento,
        consultar_cnpj,
    ],
    "suporte": [
        send_whatsapp_message,
        send_whatsapp_template,
        consultar_status_pagamento,
        consultar_cep,
    ],
    "marketing": [
        send_whatsapp_template,
        send_whatsapp_image,
    ],
    "catalogo": [
        send_whatsapp_message,
        send_whatsapp_image,
    ],
    "financeiro": [
        gerar_cobranca_pix,
        gerar_link_pagamento,
        consultar_status_pagamento,
        send_whatsapp_message,
        validar_cpf,
        consultar_cnpj,
    ],
    "recepcionista_saude": [
        list_available_slots,
        check_slot_availability,
        book_appointment,
        send_appointment_reminder,
        send_whatsapp_template,
        validar_cpf,
    ],
}


class BRSpecialistAgent(ReActAgent):
    """Wrapper fino sobre ReActAgent para identificar especialistas BR."""

    role: str
    extra_tools: tuple[Callable, ...] = ()


def _attach_formatter(model, formatter) -> None:
    """Mesma estratégia de discovery/agent.py para sobrescrever formatter."""
    if formatter is None:
        return
    innermost = model
    while hasattr(innermost, "_inner"):
        innermost = innermost._inner
    while hasattr(innermost, "_model"):
        innermost = innermost._model
    if hasattr(innermost, "formatter"):
        innermost.formatter = formatter


def build_specialist(
    role: str,
    name: str | None = None,
    extra_tools: Iterable[Callable] | None = None,
    max_iters: int = 8,
) -> BRSpecialistAgent:
    """Constrói um especialista BR para o papel indicado.

    Args:
        role: Um dos papéis em ``PROMPTS_BY_ROLE``
            (``atendente``, ``agendamento``, ``vendas``, ``suporte``,
            ``marketing``, ``catalogo``, ``financeiro``,
            ``recepcionista_saude``).
        name: Nome de exibição (default: ``f"BR_{role}"``).
        extra_tools: Tools extras a registrar (ex. tool do segmento).
        max_iters: Limite de iterações do loop ReAct.

    Returns:
        ``BRSpecialistAgent`` pronto para ``reply()``.

    Raises:
        ValueError: se ``role`` for desconhecido.
    """
    if role not in PROMPTS_BY_ROLE:
        raise ValueError(
            f"role desconhecido: {role!r}. "
            f"Válidos: {sorted(PROMPTS_BY_ROLE)}",
        )
    if role == "orchestrator":
        raise ValueError(
            "use JotaduoOrchestrator, não build_specialist, "
            "para o papel 'orchestrator'.",
        )

    model, formatter = create_model_and_formatter()
    _attach_formatter(model, formatter)

    tool_funcs = list(TOOLS_BY_ROLE.get(role, []))
    if extra_tools:
        tool_funcs.extend(extra_tools)
    toolkit = Toolkit(tools=tool_funcs)

    display_name = name or f"BR_{role}"
    agent = BRSpecialistAgent(
        name=display_name,
        sys_prompt=PROMPTS_BY_ROLE[role],
        model=model,
        tools=toolkit.tools,
        memory=InMemoryMemory(),
        max_iters=max_iters,
    )
    agent.role = role
    agent.extra_tools = tuple(extra_tools or ())
    logger.info(
        "br_team specialist built: role=%s name=%s tools=%d",
        role,
        display_name,
        len(tool_funcs),
    )
    return agent
