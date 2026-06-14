# -*- coding: utf-8 -*-
"""Fiscal provider factory for Nexora Fiscal."""

from __future__ import annotations

import os
from typing import Any

from ..constants import DEFAULT_ENV_VALUES
from .base import AbstractFiscalProvider
from .focus_nfe import FocusNFeProvider
from .nfe_io import NFEioProvider
from .webmania import WebManiaProvider

SUPPORTED_PROVIDERS = {
    "focus_nfe": FocusNFeProvider,
    "focus-nfe": FocusNFeProvider,
    "webmania": WebManiaProvider,
    "nfe_io": NFEioProvider,
    "nfe.io": NFEioProvider,
}


def current_provider_name() -> str:
    """Return configured provider key, defaulting to Focus NFe."""
    return (
        os.environ.get(
            "FISCAL_PROVIDER",
            DEFAULT_ENV_VALUES["FISCAL_PROVIDER"],
        )
        .strip()
        .lower()
    )


def current_ambiente() -> str:
    """Return configured fiscal environment, defaulting to homologacao."""
    return (
        os.environ.get(
            "FISCAL_AMBIENTE",
            DEFAULT_ENV_VALUES["FISCAL_AMBIENTE"],
        )
        .strip()
        .lower()
        or DEFAULT_ENV_VALUES["FISCAL_AMBIENTE"]
    )


def build_provider() -> AbstractFiscalProvider:
    """Instantiate the configured fiscal provider without leaking secrets."""
    provider_name = current_provider_name()
    provider_cls = SUPPORTED_PROVIDERS.get(provider_name, FocusNFeProvider)
    return provider_cls(
        api_key=os.environ.get("FISCAL_API_KEY", ""),
        ambiente=current_ambiente(),
        empresa_cnpj=os.environ.get("EMPRESA_CNPJ", ""),
        empresa_ie=os.environ.get("EMPRESA_IE", ""),
        regime_tributario=os.environ.get(
            "EMPRESA_REGIME_TRIBUTARIO",
            DEFAULT_ENV_VALUES["EMPRESA_REGIME_TRIBUTARIO"],
        ),
    )


def provider_status() -> dict[str, Any]:
    """Return non-secret provider configuration status for health checks."""
    provider_name = current_provider_name()
    return {
        "provider": provider_name,
        "ambiente": current_ambiente(),
        "supported": provider_name in SUPPORTED_PROVIDERS,
        "configured": {
            "FISCAL_PROVIDER": bool(provider_name),
            "FISCAL_API_KEY": bool(os.environ.get("FISCAL_API_KEY")),
            "EMPRESA_CNPJ": bool(os.environ.get("EMPRESA_CNPJ")),
            "EMPRESA_IE": bool(os.environ.get("EMPRESA_IE")),
            "EMPRESA_REGIME_TRIBUTARIO": bool(
                os.environ.get("EMPRESA_REGIME_TRIBUTARIO")
                or DEFAULT_ENV_VALUES["EMPRESA_REGIME_TRIBUTARIO"],
            ),
        },
    }
