# -*- coding: utf-8 -*-
"""HTTP API for Jotaduo Pix billing and reconciliation."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
from decimal import Decimal, InvalidOperation
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Query, Request
from pydantic import BaseModel

from ..providers import get_provider
from ..store.db import get_cobranca, save_cobranca, update_status

logger = logging.getLogger("jotaduo").getChild(
    "plugin.jotaduo-pix.routers.pix",
)

router = APIRouter(prefix="", tags=["jotaduo-pix"])


class WebhookAck(BaseModel):
    ok: bool
    provider: str
    txid: str | None = None
    status: str | None = None


@router.post("/webhook/{provider}", response_model=WebhookAck)
async def pix_webhook(
    provider: str,
    request: Request,
    x_pix_signature: str | None = Header(default=None),
    x_hub_signature_256: str | None = Header(default=None),
) -> WebhookAck:
    """Receive PSP callback, validate optional HMAC, and update store."""
    body = await request.body()
    signature = x_pix_signature or x_hub_signature_256
    _validate_hmac(body, signature)

    try:
        payload = json.loads(body.decode("utf-8") or "{}")
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON") from exc

    adapter = get_provider(provider)
    normalized = await adapter.parse_webhook(payload)
    txid = normalized.get("txid")
    status = normalized.get("status") or "RECEIVED"
    if not txid:
        logger.warning("Webhook without txid from provider %s", provider)
        return WebhookAck(ok=True, provider=adapter.name, status=status)

    value = _safe_decimal(normalized.get("valor"))
    existing = await get_cobranca(txid, adapter.name)
    if existing:
        await update_status(
            txid=txid,
            provider=adapter.name,
            status=str(status),
            raw_response=normalized,
            e2eid=normalized.get("e2eid"),
            valor=value,
        )
    else:
        await save_cobranca(
            txid=txid,
            provider=adapter.name,
            valor=value or Decimal("0.00"),
            devedor=None,
            status=str(status),
            br_code=None,
            e2eid=normalized.get("e2eid"),
            raw_response=normalized,
        )
    return WebhookAck(
        ok=True,
        provider=adapter.name,
        txid=txid,
        status=str(status),
    )


@router.get("/cobranca/{txid}")
async def get_pix_cobranca(
    txid: str,
    refresh: bool = Query(default=False),
) -> dict[str, Any]:
    """Read a Pix charge from SQLite and optionally refresh from provider."""
    provider = get_provider()
    stored = await get_cobranca(txid, provider.name)
    remote = None
    if refresh:
        remote = await provider.get_charge(txid)
        if stored and remote.get("status"):
            await update_status(
                txid=txid,
                provider=provider.name,
                status=str(remote["status"]),
                raw_response=remote,
            )
            stored = await get_cobranca(txid, provider.name)
    if not stored and not remote:
        raise HTTPException(status_code=404, detail="Cobrança não encontrada")
    return {"ok": True, "data": {"store": stored, "provider": remote}}


@router.get("/health")
async def pix_health() -> dict[str, Any]:
    """Return non-sensitive plugin/provider health."""
    provider_name = os.getenv("PIX_PROVIDER", "asaas")
    adapter = get_provider(provider_name)
    provider_health = await adapter.health()
    return {
        "ok": True,
        "provider": provider_health,
        "env": {
            "PIX_PROVIDER": provider_name,
            "PIX_API_KEY_configured": bool(os.getenv("PIX_API_KEY")),
            "PIX_AMBIENTE": os.getenv("PIX_AMBIENTE", "sandbox"),
            "PIX_CHAVE_configured": bool(os.getenv("PIX_CHAVE")),
            "PIX_WEBHOOK_SECRET_configured": bool(
                os.getenv("PIX_WEBHOOK_SECRET"),
            ),
        },
    }


def _validate_hmac(body: bytes, signature: str | None) -> None:
    secret = os.getenv("PIX_WEBHOOK_SECRET")
    if not secret:
        return
    if not signature:
        raise HTTPException(status_code=401, detail="Missing webhook HMAC")
    expected = hmac.new(
        secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()
    received = signature.removeprefix("sha256=").strip()
    if not hmac.compare_digest(expected, received):
        raise HTTPException(status_code=401, detail="Invalid webhook HMAC")


def _safe_decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return None
