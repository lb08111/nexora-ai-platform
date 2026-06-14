# -*- coding: utf-8 -*-
"""Tools de consulta CNPJ/CEP e validação de CPF.

CPF/CNPJ: validação local (dígitos verificadores) — não precisa de rede.
CNPJ/CEP: stub que devolve estrutura compatível com BrasilAPI/ReceitaWS;
a integração real é uma troca de URL.
"""

from __future__ import annotations

import logging
import re

from agentscope.tool import ToolResponse

from ._utils import err, json_response

logger = logging.getLogger(__name__)


def _only_digits(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def _cpf_dv(digits: str) -> bool:
    if len(digits) != 11 or digits == digits[0] * 11:
        return False
    for i in (9, 10):
        s = sum(int(digits[j]) * ((i + 1) - j) for j in range(i))
        dv = (s * 10 % 11) % 10
        if dv != int(digits[i]):
            return False
    return True


def _cnpj_dv(digits: str) -> bool:
    if len(digits) != 14 or digits == digits[0] * 14:
        return False
    weights1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    weights2 = [6] + weights1
    for idx, weights in ((12, weights1), (13, weights2)):
        s = sum(int(digits[i]) * weights[i] for i in range(idx))
        dv = 11 - (s % 11)
        dv = 0 if dv >= 10 else dv
        if dv != int(digits[idx]):
            return False
    return True


async def validar_cpf(cpf: str) -> ToolResponse:
    """Valida um CPF brasileiro (dígitos verificadores, local).

    Args:
        cpf: CPF com ou sem formatação (``111.444.777-35`` ou só dígitos).

    Returns:
        ``ToolResponse``: JSON com ``valid`` (bool) e ``cpf`` normalizado.
    """
    digits = _only_digits(cpf)
    return json_response(
        {
            "cpf": digits,
            "formatted": (
                f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"
                if len(digits) == 11
                else cpf
            ),
            "valid": _cpf_dv(digits),
        },
    )


async def consultar_cnpj(cnpj: str) -> ToolResponse:
    """Consulta dados públicos de um CNPJ (stub, formato BrasilAPI).

    Args:
        cnpj: CNPJ com ou sem formatação.

    Returns:
        ``ToolResponse``: JSON com razao_social, nome_fantasia, situacao,
        endereco e cnae principal. Stub determinístico.
    """
    digits = _only_digits(cnpj)
    if not _cnpj_dv(digits):
        return err(f"CNPJ inválido: {cnpj!r}")
    # Stub determinístico (substituir por httpx GET BrasilAPI)
    return json_response(
        {
            "cnpj": digits,
            "razao_social": f"EMPRESA STUB {digits[-4:]} LTDA",
            "nome_fantasia": f"Stub {digits[-4:]}",
            "situacao": "ATIVA",
            "data_abertura": "2010-01-01",
            "cnae_principal": "47.99-9-99",
            "endereco": {
                "logradouro": "RUA EXEMPLO",
                "numero": "100",
                "bairro": "CENTRO",
                "municipio": "SAO PAULO",
                "uf": "SP",
                "cep": "01001000",
            },
            "note": "stub: trocar por httpx GET https://brasilapi.com.br/...",
        },
    )


async def consultar_cep(cep: str) -> ToolResponse:
    """Consulta endereço por CEP (stub, formato BrasilAPI/ViaCEP).

    Args:
        cep: CEP com ou sem hífen (``01001-000`` ou ``01001000``).

    Returns:
        ``ToolResponse``: JSON com logradouro, bairro, cidade, uf.
    """
    digits = _only_digits(cep)
    if len(digits) != 8:
        return err(f"CEP inválido (8 dígitos esperados): {cep!r}")
    return json_response(
        {
            "cep": f"{digits[:5]}-{digits[5:]}",
            "logradouro": "RUA EXEMPLO",
            "bairro": "CENTRO",
            "cidade": "SAO PAULO",
            "uf": "SP",
            "ibge": "3550308",
            "note": (
                "stub: trocar por httpx GET "
                "https://brasilapi.com.br/api/cep/v2/{cep}"
            ),
        },
    )
