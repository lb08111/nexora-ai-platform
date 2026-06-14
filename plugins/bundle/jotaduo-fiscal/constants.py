# -*- coding: utf-8 -*-
"""Shared constants for the jotaduo-fiscal plugin."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

PLUGIN_DIR = Path(__file__).parent

_plugin_dir_str = str(PLUGIN_DIR)
if _plugin_dir_str not in sys.path:
    sys.path.insert(0, _plugin_dir_str)

PLUGIN_ID = "jotaduo-fiscal"
FISCAL_AGENT_ID = "jotaduo-fiscal"

DEFAULT_ENV_KEYS = (
    "FISCAL_PROVIDER",
    "FISCAL_API_KEY",
    "FISCAL_AMBIENTE",
    "EMPRESA_CNPJ",
    "EMPRESA_IE",
    "EMPRESA_REGIME_TRIBUTARIO",
)

DEFAULT_ENV_VALUES = {
    "FISCAL_PROVIDER": "focus_nfe",
    "FISCAL_AMBIENTE": "homologacao",
    "EMPRESA_REGIME_TRIBUTARIO": "simples_nacional",
}

FISCAL_TOOL_NAMES = (
    "emitir_nfe",
    "emitir_nfse",
    "emitir_nfce",
    "consultar_nota",
    "cancelar_nota",
    "carta_correcao",
    "inutilizar_numeracao",
    "baixar_xml_danfe",
)

FISCAL_TOOL_CONFIGS: dict[str, dict[str, Any]] = {
    "emitir_nfe": {
        "name": "emitir_nfe",
        "enabled": True,
        "async_execution": True,
        "description": "Emite NF-e de produto via provedor fiscal configurado.",
        "icon": "🧾",
    },
    "emitir_nfse": {
        "name": "emitir_nfse",
        "enabled": True,
        "async_execution": True,
        "description": "Emite NFS-e de serviço via provedor fiscal configurado.",
        "icon": "🏛️",
    },
    "emitir_nfce": {
        "name": "emitir_nfce",
        "enabled": True,
        "async_execution": True,
        "description": "Emite NFC-e de consumidor via provedor fiscal configurado.",
        "icon": "🛒",
    },
    "consultar_nota": {
        "name": "consultar_nota",
        "enabled": True,
        "async_execution": True,
        "description": "Consulta status de uma nota por chave de acesso ou ID.",
        "icon": "🔎",
    },
    "cancelar_nota": {
        "name": "cancelar_nota",
        "enabled": True,
        "async_execution": True,
        "description": "Cancela nota fiscal com justificativa legal.",
        "icon": "🚫",
    },
    "carta_correcao": {
        "name": "carta_correcao",
        "enabled": True,
        "async_execution": True,
        "description": "Emite carta de correção eletrônica para NF-e.",
        "icon": "✍️",
    },
    "inutilizar_numeracao": {
        "name": "inutilizar_numeracao",
        "enabled": True,
        "async_execution": True,
        "description": "Inutiliza faixa de numeração fiscal não utilizada.",
        "icon": "🧹",
    },
    "baixar_xml_danfe": {
        "name": "baixar_xml_danfe",
        "enabled": True,
        "async_execution": True,
        "description": "Baixa XML ou DANFE/PDF de uma nota autorizada.",
        "icon": "📄",
    },
}

AGENT_SPEC: dict[str, Any] = {
    "agent_id": FISCAL_AGENT_ID,
    "role": "fiscal",
    "name": "Jotaduo Fiscal",
    "description": (
        "Especialista Fiscal Jotaduo para emissão, consulta, cancelamento, "
        "carta de correção, inutilização e download de NF-e/NFS-e/NFC-e."
    ),
    "extra_tools": FISCAL_TOOL_CONFIGS,
    "running_overrides": {
        "auto_continue_on_text_only": False,
        "max_iters": 30,
    },
}
