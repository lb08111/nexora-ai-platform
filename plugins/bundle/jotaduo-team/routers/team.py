# -*- coding: utf-8 -*-
"""GET /api/jotaduo-team/team — list registered Jotaduo specialists.

Also supports POST /api/jotaduo-team/team/build to materialize a
``TeamBlueprint`` (from the DiscoveryAgent) into a runtime preview.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..constants import AGENT_SPECS

logger = logging.getLogger("jotaduo").getChild(
    "plugin.jotaduo-team.routers.team",
)

router = APIRouter(prefix="", tags=["jotaduo-team"])


class AgentInfo(BaseModel):
    agent_id: str
    name: str
    role: str
    description: str
    skill_names: list[str]
    tools_count: int


class TeamListResponse(BaseModel):
    count: int
    agents: list[AgentInfo]


class BlueprintAgentSpec(BaseModel):
    role: str = Field(..., description="Free-form role from DiscoveryAgent")
    name: str = ""


class BuildTeamRequest(BaseModel):
    blueprint: dict[str, Any] = Field(
        ...,
        description="TeamBlueprint payload, as produced by DiscoveryAgent",
    )


class BuildTeamResponse(BaseModel):
    resolved: list[dict[str, Any]]
    skipped: list[dict[str, Any]]
    role_map: dict[str, str]


@router.get("", response_model=TeamListResponse)
def list_team() -> TeamListResponse:
    """List the Jotaduo specialists this plugin registers."""
    agents = [
        AgentInfo(
            agent_id=spec["agent_id"],
            name=spec["name"],
            role=spec["role"],
            description=spec["description"],
            skill_names=spec["skill_names"],
            tools_count=len(spec.get("extra_tools", {})),
        )
        for spec in AGENT_SPECS
    ]
    return TeamListResponse(count=len(agents), agents=agents)


@router.post("/build", response_model=BuildTeamResponse)
def build_from_blueprint(body: BuildTeamRequest) -> BuildTeamResponse:
    """Materialize a DiscoveryAgent blueprint (preview only).

    Does NOT instantiate models — returns the role mapping so the
    Console can show the user which specialists were matched.
    """
    try:
        from jotaduo.agents.br_team import build_team_from_blueprint
        from jotaduo.discovery.state import TeamBlueprint
    except ImportError as exc:  # pragma: no cover - import guard
        raise HTTPException(
            status_code=500,
            detail=f"br_team not available: {exc}",
        ) from exc

    try:
        blueprint = TeamBlueprint.model_validate(body.blueprint)
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid blueprint: {exc}",
        ) from exc

    result = build_team_from_blueprint(blueprint, instantiate=False)

    resolved = (
        [
            {"original_name": spec.name, "role": role}
            for spec, role in result.role_map.items()
        ]
        if isinstance(result.role_map, dict)
        else []
    )

    return BuildTeamResponse(
        resolved=resolved,
        skipped=list(result.skipped),
        role_map={
            getattr(spec, "name", str(spec)): role
            for spec, role in (
                result.role_map.items()
                if hasattr(result.role_map, "items")
                else []
            )
        },
    )
