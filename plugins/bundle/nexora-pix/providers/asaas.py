# -*- coding: utf-8 -*-
"""Asaas Pix provider implementation.

The adapter uses Asaas v3-style endpoints and the required
``access_token`` header. In sandbox/offline mode it returns deterministic
mock responses so the plugin scaffold works without real credentials.
"""

from __future__ import annotations

import base64
import logging
import os
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from io import BytesIO
from typing import Any, Literal

import httpx
import qrcode

from .base import AbstractPixProvider

logger = logging.getLogger("qwenpaw").getChild(
    "plugin.nexora-pix.providers.asaas",
)


class AsaasPixProvider(AbstractPixProvider):
    """Asaas v3 Pix provider adapter."""

    name = "asaas"

    def __init__(self) -> None:
        self.api_key = os.getenv("PIX_API_KEY", "sandbox")
        self.ambiente = os.getenv("PIX_AMBIENTE", "sandbox")
        base_url = "https://api.asaas.com/v3"
        if self.ambiente.lower() == "sandbox":
            base_url = "https://sandbox.asaas.com/api/v3"
        self.base_url = os.getenv("ASAAS_BASE_URL", base_url).rstrip("/")

    @property
    def is_mock(self) -> bool:
        return self.api_key in {"", "sandbox"}

    @property
    def headers(self) -> dict[str, str]:
        return {
            "access_token": self.api_key,
            "accept": "application/json",
            "content-type": "application/json",
        }

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
        if self.is_mock:
            return self._mock_charge(
                txid=txid,
                valor=valor,
                devedor_nome=devedor_nome,
                descricao=descricao,
                kind="cob",
                expires_in=expiracao_segundos,
            )

        due_date = (datetime.now(UTC) + timedelta(seconds=expiracao_segundos))
        payment = await self._request(
            "POST",
            "/payments",
            json={
                "billingType": "PIX",
                "value": str(valor),
                "description": descricao,
                "externalReference": txid,
                "dueDate": due_date.date().isoformat(),
                "customer": {
                    "name": devedor_nome,
                    "cpfCnpj": devedor_cpf_cnpj,
                },
            },
        )
        qr_code = await self._request(
            "GET",
            f"/payments/{payment['id']}/pixQrCode",
        )
        return self._normalize_payment(payment, qr_code, txid=txid)

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
        if self.is_mock:
            return self._mock_charge(
                txid=txid,
                valor=valor,
                devedor_nome=devedor_nome,
                descricao="Cobrança Pix com vencimento",
                kind="cobv",
                extra={
                    "vencimento": vencimento_iso,
                    "juros_pct": str(juros_pct),
                    "multa_pct": str(multa_pct),
                    "desconto_pct": str(desconto_pct),
                },
            )

        payment = await self._request(
            "POST",
            "/payments",
            json={
                "billingType": "PIX",
                "value": str(valor),
                "description": "Cobrança Pix com vencimento",
                "externalReference": txid,
                "dueDate": vencimento_iso[:10],
                "fine": {"value": str(multa_pct)},
                "interest": {"value": str(juros_pct)},
                "discount": {
                    "value": str(desconto_pct),
                    "dueDateLimitDays": 0,
                    "type": "PERCENTAGE",
                },
                "customer": {
                    "name": devedor_nome,
                    "cpfCnpj": devedor_cpf_cnpj,
                },
            },
        )
        qr_code = await self._request(
            "GET",
            f"/payments/{payment['id']}/pixQrCode",
        )
        return self._normalize_payment(payment, qr_code, txid=txid)

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
        if self.is_mock:
            return self._mock_charge(
                txid=txid,
                valor=valor,
                devedor_nome=devedor_cpf_cnpj,
                descricao="Recorrência Pix",
                kind="recorrencia",
                extra={
                    "periodicidade": periodicidade,
                    "data_inicio": data_inicio,
                    "qtd_cobrancas": qtd_cobrancas,
                },
            )

        cycle = {
            "mensal": "MONTHLY",
            "semanal": "WEEKLY",
            "anual": "YEARLY",
        }[periodicidade]
        subscription = await self._request(
            "POST",
            "/subscriptions",
            json={
                "billingType": "PIX",
                "value": str(valor),
                "nextDueDate": data_inicio[:10],
                "cycle": cycle,
                "description": "Recorrência Pix",
                "externalReference": txid,
                "maxPayments": qtd_cobrancas,
                "customer": {"cpfCnpj": devedor_cpf_cnpj},
            },
        )
        return {
            "provider": self.name,
            "txid": txid,
            "status": subscription.get("status", "PENDING"),
            "subscription_id": subscription.get("id"),
            "raw": subscription,
        }

    async def get_charge(self, txid: str) -> dict[str, Any]:
        if self.is_mock:
            return self._mock_charge(
                txid=txid,
                valor=Decimal("0.00"),
                devedor_nome="Cliente sandbox",
                descricao="Consulta sandbox",
                kind="consulta",
            )

        data = await self._request(
            "GET",
            "/payments",
            params={"externalReference": txid},
        )
        items = data.get("data") or []
        if not items:
            return {"provider": self.name, "txid": txid, "status": "NOT_FOUND"}
        payment = items[0]
        qr_code = await self._request(
            "GET",
            f"/payments/{payment['id']}/pixQrCode",
        )
        return self._normalize_payment(payment, qr_code, txid=txid)

    async def list_payments(
        self,
        *,
        inicio_iso: str,
        fim_iso: str,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        if self.is_mock:
            return []

        params: dict[str, str] = {
            "billingType": "PIX",
            "dateCreated[ge]": inicio_iso[:10],
            "dateCreated[le]": fim_iso[:10],
        }
        if status:
            params["status"] = status
        data = await self._request("GET", "/payments", params=params)
        return list(data.get("data") or [])

    async def refund_pix(
        self,
        *,
        e2eid: str,
        valor: Decimal,
        motivo: str,
    ) -> dict[str, Any]:
        if self.is_mock:
            return {
                "provider": self.name,
                "e2eid": e2eid,
                "valor": str(valor),
                "motivo": motivo,
                "status": "REFUND_REQUESTED",
                "refund_id": f"rf_{e2eid[-12:]}",
            }

        return await self._request(
            "POST",
            f"/pix/transactions/{e2eid}/refund",
            json={"value": str(valor), "description": motivo},
        )

    async def parse_webhook(self, payload: dict[str, Any]) -> dict[str, Any]:
        payment = payload.get("payment") or payload.get("data") or payload
        txid = payment.get("externalReference") or payment.get("txid")
        status = payment.get("status") or payload.get("event") or "RECEIVED"
        pix = payment.get("pixTransaction") or payment.get("pix") or {}
        e2eid = pix.get("endToEndIdentifier") or pix.get("e2eid")
        value = payment.get("value") or payment.get("netValue")
        return {
            "provider": self.name,
            "txid": txid,
            "status": status,
            "e2eid": e2eid,
            "valor": str(value) if value is not None else None,
            "raw": payload,
        }

    async def health(self) -> dict[str, Any]:
        return {
            "provider": self.name,
            "configured": bool(self.api_key),
            "sandbox": self.ambiente.lower() == "sandbox" or self.is_mock,
            "base_url": self.base_url,
        }

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method,
                url,
                headers=self.headers,
                **kwargs,
            )
        response.raise_for_status()
        return response.json()

    def _normalize_payment(
        self,
        payment: dict[str, Any],
        qr_code: dict[str, Any],
        *,
        txid: str,
    ) -> dict[str, Any]:
        br_code = qr_code.get("payload") or qr_code.get("copyPaste") or ""
        image = qr_code.get("encodedImage") or ""
        return {
            "provider": self.name,
            "txid": txid,
            "psp_id": payment.get("id"),
            "status": payment.get("status", "PENDING"),
            "valor": str(payment.get("value", "")),
            "br_code": br_code,
            "qr_code_image_b64": image,
            "raw": {"payment": payment, "pixQrCode": qr_code},
        }

    def _mock_charge(
        self,
        *,
        txid: str,
        valor: Decimal,
        devedor_nome: str,
        descricao: str,
        kind: str,
        expires_in: int | None = None,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        br_code = (
            "00020101021226930014br.gov.bcb.pix"
            f"2571pix.sandbox.nexora.local/{txid}"
            "5204000053039865802BR5913NEXORA PIX6009SAO PAULO"
            "62070503***6304ABCD"
        )
        image = self._qr_png_b64(br_code)
        payload: dict[str, Any] = {
            "provider": self.name,
            "txid": txid,
            "status": "ATIVA",
            "valor": str(valor),
            "devedor_nome": devedor_nome,
            "descricao": descricao,
            "br_code": br_code,
            "qr_code_image_b64": image,
            "kind": kind,
            "ambiente": self.ambiente,
            "raw": {
                "id": f"pay_{txid}",
                "externalReference": txid,
                "status": "PENDING",
                "value": str(valor),
            },
        }
        if expires_in is not None:
            payload["expiracao_segundos"] = expires_in
        if extra:
            payload.update(extra)
        return payload

    @staticmethod
    def _qr_png_b64(text: str) -> str:
        img = qrcode.make(text)
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode("ascii")
