# -*- coding: utf-8 -*-
"""Adapter: discovery ``TurnResult`` → CopilotKit CoAgent state JSON.

CopilotKit's CoAgent contract is a single JSON object the React side reads
via ``useCoAgent`` / renders via ``useCoAgentStateRender``. We project the
discovery agent's ``DiscoveryState`` + optional ``TeamBlueprint`` into a
flat ``DiscoveryAgentState`` so a single state stream drives every
component without ad-hoc shape negotiation.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field

from qwenpaw.discovery.session import TurnResult

# --- component manifest --------------------------------------------------

_MANIFEST_PATH = Path(__file__).parent / "components" / "manifest.json"


def components_manifest() -> dict[str, Any]:
    """Return the static state→component mapping consumed by the frontend."""
    return json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))


def list_components() -> list[str]:
    return [c["name"] for c in components_manifest()["components"]]


# --- state contract ------------------------------------------------------


class DiscoveryAgentState(BaseModel):
    """Single JSON payload streamed to the CopilotKit CoAgent.

    The frontend uses ``useCoAgent<DiscoveryAgentState>`` and binds each
    component declared in ``manifest.json`` to a slice of this shape.
    """

    session_id: str
    status: str = Field(
        default="in_progress",
        description="in_progress | done | error",
    )
    question: Optional[str] = None
    company: dict = Field(default_factory=dict)
    open_areas: list[dict] = Field(default_factory=list)
    integrations: list[dict] = Field(default_factory=list)
    transcript: list[dict] = Field(default_factory=list)
    blueprint: Optional[dict] = None
    turn_index: int = 0
    rendered_components: list[str] = Field(default_factory=list)


def _select_components(payload: "DiscoveryAgentState") -> list[str]:
    """Decide which manifest components have non-empty data to render.

    Mirrors what ``useCoAgentStateRender`` does on the client: only mount
    a component when its slice is non-empty. We treat the blueprint's
    ``detected_integrations`` / ``proposed_team`` as fallback signals so a
    scripted (LLM-free) session still lights up the integration card once
    the blueprint arrives, even when the running state never accumulated
    integrations during the interview.
    """
    rendered: list[str] = []
    bp = payload.blueprint or {}
    bp_integrations = bp.get("detected_integrations") or []
    bp_open = bp.get("open_questions") or []

    if payload.company or bp.get("company_profile"):
        rendered.append("CompanyProfileCard")
    if payload.open_areas or bp_open:
        rendered.append("OpenAreasList")
    if payload.integrations or bp_integrations:
        rendered.append("IntegrationsList")
    if payload.blueprint is not None:
        rendered.append("BlueprintPreview")
    # The panel is always rendered — it is the CopilotKit provider shell.
    rendered.append("DiscoveryAgentPanel")
    return rendered


def build_agent_state(
    session_id: str,
    turn: TurnResult,
    *,
    turn_index: int,
) -> DiscoveryAgentState:
    """Project a ``TurnResult`` into the CopilotKit CoAgent state JSON."""
    state = turn.state or {}
    payload = DiscoveryAgentState(
        session_id=session_id,
        status="done" if turn.done else "in_progress",
        question=turn.question,
        company=state.get("company") or {},
        open_areas=list(state.get("open_areas") or []),
        integrations=list(state.get("integrations") or []),
        transcript=list(state.get("transcript") or []),
        blueprint=turn.blueprint,
        turn_index=turn_index,
    )
    payload.rendered_components = _select_components(payload)
    return payload
