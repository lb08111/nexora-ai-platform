# -*- coding: utf-8 -*-
"""LLM-callable fiscal tools for Nexora Fiscal.

Every tool validates its input with Pydantic and delegates the operation to
``AbstractFiscalProvider`` through the configured provider factory.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
)

from ..providers import build_provider, current_ambiente, current_provider_name

logger = logging.getLogger("qwenpaw").getChild(
    "plugin.nexora-fiscal.tools.fiscal_tools",
)

_DIGITS_RE = re.compile(r"\D+")


def _ok(data: Any) -> dict[str, Any]:
    return {"ok": True, "data": data, "error": None}


def _error(message: str, data: Any = None) -> dict[str, Any]:
    return {"ok": False, "data": data, "error": message}


def _only_digits(value: str) -> str:
    return _DIGITS_RE.sub("", value or "")


def _validate_cnpj_cpf(value: str, field_name: str = "documento") -> str:
    digits = _only_digits(value)
    if len(digits) not in (11, 14):
        raise ValueError(
            f"{field_name} deve ter CPF (11) ou CNPJ (14) dígitos"
        )
    if len(set(digits)) == 1:
        raise ValueError(f"{field_name} parece inválido")
    return digits


def _validate_cnpj(value: str, field_name: str = "CNPJ") -> str:
    digits = _only_digits(value)
    if len(digits) != 14:
        raise ValueError(f"{field_name} deve conter 14 dígitos")
    if len(set(digits)) == 1:
        raise ValueError(f"{field_name} parece inválido")
    return digits


def _configured_provider_or_error() -> (
    tuple[Any | None, dict[str, Any] | None]
):
    missing = []
    if not os.environ.get("FISCAL_API_KEY"):
        missing.append("FISCAL_API_KEY")
    if not os.environ.get("EMPRESA_CNPJ"):
        missing.append("EMPRESA_CNPJ")

    if missing:
        return None, _error(
            "Configuração fiscal incompleta. Defina as env vars ausentes.",
            {
                "missing_env_vars": missing,
                "provider": current_provider_name(),
                "ambiente": current_ambiente(),
                "safe_default": "FISCAL_AMBIENTE=homologacao",
            },
        )

    try:
        _validate_cnpj(os.environ.get("EMPRESA_CNPJ", ""), "EMPRESA_CNPJ")
    except ValueError as exc:
        return None, _error(str(exc), {"env_var": "EMPRESA_CNPJ"})

    return build_provider(), None


def _validation_error(exc: ValidationError) -> dict[str, Any]:
    return _error("Entrada inválida para ferramenta fiscal.", exc.errors())


async def _call_provider(method_name: str, *args: Any) -> dict[str, Any]:
    provider, error = _configured_provider_or_error()
    if error:
        return error
    try:
        method = getattr(provider, method_name)
        result = await method(*args)
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("Fiscal provider call failed: %s", method_name)
        return _error(f"Falha ao chamar provedor fiscal: {exc}")
    if not isinstance(result, dict) or "ok" not in result:
        return _ok(result)
    result.setdefault("data", None)
    result.setdefault("error", None)
    return result


class FiscalItem(BaseModel):
    """Flexible fiscal item accepted by NF-e/NFC-e payloads."""

    model_config = ConfigDict(extra="allow")

    descricao: str | None = Field(default=None, min_length=1)
    quantidade: float | None = Field(default=None, gt=0)
    valor_unitario: float | None = Field(default=None, ge=0)
    valor_total: float | None = Field(default=None, ge=0)
    ncm: str | None = None
    cfop: str | None = None


class NFeRequest(BaseModel):
    """Validated NF-e emission input."""

    model_config = ConfigDict(extra="allow")

    destinatario_cnpj_cpf: str
    itens: list[FiscalItem] = Field(min_length=1)
    valor_total: float = Field(gt=0)
    natureza_operacao: str = Field(min_length=3)
    destinatario: dict[str, Any] = Field(default_factory=dict)
    serie: int | None = Field(default=None, ge=1)
    numero: int | None = Field(default=None, ge=1)
    referencia: str | None = Field(default=None, min_length=1)

    @field_validator("destinatario_cnpj_cpf")
    @classmethod
    def validate_destinatario(cls, value: str) -> str:
        return _validate_cnpj_cpf(value, "destinatario_cnpj_cpf")


class NFSeRequest(BaseModel):
    """Validated NFS-e emission input."""

    model_config = ConfigDict(extra="allow")

    tomador: dict[str, Any]
    servico: dict[str, Any]
    valor: float = Field(gt=0)
    codigo_servico: str = Field(min_length=1)
    referencia: str | None = Field(default=None, min_length=1)
    municipio_prestacao: str | None = None

    @field_validator("tomador")
    @classmethod
    def validate_tomador(cls, value: dict[str, Any]) -> dict[str, Any]:
        doc = (
            value.get("cnpj_cpf")
            or value.get("cnpj")
            or value.get("cpf")
            or value.get("documento")
        )
        if not doc:
            raise ValueError(
                "tomador deve informar cnpj_cpf, cnpj, cpf ou documento"
            )
        value = dict(value)
        value["cnpj_cpf"] = _validate_cnpj_cpf(str(doc), "tomador")
        return value


class NFCeRequest(BaseModel):
    """Validated NFC-e emission input."""

    model_config = ConfigDict(extra="allow")

    itens: list[FiscalItem] = Field(min_length=1)
    valor_total: float = Field(gt=0)
    forma_pagamento: str = Field(min_length=2)
    destinatario_cnpj_cpf: str | None = None
    serie: int | None = Field(default=None, ge=1)
    numero: int | None = Field(default=None, ge=1)
    referencia: str | None = Field(default=None, min_length=1)

    @field_validator("destinatario_cnpj_cpf")
    @classmethod
    def validate_destinatario(cls, value: str | None) -> str | None:
        if not value:
            return value
        return _validate_cnpj_cpf(value, "destinatario_cnpj_cpf")


class ChaveRequest(BaseModel):
    """Validated access-key/reference input."""

    chave_acesso: str = Field(min_length=1)


class CancelRequest(ChaveRequest):
    """Validated cancellation input."""

    justificativa: str = Field(min_length=15)


class CartaCorrecaoRequest(ChaveRequest):
    """Validated correction letter input."""

    correcao: str = Field(min_length=15)


class InutilizacaoRequest(BaseModel):
    """Validated number voiding input."""

    serie: int = Field(ge=1)
    numero_inicial: int = Field(ge=1)
    numero_final: int = Field(ge=1)
    justificativa: str = Field(min_length=15)

    @field_validator("numero_final")
    @classmethod
    def validate_range(cls, value: int, info: Any) -> int:
        start = (
            info.data.get("numero_inicial") if hasattr(info, "data") else None
        )
        if start is not None and value < start:
            raise ValueError("numero_final deve ser maior ou igual ao inicial")
        return value


class DownloadRequest(ChaveRequest):
    """Validated DANFE/XML download input."""

    formato: Literal["pdf", "xml"] = "pdf"


async def emitir_nfe(
    destinatario_cnpj_cpf: str,
    itens: list[dict[str, Any]],
    valor_total: float,
    natureza_operacao: str,
    destinatario: dict[str, Any] | None = None,
    serie: int | None = None,
    numero: int | None = None,
    referencia: str | None = None,
    **extras: Any,
) -> dict[str, Any]:
    """Emite uma NF-e de produto no Brasil.

    Use quando houver venda de mercadoria/produto com destinatário identificado.
    Informe CNPJ/CPF do destinatário, itens fiscais (descrição, quantidade,
    valores, NCM/CFOP quando disponível), valor total e natureza da operação.
    A ferramenta valida documentos, exige provedor configurado e delega tudo ao
    provider fiscal (Focus NFe por padrão, homologação por segurança).
    """
    try:
        request = NFeRequest(
            destinatario_cnpj_cpf=destinatario_cnpj_cpf,
            itens=itens,
            valor_total=valor_total,
            natureza_operacao=natureza_operacao,
            destinatario=destinatario or {},
            serie=serie,
            numero=numero,
            referencia=referencia,
            **extras,
        )
    except ValidationError as exc:
        return _validation_error(exc)
    return await _call_provider(
        "emitir_nfe",
        request.model_dump(exclude_none=True),
    )


async def emitir_nfse(
    tomador: dict[str, Any],
    servico: dict[str, Any],
    valor: float,
    codigo_servico: str,
    referencia: str | None = None,
    municipio_prestacao: str | None = None,
    **extras: Any,
) -> dict[str, Any]:
    """Emite uma NFS-e de serviço.

    Use para prestação de serviços municipais. ``tomador`` deve incluir CNPJ
    ou CPF; ``servico`` deve conter descrição e dados tributários disponíveis;
    ``codigo_servico`` é o código municipal/LC 116 usado pelo emissor.
    """
    try:
        request = NFSeRequest(
            tomador=tomador,
            servico=servico,
            valor=valor,
            codigo_servico=codigo_servico,
            referencia=referencia,
            municipio_prestacao=municipio_prestacao,
            **extras,
        )
    except ValidationError as exc:
        return _validation_error(exc)
    return await _call_provider(
        "emitir_nfse",
        request.model_dump(exclude_none=True),
    )


async def emitir_nfce(
    itens: list[dict[str, Any]],
    valor_total: float,
    forma_pagamento: str,
    destinatario_cnpj_cpf: str | None = None,
    serie: int | None = None,
    numero: int | None = None,
    referencia: str | None = None,
    **extras: Any,
) -> dict[str, Any]:
    """Emite uma NFC-e de consumidor final.

    Use para venda presencial/PDV ao consumidor. Destinatário é opcional, mas
    se informado precisa ser CPF/CNPJ válido. ``forma_pagamento`` deve refletir
    o meio de pagamento usado na operação (pix, dinheiro, cartão etc.).
    """
    try:
        request = NFCeRequest(
            itens=itens,
            valor_total=valor_total,
            forma_pagamento=forma_pagamento,
            destinatario_cnpj_cpf=destinatario_cnpj_cpf,
            serie=serie,
            numero=numero,
            referencia=referencia,
            **extras,
        )
    except ValidationError as exc:
        return _validation_error(exc)
    return await _call_provider(
        "emitir_nfce",
        request.model_dump(exclude_none=True),
    )


async def consultar_nota(
    chave_acesso: str | None = None,
    nota_id: str | None = None,
) -> dict[str, Any]:
    """Consulta uma nota fiscal por chave de acesso ou ID/referência.

    Use para acompanhar autorização, rejeição, cancelamento ou processamento
    assíncrono de NF-e, NFS-e ou NFC-e. Informe ``chave_acesso`` quando tiver a
    chave SEFAZ; caso contrário, use ``nota_id``/referência do provedor.
    """
    try:
        request = ChaveRequest(chave_acesso=chave_acesso or nota_id or "")
    except ValidationError as exc:
        return _validation_error(exc)
    return await _call_provider("consultar_nota", request.chave_acesso)


async def cancelar_nota(
    chave_acesso: str, justificativa: str
) -> dict[str, Any]:
    """Cancela uma nota fiscal autorizada.

    Use somente após confirmação humana explícita. A justificativa deve ter no
    mínimo 15 caracteres, ser verdadeira e compatível com as regras SEFAZ.
    """
    try:
        request = CancelRequest(
            chave_acesso=chave_acesso,
            justificativa=justificativa,
        )
    except ValidationError as exc:
        return _validation_error(exc)
    return await _call_provider(
        "cancelar_nota",
        request.chave_acesso,
        request.justificativa,
    )


async def carta_correcao(chave_acesso: str, correcao: str) -> dict[str, Any]:
    """Emite carta de correção eletrônica para NF-e.

    Use para corrigir informações permitidas pela legislação sem alterar
    valores, impostos, destinatário essencial ou variáveis vedadas. O texto da
    correção deve ter no mínimo 15 caracteres.
    """
    try:
        request = CartaCorrecaoRequest(
            chave_acesso=chave_acesso,
            correcao=correcao,
        )
    except ValidationError as exc:
        return _validation_error(exc)
    return await _call_provider(
        "carta_correcao",
        request.chave_acesso,
        request.correcao,
    )


async def inutilizar_numeracao(
    serie: int,
    numero_inicial: int,
    numero_final: int,
    justificativa: str,
) -> dict[str, Any]:
    """Inutiliza uma faixa de numeração fiscal não utilizada.

    Use somente após confirmação humana explícita e quando houver quebra de
    sequência numérica. A justificativa precisa ter no mínimo 15 caracteres.
    """
    try:
        request = InutilizacaoRequest(
            serie=serie,
            numero_inicial=numero_inicial,
            numero_final=numero_final,
            justificativa=justificativa,
        )
    except ValidationError as exc:
        return _validation_error(exc)
    return await _call_provider(
        "inutilizar_numeracao",
        request.serie,
        request.numero_inicial,
        request.numero_final,
        request.justificativa,
    )


async def baixar_xml_danfe(
    chave_acesso: str,
    formato: Literal["pdf", "xml"] = "pdf",
) -> dict[str, Any]:
    """Baixa DANFE/PDF ou XML de uma nota fiscal.

    Use após autorização ou para auditoria. ``formato`` aceita somente ``pdf``
    para DANFE ou ``xml`` para o XML fiscal autorizado.
    """
    try:
        request = DownloadRequest(chave_acesso=chave_acesso, formato=formato)
    except ValidationError as exc:
        return _validation_error(exc)
    return await _call_provider(
        "baixar_xml_danfe",
        request.chave_acesso,
        request.formato,
    )
