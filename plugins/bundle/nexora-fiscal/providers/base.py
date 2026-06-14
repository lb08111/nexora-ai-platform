# -*- coding: utf-8 -*-
"""Base fiscal provider interface used by Nexora Fiscal tools."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

FiscalResult = dict[str, Any]


def fiscal_response(
    ok: bool,
    data: Any = None,
    error: str | dict[str, Any] | None = None,
) -> FiscalResult:
    """Return the canonical tool/provider response shape."""
    return {"ok": ok, "data": data, "error": error}


class AbstractFiscalProvider(ABC):
    """Abstract interface for Brazilian fiscal document providers."""

    provider_name: str = "abstract"

    def __init__(
        self,
        api_key: str,
        ambiente: str = "homologacao",
        empresa_cnpj: str = "",
        empresa_ie: str = "",
        regime_tributario: str = "simples_nacional",
    ) -> None:
        self.api_key = api_key.strip()
        self.ambiente = (ambiente or "homologacao").strip().lower()
        self.empresa_cnpj = empresa_cnpj.strip()
        self.empresa_ie = empresa_ie.strip()
        self.regime_tributario = regime_tributario.strip()

    @abstractmethod
    async def emitir_nfe(self, payload: dict[str, Any]) -> FiscalResult:
        """Issue an NF-e through the provider."""

    @abstractmethod
    async def emitir_nfse(self, payload: dict[str, Any]) -> FiscalResult:
        """Issue an NFS-e through the provider."""

    @abstractmethod
    async def emitir_nfce(self, payload: dict[str, Any]) -> FiscalResult:
        """Issue an NFC-e through the provider."""

    @abstractmethod
    async def consultar_nota(self, chave_acesso: str) -> FiscalResult:
        """Query invoice status by access key or provider reference."""

    @abstractmethod
    async def cancelar_nota(
        self,
        chave_acesso: str,
        justificativa: str,
    ) -> FiscalResult:
        """Cancel an invoice by access key/reference."""

    @abstractmethod
    async def carta_correcao(
        self,
        chave_acesso: str,
        correcao: str,
    ) -> FiscalResult:
        """Emit a correction letter for an NF-e."""

    @abstractmethod
    async def inutilizar_numeracao(
        self,
        serie: int,
        numero_inicial: int,
        numero_final: int,
        justificativa: str,
    ) -> FiscalResult:
        """Void an unused invoice number range."""

    @abstractmethod
    async def baixar_xml_danfe(
        self,
        chave_acesso: str,
        formato: str = "pdf",
    ) -> FiscalResult:
        """Download XML or DANFE/PDF for an invoice."""
