# -*- coding: utf-8 -*-
"""Tools de agenda (slots, agendamento, lembrete) — stubs in-memory.

A implementação real deve plugar em Google Calendar, Outlook ou agendas
proprietárias (Doctoralia, Trinks, etc.). O store in-memory aqui é
suficiente para desenvolvimento, testes e demos do TeamLead.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from threading import RLock
from typing import Optional
from uuid import uuid4

from agentscope.tool import ToolResponse

from ._utils import err, json_response

logger = logging.getLogger(__name__)

# Store in-memory: {agenda_id: [{slot_iso, customer, service, booking_id}]}
_BOOKINGS: dict[str, list[dict]] = {}
_LOCK = RLock()

_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?")


def _parse_iso(value: str) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


async def list_available_slots(
    agenda_id: str,
    date: str,
    slot_minutes: int = 30,
    business_hours_start: int = 9,
    business_hours_end: int = 18,
) -> ToolResponse:
    """Lista horários livres em uma data para um profissional/recurso.

    Args:
        agenda_id: Identificador da agenda (ex. ``"dr_silva"``,
            ``"sala_1"``, ``"cadeira_barbeiro_2"``).
        date: Data no formato ``YYYY-MM-DD``.
        slot_minutes: Duração de cada slot em minutos (padrão 30).
        business_hours_start: Hora de abertura (0–23, padrão 9).
        business_hours_end: Hora de fechamento (0–23, padrão 18).

    Returns:
        ``ToolResponse``: JSON com lista de ``slots`` ISO disponíveis.
    """
    try:
        day = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return err(f"date inválida (use YYYY-MM-DD): {date!r}")
    if slot_minutes <= 0 or slot_minutes > 240:
        return err("slot_minutes deve estar entre 1 e 240")
    if not 0 <= business_hours_start < business_hours_end <= 24:
        return err("janela de horário inválida")

    with _LOCK:
        taken = {
            b["slot_iso"]
            for b in _BOOKINGS.get(agenda_id, [])
            if b["slot_iso"].startswith(date)
        }
    slots: list[str] = []
    cursor = day.replace(hour=business_hours_start, minute=0)
    end = day.replace(hour=business_hours_end, minute=0)
    while cursor < end:
        iso = cursor.strftime("%Y-%m-%dT%H:%M:00")
        if iso not in taken:
            slots.append(iso)
        cursor += timedelta(minutes=slot_minutes)
    return json_response(
        {
            "agenda_id": agenda_id,
            "date": date,
            "slot_minutes": slot_minutes,
            "slots": slots,
        },
    )


async def check_slot_availability(
    agenda_id: str,
    slot_iso: str,
) -> ToolResponse:
    """Verifica se um horário específico está livre.

    Args:
        agenda_id: Identificador da agenda.
        slot_iso: Horário ISO 8601 (``2026-06-15T14:30:00``).

    Returns:
        ``ToolResponse``: JSON com ``available`` (bool) e ``slot_iso``.
    """
    if not _ISO.match(slot_iso):
        return err(f"slot_iso inválido: {slot_iso!r}")
    with _LOCK:
        taken = {b["slot_iso"] for b in _BOOKINGS.get(agenda_id, [])}
    return json_response(
        {
            "agenda_id": agenda_id,
            "slot_iso": slot_iso,
            "available": slot_iso not in taken,
        },
    )


async def book_appointment(
    agenda_id: str,
    slot_iso: str,
    customer_name: str,
    customer_phone: str,
    service: str = "",
    notes: str = "",
) -> ToolResponse:
    """Reserva um horário para um cliente.

    Args:
        agenda_id: Identificador da agenda/recurso.
        slot_iso: Horário no formato ISO 8601.
        customer_name: Nome completo do cliente.
        customer_phone: Telefone (BR ou E.164).
        service: Descrição do serviço (ex. ``"corte feminino"``).
        notes: Observações livres (alergias, preferências etc.).

    Returns:
        ``ToolResponse``: JSON com ``booking_id`` ou erro de conflito.
    """
    if not _ISO.match(slot_iso):
        return err(f"slot_iso inválido: {slot_iso!r}")
    if not customer_name.strip() or not customer_phone.strip():
        return err("customer_name e customer_phone são obrigatórios")

    booking_id = f"apt-{uuid4().hex[:10]}"
    with _LOCK:
        bookings = _BOOKINGS.setdefault(agenda_id, [])
        if any(b["slot_iso"] == slot_iso for b in bookings):
            return err(
                f"slot {slot_iso} já reservado em {agenda_id}",
            )
        bookings.append(
            {
                "booking_id": booking_id,
                "slot_iso": slot_iso,
                "customer_name": customer_name,
                "customer_phone": customer_phone,
                "service": service,
                "notes": notes,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        )
    logger.info(
        "[agenda.stub.book] %s @ %s by %s (%s) [id=%s]",
        agenda_id,
        slot_iso,
        customer_name,
        customer_phone,
        booking_id,
    )
    return json_response(
        {
            "status": "booked",
            "booking_id": booking_id,
            "agenda_id": agenda_id,
            "slot_iso": slot_iso,
            "customer_name": customer_name,
            "service": service,
        },
    )


async def send_appointment_reminder(
    booking_id: str,
    hours_before: int = 24,
) -> ToolResponse:
    """Dispara lembrete antecipado de uma reserva.

    Em produção, agenda um job no APScheduler (já presente em deps)
    para enviar um template WhatsApp ``hours_before`` antes do slot.

    Args:
        booking_id: ID retornado por ``book_appointment``.
        hours_before: Quantas horas antes do horário disparar.

    Returns:
        ``ToolResponse``: JSON com ``scheduled_for`` (ISO) ou erro.
    """
    if hours_before < 0 or hours_before > 168:
        return err("hours_before deve estar entre 0 e 168")
    with _LOCK:
        for bookings in _BOOKINGS.values():
            for b in bookings:
                if b["booking_id"] == booking_id:
                    slot_dt = _parse_iso(b["slot_iso"])
                    if slot_dt is None:
                        return err("slot_iso da reserva corrompido")
                    scheduled = slot_dt - timedelta(hours=hours_before)
                    logger.info(
                        "[agenda.stub.reminder] %s scheduled %s",
                        booking_id,
                        scheduled.isoformat(),
                    )
                    return json_response(
                        {
                            "status": "scheduled",
                            "booking_id": booking_id,
                            "scheduled_for": scheduled.isoformat(),
                            "customer_phone": b["customer_phone"],
                        },
                    )
    return err(f"booking_id não encontrado: {booking_id}")
