# -*- coding: utf-8 -*-
"""Testes dos prompts pt-BR: garantir conteúdo crítico presente."""

from __future__ import annotations

import pytest

from qwenpaw.agents.br_team.prompts import PROMPTS_BY_ROLE


@pytest.mark.parametrize("role", sorted(PROMPTS_BY_ROLE))
def test_prompt_existe_e_nao_vazio(role):
    p = PROMPTS_BY_ROLE[role]
    assert isinstance(p, str)
    assert len(p) > 200, f"prompt {role} muito curto"


@pytest.mark.parametrize("role", sorted(PROMPTS_BY_ROLE))
def test_prompt_em_pt_br(role):
    p = PROMPTS_BY_ROLE[role].lower()
    # heurística: ao menos 1 palavra-chave pt-BR em cada prompt
    pt_markers = [" você ", "português", "pt-br", "brasil", "cliente"]
    assert any(m in p for m in pt_markers), (
        f"prompt {role} não parece pt-BR"
    )


def test_recepcionista_saude_menciona_lgpd_e_samu():
    p = PROMPTS_BY_ROLE["recepcionista_saude"].lower()
    assert "lgpd" in p
    assert "samu" in p or "192" in p


def test_financeiro_proibe_dados_cartao_no_chat():
    p = PROMPTS_BY_ROLE["financeiro"].lower()
    assert "cartão" in p or "cartao" in p
    assert "senha" in PROMPTS_BY_ROLE["financeiro"].lower() or (
        "código do cartão" in p or "codigo do cartao" in p
    )


def test_marketing_exige_template_fora_da_janela():
    p = PROMPTS_BY_ROLE["marketing"].lower()
    assert "send_whatsapp_template" in p
    assert "24h" in p


def test_orchestrator_lista_antes_de_chamar():
    p = PROMPTS_BY_ROLE["orchestrator"].lower()
    assert "list_agents" in p
    assert "chat_with_agent" in p
    assert "loop" in p
