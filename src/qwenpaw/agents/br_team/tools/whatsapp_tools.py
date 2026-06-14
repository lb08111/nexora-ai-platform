# -*- coding: utf-8 -*-
"""Tools de WhatsApp (envio de mensagem, template e imagem).

Stub que registra a saída via logger. A integração real deve plugar em
``qwenpaw.app.channels.whatsapp`` ou em provedores externos (Z-API,
Evolution API, Twilio, WhatsApp Cloud API). O contrato fica fixo.
"""

from __future__ import annotations

import logging
import re

from agentscope.tool import ToolResponse

from ._utils import err, json_response

logger = logging.getLogger(__name__)

_E164 = re.compile(r"^\+?\d{10,15}$")


def _normalize_phone(phone: str) -> str:
    cleaned = re.sub(r"[\s\-()]+", "", phone or "")
    if cleaned.startswith("+"):
        return cleaned
    digits = re.sub(r"\D", "", cleaned)
    if len(digits) in (10, 11):  # número BR sem DDI
        return f"+55{digits}"
    return cleaned


async def send_whatsapp_message(
    phone: str,
    message: str,
) -> ToolResponse:
    """Envia uma mensagem de texto livre via WhatsApp.

    Args:
        phone: Telefone do destinatário em E.164 (``+5511999998888``) ou
            BR sem DDI (``11999998888``); a normalização aplica ``+55``.
        message: Texto da mensagem em português, pode conter emojis.

    Returns:
        ``ToolResponse``: JSON com ``status``, ``message_id`` (stub),
        ``phone`` normalizado e ``preview`` do conteúdo enviado.
    """
    if not message or not message.strip():
        return err("mensagem vazia")
    normalized = _normalize_phone(phone)
    if not _E164.match(normalized.lstrip("+")) and not normalized.startswith(
        "+",
    ):
        return err(f"telefone inválido: {phone!r}")
    logger.info("[whatsapp.stub] -> %s: %s", normalized, message[:80])
    return json_response(
        {
            "status": "queued",
            "channel": "whatsapp",
            "phone": normalized,
            "message_id": f"stub-{abs(hash((normalized, message))) % 10**10}",
            "preview": message[:160],
            "note": (
                "stub: integração real plugar em "
                "qwenpaw.app.channels.whatsapp ou provedor externo."
            ),
        },
    )


async def send_whatsapp_template(
    phone: str,
    template_name: str,
    variables: dict[str, str] | None = None,
) -> ToolResponse:
    """Envia um template aprovado (HSM) via WhatsApp Business.

    Use para mensagens proativas fora da janela de 24h (lembrete de
    consulta, confirmação de pedido, recuperação de carrinho).

    Args:
        phone: Telefone do destinatário (BR ou E.164).
        template_name: Nome do template aprovado no provedor (ex.
            ``lembrete_consulta_v1``).
        variables: Dicionário de substituições do template (ex.
            ``{"nome": "Maria", "data": "12/06 às 14h"}``).

    Returns:
        ``ToolResponse``: JSON com ``status`` e ``template_name``.
    """
    if not template_name or not template_name.strip():
        return err("template_name vazio")
    normalized = _normalize_phone(phone)
    payload = {
        "status": "queued",
        "channel": "whatsapp_template",
        "phone": normalized,
        "template_name": template_name,
        "variables": variables or {},
        "note": "stub: aprovar template no provedor antes de produção.",
    }
    logger.info(
        "[whatsapp.stub.template] -> %s: %s vars=%s",
        normalized,
        template_name,
        variables,
    )
    return json_response(payload)


async def send_whatsapp_image(
    phone: str,
    image_url: str,
    caption: str = "",
) -> ToolResponse:
    """Envia uma imagem via WhatsApp (catálogo, comprovante, cardápio).

    Args:
        phone: Telefone do destinatário.
        image_url: URL pública da imagem (jpg/png/webp).
        caption: Legenda opcional em português.

    Returns:
        ``ToolResponse``: JSON com ``status`` e metadados do envio.
    """
    if not image_url or not image_url.startswith(("http://", "https://")):
        return err(f"image_url inválida: {image_url!r}")
    normalized = _normalize_phone(phone)
    logger.info(
        "[whatsapp.stub.image] -> %s url=%s caption=%s",
        normalized,
        image_url,
        caption[:60],
    )
    return json_response(
        {
            "status": "queued",
            "channel": "whatsapp_image",
            "phone": normalized,
            "image_url": image_url,
            "caption": caption,
            "note": "stub",
        },
    )
