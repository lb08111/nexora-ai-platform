# -*- coding: utf-8 -*-
"""Mercado Pago Pix provider stub."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Literal

from .base import AbstractPixProvider


class MercadoPagoPixProvider(AbstractPixProvider):
    """Provider placeholder for a future Mercado Pago integration."""

    name = "mercado_pago"

    async def create_immediate_charge(self, **kwargs: Any) -> dict[str, Any]:
        return self._not_implemented("create_immediate_charge")

    async def create_due_charge(self, **kwargs: Any) -> dict[str, Any]:
        return self._not_implemented("create_due_charge")

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
        return self._not_implemented("create_recurring_charge")

    async def get_charge(self, txid: str) -> dict[str, Any]:
        return self._not_implemented("get_charge", txid=txid)

    async def list_payments(
        self,
        *,
        inicio_iso: str,
        fim_iso: str,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        return []

    async def refund_pix(
        self,
        *,
        e2eid: str,
        valor: Decimal,
        motivo: str,
    ) -> dict[str, Any]:
        return self._not_implemented("refund_pix", e2eid=e2eid)

    async def parse_webhook(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "provider": self.name,
            "txid": payload.get("txid"),
            "status": payload.get("status", "received"),
            "e2eid": payload.get("e2eid"),
            "valor": payload.get("valor"),
            "raw": payload,
        }

    async def health(self) -> dict[str, Any]:
        return {
            "provider": self.name,
            "configured": False,
            "sandbox": True,
            "implemented": False,
        }

    def _not_implemented(self, operation: str, **extra: Any) -> dict[str, Any]:
        payload = {
            "provider": self.name,
            "operation": operation,
            "status": "NOT_IMPLEMENTED",
            "message": "Mercado Pago provider scaffold is not wired yet.",
        }
        payload.update(extra)
        return payload
