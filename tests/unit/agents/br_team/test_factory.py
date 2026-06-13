# -*- coding: utf-8 -*-
"""Testes da factory que mapeia TeamBlueprint -> sub-agentes BR."""

from __future__ import annotations

import pytest

from qwenpaw.agents.br_team.factory import (
    SPECIALIST_REGISTRY,
    build_team_from_blueprint,
    resolve_role,
)
from qwenpaw.discovery.state import (
    AgentSpec,
    CompanyProfile,
    TeamBlueprint,
)


# --- resolve_role -------------------------------------------------------


@pytest.mark.parametrize(
    "spec_role, expected",
    [
        ("Atendente WhatsApp", "atendente"),
        ("ATENDIMENTO ao cliente", "atendente"),
        ("SAC", "atendente"),
        ("Agendamento de consultas", "agendamento"),
        ("Recepção da clínica", "recepcionista_saude"),
        ("Secretaria médica", "recepcionista_saude"),
        ("Vendedor consultivo", "vendas"),
        ("Comercial B2B", "vendas"),
        ("Recuperação de carrinho", "vendas"),
        ("Suporte pós-venda", "suporte"),
        ("Ouvidoria", "suporte"),
        ("Marketing & social media", "marketing"),
        ("Fidelização de clientes", "marketing"),
        ("Catálogo de produtos", "catalogo"),
        ("Cardápio (restaurante)", "catalogo"),
        ("Financeiro / Cobrança", "financeiro"),
        ("Pix e boleto", "financeiro"),
    ],
)
def test_resolve_role_sinonimos_pt_br(spec_role, expected):
    assert resolve_role(spec_role) == expected


def test_resolve_role_desconhecido_retorna_none():
    assert resolve_role("Astrofísico do espaço sideral") is None


def test_resolve_role_usa_nome_como_fallback():
    assert (
        resolve_role(spec_role="papel inventado", spec_name="Atendente Bia")
        == "atendente"
    )


def test_resolve_role_acentos_e_caixa():
    assert resolve_role("ATENDIMENTO") == "atendente"
    assert resolve_role("recepção") == "agendamento"
    assert resolve_role("Recepção da Clínica") == "recepcionista_saude"


# --- registry -----------------------------------------------------------


def test_registry_tem_8_papeis_sem_orchestrator():
    expected = {
        "atendente",
        "agendamento",
        "vendas",
        "suporte",
        "marketing",
        "catalogo",
        "financeiro",
        "recepcionista_saude",
    }
    assert set(SPECIALIST_REGISTRY) == expected


def test_registry_factories_sao_callable():
    for role, factory in SPECIALIST_REGISTRY.items():
        assert callable(factory), f"{role} factory não é callable"


# --- build_team_from_blueprint (sem instanciar agentes) -----------------


def _mk_blueprint(*specs: AgentSpec) -> TeamBlueprint:
    return TeamBlueprint(
        company_profile=CompanyProfile(segment="ecommerce"),
        proposed_team=list(specs),
    )


def test_build_resolve_sem_instanciar_modelo():
    bp = _mk_blueprint(
        AgentSpec(name="Bia", role="Atendente WhatsApp", objective="x"),
        AgentSpec(name="Vera", role="Vendedor consultivo", objective="x"),
        AgentSpec(name="Lucas", role="Financeiro Pix", objective="x"),
        AgentSpec(name="Xpto", role="papel marciano", objective="x"),
    )
    result = build_team_from_blueprint(bp, instantiate=False)
    assert result.role_map == {
        "Bia": "atendente",
        "Vera": "vendas",
        "Lucas": "financeiro",
    }
    assert len(result.skipped) == 1
    assert result.skipped[0]["name"] == "Xpto"
    assert result.specialists == []  # instantiate=False


def test_build_blueprint_vazio():
    bp = _mk_blueprint()
    result = build_team_from_blueprint(bp, instantiate=False)
    assert result.role_map == {}
    assert result.skipped == []
    assert result.specialists == []


def test_build_blueprint_clinica_resolve_recepcionista_saude():
    bp = _mk_blueprint(
        AgentSpec(
            name="Recep",
            role="Recepcionista de saúde / clínica",
            objective="x",
        ),
        AgentSpec(name="Ana", role="Agendamento", objective="x"),
    )
    result = build_team_from_blueprint(bp, instantiate=False)
    assert result.role_map["Recep"] == "recepcionista_saude"
    assert result.role_map["Ana"] == "agendamento"
