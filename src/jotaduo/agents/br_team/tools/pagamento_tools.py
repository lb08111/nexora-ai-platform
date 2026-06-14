# -*- coding: utf-8 -*-
"""Tools de pagamento: Pix e links de pagamento (stubs).

Integração real fica em provedores como Gerencianet, Mercado Pago,
Asaas, PagBank, Stripe BR. O contrato aqui já reflete o que esses
provedores devolvem (txid, qr_code copia-e-cola, link).
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from threading import RLock
from uuid import uuid4

from agentscope.tool import ToolResponse

from ._utils import err, json_response
from .cnpj_cep_tools import _cnpj_dv, _cpf_dv  # noqa: F401

logger = logging.getLogger(__name__)

_PAYMENTS: dict[str, dict] = {}
_LOCK = RLock()


def _format_brl(cents: int) -> str:
    return f"R$ {cents / 100:.2f}".replace(".", ",")


async def gerar_cobranca_pix(
    valor_centavos: int,
    descricao: str,
    devedor_nome: str = "",
    devedor_cpf: str = "",
    expira_em_minutos: int = 30,
) -> ToolResponse:
    """Gera uma cobrança Pix (QR Code + copia-e-cola).

    Args:
        valor_centavos: Valor em centavos (ex. ``9990`` = R$ 99,90).
        descricao: Descrição que aparece no comprovante.
        devedor_nome: Nome do pagador (opcional, ajuda na conciliação).
        devedor_cpf: CPF do pagador apenas dígitos (opcional).
        expira_em_minutos: Validade do QR (padrão 30 min).

    Returns:
        ``ToolResponse``: JSON com ``txid``, ``qr_code`` (copia-e-cola
        de exemplo) e ``expires_at``.
    """
    if valor_centavos <= 0:
        return err("valor_centavos deve ser > 0")
    if not descricao.strip():
        return err("descricao é obrigatória")
    if devedor_cpf:
        digits = re.sub(r"\D", "", devedor_cpf)
        if not _cpf_dv(digits):
            return err(f"CPF inválido: {devedor_cpf!r}")
        devedor_cpf = digits

    txid = f"pix{uuid4().hex[:21]}"  # 22 chars min (PSP padrão BCB)
    expires = datetime.now(timezone.utc) + timedelta(minutes=expira_em_minutos)
    with _LOCK:
        _PAYMENTS[txid] = {
            "method": "pix",
            "valor_centavos": valor_centavos,
            "descricao": descricao,
            "devedor_nome": devedor_nome,
            "devedor_cpf": devedor_cpf,
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": expires.isoformat(),
        }
    logger.info(
        "[pix.stub] gerado %s valor=%s",
        txid,
        _format_brl(valor_centavos),
    )
    return json_response(
        {
            "txid": txid,
            "valor": _format_brl(valor_centavos),
            "valor_centavos": valor_centavos,
            "descricao": descricao,
            "expires_at": expires.isoformat(),
            "qr_code": (
                f"00020126360014BR.GOV.BCB.PIX0114STUB{txid}"
                f"520400005303986540{valor_centavos / 100:.2f}"
                "5802BR5913STUB MERCHANT6009SAO PAULO"
                f"62070503***6304STUB"
            ),
            "note": (
                "stub: substituir por provedor real (Gerencianet, "
                "Mercado Pago, Asaas, PagBank)."
            ),
        },
    )


async def gerar_link_pagamento(
    valor_centavos: int,
    descricao: str,
    metodos: str = "pix,credit_card,boleto",
    expira_em_horas: int = 24,
) -> ToolResponse:
    """Gera um link de pagamento (checkout transparente).

    Args:
        valor_centavos: Valor em centavos.
        descricao: Descrição do item/serviço.
        metodos: Lista CSV de métodos aceitos
            (``pix``, ``credit_card``, ``boleto``, ``debit_card``).
        expira_em_horas: Validade do link em horas.

    Returns:
        ``ToolResponse``: JSON com ``payment_id``, ``url`` e métodos.
    """
    if valor_centavos <= 0:
        return err("valor_centavos deve ser > 0")
    metodos_list = [m.strip() for m in metodos.split(",") if m.strip()]
    if not metodos_list:
        return err("informe ao menos um método de pagamento")

    payment_id = f"pl_{uuid4().hex[:12]}"
    expires = datetime.now(timezone.utc) + timedelta(hours=expira_em_horas)
    with _LOCK:
        _PAYMENTS[payment_id] = {
            "method": "link",
            "valor_centavos": valor_centavos,
            "descricao": descricao,
            "metodos": metodos_list,
            "status": "pending",
            "expires_at": expires.isoformat(),
        }
    return json_response(
        {
            "payment_id": payment_id,
            "url": f"https://pay.stub.jotaduo.local/c/{payment_id}",
            "valor": _format_brl(valor_centavos),
            "metodos": metodos_list,
            "expires_at": expires.isoformat(),
            "note": "stub",
        },
    )


async def consultar_status_pagamento(
    payment_id: str,
) -> ToolResponse:
    """Consulta o status de uma cobrança Pix ou link de pagamento.

    Args:
        payment_id: ``txid`` (Pix) ou ``payment_id`` (link).

    Returns:
        ``ToolResponse``: JSON com ``status`` (``pending`` | ``paid`` |
        ``expired`` | ``cancelled``) e timestamps.
    """
    with _LOCK:
        record = _PAYMENTS.get(payment_id)
    if record is None:
        return err(f"payment_id não encontrado: {payment_id}")
    expires_at = datetime.fromisoformat(record["expires_at"])
    if (
        record["status"] == "pending"
        and datetime.now(timezone.utc) > expires_at
    ):
        record["status"] = "expired"
    return json_response(
        {
            "payment_id": payment_id,
            "status": record["status"],
            "valor": _format_brl(record["valor_centavos"]),
            "method": record["method"],
            "expires_at": record["expires_at"],
        },
    )
