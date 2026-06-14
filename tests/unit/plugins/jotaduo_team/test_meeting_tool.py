# -*- coding: utf-8 -*-
"""Tests for ``convene_meeting`` tool (uses the offline stub branch).

We don't have a live MultiAgentManager in unit tests; the tool falls
back to a deterministic stub when ``chat_with_agent`` can't be
imported. We monkeypatch the import to force the stub path.
"""

from __future__ import annotations

import asyncio
import json
import sys

import pytest

from jotaduo_team_plugin.constants import (
    AGENDAMENTO_AGENT_ID,
    ALL_AGENT_IDS,
    ATENDENTE_AGENT_ID,
    FINANCEIRO_AGENT_ID,
    ORCHESTRATOR_AGENT_ID,
    VENDAS_AGENT_ID,
)
from jotaduo_team_plugin.tools.meeting_tools import convene_meeting


def _payload(resp):
    blocks = resp.content
    for blk in blocks:
        text = blk.get("text") if isinstance(blk, dict) else None
        if text:
            return json.loads(text)
    raise AssertionError("no payload found")


@pytest.fixture
def force_stub(monkeypatch):
    """Force the meeting tool to use the offline stub path."""
    import jotaduo_team_plugin.tools.meeting_tools as mt

    async def _stub(agent_id, prompt):
        return mt._stub_response(agent_id, prompt)

    monkeypatch.setattr(mt, "_call_agent", _stub)
    return mt


@pytest.mark.asyncio
async def test_convene_with_default_participants_skips_convener(force_stub):
    resp = await convene_meeting(
        topic="Cliente quer parcelar em 12x — pode?",
        convener=ORCHESTRATOR_AGENT_ID,
    )
    payload = _payload(resp)

    assert payload["meeting_id"].startswith("mtg-")
    assert ORCHESTRATOR_AGENT_ID not in payload["participants"]
    expected = [a for a in ALL_AGENT_IDS if a != ORCHESTRATOR_AGENT_ID]
    assert payload["participants"] == expected
    assert len(payload["transcript"]) == len(expected)
    assert all(item["error"] is None for item in payload["transcript"])
    assert payload["summary"].startswith("Reunião sobre:")


@pytest.mark.asyncio
async def test_convene_accepts_bare_role_names(force_stub):
    resp = await convene_meeting(
        topic="Qual canal usar amanhã?",
        participants=["vendas", "atendente"],
    )
    payload = _payload(resp)
    assert payload["participants"] == [VENDAS_AGENT_ID, ATENDENTE_AGENT_ID]


@pytest.mark.asyncio
async def test_convene_dedupes_and_filters_invalid(force_stub):
    resp = await convene_meeting(
        topic="Qual horário?",
        participants=[
            VENDAS_AGENT_ID,
            "vendas",  # alias dedupes
            "astrofisico",  # invalid → drop
            AGENDAMENTO_AGENT_ID,
        ],
    )
    payload = _payload(resp)
    assert payload["participants"] == [
        VENDAS_AGENT_ID,
        AGENDAMENTO_AGENT_ID,
    ]


@pytest.mark.asyncio
async def test_convene_empty_topic_returns_error(force_stub):
    resp = await convene_meeting(topic="   ")
    text_blk = resp.content[0]
    text = text_blk.get("text") if isinstance(text_blk, dict) else None
    assert text is not None
    assert "Tópico vazio" in text


@pytest.mark.asyncio
async def test_convene_no_valid_participants_returns_error(force_stub):
    resp = await convene_meeting(
        topic="ok",
        participants=["xyz", "noexiste"],
    )
    text_blk = resp.content[0]
    text = text_blk.get("text") if isinstance(text_blk, dict) else None
    assert text is not None
    assert "Nenhum participante válido" in text


@pytest.mark.asyncio
async def test_convene_captures_timeout(monkeypatch):
    """When an agent times out, the contribution is recorded with error."""
    import jotaduo_team_plugin.tools.meeting_tools as mt

    async def _hang(agent_id, prompt):
        await asyncio.sleep(5)
        return "never"

    monkeypatch.setattr(mt, "_call_agent", _hang)

    resp = await convene_meeting(
        topic="Demoroso",
        participants=[VENDAS_AGENT_ID],
        per_agent_timeout_s=0.1,
    )
    payload = _payload(resp)
    item = payload["transcript"][0]
    assert item["error"] is not None
    assert "timeout" in item["error"]


@pytest.mark.asyncio
async def test_convene_captures_exception(monkeypatch):
    import jotaduo_team_plugin.tools.meeting_tools as mt

    async def _boom(agent_id, prompt):
        raise RuntimeError("provider down")

    monkeypatch.setattr(mt, "_call_agent", _boom)

    resp = await convene_meeting(
        topic="boom",
        participants=[FINANCEIRO_AGENT_ID],
    )
    payload = _payload(resp)
    item = payload["transcript"][0]
    assert "provider down" in item["error"]
