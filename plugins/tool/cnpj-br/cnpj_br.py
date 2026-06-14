# -*- coding: utf-8 -*-
"""CNPJ Brasil Tool Plugin Entry Point."""

import importlib.util
import logging
import os
import sys

from qwenpaw.plugins.api import PluginApi

logger = logging.getLogger(__name__)

_PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))


_TOOLS = [
    (
        "consultar_cnpj",
        "Consulta CNPJ na BrasilAPI com ReceitaWS como fallback",
        "🏢",
    ),
    ("consultar_cep", "Consulta CEP pela BrasilAPI", "📮"),
    ("consultar_cpf", "Valida CPF offline pelo dígito verificador", "👤"),
    (
        "validar_inscricao_estadual",
        "Valida inscrição estadual offline por UF",
        "🧾",
    ),
    (
        "consultar_simples_nacional",
        "Consulta situação no Simples Nacional e MEI por CNPJ",
        "💼",
    ),
    (
        "enriquecer_lead",
        "Enriquece lead por CNPJ e calcula score comercial",
        "✨",
    ),
]


def _load_tool_module():
    """Load cnpj_br_tool.py from this plugin's directory via importlib."""
    if _PLUGIN_DIR not in sys.path:
        sys.path.insert(0, _PLUGIN_DIR)

    tool_path = os.path.join(_PLUGIN_DIR, "cnpj_br_tool.py")
    spec = importlib.util.spec_from_file_location(
        "cnpj_br_tool",
        tool_path,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CnpjBrPlugin:
    """CNPJ Brasil Tool Plugin.

    Registers Brazilian cadastral lookup tools into the Agent's toolkit.
    """

    def register(self, api: PluginApi):
        """Register cnpj-br tools.

        Args:
            api: PluginApi instance.
        """
        tool = _load_tool_module()

        if not hasattr(api, "register_tool"):
            logger.warning(
                "Plugin API does not expose register_tool; relying on "
                "tool-type auto-discovery from plugin.json meta.tools"
            )
            return

        for tool_name, description, icon in _TOOLS:
            api.register_tool(
                tool_name=tool_name,
                tool_func=getattr(tool, tool_name),
                description=description,
                icon=icon,
            )

        logger.info("CNPJ Brasil tool plugin registered")


# Export plugin instance
plugin = CnpjBrPlugin()
