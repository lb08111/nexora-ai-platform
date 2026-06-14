# -*- coding: utf-8 -*-
"""Pix provider adapters."""

from __future__ import annotations

from .base import AbstractPixProvider

__all__ = ["AbstractPixProvider", "get_provider"]


def get_provider(name: str | None = None) -> AbstractPixProvider:
    """Return a provider implementation by name."""
    import os

    provider_name = (name or os.getenv("PIX_PROVIDER") or "asaas").lower()
    if provider_name == "asaas":
        from .asaas import AsaasPixProvider

        return AsaasPixProvider()
    if provider_name in {"mercado_pago", "mercadopago", "mp"}:
        from .mercado_pago import MercadoPagoPixProvider

        return MercadoPagoPixProvider()
    if provider_name in {"pagbank", "pagseguro"}:
        from .pagbank import PagBankPixProvider

        return PagBankPixProvider()
    if provider_name in {"bcb_direct", "bcb", "bacen"}:
        from .bcb_direct import BcbDirectPixProvider

        return BcbDirectPixProvider()
    raise ValueError(f"Unsupported Pix provider: {provider_name}")
