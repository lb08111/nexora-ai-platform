# -*- coding: utf-8 -*-
"""Testes das tools BR: WhatsApp, agenda, pagamento, CNPJ/CEP/CPF."""

from __future__ import annotations

import json
import re

import pytest

from jotaduo.agents.br_team.tools import (
    book_appointment,
    check_slot_availability,
    consultar_cep,
    consultar_cnpj,
    consultar_status_pagamento,
    gerar_cobranca_pix,
    gerar_link_pagamento,
    list_available_slots,
    send_appointment_reminder,
    send_whatsapp_image,
    send_whatsapp_message,
    send_whatsapp_template,
    validar_cpf,
)


def _payload(resp) -> dict:
    """Extrai o JSON do ToolResponse (textos concatenados)."""
    text = ""
    for block in resp.content:
        if isinstance(block, dict) and block.get("type") == "text":
            text += block.get("text", "")
    return json.loads(text)


def _raw_text(resp) -> str:
    text = ""
    for block in resp.content:
        if isinstance(block, dict) and block.get("type") == "text":
            text += block.get("text", "")
    return text


# --- WhatsApp -----------------------------------------------------------


@pytest.mark.asyncio
async def test_whatsapp_normaliza_telefone_br_sem_ddi():
    resp = await send_whatsapp_message("11999998888", "Olá!")
    data = _payload(resp)
    assert data["phone"] == "+5511999998888"
    assert data["status"] == "queued"
    assert "stub" in data["note"].lower()


@pytest.mark.asyncio
async def test_whatsapp_aceita_e164():
    resp = await send_whatsapp_message("+5511999998888", "Oi")
    assert _payload(resp)["phone"] == "+5511999998888"


@pytest.mark.asyncio
async def test_whatsapp_rejeita_mensagem_vazia():
    resp = await send_whatsapp_message("11999998888", "   ")
    assert "ERROR" in _raw_text(resp)


@pytest.mark.asyncio
async def test_whatsapp_template_exige_nome():
    resp = await send_whatsapp_template("11999998888", "")
    assert "ERROR" in _raw_text(resp)


@pytest.mark.asyncio
async def test_whatsapp_template_passa_variaveis():
    resp = await send_whatsapp_template(
        "11999998888",
        "lembrete_consulta_v1",
        {"nome": "Maria", "data": "12/06 às 14h"},
    )
    data = _payload(resp)
    assert data["template_name"] == "lembrete_consulta_v1"
    assert data["variables"]["nome"] == "Maria"


@pytest.mark.asyncio
async def test_whatsapp_image_valida_url():
    resp = await send_whatsapp_image("11999998888", "nao-e-url")
    assert "ERROR" in _raw_text(resp)
    resp_ok = await send_whatsapp_image(
        "11999998888",
        "https://exemplo.com/foto.jpg",
        "Veja",
    )
    assert _payload(resp_ok)["status"] == "queued"


# --- Agenda -------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_slots_devolve_horarios_no_intervalo(tmp_path):
    resp = await list_available_slots(
        agenda_id="dr_teste_unico_1",
        date="2026-07-01",
        slot_minutes=60,
        business_hours_start=9,
        business_hours_end=12,
    )
    slots = _payload(resp)["slots"]
    # 9, 10, 11 → 3 slots
    assert len(slots) == 3
    assert all(s.startswith("2026-07-01T") for s in slots)


@pytest.mark.asyncio
async def test_list_slots_rejeita_data_invalida():
    resp = await list_available_slots("dr_x", "01-07-2026")
    assert "ERROR" in _raw_text(resp)


@pytest.mark.asyncio
async def test_book_e_consultar_disponibilidade():
    slot = "2026-07-02T10:00:00"
    av = await check_slot_availability("dr_book_test", slot)
    assert _payload(av)["available"] is True

    booked = await book_appointment(
        agenda_id="dr_book_test",
        slot_iso=slot,
        customer_name="Maria Silva",
        customer_phone="11999998888",
        service="consulta",
    )
    data = _payload(booked)
    assert data["status"] == "booked"
    assert data["booking_id"].startswith("apt-")

    av2 = await check_slot_availability("dr_book_test", slot)
    assert _payload(av2)["available"] is False


@pytest.mark.asyncio
async def test_book_recusa_conflito():
    slot = "2026-07-03T10:00:00"
    await book_appointment(
        "dr_conflito",
        slot,
        "A",
        "11999998888",
    )
    second = await book_appointment(
        "dr_conflito",
        slot,
        "B",
        "11999998888",
    )
    assert "ERROR" in _raw_text(second)


@pytest.mark.asyncio
async def test_reminder_calcula_horario():
    booked = await book_appointment(
        agenda_id="dr_lembrete",
        slot_iso="2026-07-04T14:00:00",
        customer_name="Joao",
        customer_phone="11999998888",
    )
    booking_id = _payload(booked)["booking_id"]
    reminder = await send_appointment_reminder(booking_id, hours_before=24)
    data = _payload(reminder)
    assert data["status"] == "scheduled"
    assert "2026-07-03T14:00" in data["scheduled_for"]


@pytest.mark.asyncio
async def test_reminder_booking_inexistente():
    resp = await send_appointment_reminder("apt-naoexiste", 24)
    assert "ERROR" in _raw_text(resp)


# --- Pagamento ----------------------------------------------------------


@pytest.mark.asyncio
async def test_pix_gera_txid_e_formato_brl():
    resp = await gerar_cobranca_pix(9990, "Pedido #123")
    data = _payload(resp)
    assert re.match(r"^pix[a-f0-9]{21}$", data["txid"])
    assert data["valor"] == "R$ 99,90"


@pytest.mark.asyncio
async def test_pix_valida_cpf_quando_informado():
    resp = await gerar_cobranca_pix(
        1000,
        "x",
        devedor_cpf="00000000000",  # inválido
    )
    assert "ERROR" in _raw_text(resp)


@pytest.mark.asyncio
async def test_link_pagamento_e_consulta_status():
    link = await gerar_link_pagamento(15000, "Curso online")
    data = _payload(link)
    assert data["payment_id"].startswith("pl_")
    status = await consultar_status_pagamento(data["payment_id"])
    assert _payload(status)["status"] == "pending"


@pytest.mark.asyncio
async def test_link_pagamento_rejeita_sem_metodos():
    resp = await gerar_link_pagamento(1000, "x", metodos=" , , ")
    assert "ERROR" in _raw_text(resp)


# --- CNPJ / CEP / CPF ---------------------------------------------------


@pytest.mark.asyncio
async def test_validar_cpf_dv_correto():
    # CPF de teste com DV válido
    resp = await validar_cpf("11144477735")
    assert _payload(resp)["valid"] is True


@pytest.mark.asyncio
async def test_validar_cpf_repetido_invalido():
    resp = await validar_cpf("11111111111")
    assert _payload(resp)["valid"] is False


@pytest.mark.asyncio
async def test_consultar_cnpj_invalido():
    resp = await consultar_cnpj("00000000000000")
    assert "ERROR" in _raw_text(resp)


@pytest.mark.asyncio
async def test_consultar_cnpj_valido():
    # CNPJ válido conhecido (Receita Federal): 11.222.333/0001-81
    resp = await consultar_cnpj("11222333000181")
    data = _payload(resp)
    assert data["cnpj"] == "11222333000181"
    assert data["situacao"] == "ATIVA"


@pytest.mark.asyncio
async def test_consultar_cep_normaliza_formato():
    resp = await consultar_cep("01001000")
    assert _payload(resp)["cep"] == "01001-000"


@pytest.mark.asyncio
async def test_consultar_cep_rejeita_curto():
    resp = await consultar_cep("123")
    assert "ERROR" in _raw_text(resp)
