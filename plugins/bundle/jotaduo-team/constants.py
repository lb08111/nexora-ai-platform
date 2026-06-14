# -*- coding: utf-8 -*-
"""Shared constants and agent specs for the jotaduo-team plugin.

Reuses ``jotaduo.agents.br_team`` (prompts + tools + factory) to register
five Brazilian specialist agents into the JotaDuo multi-agent manager.
"""

import sys
from pathlib import Path
from typing import Any

PLUGIN_DIR = Path(__file__).parent

_plugin_dir_str = str(PLUGIN_DIR)
if _plugin_dir_str not in sys.path:
    sys.path.insert(0, _plugin_dir_str)

# Built-in agent IDs (kebab-case, stable across upgrades).
ORCHESTRATOR_AGENT_ID = "jotaduo-orchestrator"
ATENDENTE_AGENT_ID = "jotaduo-atendente"
AGENDAMENTO_AGENT_ID = "jotaduo-agendamento"
VENDAS_AGENT_ID = "jotaduo-vendas"
FINANCEIRO_AGENT_ID = "jotaduo-financeiro"

ALL_AGENT_IDS = (
    ORCHESTRATOR_AGENT_ID,
    ATENDENTE_AGENT_ID,
    AGENDAMENTO_AGENT_ID,
    VENDAS_AGENT_ID,
    FINANCEIRO_AGENT_ID,
)

# Map of agent_id -> br_team role key. The role drives prompt + toolkit
# selection inside ``jotaduo.agents.br_team``.
AGENT_ROLE_MAP: dict[str, str] = {
    ORCHESTRATOR_AGENT_ID: "orchestrator",
    ATENDENTE_AGENT_ID: "atendente",
    AGENDAMENTO_AGENT_ID: "agendamento",
    VENDAS_AGENT_ID: "vendas",
    FINANCEIRO_AGENT_ID: "financeiro",
}

# Tools that should be ENABLED on the orchestrator only.
_ORCHESTRATOR_EXTRA_TOOLS: dict[str, dict[str, Any]] = {
    "chat_with_agent": {
        "name": "chat_with_agent",
        "enabled": True,
        "description": "Envia mensagem para outro agente do time Jotaduo",
        "icon": "💬",
    },
    "submit_to_agent": {
        "name": "submit_to_agent",
        "enabled": True,
        "async_execution": True,
        "description": "Submete tarefa assíncrona para um especialista",
        "icon": "📨",
    },
    "list_agents": {
        "name": "list_agents",
        "enabled": True,
        "description": "Lista os especialistas Jotaduo disponíveis",
        "icon": "🔍",
    },
    "convene_meeting": {
        "name": "convene_meeting",
        "enabled": True,
        "async_execution": True,
        "description": (
            "Convoca uma reunião com vários especialistas em paralelo "
            "e agrega as opiniões em uma transcrição"
        ),
        "icon": "🎤",
    },
}

# Specialist tools are disabled chat_with_agent (specialists só respondem ao
# orquestrador, não dão chat horizontal entre si).
_SPECIALIST_DISABLED_TOOLS: dict[str, dict[str, Any]] = {
    "chat_with_agent": {
        "name": "chat_with_agent",
        "enabled": False,
        "description": "Disabled for specialists (hub-and-spoke).",
        "icon": "💬",
    },
}

AGENT_SPECS: list[dict[str, Any]] = [
    {
        "agent_id": ORCHESTRATOR_AGENT_ID,
        "role": "orchestrator",
        "name": "Jotaduo Orchestrator",
        "description": (
            "Maestro do time Jotaduo. Recebe mensagens dos clientes "
            "(WhatsApp/Instagram/site) e roteia para o especialista "
            "certo (atendente, agendamento, vendas, suporte, "
            "financeiro). Convoca reuniões quando o caso é complexo."
        ),
        "skill_names": ["br_orchestrator-pt", "jotaduo-meeting-pt"],
        "extra_tools": _ORCHESTRATOR_EXTRA_TOOLS,
        "running_overrides": {
            "auto_continue_on_text_only": False,
            "max_iters": 50,
        },
    },
    {
        "agent_id": ATENDENTE_AGENT_ID,
        "role": "atendente",
        "name": "Jotaduo Atendente",
        "description": (
            "Primeiro contato no WhatsApp. Cumprimenta, classifica a "
            "intenção e responde dúvidas simples. Escala quando o "
            "assunto for específico de outro especialista."
        ),
        "skill_names": ["br_atendente-pt"],
        "extra_tools": _SPECIALIST_DISABLED_TOOLS,
    },
    {
        "agent_id": AGENDAMENTO_AGENT_ID,
        "role": "agendamento",
        "name": "Jotaduo Agendamento",
        "description": (
            "Marca, remarca e cancela horários (clínica, salão, "
            "consultoria). Confere disponibilidade real antes de "
            "confirmar e dispara lembretes anti no-show."
        ),
        "skill_names": ["br_agendamento-pt"],
        "extra_tools": _SPECIALIST_DISABLED_TOOLS,
    },
    {
        "agent_id": VENDAS_AGENT_ID,
        "role": "vendas",
        "name": "Jotaduo Vendas",
        "description": (
            "Qualifica leads, envia orçamento, gera link de "
            "pagamento ou cobrança Pix. Nunca inventa desconto."
        ),
        "skill_names": ["br_vendas-pt"],
        "extra_tools": _SPECIALIST_DISABLED_TOOLS,
    },
    {
        "agent_id": FINANCEIRO_AGENT_ID,
        "role": "financeiro",
        "name": "Jotaduo Financeiro",
        "description": (
            "Gera Pix, link de pagamento, confere status, faz "
            "conciliação. Nunca pede dados completos de cartão."
        ),
        "skill_names": ["br_financeiro-pt"],
        "extra_tools": _SPECIALIST_DISABLED_TOOLS,
    },
]

# Skills shipped with this plugin (copied into the shared skill pool).
PLUGIN_SKILLS = ["jotaduo-meeting-pt"]

# Default env keys provisioned into envs.json so they appear in the
# Console without the user having to type them.
DEFAULT_ENV_KEYS = (
    "WHATSAPP_PROVIDER",
    "WHATSAPP_TOKEN",
    "PIX_PROVIDER",
    "PIX_TOKEN",
    "BRASILAPI_BASE_URL",
)

DEFAULT_ENV_VALUES: dict[str, str] = {
    "WHATSAPP_PROVIDER": "zapi",
    "PIX_PROVIDER": "gerencianet-sandbox",
    "BRASILAPI_BASE_URL": "https://brasilapi.com.br/api",
}
