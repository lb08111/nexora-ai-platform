# -*- coding: utf-8 -*-
import json

import pytest

from qwenpaw.discovery.state import DiscoveryState, OpenArea
from qwenpaw.discovery.tools import InterviewSession


def _text(resp):
    # TextBlock in ToolResponse is a dict
    text_parts = []
    for b in resp.content:
        if isinstance(b, dict) and b.get("type") == "text":
            text_parts.append(b.get("text", ""))
    return "".join(text_parts)


@pytest.mark.asyncio
async def test_segment_lookup_known(tmp_path):
    s = InterviewSession(DiscoveryState(session_id="s1"), out_dir=tmp_path)
    chunk = await s.segment_lookup("tenho uma loja virtual")
    assert "ecommerce" in _text(chunk).lower()
    assert s.state.company.segment == "ecommerce"


@pytest.mark.asyncio
async def test_segment_lookup_unknown_records_open_question(tmp_path):
    s = InterviewSession(DiscoveryState(session_id="s1"), out_dir=tmp_path)
    chunk = await s.segment_lookup("mineração de asteroides")
    assert "livre" in _text(chunk).lower() or "não" in _text(chunk).lower()
    assert any(a.id == "validar-segmento" for a in s.state.open_areas)


@pytest.mark.asyncio
async def test_reflect_mutates_state(tmp_path):
    s = InterviewSession(DiscoveryState(session_id="s1"), out_dir=tmp_path)
    s.state.open_areas.append(
        OpenArea(
            id="segmento",
            topic="qual segmento",
            confidence=0.1,
            priority=5,
        ),
    )
    updates = json.dumps(
        {
            "learned": "e-commerce de roupas",
            "close_area_ids": ["segmento"],
            "new_areas": [
                {
                    "id": "logistica",
                    "topic": "entrega",
                    "confidence": 0.1,
                    "priority": 4,
                },
            ],
            "integrations": [
                {
                    "kind": "planilha",
                    "name": "Sheets",
                    "data_location": "drive",
                    "confidence": 0.6,
                },
            ],
            "company_updates": {"segment": "e-commerce"},
            "confidence_updates": {},
        },
    )
    await s.reflect("e-commerce de roupas", updates)
    ids = [a.id for a in s.state.open_areas]
    assert "segmento" not in ids and "logistica" in ids
    assert s.state.company.segment == "e-commerce"
    assert s.state.integrations[0].name == "Sheets"


@pytest.mark.asyncio
async def test_emit_blueprint_writes_files(tmp_path):
    s = InterviewSession(DiscoveryState(session_id="s1"), out_dir=tmp_path)
    bp = {
        "company_profile": {
            "segment": "e-commerce",
            "size": "micro",
            "business_model": "venda online",
            "pains": ["atendimento lento"],
        },
        "process_map": [{"name": "atendimento", "description": "SAC"}],
        "detected_integrations": [],
        "proposed_team": [
            {
                "name": "Atendente",
                "role": "SAC",
                "objective": "responder",
                "tasks": ["responder"],
                "tools_integrations": ["mcp:evolution-whatsapp"],
                "talks_to": [],
            },
        ],
        "roadmap": [{"order": 1, "title": "WhatsApp", "rationale": "dor"}],
        "open_questions": [],
    }
    result = await s.emit_blueprint(json.dumps(bp))
    assert (tmp_path / "blueprint.json").exists()
    assert (tmp_path / "blueprint.md").exists()
    assert s.emitted is True
