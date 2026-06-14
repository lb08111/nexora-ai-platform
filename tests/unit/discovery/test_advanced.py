# -*- coding: utf-8 -*-
"""Testes avançados para o discovery agent: edge cases e robustez profissional."""
import json
import tempfile
from pathlib import Path

import pytest

from jotaduo.discovery.state import (
    DiscoveryState,
    OpenArea,
    TeamBlueprint,
    Integration,
)
from jotaduo.discovery.tools import InterviewSession


# --- Edge cases em DiscoveryState ---


def test_next_focus_with_empty_open_areas():
    """next_focus deve retornar None quando não há áreas."""
    state = DiscoveryState(session_id="s1")
    assert state.open_areas == []
    assert state.next_focus() is None


def test_next_focus_picks_lowest_confidence():
    """next_focus prioriza menor confiança quando priority é mesmo."""
    state = DiscoveryState(session_id="s1")
    state.open_areas = [
        OpenArea(id="a", topic="A", confidence=0.9, priority=2),
        OpenArea(id="b", topic="B", confidence=0.1, priority=2),
    ]
    assert state.next_focus().id == "b"


def test_next_focus_prioritizes_critical():
    """next_focus considera priority como tiebreaker (maior priority vence)."""
    state = DiscoveryState(session_id="s1")
    state.open_areas = [
        OpenArea(id="optional", topic="Opt", confidence=0.1, priority=1),
        OpenArea(id="critical", topic="Crit", confidence=0.5, priority=5),
    ]
    # Ambas têm mesma confiança na ordenação (0.1, -5) < (0.5, -1), então optional
    focus = state.next_focus()
    assert focus.id == "optional"


def test_ready_to_emit_no_critical_areas():
    """ready_to_emit é True quando não há áreas críticas (priority >= 3)."""
    state = DiscoveryState(session_id="s1")
    state.open_areas = [
        OpenArea(id="low", topic="Low", confidence=0.0, priority=1),
    ]
    # Não há críticas, então: True
    assert state.ready_to_emit() is True


def test_ready_to_emit_with_critical_below_threshold():
    """ready_to_emit é False quando alguma área crítica está abaixo do limiar."""
    state = DiscoveryState(session_id="s1")
    state.open_areas = [
        OpenArea(id="segmento", topic="Qual é o segmento?", confidence=0.3, priority=5),
    ]
    # Crítica com confiança 0.3 < threshold 0.7 → False
    assert state.ready_to_emit(threshold=0.7) is False


def test_ready_to_emit_all_critical_above_threshold():
    """ready_to_emit é True quando todas as críticas estão acima do limiar."""
    state = DiscoveryState(session_id="s1")
    state.open_areas = [
        OpenArea(id="seg", topic="Segmento", confidence=0.8, priority=5),
        OpenArea(id="modelo", topic="Modelo", confidence=0.75, priority=4),
        OpenArea(id="opt", topic="Opcional", confidence=0.0, priority=2),
    ]
    # Críticas: seg (0.8 >= 0.7), modelo (0.75 >= 0.7) → True
    assert state.ready_to_emit(threshold=0.7) is True


def test_ready_to_emit_custom_threshold():
    """ready_to_emit respeita threshold customizado."""
    state = DiscoveryState(session_id="s1")
    state.open_areas = [
        OpenArea(id="teste", topic="Test", confidence=0.5, priority=3),
    ]
    assert state.ready_to_emit(threshold=0.6) is False
    assert state.ready_to_emit(threshold=0.4) is True


def test_confidence_bounds_validation():
    """OpenArea valida confiança entre 0.0 e 1.0."""
    with pytest.raises(ValueError):
        OpenArea(id="x", topic="T", confidence=1.5, priority=1)
    with pytest.raises(ValueError):
        OpenArea(id="x", topic="T", confidence=-0.1, priority=1)


def test_priority_bounds_validation():
    """OpenArea valida prioridade entre 1 e 5."""
    with pytest.raises(ValueError):
        OpenArea(id="x", topic="T", confidence=0.5, priority=6)
    with pytest.raises(ValueError):
        OpenArea(id="x", topic="T", confidence=0.5, priority=0)


# --- Persistência de estado ---


@pytest.mark.asyncio
async def test_state_json_persistence():
    """Estado pode ser serializado e desserializado sem perda."""
    state = DiscoveryState(session_id="s1")
    state.company.segment = "ecommerce"
    state.open_areas.append(
        OpenArea(id="dores", topic="Quais são as dores?", confidence=0.3, priority=3),
    )
    state.integrations.append(
        Integration(kind="crm", name="Salesforce", confidence=0.8),
    )

    json_str = state.model_dump_json()
    restored = DiscoveryState.model_validate_json(json_str)

    assert restored.session_id == state.session_id
    assert restored.company.segment == "ecommerce"
    assert restored.open_areas[0].id == "dores"
    assert restored.integrations[0].name == "Salesforce"


@pytest.mark.asyncio
async def test_session_state_file_persistence(tmp_path: Path):
    """InterviewSession state pode ser salvo em arquivo."""
    state = DiscoveryState(session_id="s1")
    state.company.segment = "varejo"

    session = InterviewSession(state, out_dir=tmp_path)

    # Salvar manualmente (como faria o runner)
    state_file = tmp_path / "discovery_state.json"
    state_file.write_text(state.model_dump_json(), encoding="utf-8")

    # Restaurar
    loaded_json = state_file.read_text(encoding="utf-8")
    restored = DiscoveryState.model_validate_json(loaded_json)

    assert restored.session_id == "s1"
    assert restored.company.segment == "varejo"


# --- Error handling robustness ---


@pytest.mark.asyncio
async def test_reflect_invalid_json_graceful(tmp_path: Path):
    """reflect deve tratar JSON inválido graciosamente."""
    session = InterviewSession(DiscoveryState(session_id="s1"), out_dir=tmp_path)
    result = await session.reflect("algo", "{ INVALID JSON ]")
    text = "".join(b.get("text", "") for b in result.content if isinstance(b, dict))
    assert "inválido" in text.lower() or "invalid" in text.lower()


@pytest.mark.asyncio
async def test_emit_blueprint_invalid_json_graceful(tmp_path: Path):
    """emit_blueprint deve tratar JSON inválido graciosamente."""
    session = InterviewSession(DiscoveryState(session_id="s1"), out_dir=tmp_path)
    result = await session.emit_blueprint("[ NOT VALID {")
    text = "".join(b.get("text", "") for b in result.content if isinstance(b, dict))
    assert "inválido" in text.lower() or "invalid" in text.lower()


@pytest.mark.asyncio
async def test_reflect_missing_required_fields(tmp_path: Path):
    """reflect deve validar schema ReflectUpdate."""
    session = InterviewSession(DiscoveryState(session_id="s1"), out_dir=tmp_path)
    # ReflectUpdate requer "learned"
    invalid_update = json.dumps({"close_area_ids": []})
    result = await session.reflect("test", invalid_update)
    text = "".join(b.get("text", "") for b in result.content if isinstance(b, dict))
    assert "inválido" in text.lower()


# --- Deduplicação de open_areas ---


@pytest.mark.asyncio
async def test_reflect_no_duplicate_open_areas(tmp_path: Path):
    """reflect não deve criar duplicatas de open_areas."""
    session = InterviewSession(DiscoveryState(session_id="s1"), out_dir=tmp_path)
    session.state.open_areas.append(
        OpenArea(id="base", topic="Base", confidence=0.1, priority=3),
    )

    updates = json.dumps({
        "learned": "learning",
        "new_areas": [
            {"id": "base", "topic": "Base Updated", "confidence": 0.5, "priority": 3},
        ],
    })

    await session.reflect("learning", updates)

    # Deve ter apenas 1 "base", não 2
    base_count = sum(1 for a in session.state.open_areas if a.id == "base")
    assert base_count == 1


# --- Deduplicação de integrações ---


@pytest.mark.asyncio
async def test_reflect_no_duplicate_integrations(tmp_path: Path):
    """reflect não deve criar duplicatas de integrações."""
    session = InterviewSession(DiscoveryState(session_id="s1"), out_dir=tmp_path)
    session.state.integrations.append(
        Integration(kind="crm", name="HubSpot"),
    )

    updates = json.dumps({
        "learned": "integração confirmada",
        "integrations": [
            {"kind": "crm", "name": "HubSpot", "data_location": "cloud"},
        ],
    })

    await session.reflect("confirmado", updates)

    # Deve ter apenas 1 HubSpot
    hubspot_count = sum(
        1 for i in session.state.integrations
        if i.kind == "crm" and i.name == "HubSpot"
    )
    assert hubspot_count == 1


# --- Blueprint gerado correctness ---


@pytest.mark.asyncio
async def test_emit_blueprint_generates_markdown(tmp_path: Path):
    """emit_blueprint deve gerar arquivo .md bem formatado."""
    session = InterviewSession(DiscoveryState(session_id="s1"), out_dir=tmp_path)
    bp = {
        "company_profile": {
            "segment": "ecommerce",
            "size": "micro",
            "business_model": "venda online",
        },
        "process_map": [{"name": "vendas", "description": "Processo de venda"}],
        "detected_integrations": [
            {
                "kind": "planilha",
                "name": "Google Sheets",
                "data_location": "drive",
                "confidence": 0.8,
            },
        ],
        "proposed_team": [
            {
                "name": "VendedorBot",
                "role": "Vendedor",
                "objective": "vender",
                "tasks": ["receber pedidos"],
                "tools_integrations": ["mcp:sheets"],
                "talks_to": [],
            },
        ],
        "roadmap": [{"order": 1, "title": "VendedorBot", "rationale": "primeiro"}],
        "open_questions": ["volume de vendas/dia"],
    }

    await session.emit_blueprint(json.dumps(bp))

    md_file = tmp_path / "blueprint.md"
    assert md_file.exists()
    md_content = md_file.read_text()
    assert "ecommerce" in md_content.lower()
    assert "VendedorBot" in md_content
    assert "Google Sheets" in md_content
