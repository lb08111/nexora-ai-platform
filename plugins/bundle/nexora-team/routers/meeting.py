# -*- coding: utf-8 -*-
"""HTTP API for Nexora team meetings.

Endpoints
---------
POST   /api/nexora-team/meeting          → convene a new meeting
GET    /api/nexora-team/meeting          → list recent meetings
GET    /api/nexora-team/meeting/{id}     → fetch a meeting transcript
DELETE /api/nexora-team/meeting          → clear the in-memory store
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ..constants import ALL_AGENT_IDS, ORCHESTRATOR_AGENT_ID
from ..store import get_meeting_store
from ..tools.meeting_tools import convene_meeting

logger = logging.getLogger("qwenpaw").getChild(
    "plugin.nexora-team.routers.meeting",
)

router = APIRouter(prefix="", tags=["nexora-team-meeting"])


class ConveneMeetingRequest(BaseModel):
    topic: str = Field(..., min_length=3)
    participants: list[str] | None = Field(
        default=None,
        description=(
            "Agent IDs or bare role names. Default: all 4 Nexora "
            "specialists (excluding the convener)."
        ),
    )
    convener: str = Field(default=ORCHESTRATOR_AGENT_ID)
    context: str = ""
    per_agent_timeout_s: float = Field(default=30.0, ge=1.0, le=300.0)


class ContributionView(BaseModel):
    agent_id: str
    agent_name: str
    role: str
    content: str
    elapsed_ms: int
    error: str | None = None


class MeetingView(BaseModel):
    id: str
    topic: str
    convener: str
    participants: list[str]
    status: str
    summary: str | None
    created_at: float
    finished_at: float | None
    contributions: list[ContributionView]


@router.post("", response_model=MeetingView)
async def convene(body: ConveneMeetingRequest) -> MeetingView:
    """Convene a new meeting and return the full transcript."""
    resp = await convene_meeting(
        topic=body.topic,
        participants=body.participants,
        convener=body.convener,
        context=body.context,
        per_agent_timeout_s=body.per_agent_timeout_s,
    )
    payload = _extract_payload(resp)
    meeting = get_meeting_store().get(payload["meeting_id"])
    if meeting is None:
        raise HTTPException(
            status_code=500,
            detail="Meeting was created but not retrievable.",
        )
    return _to_view(meeting)


@router.get("", response_model=list[MeetingView])
def list_meetings(
    limit: int = Query(20, ge=1, le=200),
    status: str | None = Query(None),
) -> list[MeetingView]:
    """List recent meetings (most recent first)."""
    return [_to_view(m) for m in get_meeting_store().list(limit, status)]


@router.get("/{meeting_id}", response_model=MeetingView)
def get_meeting(meeting_id: str) -> MeetingView:
    meeting = get_meeting_store().get(meeting_id)
    if meeting is None:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return _to_view(meeting)


@router.delete("")
def clear_meetings() -> dict[str, str]:
    """Drop the in-memory store (admin / test usage)."""
    get_meeting_store().clear()
    return {"status": "cleared"}


@router.get("/_/participants")
def list_participants() -> dict[str, list[str]]:
    """Convenience endpoint for the Console UI."""
    return {"agent_ids": list(ALL_AGENT_IDS)}


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


def _to_view(meeting) -> MeetingView:
    return MeetingView(
        id=meeting.id,
        topic=meeting.topic,
        convener=meeting.convener,
        participants=meeting.participants,
        status=meeting.status,
        summary=meeting.summary,
        created_at=meeting.created_at,
        finished_at=meeting.finished_at,
        contributions=[
            ContributionView(
                agent_id=c.agent_id,
                agent_name=c.agent_name,
                role=c.role,
                content=c.content,
                elapsed_ms=c.elapsed_ms,
                error=c.error,
            )
            for c in meeting.contributions
        ],
    )


def _extract_payload(resp) -> dict:
    """ToolResponse payload extractor (mirrors br_team test helper)."""
    import json as _json

    content = getattr(resp, "content", resp)
    if isinstance(content, list):
        for blk in content:
            text = (
                blk.get("text")
                if isinstance(blk, dict)
                else getattr(blk, "text", None)
            )
            if text:
                try:
                    return _json.loads(text)
                except Exception:
                    continue
    if isinstance(content, str):
        return _json.loads(content)
    raise HTTPException(status_code=500, detail="Unexpected tool response")
