# -*- coding: utf-8 -*-
"""WebMania fiscal provider stub."""

from __future__ import annotations

from typing import Any

from .base import AbstractFiscalProvider, FiscalResult, fiscal_response


class WebManiaProvider(AbstractFiscalProvider):
    """Placeholder adapter for WebManiaBR fiscal APIs."""

    provider_name = "webmania"

    async def emitir_nfe(self, payload: dict[str, Any]) -> FiscalResult:
        return self._not_wired("emitir_nfe", payload)

    async def emitir_nfse(self, payload: dict[str, Any]) -> FiscalResult:
        return self._not_wired("emitir_nfse", payload)

    async def emitir_nfce(self, payload: dict[str, Any]) -> FiscalResult:
        return self._not_wired("emitir_nfce", payload)

    async def consultar_nota(self, chave_acesso: str) -> FiscalResult:
        return self._not_wired(
            "consultar_nota", {"chave_acesso": chave_acesso}
        )

    async def cancelar_nota(
        self,
        chave_acesso: str,
        justificativa: str,
    ) -> FiscalResult:
        return self._not_wired(
            "cancelar_nota",
            {"chave_acesso": chave_acesso, "justificativa": justificativa},
        )

    async def carta_correcao(
        self,
        chave_acesso: str,
        correcao: str,
    ) -> FiscalResult:
        return self._not_wired(
            "carta_correcao",
            {"chave_acesso": chave_acesso, "correcao": correcao},
        )

    async def inutilizar_numeracao(
        self,
        serie: int,
        numero_inicial: int,
        numero_final: int,
        justificativa: str,
    ) -> FiscalResult:
        return self._not_wired(
            "inutilizar_numeracao",
            {
                "serie": serie,
                "numero_inicial": numero_inicial,
                "numero_final": numero_final,
                "justificativa": justificativa,
            },
        )

    async def baixar_xml_danfe(
        self,
        chave_acesso: str,
        formato: str = "pdf",
    ) -> FiscalResult:
        return self._not_wired(
            "baixar_xml_danfe",
            {"chave_acesso": chave_acesso, "formato": formato},
        )

    def _not_wired(
        self, operation: str, payload: dict[str, Any]
    ) -> FiscalResult:
        return fiscal_response(
            False,
            {
                "provider": self.provider_name,
                "operation": operation,
                "payload": payload,
            },
            "WebMania provider is a scaffold stub and is not wired yet.",
        )
