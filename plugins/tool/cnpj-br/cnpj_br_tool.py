# -*- coding: utf-8 -*-
# pylint: disable=too-many-return-statements,too-many-branches
# pylint: disable=too-many-statements,too-many-locals
"""Ferramentas de consulta cadastral brasileira para o plugin cnpj-br."""

import logging
import re
from typing import Any, Optional

try:
    from jotaduo.plugins import get_tool_config
except (
    Exception
):  # pragma: no cover - available inside Jotaduo/JotaDuo runtime

    def get_tool_config(_tool_name: str) -> dict[str, Any]:
        return {}


try:
    from clients import BrasilApiClient, ReceitaWsClient
    from validators import (
        formatar_cnpj,
        formatar_cpf,
        limpar_documento,
        validar_cep,
        validar_cnpj,
        validar_cpf,
    )
except ImportError:  # pragma: no cover - package import fallback
    from .clients import BrasilApiClient, ReceitaWsClient
    from .validators import (
        formatar_cnpj,
        formatar_cpf,
        limpar_documento,
        validar_cep,
        validar_cnpj,
        validar_cpf,
    )

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 15.0
_DEFAULT_CACHE_TTL = 3600
_PROVIDER_OPTIONS = {"brasilapi", "receitaws", "auto"}
_DEFAULT_HIGH_VALUE_CNAE_PREFIXES = {
    "620",
    "631",
    "642",
    "646",
    "649",
    "702",
    "711",
    "721",
    "722",
    "749",
    "861",
    "862",
    "863",
}
_FREE_EMAIL_DOMAINS = {
    "gmail.com",
    "hotmail.com",
    "outlook.com",
    "yahoo.com",
    "icloud.com",
    "live.com",
    "uol.com.br",
    "bol.com.br",
}


def _result(
    ok: bool,
    data: dict[str, Any] | None,
    error: str | None,
    fonte: str,
) -> dict[str, Any]:
    return {"ok": ok, "data": data, "error": error, "fonte": fonte}


def _is_client_error(payload: dict[str, Any]) -> bool:
    return payload.get("ok") is False and "error" in payload


def _provider_error(payload: dict[str, Any]) -> str:
    return str(payload.get("error") or "Fonte pública indisponível.")


def _coerce_timeout(value: Any) -> float:
    try:
        timeout = float(value)
    except (TypeError, ValueError):
        timeout = _DEFAULT_TIMEOUT
    return min(max(timeout, 5.0), 60.0)


def _coerce_ttl(value: Any) -> int:
    try:
        ttl = int(value)
    except (TypeError, ValueError):
        ttl = _DEFAULT_CACHE_TTL
    return max(ttl, 0)


def _settings(tool_name: str) -> tuple[str, float, int, set[str]]:
    config = get_tool_config(tool_name) or {}
    provider = str(config.get("provider_fallback") or "auto").lower()
    if provider not in _PROVIDER_OPTIONS:
        provider = "auto"

    high_value = config.get("cnaes_alto_valor")
    if isinstance(high_value, str):
        cnaes = {limpar_documento(item) for item in high_value.split(",")}
        cnaes = {item for item in cnaes if item}
    elif isinstance(high_value, (list, tuple, set)):
        cnaes = {limpar_documento(str(item)) for item in high_value if item}
    else:
        cnaes = set(_DEFAULT_HIGH_VALUE_CNAE_PREFIXES)

    return (
        provider,
        _coerce_timeout(config.get("timeout")),
        _coerce_ttl(config.get("cache_ttl_seconds")),
        cnaes or set(_DEFAULT_HIGH_VALUE_CNAE_PREFIXES),
    )


def _formatar_cep(cep: Any) -> str | None:
    digits = limpar_documento(str(cep or ""))
    if len(digits) != 8:
        return str(cep).strip() if cep else None
    return f"{digits[:5]}-{digits[5:]}"


def _str_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalizar_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"sim", "s", "true", "1", "yes", "y"}:
        return True
    if text in {"não", "nao", "n", "false", "0", "no", ""}:
        return False
    return None


def _parse_capital_social(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).replace("R$", "").replace(" ", "").strip()
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def _normalizar_cnae_principal_brasilapi(
    raw: dict[str, Any],
) -> dict[str, Any] | None:
    codigo = raw.get("cnae_fiscal") or raw.get("cnae_fiscal_codigo")
    descricao = raw.get("cnae_fiscal_descricao")
    if not codigo and not descricao:
        return None
    return {
        "codigo": _str_or_none(codigo),
        "descricao": _str_or_none(descricao),
    }


def _normalizar_cnae_principal_receitaws(
    raw: dict[str, Any],
) -> dict[str, Any] | None:
    atividades = raw.get("atividade_principal") or []
    if not atividades:
        return None
    principal = atividades[0] or {}
    return {
        "codigo": _str_or_none(principal.get("code")),
        "descricao": _str_or_none(principal.get("text")),
    }


def _normalizar_cnaes_secundarios(
    items: Any,
    fonte: str,
) -> list[dict[str, Any]]:
    if not isinstance(items, list):
        return []
    normalized = []
    for item in items:
        if not isinstance(item, dict):
            continue
        if fonte == "brasilapi":
            codigo = item.get("codigo") or item.get("code")
            descricao = item.get("descricao") or item.get("text")
        else:
            codigo = item.get("code") or item.get("codigo")
            descricao = item.get("text") or item.get("descricao")
        normalized.append(
            {
                "codigo": _str_or_none(codigo),
                "descricao": _str_or_none(descricao),
            },
        )
    return normalized


def _normalizar_socios(items: Any, fonte: str) -> list[dict[str, Any]]:
    if not isinstance(items, list):
        return []
    socios = []
    for item in items:
        if not isinstance(item, dict):
            continue
        if fonte == "brasilapi":
            nome = item.get("nome_socio") or item.get("nome")
            qualificacao = item.get("qualificacao_socio") or item.get("qual")
        else:
            nome = item.get("nome") or item.get("nome_socio")
            qualificacao = item.get("qual") or item.get("qualificacao_socio")
        socios.append(
            {
                "nome": _str_or_none(nome),
                "qualificacao": _str_or_none(qualificacao),
                "cpf_cnpj": _str_or_none(
                    item.get("cnpj_cpf_do_socio")
                    or item.get("cpf_cnpj")
                    or item.get("cpf_representante_legal"),
                ),
            },
        )
    return socios


def _normalizar_brasilapi(raw: dict[str, Any]) -> dict[str, Any]:
    telefone = raw.get("ddd_telefone_1") or raw.get("ddd_telefone_2")
    logradouro = " ".join(
        item
        for item in [
            _str_or_none(raw.get("descricao_tipo_de_logradouro")),
            _str_or_none(raw.get("logradouro")),
        ]
        if item
    )
    simples_optante = _normalizar_bool(raw.get("opcao_pelo_simples"))
    mei_optante = _normalizar_bool(raw.get("opcao_pelo_mei"))

    return {
        "cnpj": formatar_cnpj(str(raw.get("cnpj") or "")),
        "razao_social": _str_or_none(raw.get("razao_social")),
        "nome_fantasia": _str_or_none(raw.get("nome_fantasia")),
        "situacao": _str_or_none(
            raw.get("descricao_situacao_cadastral")
            or raw.get("situacao_cadastral"),
        ),
        "data_situacao": _str_or_none(raw.get("data_situacao_cadastral")),
        "abertura": _str_or_none(raw.get("data_inicio_atividade")),
        "natureza_juridica": _str_or_none(raw.get("natureza_juridica")),
        "capital_social": _parse_capital_social(raw.get("capital_social")),
        "endereco": {
            "logradouro": _str_or_none(logradouro),
            "numero": _str_or_none(raw.get("numero")),
            "complemento": _str_or_none(raw.get("complemento")),
            "bairro": _str_or_none(raw.get("bairro")),
            "municipio": _str_or_none(raw.get("municipio")),
            "uf": _str_or_none(raw.get("uf")),
            "cep": _formatar_cep(raw.get("cep")),
        },
        "telefone": _str_or_none(telefone),
        "email": _str_or_none(raw.get("email")),
        "cnae_principal": _normalizar_cnae_principal_brasilapi(raw),
        "cnaes_secundarios": _normalizar_cnaes_secundarios(
            raw.get("cnaes_secundarios"),
            "brasilapi",
        ),
        "socios": _normalizar_socios(raw.get("qsa"), "brasilapi"),
        "simples": {
            "optante": simples_optante,
            "data_opcao": _str_or_none(raw.get("data_opcao_pelo_simples")),
        },
        "mei": {"optante": mei_optante},
    }


def _normalizar_receitaws(raw: dict[str, Any]) -> dict[str, Any]:
    simples = (
        raw.get("simples") if isinstance(raw.get("simples"), dict) else {}
    )
    simei = raw.get("simei") if isinstance(raw.get("simei"), dict) else {}
    return {
        "cnpj": formatar_cnpj(str(raw.get("cnpj") or "")),
        "razao_social": _str_or_none(raw.get("nome")),
        "nome_fantasia": _str_or_none(raw.get("fantasia")),
        "situacao": _str_or_none(raw.get("situacao")),
        "data_situacao": _str_or_none(raw.get("data_situacao")),
        "abertura": _str_or_none(raw.get("abertura")),
        "natureza_juridica": _str_or_none(raw.get("natureza_juridica")),
        "capital_social": _parse_capital_social(raw.get("capital_social")),
        "endereco": {
            "logradouro": _str_or_none(raw.get("logradouro")),
            "numero": _str_or_none(raw.get("numero")),
            "complemento": _str_or_none(raw.get("complemento")),
            "bairro": _str_or_none(raw.get("bairro")),
            "municipio": _str_or_none(raw.get("municipio")),
            "uf": _str_or_none(raw.get("uf")),
            "cep": _formatar_cep(raw.get("cep")),
        },
        "telefone": _str_or_none(raw.get("telefone")),
        "email": _str_or_none(raw.get("email")),
        "cnae_principal": _normalizar_cnae_principal_receitaws(raw),
        "cnaes_secundarios": _normalizar_cnaes_secundarios(
            raw.get("atividades_secundarias"),
            "receitaws",
        ),
        "socios": _normalizar_socios(raw.get("qsa"), "receitaws"),
        "simples": {
            "optante": _normalizar_bool(simples.get("optante")),
            "data_opcao": _str_or_none(simples.get("data_opcao")),
        },
        "mei": {"optante": _normalizar_bool(simei.get("optante"))},
    }


def _provider_order(provider: str) -> list[str]:
    if provider == "brasilapi":
        return ["brasilapi"]
    if provider == "receitaws":
        return ["receitaws"]
    return ["brasilapi", "receitaws"]


async def _consultar_cnpj_impl(
    cnpj: str,
    config_tool_name: str,
) -> dict[str, Any]:
    cnpj_limpo = limpar_documento(cnpj)
    if not validar_cnpj(cnpj_limpo):
        return _result(
            False,
            None,
            "CNPJ inválido. Verifique os 14 dígitos informados.",
            "offline",
        )

    provider, timeout, cache_ttl, _ = _settings(config_tool_name)
    brasilapi = BrasilApiClient(timeout=timeout, cache_ttl_seconds=cache_ttl)
    receitaws = ReceitaWsClient(timeout=timeout, cache_ttl_seconds=cache_ttl)
    last_error = "Registro não encontrado nas fontes públicas."
    last_source = "brasilapi"

    for source in _provider_order(provider):
        last_source = source
        if source == "brasilapi":
            payload = await brasilapi.cnpj(cnpj_limpo)
            if not _is_client_error(payload):
                return _result(
                    True,
                    _normalizar_brasilapi(payload),
                    None,
                    "brasilapi",
                )
            last_error = _provider_error(payload)
            logger.info("BrasilAPI CNPJ lookup failed: %s", last_error)
            continue

        payload = await receitaws.cnpj(cnpj_limpo)
        if not _is_client_error(payload) and payload.get("status") != "ERROR":
            return _result(
                True,
                _normalizar_receitaws(payload),
                None,
                "receitaws",
            )
        last_error = (
            _provider_error(payload)
            if _is_client_error(payload)
            else str(
                payload.get("message")
                or "ReceitaWS não retornou dados para o CNPJ.",
            )
        )
        logger.info("ReceitaWS CNPJ lookup failed: %s", last_error)

    return _result(
        False,
        None,
        f"Não foi possível consultar o CNPJ: {last_error}",
        last_source,
    )


async def consultar_cnpj(cnpj: str) -> dict[str, Any]:
    """Consulta um CNPJ brasileiro em fontes públicas.

    Valida o CNPJ offline, consulta primeiro a BrasilAPI (gratuita e sem chave)
    e, em modo automático, usa ReceitaWS como fallback. Retorna um cadastro
    normalizado com razão social, situação, endereço, CNAE, sócios, Simples e MEI.
    """
    return await _consultar_cnpj_impl(cnpj, "consultar_cnpj")


async def consultar_cep(cep: str) -> dict[str, Any]:
    """Consulta endereço por CEP na BrasilAPI.

    Use para obter logradouro, bairro, cidade, UF e código IBGE a partir de um
    CEP brasileiro. A validação local exige exatamente 8 dígitos antes da chamada.
    """
    cep_limpo = limpar_documento(cep)
    if not validar_cep(cep_limpo):
        return _result(
            False,
            None,
            "CEP inválido. Informe exatamente 8 dígitos.",
            "offline",
        )

    _, timeout, cache_ttl, _ = _settings("consultar_cep")
    payload = await BrasilApiClient(
        timeout=timeout,
        cache_ttl_seconds=cache_ttl,
    ).cep(
        cep_limpo,
    )
    if _is_client_error(payload):
        return _result(False, None, _provider_error(payload), "brasilapi")

    data = {
        "cep": _formatar_cep(payload.get("cep") or cep_limpo),
        "logradouro": _str_or_none(
            payload.get("street") or payload.get("logradouro"),
        ),
        "bairro": _str_or_none(
            payload.get("neighborhood") or payload.get("bairro"),
        ),
        "cidade": _str_or_none(payload.get("city") or payload.get("cidade")),
        "uf": _str_or_none(payload.get("state") or payload.get("uf")),
        "ibge": _str_or_none(payload.get("city_ibge") or payload.get("ibge")),
    }
    return _result(True, data, None, "brasilapi")


async def consultar_cpf(cpf: str) -> dict[str, Any]:
    """Valida CPF offline pelo dígito verificador.

    Esta ferramenta NÃO consulta dados pessoais na Receita Federal. Não existe
    API pública gratuita oficial para dados cadastrais de CPF; por isso o retorno
    informa apenas validade matemática, documento limpo e formato padronizado.
    """
    cpf_limpo = limpar_documento(cpf)
    valido = validar_cpf(cpf_limpo)
    data = {
        "cpf": cpf_limpo,
        "cpf_formatado": formatar_cpf(cpf_limpo)
        if len(cpf_limpo) == 11
        else None,
        "valido": valido,
        "observacao": (
            "Validação offline por dígito verificador; não consulta dados pessoais."
        ),
    }
    return _result(True, data, None, "offline")


def _digits_ie(ie: str) -> str:
    return limpar_documento(ie)


def _all_same(digits: str) -> bool:
    return bool(digits) and len(set(digits)) == 1


def _mod11_check(digits: str, weights: list[int]) -> int:
    total = sum(int(digit) * weight for digit, weight in zip(digits, weights))
    digit = 11 - (total % 11)
    return 0 if digit >= 10 else digit


def _validar_ie_sp(ie: str) -> bool:
    digits = _digits_ie(ie)
    if len(digits) != 12 or _all_same(digits):
        return False
    first = sum(
        int(digits[i]) * weight
        for i, weight in enumerate([1, 3, 4, 5, 6, 7, 8, 10])
    )
    first_digit = (first % 11) % 10
    second = sum(
        int(digits[i]) * weight
        for i, weight in enumerate([3, 2, 10, 9, 8, 7, 6, 5, 4, 3, 2])
    )
    second_digit = (second % 11) % 10
    return int(digits[8]) == first_digit and int(digits[11]) == second_digit


def _validar_ie_rj(ie: str) -> bool:
    digits = _digits_ie(ie)
    if len(digits) != 8 or _all_same(digits):
        return False
    return int(digits[-1]) == _mod11_check(digits[:7], [2, 7, 6, 5, 4, 3, 2])


def _validar_ie_mg(ie: str) -> bool:
    digits = _digits_ie(ie)
    if len(digits) != 13 or _all_same(digits):
        return False
    body = digits[:3] + "0" + digits[3:11]
    total = 0
    for digit, weight in zip(body, [1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2]):
        total += sum(int(part) for part in str(int(digit) * weight))
    first_digit = (10 - (total % 10)) % 10
    second_digit = _mod11_check(
        digits[:3] + digits[3:12],
        [3, 2, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2],
    )
    return int(digits[11]) == first_digit and int(digits[12]) == second_digit


def _validar_ie_rs(ie: str) -> bool:
    digits = _digits_ie(ie)
    if len(digits) != 10 or _all_same(digits):
        return False
    return int(digits[-1]) == _mod11_check(
        digits[:9],
        [2, 9, 8, 7, 6, 5, 4, 3, 2],
    )


def _validar_ie_pr(ie: str) -> bool:
    digits = _digits_ie(ie)
    if len(digits) != 10 or _all_same(digits):
        return False
    first = _mod11_check(digits[:8], [3, 2, 7, 6, 5, 4, 3, 2])
    second = _mod11_check(digits[:8] + str(first), [4, 3, 2, 7, 6, 5, 4, 3, 2])
    return int(digits[8]) == first and int(digits[9]) == second


def _ba_modulo(first_digit: str) -> int:
    return 10 if first_digit in {"0", "1", "2", "3", "4", "5", "8"} else 11


def _ba_digit(digits: str, weights: list[int], modulo: int) -> int:
    total = sum(int(digit) * weight for digit, weight in zip(digits, weights))
    remainder = total % modulo
    digit = 0 if remainder == 0 else modulo - remainder
    return 0 if digit >= 10 else digit


def _validar_ie_ba(ie: str) -> bool:
    digits = _digits_ie(ie)
    if len(digits) not in {8, 9} or _all_same(digits):
        return False
    modulo = _ba_modulo(digits[0])
    if len(digits) == 8:
        second = _ba_digit(digits[:7], [7, 6, 5, 4, 3, 2, 1], modulo)
        first = _ba_digit(
            digits[:6] + str(second),
            [8, 7, 6, 5, 4, 3, 2],
            modulo,
        )
        return int(digits[6]) == first and int(digits[7]) == second
    second = _ba_digit(digits[:8], [8, 7, 6, 5, 4, 3, 2, 1], modulo)
    first = _ba_digit(
        digits[:7] + str(second),
        [9, 8, 7, 6, 5, 4, 3, 2],
        modulo,
    )
    return int(digits[7]) == first and int(digits[8]) == second


def _validar_ie_pe(ie: str) -> bool:
    digits = _digits_ie(ie)
    if len(digits) != 9 or _all_same(digits):
        return False
    first = _mod11_check(digits[:7], [8, 7, 6, 5, 4, 3, 2])
    second = _mod11_check(digits[:7] + str(first), [9, 8, 7, 6, 5, 4, 3, 2])
    return int(digits[7]) == first and int(digits[8]) == second


def _validar_ie_go(ie: str) -> bool:
    digits = _digits_ie(ie)
    if (
        len(digits) != 9
        or _all_same(digits)
        or digits[:2] not in {"10", "11", "15"}
    ):
        return False
    total = sum(
        int(digit) * weight
        for digit, weight in zip(digits[:8], [9, 8, 7, 6, 5, 4, 3, 2])
    )
    remainder = total % 11
    digit = 11 - remainder
    if digit == 10:
        number = int(digits[:8])
        digit = 1 if 10103105 <= number <= 10119997 and remainder == 1 else 0
    elif digit == 11:
        digit = 0
    return int(digits[8]) == digit


def _validar_ie_df(ie: str) -> bool:
    digits = _digits_ie(ie)
    if len(digits) != 13 or _all_same(digits) or not digits.startswith("07"):
        return False
    first = _mod11_check(digits[:11], [4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    second = _mod11_check(
        digits[:11] + str(first),
        [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2],
    )
    return int(digits[11]) == first and int(digits[12]) == second


def _validar_ie_sc_es_ce(ie: str) -> bool:
    digits = _digits_ie(ie)
    if len(digits) != 9 or _all_same(digits):
        return False
    return int(digits[-1]) == _mod11_check(
        digits[:8],
        [9, 8, 7, 6, 5, 4, 3, 2],
    )


_IE_VALIDATORS = {
    "SP": _validar_ie_sp,
    "RJ": _validar_ie_rj,
    "MG": _validar_ie_mg,
    "RS": _validar_ie_rs,
    "PR": _validar_ie_pr,
    "BA": _validar_ie_ba,
    "PE": _validar_ie_pe,
    "GO": _validar_ie_go,
    "DF": _validar_ie_df,
    "SC": _validar_ie_sc_es_ce,
    "ES": _validar_ie_sc_es_ce,
    "CE": _validar_ie_sc_es_ce,
}


async def validar_inscricao_estadual(uf: str, ie: str) -> dict[str, Any]:
    """Valida inscrição estadual offline conforme a UF.

    Implementa algoritmos para SP, RJ, MG, RS, PR, BA, PE, GO, DF, SC, ES e CE.
    Para UFs ainda não suportadas, retorna erro claro sem consultar serviços externos.
    """
    uf_limpa = re.sub(r"[^A-Za-z]", "", str(uf or "")).upper()
    validator = _IE_VALIDATORS.get(uf_limpa)
    if not validator:
        return _result(False, None, "UF não suportada ainda.", "offline")

    ie_limpa = _digits_ie(ie)
    valido = validator(ie)
    data = {"uf": uf_limpa, "ie": ie_limpa, "valido": valido}
    return _result(True, data, None, "offline")


def _classificar_simples(simples: dict[str, Any], mei: dict[str, Any]) -> str:
    if mei.get("optante") is True:
        return "Optante pelo MEI. Abordagem recomendada: baixo ticket e onboarding simples."
    if simples.get("optante") is True:
        return (
            "Optante pelo Simples Nacional. Boa aderência para soluções SMB."
        )
    if simples.get("optante") is False:
        return "Não optante pelo Simples Nacional ou informação não atualizada na fonte."
    return "Situação no Simples Nacional não informada pela fonte pública."


async def consultar_simples_nacional(cnpj: str) -> dict[str, Any]:
    """Consulta Simples Nacional e MEI a partir de um CNPJ.

    Reaproveita a consulta CNPJ, extrai os blocos `simples` e `mei` e adiciona
    uma classificação textual amigável para uso comercial ou atendimento.
    """
    consulta = await _consultar_cnpj_impl(cnpj, "consultar_simples_nacional")
    if not consulta["ok"]:
        return consulta

    dados = consulta["data"] or {}
    simples = dados.get("simples") or {}
    mei = dados.get("mei") or {}
    data = {
        "cnpj": dados.get("cnpj"),
        "razao_social": dados.get("razao_social"),
        "simples": simples,
        "mei": mei,
        "classificacao": _classificar_simples(simples, mei),
    }
    return _result(True, data, None, consulta["fonte"])


def _email_domain(email: str | None) -> str | None:
    if not email or "@" not in email:
        return None
    return email.rsplit("@", 1)[1].strip().lower() or None


def _capital_points(capital: float | None) -> tuple[int, str]:
    if capital is None:
        return 0, "Capital social não informado."
    if capital >= 5_000_000:
        return 20, "Capital social acima de R$ 5 milhões."
    if capital >= 1_000_000:
        return 15, "Capital social acima de R$ 1 milhão."
    if capital >= 100_000:
        return 10, "Capital social acima de R$ 100 mil."
    if capital > 0:
        return 5, "Capital social informado."
    return 0, "Capital social zerado ou indisponível."


def _cnae_is_high_value(
    cnae: dict[str, Any] | None,
    prefixes: set[str],
) -> bool:
    if not cnae:
        return False
    codigo = limpar_documento(str(cnae.get("codigo") or ""))
    return any(codigo.startswith(prefix) for prefix in prefixes)


def _suggestion(score: int) -> str:
    if score >= 75:
        return "Priorizar contato comercial consultivo com proposta personalizada."
    if score >= 50:
        return (
            "Nutrir o lead e validar dor, orçamento e decisor antes da oferta."
        )
    return "Coletar mais dados e qualificar fit antes de acionar vendas."


async def enriquecer_lead(
    cnpj: str,
    email: Optional[str] = None,
    telefone: Optional[str] = None,
) -> dict[str, Any]:
    """Enriquece um lead por CNPJ e calcula score comercial simples.

    A consulta usa BrasilAPI/ReceitaWS, normaliza o cadastro e calcula score 0-100
    por sinais: situação ATIVA, faixa de capital social, email/telefone no cadastro,
    domínio do email informado e CNAE de alto valor.
    """
    consulta = await _consultar_cnpj_impl(cnpj, "enriquecer_lead")
    if not consulta["ok"]:
        return consulta

    _, _, _, high_value_cnaes = _settings("enriquecer_lead")
    dados = consulta["data"] or {}
    breakdown: list[dict[str, Any]] = []
    score = 0

    situacao = str(dados.get("situacao") or "").upper()
    ativa_points = 30 if "ATIVA" in situacao else 0
    score += ativa_points
    breakdown.append(
        {
            "sinal": "situacao_cadastral_ativa",
            "pontos": ativa_points,
            "detalhe": "Situação cadastral ATIVA."
            if ativa_points
            else "Situação cadastral não está ATIVA.",
        },
    )

    capital_points, capital_detail = _capital_points(
        dados.get("capital_social"),
    )
    score += capital_points
    breakdown.append(
        {
            "sinal": "capital_social",
            "pontos": capital_points,
            "detalhe": capital_detail,
        },
    )

    cadastro_email = _str_or_none(dados.get("email"))
    cadastro_telefone = _str_or_none(dados.get("telefone")) or _str_or_none(
        telefone,
    )
    email_points = 10 if cadastro_email else 0
    phone_points = 10 if cadastro_telefone else 0
    score += email_points + phone_points
    breakdown.append(
        {
            "sinal": "email_no_cadastro",
            "pontos": email_points,
            "detalhe": "Email encontrado no cadastro."
            if email_points
            else "Sem email público no cadastro.",
        },
    )
    breakdown.append(
        {
            "sinal": "telefone_disponivel",
            "pontos": phone_points,
            "detalhe": "Telefone disponível."
            if phone_points
            else "Telefone não informado.",
        },
    )

    informed_domain = _email_domain(email)
    registry_domain = _email_domain(cadastro_email)
    domain_points = 0
    if (
        informed_domain
        and registry_domain
        and informed_domain == registry_domain
    ):
        domain_points = 15
    elif informed_domain and informed_domain not in _FREE_EMAIL_DOMAINS:
        domain_points = 8
    score += domain_points
    breakdown.append(
        {
            "sinal": "dominio_email_informado",
            "pontos": domain_points,
            "detalhe": (
                "Domínio do email informado bate com o cadastro."
                if domain_points == 15
                else "Email informado usa domínio corporativo."
                if domain_points == 8
                else "Sem evidência de domínio corporativo compatível."
            ),
        },
    )

    cnae_points = (
        15
        if _cnae_is_high_value(dados.get("cnae_principal"), high_value_cnaes)
        else 0
    )
    score += cnae_points
    breakdown.append(
        {
            "sinal": "cnae_alto_valor",
            "pontos": cnae_points,
            "detalhe": "CNAE principal em categoria de alto valor."
            if cnae_points
            else "CNAE principal fora da lista de alto valor.",
        },
    )

    score = min(score, 100)
    data = {
        "score": score,
        "score_breakdown": breakdown,
        "dados_cnpj": dados,
        "sugestao_proxima_acao": _suggestion(score),
    }
    return _result(True, data, None, consulta["fonte"])
