# -*- coding: utf-8 -*-
"""Adapter contract tests: TurnResult → DiscoveryAgentState shape.

Drives the deterministic ``ScriptedDiscoverySession`` directly and checks
that ``build_agent_state`` produces the exact JSON shape the CopilotKit
frontend expects (see ``components/types.ts``).
"""
from __future__ import annotations

from copilotkit_adapter import (
    DiscoveryAgentState,
    build_agent_state,
    components_manifest,
    list_components,
)
import pytest

from jotaduo.discovery import ScriptedDiscoverySession


@pytest.mark.asyncio
async def test_build_agent_state_opening_turn_carries_question():
    sess = ScriptedDiscoverySession()
    turn = await sess.next_turn(None)
    state = build_agent_state("sid-1", turn, turn_index=0)

    assert isinstance(state, DiscoveryAgentState)
    assert state.session_id == "sid-1"
    assert state.status == "in_progress"
    assert state.question  # opening question must exist
    assert state.blueprint is None
    assert state.turn_index == 0
    # Panel is always rendered — it is the CopilotKit shell.
    assert "DiscoveryAgentPanel" in state.rendered_components


@pytest.mark.asyncio
async def test_build_agent_state_progresses_company_slice():
    sess = ScriptedDiscoverySession()
    await sess.next_turn(None)  # opening question
    turn = await sess.next_turn(
        "Tenho uma loja virtual de roupas femininas.",
    )
    state = build_agent_state("sid-2", turn, turn_index=1)

    assert state.company.get("segment") == "ecommerce"
    # company slice non-empty → CompanyProfileCard must render
    assert "CompanyProfileCard" in state.rendered_components


@pytest.mark.asyncio
async def test_build_agent_state_done_carries_blueprint_and_lights_preview():
    sess = ScriptedDiscoverySession()
    await sess.next_turn(None)
    await sess.next_turn("loja virtual de roupas femininas")
    await sess.next_turn("uso planilha e WhatsApp")
    turn = await sess.next_turn("atendimento toma o dia inteiro")

    state = build_agent_state("sid-3", turn, turn_index=3)

    assert turn.done is True
    assert state.status == "done"
    assert state.blueprint is not None
    assert state.blueprint["proposed_team"]
    assert "BlueprintPreview" in state.rendered_components


def test_components_manifest_matches_python_view():
    manifest = components_manifest()
    names = [c["name"] for c in manifest["components"]]
    assert names == list_components()
    # Every component must declare the slice and file it binds to.
    for c in manifest["components"]:
        assert "name" in c and "file" in c and "stateSlice" in c
