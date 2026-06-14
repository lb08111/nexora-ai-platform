# -*- coding: utf-8 -*-
"""HTTP endpoints for Jotaduo Fiscal webhooks and status checks."""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request

from ..providers import build_provider, provider_status

logger = logging.getLogger("jotaduo").getChild(
    "plugin.jotaduo-fiscal.routers.fiscal_router",
)

router = APIRouter(tags=["jotaduo-fiscal"])


@router.post("/webhook/{provider}")
async def receive_webhook(
    provider: str,
    request: Request,
    x_focusnfe_signature: str | None = Header(default=None),
    x_webhook_signature: str | None = Header(default=None),
) -> dict[str, Any]:
    """Receive provider/SEFAZ callback and log the status update.

    If ``FISCAL_WEBHOOK_SECRET`` is defined, the endpoint accepts either a
    plain shared-secret header or a sha256/hmac-sha256 signature.
    """
    body = await request.body()
    signature = x_focusnfe_signature or x_webhook_signature
    _validate_signature(body, signature)

    try:
        payload = await request.json()
    except ValueError:
        payload = {"raw": body.decode("utf-8", errors="replace")}

    logger.info(
        "Fiscal webhook received provider=%s keys=%s",
        provider,
        sorted(payload.keys()) if isinstance(payload, dict) else type(payload),
    )
    return {"ok": True, "data": {"provider": provider}, "error": None}


@router.get("/notas/{chave}")
async def get_nota(chave: str) -> dict[str, Any]:
    """Proxy invoice consultation to the configured provider."""
    fiscal_provider = build_provider()
    return await fiscal_provider.consultar_nota(chave)


@router.get("/health")
async def health() -> dict[str, Any]:
    """Return fiscal provider health/configuration without leaking secrets."""
    return {"ok": True, "data": provider_status(), "error": None}


def _validate_signature(body: bytes, signature: str | None) -> None:
    secret = os.environ.get("FISCAL_WEBHOOK_SECRET", "").strip()
    if not secret:
        return
    if not signature:
        raise HTTPException(
            status_code=401, detail="Missing webhook signature"
        )

    candidates = {
        secret,
        hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest(),
    }
    candidates.add(
        "sha256=" + next(iter(c for c in candidates if c != secret))
    )
    if not any(
        hmac.compare_digest(signature, candidate) for candidate in candidates
    ):
        raise HTTPException(
            status_code=401, detail="Invalid webhook signature"
        )
