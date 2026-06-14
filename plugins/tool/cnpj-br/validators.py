# -*- coding: utf-8 -*-
"""Validadores offline para documentos brasileiros."""

import re


_INVALID_CPF = {str(digit) * 11 for digit in range(10)}
_INVALID_CNPJ = {str(digit) * 14 for digit in range(10)}


def limpar_documento(doc: str) -> str:
    """Remove pontuação e espaços de CPF, CNPJ, CEP ou IE."""
    if doc is None:
        return ""
    return re.sub(r"\D", "", str(doc))


def validar_cpf(cpf: str) -> bool:
    """Valida CPF pelo algoritmo oficial dos dígitos verificadores."""
    digits = limpar_documento(cpf)
    if len(digits) != 11 or digits in _INVALID_CPF:
        return False

    values = [int(digit) for digit in digits]
    total = sum(values[index] * (10 - index) for index in range(9))
    first = 0 if total % 11 < 2 else 11 - (total % 11)
    if values[9] != first:
        return False

    total = sum(values[index] * (11 - index) for index in range(10))
    second = 0 if total % 11 < 2 else 11 - (total % 11)
    return values[10] == second


def validar_cnpj(cnpj: str) -> bool:
    """Valida CNPJ pelo algoritmo oficial dos dígitos verificadores."""
    digits = limpar_documento(cnpj)
    if len(digits) != 14 or digits in _INVALID_CNPJ:
        return False

    values = [int(digit) for digit in digits]
    weights_first = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    weights_second = [6] + weights_first

    total = sum(values[index] * weights_first[index] for index in range(12))
    first = 0 if total % 11 < 2 else 11 - (total % 11)
    if values[12] != first:
        return False

    total = sum(values[index] * weights_second[index] for index in range(13))
    second = 0 if total % 11 < 2 else 11 - (total % 11)
    return values[13] == second


def formatar_cnpj(cnpj: str) -> str:
    """Formata CNPJ limpo como XX.XXX.XXX/XXXX-XX."""
    digits = limpar_documento(cnpj)
    if len(digits) != 14:
        return digits
    return (
        f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/"
        f"{digits[8:12]}-{digits[12:]}"
    )


def formatar_cpf(cpf: str) -> str:
    """Formata CPF limpo como XXX.XXX.XXX-XX."""
    digits = limpar_documento(cpf)
    if len(digits) != 11:
        return digits
    return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"


def validar_cep(cep: str) -> bool:
    """Valida CEP pelo tamanho: exatamente 8 dígitos."""
    return len(limpar_documento(cep)) == 8
