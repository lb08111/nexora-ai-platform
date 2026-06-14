# -*- coding: utf-8 -*-
"""Abstract provider interface for Pix PSP adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Any, Literal


class AbstractPixProvider(ABC):
    """Async interface implemented by Pix providers."""

    name: str

    @abstractmethod
    async def create_immediate_charge(
        self,
        *,
        txid: str,
        valor: Decimal,
        devedor_cpf_cnpj: str,
        devedor_nome: str,
        descricao: str,
        expiracao_segundos: int,
    ) -> dict[str, Any]:
        """Create an immediate Pix charge and return PSP payload."""

    @abstractmethod
    async def create_due_charge(
        self,
        *,
        txid: str,
        valor: Decimal,
        devedor_cpf_cnpj: str,
        devedor_nome: str,
        vencimento_iso: str,
        juros_pct: Decimal,
        multa_pct: Decimal,
        desconto_pct: Decimal,
    ) -> dict[str, Any]:
        """Create a Pix charge with due date and fee policy."""

    @abstractmethod
    async def create_recurring_charge(
        self,
        *,
        txid: str,
        valor: Decimal,
        devedor_cpf_cnpj: str,
        periodicidade: Literal["mensal", "semanal", "anual"],
        data_inicio: str,
        qtd_cobrancas: int,
    ) -> dict[str, Any]:
        """Create or schedule a Pix recurring billing plan."""

    @abstractmethod
    async def get_charge(self, txid: str) -> dict[str, Any]:
        """Fetch a charge by txid."""

    @abstractmethod
    async def list_payments(
        self,
        *,
        inicio_iso: str,
        fim_iso: str,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        """List Pix payments or charges for reconciliation."""

    @abstractmethod
    async def refund_pix(
        self,
        *,
        e2eid: str,
        valor: Decimal,
        motivo: str,
    ) -> dict[str, Any]:
        """Request a Pix refund by E2EID."""

    @abstractmethod
    async def parse_webhook(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Normalize a PSP webhook payload to txid/status/e2eid fields."""

    @abstractmethod
    async def health(self) -> dict[str, Any]:
        """Return provider health without leaking secrets."""
