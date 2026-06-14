# -*- coding: utf-8 -*-
"""Pix billing tools exposed to the Jotaduo Cobrança agent."""

from __future__ import annotations

import base64
import logging
import os
import re
import secrets
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from io import BytesIO
from typing import Any, Literal

import qrcode
from pydantic import BaseModel, Field, field_validator

from ..providers import get_provider
from ..store.db import (
    get_cobranca,
    list_cobrancas,
    save_cobranca,
    update_payment,
)

logger = logging.getLogger("jotaduo").getChild("plugin.jotaduo-pix.tools")

TXID_RE = re.compile(r"^[A-Za-z0-9]{26,35}$")


def _ok(data: Any) -> dict[str, Any]:
    return {"ok": True, "data": data, "error": None}


def _err(message: str, data: Any = None) -> dict[str, Any]:
    return {"ok": False, "data": data, "error": message}


def _cpf_cnpj_digits(value: str) -> str:
    digits = re.sub(r"\D", "", value or "")
    if len(digits) not in {11, 14}:
        raise ValueError("CPF/CNPJ deve ter 11 ou 14 dígitos")
    if len(set(digits)) == 1:
        raise ValueError("CPF/CNPJ inválido")
    return digits


def _decimal_money(value: Any) -> Decimal:
    try:
        amount = Decimal(str(value)).quantize(Decimal("0.01"), ROUND_HALF_UP)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("Valor monetário inválido") from exc
    if amount <= Decimal("0.00"):
        raise ValueError("Valor deve ser maior que zero")
    return amount


def _decimal_pct(value: Any) -> Decimal:
    try:
        pct = Decimal(str(value)).quantize(Decimal("0.01"), ROUND_HALF_UP)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("Percentual inválido") from exc
    if pct < Decimal("0.00"):
        raise ValueError("Percentual não pode ser negativo")
    return pct


def _generate_txid() -> str:
    return secrets.token_hex(13)[:26]


def _validate_txid(txid: str) -> str:
    if not TXID_RE.fullmatch(txid):
        raise ValueError("txid deve ser alfanumérico e ter 26 a 35 caracteres")
    return txid


class ImmediateChargeInput(BaseModel):
    valor: Decimal
    devedor_cpf_cnpj: str
    devedor_nome: str = Field(..., min_length=2)
    descricao: str = Field(..., min_length=1, max_length=140)
    expiracao_segundos: int = Field(default=3600, ge=60, le=86400)
    txid: str | None = None

    @field_validator("valor", mode="before")
    @classmethod
    def validate_amount(cls, value: Any) -> Decimal:
        return _decimal_money(value)

    @field_validator("devedor_cpf_cnpj")
    @classmethod
    def validate_doc(cls, value: str) -> str:
        return _cpf_cnpj_digits(value)

    @field_validator("txid")
    @classmethod
    def validate_optional_txid(cls, value: str | None) -> str | None:
        return _validate_txid(value) if value else None


class DueChargeInput(BaseModel):
    valor: Decimal
    devedor_cpf_cnpj: str
    devedor_nome: str = Field(..., min_length=2)
    vencimento_iso: str = Field(..., min_length=10)
    juros_pct: Decimal = Decimal("0.00")
    multa_pct: Decimal = Decimal("0.00")
    desconto_pct: Decimal = Decimal("0.00")
    txid: str | None = None

    @field_validator("valor", mode="before")
    @classmethod
    def validate_amount(cls, value: Any) -> Decimal:
        return _decimal_money(value)

    @field_validator("juros_pct", "multa_pct", "desconto_pct", mode="before")
    @classmethod
    def validate_percent(cls, value: Any) -> Decimal:
        return _decimal_pct(value)

    @field_validator("devedor_cpf_cnpj")
    @classmethod
    def validate_doc(cls, value: str) -> str:
        return _cpf_cnpj_digits(value)

    @field_validator("txid")
    @classmethod
    def validate_optional_txid(cls, value: str | None) -> str | None:
        return _validate_txid(value) if value else None


class RecurrenceInput(BaseModel):
    valor: Decimal
    devedor_cpf_cnpj: str
    periodicidade: Literal["mensal", "semanal", "anual"]
    data_inicio: str = Field(..., min_length=10)
    qtd_cobrancas: int = Field(..., ge=1, le=120)
    txid: str | None = None

    @field_validator("valor", mode="before")
    @classmethod
    def validate_amount(cls, value: Any) -> Decimal:
        return _decimal_money(value)

    @field_validator("devedor_cpf_cnpj")
    @classmethod
    def validate_doc(cls, value: str) -> str:
        return _cpf_cnpj_digits(value)

    @field_validator("txid")
    @classmethod
    def validate_optional_txid(cls, value: str | None) -> str | None:
        return _validate_txid(value) if value else None


class TxidInput(BaseModel):
    txid: str

    @field_validator("txid")
    @classmethod
    def validate_txid(cls, value: str) -> str:
        return _validate_txid(value)


class ListReceiptsInput(BaseModel):
    inicio_iso: str = Field(..., min_length=10)
    fim_iso: str = Field(..., min_length=10)
    status: str | None = None


class ReconcileInput(BaseModel):
    txid: str
    valor_recebido: Decimal
    e2eid: str = Field(..., min_length=10)

    @field_validator("txid")
    @classmethod
    def validate_txid(cls, value: str) -> str:
        return _validate_txid(value)

    @field_validator("valor_recebido", mode="before")
    @classmethod
    def validate_amount(cls, value: Any) -> Decimal:
        return _decimal_money(value)


class RefundInput(BaseModel):
    e2eid: str = Field(..., min_length=10)
    valor: Decimal
    motivo: str = Field(..., min_length=3, max_length=140)

    @field_validator("valor", mode="before")
    @classmethod
    def validate_amount(cls, value: Any) -> Decimal:
        return _decimal_money(value)


class StaticQrInput(BaseModel):
    chave_pix: str = Field(..., min_length=3)
    valor: Decimal | None = None
    descricao: str = Field(default="", max_length=72)

    @field_validator("valor", mode="before")
    @classmethod
    def validate_optional_amount(cls, value: Any) -> Decimal | None:
        if value is None or value == "":
            return None
        return _decimal_money(value)


async def criar_cobranca_pix(
    valor: float,
    devedor_cpf_cnpj: str,
    devedor_nome: str,
    descricao: str,
    expiracao_segundos: int = 3600,
    txid: str | None = None,
) -> dict[str, Any]:
    """Cria cobrança Pix imediata com QR Code dinâmico e BR Code.

    Args:
        valor: Valor em reais. Convertido para Decimal internamente.
        devedor_cpf_cnpj: CPF/CNPJ do pagador, com ou sem pontuação.
        devedor_nome: Nome do pagador.
        descricao: Descrição curta da cobrança.
        expiracao_segundos: Tempo de expiração do QR dinâmico.
    """
    try:
        body = ImmediateChargeInput(
            valor=valor,
            devedor_cpf_cnpj=devedor_cpf_cnpj,
            devedor_nome=devedor_nome,
            descricao=descricao,
            expiracao_segundos=expiracao_segundos,
            txid=txid,
        )
        provider = get_provider()
        txid = body.txid or _generate_txid()
        existing = await get_cobranca(txid, provider.name)
        if existing:
            return _ok(existing)
        result = await provider.create_immediate_charge(
            txid=txid,
            valor=body.valor,
            devedor_cpf_cnpj=body.devedor_cpf_cnpj,
            devedor_nome=body.devedor_nome,
            descricao=body.descricao,
            expiracao_segundos=body.expiracao_segundos,
        )
        if result.get("status") == "NOT_IMPLEMENTED":
            return _err(result["message"], result)
        stored = await save_cobranca(
            txid=txid,
            provider=provider.name,
            valor=body.valor,
            devedor=body.devedor_cpf_cnpj,
            status=str(result.get("status", "ATIVA")),
            br_code=result.get("br_code"),
            raw_response=result,
        )
        data = {**result, "store": stored}
        return _ok(data)
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("criar_cobranca_pix failed: %s", exc)
        return _err(str(exc))


async def criar_cobranca_com_vencimento(
    valor: float,
    devedor_cpf_cnpj: str,
    devedor_nome: str,
    vencimento_iso: str,
    juros_pct: float = 0,
    multa_pct: float = 0,
    desconto_pct: float = 0,
    txid: str | None = None,
) -> dict[str, Any]:
    """Cria cobrança Pix com vencimento, juros, multa e desconto.

    Retorna payload com ``txid``, ``br_code`` e imagem QR Code quando o
    PSP disponibilizar esses campos.
    """
    try:
        body = DueChargeInput(
            valor=valor,
            devedor_cpf_cnpj=devedor_cpf_cnpj,
            devedor_nome=devedor_nome,
            vencimento_iso=vencimento_iso,
            juros_pct=juros_pct,
            multa_pct=multa_pct,
            desconto_pct=desconto_pct,
            txid=txid,
        )
        provider = get_provider()
        txid = body.txid or _generate_txid()
        existing = await get_cobranca(txid, provider.name)
        if existing:
            return _ok(existing)
        result = await provider.create_due_charge(
            txid=txid,
            valor=body.valor,
            devedor_cpf_cnpj=body.devedor_cpf_cnpj,
            devedor_nome=body.devedor_nome,
            vencimento_iso=body.vencimento_iso,
            juros_pct=body.juros_pct,
            multa_pct=body.multa_pct,
            desconto_pct=body.desconto_pct,
        )
        if result.get("status") == "NOT_IMPLEMENTED":
            return _err(result["message"], result)
        stored = await save_cobranca(
            txid=txid,
            provider=provider.name,
            valor=body.valor,
            devedor=body.devedor_cpf_cnpj,
            status=str(result.get("status", "ATIVA")),
            br_code=result.get("br_code"),
            raw_response=result,
        )
        return _ok({**result, "store": stored})
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("criar_cobranca_com_vencimento failed: %s", exc)
        return _err(str(exc))


async def criar_recorrencia(
    valor: float,
    devedor_cpf_cnpj: str,
    periodicidade: Literal["mensal", "semanal", "anual"],
    data_inicio: str,
    qtd_cobrancas: int,
    txid: str | None = None,
) -> dict[str, Any]:
    """Cria ou agenda recorrência Pix para mensalidade/assinatura."""
    try:
        body = RecurrenceInput(
            valor=valor,
            devedor_cpf_cnpj=devedor_cpf_cnpj,
            periodicidade=periodicidade,
            data_inicio=data_inicio,
            qtd_cobrancas=qtd_cobrancas,
            txid=txid,
        )
        provider = get_provider()
        txid = body.txid or _generate_txid()
        existing = await get_cobranca(txid, provider.name)
        if existing:
            return _ok(existing)
        result = await provider.create_recurring_charge(
            txid=txid,
            valor=body.valor,
            devedor_cpf_cnpj=body.devedor_cpf_cnpj,
            periodicidade=body.periodicidade,
            data_inicio=body.data_inicio,
            qtd_cobrancas=body.qtd_cobrancas,
        )
        if result.get("status") == "NOT_IMPLEMENTED":
            return _err(result["message"], result)
        stored = await save_cobranca(
            txid=txid,
            provider=provider.name,
            valor=body.valor,
            devedor=body.devedor_cpf_cnpj,
            status=str(result.get("status", "AGENDADA")),
            br_code=result.get("br_code"),
            raw_response=result,
        )
        return _ok({**result, "store": stored})
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("criar_recorrencia failed: %s", exc)
        return _err(str(exc))


async def consultar_cobranca(txid: str) -> dict[str, Any]:
    """Consulta cobrança por txid no store e, se necessário, no PSP."""
    try:
        body = TxidInput(txid=txid)
        provider = get_provider()
        stored = await get_cobranca(body.txid, provider.name)
        remote = await provider.get_charge(body.txid)
        return _ok({"store": stored, "provider": remote})
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("consultar_cobranca failed: %s", exc)
        return _err(str(exc))


async def listar_recebimentos(
    inicio_iso: str,
    fim_iso: str,
    status: str | None = None,
) -> dict[str, Any]:
    """Lista recebimentos do período no store local e no PSP configurado."""
    try:
        body = ListReceiptsInput(
            inicio_iso=inicio_iso,
            fim_iso=fim_iso,
            status=status,
        )
        provider = get_provider()
        local = await list_cobrancas(
            inicio_iso=body.inicio_iso,
            fim_iso=body.fim_iso,
            status=body.status,
        )
        remote = await provider.list_payments(
            inicio_iso=body.inicio_iso,
            fim_iso=body.fim_iso,
            status=body.status,
        )
        return _ok({"store": local, "provider": remote})
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("listar_recebimentos failed: %s", exc)
        return _err(str(exc))


async def conciliar_pagamento(
    txid: str,
    valor_recebido: float,
    e2eid: str,
) -> dict[str, Any]:
    """Concilia pagamento Pix validando txid, valor recebido e E2EID."""
    try:
        body = ReconcileInput(
            txid=txid,
            valor_recebido=valor_recebido,
            e2eid=e2eid,
        )
        provider = get_provider()
        stored = await get_cobranca(body.txid, provider.name)
        if not stored:
            return _err("Cobrança não encontrada para conciliação")
        expected = Decimal(str(stored["valor"])).quantize(Decimal("0.01"))
        if expected != body.valor_recebido:
            return _err(
                "Valor recebido divergente",
                {
                    "esperado": str(expected),
                    "recebido": str(body.valor_recebido),
                },
            )
        updated = await update_payment(
            txid=body.txid,
            provider=provider.name,
            valor_recebido=body.valor_recebido,
            e2eid=body.e2eid,
            raw_response={"source": "manual_reconciliation"},
        )
        return _ok(updated)
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("conciliar_pagamento failed: %s", exc)
        return _err(str(exc))


async def devolver_pix(
    e2eid: str,
    valor: float,
    motivo: str,
) -> dict[str, Any]:
    """Solicita devolução Pix ao PSP pelo E2EID e valor informado."""
    try:
        body = RefundInput(e2eid=e2eid, valor=valor, motivo=motivo)
        provider = get_provider()
        result = await provider.refund_pix(
            e2eid=body.e2eid,
            valor=body.valor,
            motivo=body.motivo,
        )
        if result.get("status") == "NOT_IMPLEMENTED":
            return _err(result["message"], result)
        return _ok(result)
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("devolver_pix failed: %s", exc)
        return _err(str(exc))


async def gerar_qr_code_estatico(
    chave_pix: str,
    valor: float | None,
    descricao: str,
) -> dict[str, Any]:
    """Gera QR Code Pix estático localmente sem chamada ao PSP.

    Retorna imagem PNG em base64 e um BR Code simples para copia-e-cola.
    """
    try:
        key = chave_pix or os.getenv("PIX_CHAVE", "")
        body = StaticQrInput(chave_pix=key, valor=valor, descricao=descricao)
        br_code = _build_static_brcode(
            chave_pix=body.chave_pix,
            valor=body.valor,
            descricao=body.descricao,
        )
        img = qrcode.make(br_code)
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        image_b64 = base64.b64encode(buffer.getvalue()).decode("ascii")
        return _ok(
            {
                "br_code": br_code,
                "qr_code_image_b64": image_b64,
                "valor": str(body.valor) if body.valor is not None else None,
                "descricao": body.descricao,
            },
        )
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("gerar_qr_code_estatico failed: %s", exc)
        return _err(str(exc))


def _build_static_brcode(
    *,
    chave_pix: str,
    valor: Decimal | None,
    descricao: str,
) -> str:
    merchant_name = "JOTADUO PIX"[:25]
    merchant_city = "SAO PAULO"[:15]
    gui = _emv("00", "br.gov.bcb.pix")
    key = _emv("01", chave_pix)
    desc = _emv("02", descricao[:72]) if descricao else ""
    account = _emv("26", gui + key + desc)
    amount = _emv("54", f"{valor:.2f}") if valor is not None else ""
    payload = (
        _emv("00", "01")
        + _emv("01", "11")
        + account
        + _emv("52", "0000")
        + _emv("53", "986")
        + amount
        + _emv("58", "BR")
        + _emv("59", merchant_name)
        + _emv("60", merchant_city)
        + _emv("62", _emv("05", "***"))
    )
    crc_input = payload + "6304"
    return crc_input + _crc16_ccitt(crc_input)


def _emv(tag: str, value: str) -> str:
    raw = value or ""
    return f"{tag}{len(raw):02d}{raw}"


def _crc16_ccitt(payload: str) -> str:
    crc = 0xFFFF
    for char in payload.encode("utf-8"):
        crc ^= char << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return f"{crc:04X}"
