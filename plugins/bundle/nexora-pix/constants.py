# -*- coding: utf-8 -*-
"""Shared constants and agent specs for the nexora-pix plugin."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

PLUGIN_DIR = Path(__file__).parent
STORE_DIR = PLUGIN_DIR / "store"
PIX_DB_PATH = STORE_DIR / "pix.db"

_plugin_dir_str = str(PLUGIN_DIR)
if _plugin_dir_str not in sys.path:
    sys.path.insert(0, _plugin_dir_str)

COBRANCA_AGENT_ID = "nexora-cobranca"
ALL_AGENT_IDS = (COBRANCA_AGENT_ID,)

PIX_TOOL_NAMES = (
    "criar_cobranca_pix",
    "criar_cobranca_com_vencimento",
    "criar_recorrencia",
    "consultar_cobranca",
    "listar_recebimentos",
    "conciliar_pagamento",
    "devolver_pix",
    "gerar_qr_code_estatico",
)

PIX_EXTRA_TOOLS: dict[str, dict[str, Any]] = {
    "criar_cobranca_pix": {
        "name": "criar_cobranca_pix",
        "enabled": True,
        "async_execution": True,
        "description": "Gera cobrança Pix imediata com QR Code dinâmico.",
        "icon": "💸",
    },
    "criar_cobranca_com_vencimento": {
        "name": "criar_cobranca_com_vencimento",
        "enabled": True,
        "async_execution": True,
        "description": "Gera cobrança Pix com vencimento, juros, multa e desconto.",
        "icon": "📅",
    },
    "criar_recorrencia": {
        "name": "criar_recorrencia",
        "enabled": True,
        "async_execution": True,
        "description": "Agenda cobranças Pix recorrentes.",
        "icon": "🔁",
    },
    "consultar_cobranca": {
        "name": "consultar_cobranca",
        "enabled": True,
        "async_execution": True,
        "description": "Consulta status de uma cobrança Pix por txid.",
        "icon": "🔎",
    },
    "listar_recebimentos": {
        "name": "listar_recebimentos",
        "enabled": True,
        "async_execution": True,
        "description": "Lista recebimentos Pix para conciliação financeira.",
        "icon": "📒",
    },
    "conciliar_pagamento": {
        "name": "conciliar_pagamento",
        "enabled": True,
        "async_execution": True,
        "description": "Concilia pagamento Pix recebido com txid, valor e E2EID.",
        "icon": "✅",
    },
    "devolver_pix": {
        "name": "devolver_pix",
        "enabled": True,
        "async_execution": True,
        "description": "Solicita devolução Pix pelo E2EID.",
        "icon": "↩️",
    },
    "gerar_qr_code_estatico": {
        "name": "gerar_qr_code_estatico",
        "enabled": True,
        "async_execution": True,
        "description": "Gera QR Code Pix estático localmente.",
        "icon": "🧾",
    },
}

AGENT_SPECS: list[dict[str, Any]] = [
    {
        "agent_id": COBRANCA_AGENT_ID,
        "role": "cobranca",
        "name": "Nexora Cobrança",
        "description": (
            "Especialista pt-BR em cobrança Pix, recorrência, "
            "conciliação, webhooks e devoluções. Confirma dados antes "
            "de gerar cobranças e orienta clientes com segurança."
        ),
        "skill_names": [],
        "extra_tools": PIX_EXTRA_TOOLS,
        "running_overrides": {
            "auto_continue_on_text_only": False,
            "max_iters": 50,
        },
    },
]

DEFAULT_ENV_KEYS = (
    "PIX_PROVIDER",
    "PIX_API_KEY",
    "PIX_AMBIENTE",
    "PIX_CHAVE",
    "PIX_WEBHOOK_SECRET",
)

DEFAULT_ENV_VALUES: dict[str, str] = {
    "PIX_PROVIDER": "asaas",
    "PIX_AMBIENTE": "sandbox",
}
