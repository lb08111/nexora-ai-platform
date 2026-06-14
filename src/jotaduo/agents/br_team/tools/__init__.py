# -*- coding: utf-8 -*-
"""Toolkit brasileiro: WhatsApp, agenda, Pix, CNPJ/CEP.

Stubs assíncronos com interface estável. As integrações reais (Z-API,
Evolution API, Google Calendar, Gerencianet, BrasilAPI etc.) entram
depois — o contrato fica fixo e os agentes/testes não mudam.
"""

from __future__ import annotations

from .agenda_tools import (
    book_appointment,
    check_slot_availability,
    list_available_slots,
    send_appointment_reminder,
)
from .cnpj_cep_tools import (
    consultar_cep,
    consultar_cnpj,
    validar_cpf,
)
from .pagamento_tools import (
    consultar_status_pagamento,
    gerar_cobranca_pix,
    gerar_link_pagamento,
)
from .whatsapp_tools import (
    send_whatsapp_image,
    send_whatsapp_message,
    send_whatsapp_template,
)

__all__ = [
    "send_whatsapp_message",
    "send_whatsapp_template",
    "send_whatsapp_image",
    "check_slot_availability",
    "list_available_slots",
    "book_appointment",
    "send_appointment_reminder",
    "gerar_cobranca_pix",
    "gerar_link_pagamento",
    "consultar_status_pagamento",
    "consultar_cnpj",
    "consultar_cep",
    "validar_cpf",
]
