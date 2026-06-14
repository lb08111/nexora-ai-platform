# -*- coding: utf-8 -*-
"""FastAPI router exposing the discovery agent as a CopilotKit CoAgent.

Endpoints (mounted under ``/api/discovery-copilotkit``):

- ``POST   /sessions``                 — create a new session, returns the
  initial agent state (opening question + empty slices).
- ``POST   /sessions/{sid}/turn``      — submit the user message, returns
  the new agent state (next question OR final blueprint).
- ``GET    /sessions/{sid}``           — fetch the latest agent state.
- ``GET    /sessions/{sid}/blueprint`` — final ``TeamBlueprint`` once done.
- ``GET    /components``               — manifest mapping state slices to
  CopilotKit React components.

The router holds an in-memory session map; production deployments can swap
in a Redis-backed manager via ``SessionManager.set_factory``.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Callable, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from jotaduo.discovery import ScriptedDiscoverySession
from jotaduo.discovery.session import DiscoverySession

from copilotkit_adapter import (
    DiscoveryAgentState,
    build_agent_state,
    components_manifest,
)


# --- session manager -----------------------------------------------------


@dataclass
class _SessionEntry:
    session: DiscoverySession
    last_state: DiscoveryAgentState
    turn_index: int = 0
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class SessionManager:
    """Holds live discovery sessions keyed by ``session_id``.

    Defaults to the LLM-free ``ScriptedDiscoverySession`` so the plugin
    can be exercised in tests / eval without an active model. Production
    callers can inject ``LiveDiscoverySession`` via ``set_factory``.
    """

    def __init__(
        self,
        factory: Callable[[], DiscoverySession] | None = None,
    ) -> None:
        self._factory: Callable[[], DiscoverySession] = (
            factory or ScriptedDiscoverySession
        )
        self._sessions: dict[str, _SessionEntry] = {}

    def set_factory(self, factory: Callable[[], DiscoverySession]) -> None:
        self._factory = factory

    async def create(self) -> tuple[str, DiscoveryAgentState]:
        sid = uuid4().hex[:12]
        session = self._factory()
        turn = await session.next_turn(None)
        state = build_agent_state(sid, turn, turn_index=0)
        self._sessions[sid] = _SessionEntry(
            session=session,
            last_state=state,
            turn_index=0,
        )
        return sid, state

    async def turn(
        self,
        sid: str,
        user_message: str,
    ) -> DiscoveryAgentState:
        entry = self._sessions.get(sid)
        if entry is None:
            raise HTTPException(status_code=404, detail="session not found")
        if entry.last_state.status == "done":
            # Already finished — return the cached terminal state instead
            # of replaying through a closed scripted/live session.
            return entry.last_state
        async with entry.lock:
            entry.turn_index += 1
            turn_result = await entry.session.next_turn(user_message)
            state = build_agent_state(
                sid,
                turn_result,
                turn_index=entry.turn_index,
            )
            entry.last_state = state
            return state

    def get(self, sid: str) -> DiscoveryAgentState:
        entry = self._sessions.get(sid)
        if entry is None:
            raise HTTPException(status_code=404, detail="session not found")
        return entry.last_state

    def reset(self) -> None:
        """Drop all sessions (used by tests)."""
        self._sessions.clear()


_MANAGER = SessionManager()


def get_session_manager() -> SessionManager:
    """Return the process-wide session manager (override-friendly)."""
    return _MANAGER


# --- request / response schemas ------------------------------------------


class CreateSessionResponse(BaseModel):
    session_id: str
    state: DiscoveryAgentState


class TurnRequest(BaseModel):
    message: str = Field(..., min_length=1)


class TurnResponse(BaseModel):
    state: DiscoveryAgentState


class BlueprintResponse(BaseModel):
    session_id: str
    blueprint: Optional[dict]


class ComponentsResponse(BaseModel):
    components: list[dict[str, Any]]
    version: str


# --- router builder ------------------------------------------------------


def build_router(
    manager: SessionManager | None = None,
) -> APIRouter:
    """Build the FastAPI router. Injectable manager keeps tests hermetic."""
    mgr = manager or _MANAGER
    router = APIRouter()

    @router.post("/sessions", response_model=CreateSessionResponse)
    async def create_session() -> CreateSessionResponse:
        sid, state = await mgr.create()
        return CreateSessionResponse(session_id=sid, state=state)

    @router.post(
        "/sessions/{sid}/turn",
        response_model=TurnResponse,
    )
    async def post_turn(sid: str, body: TurnRequest) -> TurnResponse:
        state = await mgr.turn(sid, body.message)
        return TurnResponse(state=state)

    @router.get(
        "/sessions/{sid}",
        response_model=DiscoveryAgentState,
    )
    async def get_state(sid: str) -> DiscoveryAgentState:
        return mgr.get(sid)

    @router.get(
        "/sessions/{sid}/blueprint",
        response_model=BlueprintResponse,
    )
    async def get_blueprint(sid: str) -> BlueprintResponse:
        state = mgr.get(sid)
        if state.blueprint is None:
            raise HTTPException(
                status_code=409,
                detail="blueprint not ready (session still in progress)",
            )
        return BlueprintResponse(
            session_id=sid,
            blueprint=state.blueprint,
        )

    @router.get("/components", response_model=ComponentsResponse)
    def get_components() -> ComponentsResponse:
        manifest = components_manifest()
        return ComponentsResponse(
            components=manifest["components"],
            version=manifest.get("version", "0.0.0"),
        )

    return router
