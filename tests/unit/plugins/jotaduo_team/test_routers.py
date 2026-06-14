# -*- coding: utf-8 -*-
"""Tests for the jotaduo-team HTTP routers.

Wires the routers into a fresh FastAPI app so we don't depend on the
jotaduo plugin loader being initialised.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

import jotaduo_team_plugin.tools.meeting_tools as mt
from jotaduo_team_plugin.routers.meeting import router as meeting_router
from jotaduo_team_plugin.routers.team import router as team_router


def _make_app():
    app = FastAPI()
    app.include_router(team_router, prefix="/api/jotaduo-team/team")
    app.include_router(meeting_router, prefix="/api/jotaduo-team/meeting")
    return app


def test_team_list_returns_5_agents():
    client = TestClient(_make_app())
    r = client.get("/api/jotaduo-team/team")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["count"] == 5
    roles = {a["role"] for a in data["agents"]}
    assert roles == {
        "orchestrator",
        "atendente",
        "agendamento",
        "vendas",
        "financeiro",
    }
    # orchestrator carries the convene_meeting tool spec
    orch = next(a for a in data["agents"] if a["role"] == "orchestrator")
    assert orch["tools_count"] >= 4


def test_participants_endpoint_returns_full_roster():
    client = TestClient(_make_app())
    r = client.get("/api/jotaduo-team/meeting/_/participants")
    assert r.status_code == 200
    body = r.json()
    assert "jotaduo-orchestrator" in body["agent_ids"]
    assert "jotaduo-vendas" in body["agent_ids"]


def test_meeting_convene_returns_transcript(monkeypatch):
    async def _stub(agent_id, prompt):
        return mt._stub_response(agent_id, prompt)

    monkeypatch.setattr(mt, "_call_agent", _stub)

    client = TestClient(_make_app())
    r = client.post(
        "/api/jotaduo-team/meeting",
        json={
            "topic": "Cliente quer parcelar em 12x?",
            "participants": ["vendas", "financeiro"],
            "convener": "jotaduo-orchestrator",
        },
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["id"].startswith("mtg-")
    assert data["status"] == "completed"
    assert {c["role"] for c in data["contributions"]} == {
        "vendas",
        "financeiro",
    }
    assert data["summary"]


def test_meeting_get_by_id_roundtrip(monkeypatch):
    async def _stub(agent_id, prompt):
        return mt._stub_response(agent_id, prompt)

    monkeypatch.setattr(mt, "_call_agent", _stub)

    client = TestClient(_make_app())
    created = client.post(
        "/api/jotaduo-team/meeting",
        json={"topic": "Roundtrip test topic", "participants": ["vendas"]},
    ).json()
    mid = created["id"]

    r = client.get(f"/api/jotaduo-team/meeting/{mid}")
    assert r.status_code == 200
    assert r.json()["id"] == mid


def test_meeting_list_returns_recent_first(monkeypatch):
    async def _stub(agent_id, prompt):
        return mt._stub_response(agent_id, prompt)

    monkeypatch.setattr(mt, "_call_agent", _stub)

    client = TestClient(_make_app())
    a = client.post(
        "/api/jotaduo-team/meeting",
        json={"topic": "First topic here", "participants": ["vendas"]},
    ).json()
    b = client.post(
        "/api/jotaduo-team/meeting",
        json={"topic": "Second topic here", "participants": ["vendas"]},
    ).json()

    listed = client.get("/api/jotaduo-team/meeting?limit=5").json()
    assert [m["id"] for m in listed[:2]] == [b["id"], a["id"]]


def test_meeting_404_for_unknown_id():
    client = TestClient(_make_app())
    r = client.get("/api/jotaduo-team/meeting/mtg-bogus")
    assert r.status_code == 404


def test_meeting_validation_short_topic():
    client = TestClient(_make_app())
    r = client.post(
        "/api/jotaduo-team/meeting",
        json={"topic": "ab"},
    )
    assert r.status_code == 422


def test_meeting_clear_endpoint(monkeypatch):
    async def _stub(agent_id, prompt):
        return mt._stub_response(agent_id, prompt)

    monkeypatch.setattr(mt, "_call_agent", _stub)

    client = TestClient(_make_app())
    client.post(
        "/api/jotaduo-team/meeting",
        json={"topic": "Topic to be cleared", "participants": ["vendas"]},
    )
    assert len(client.get("/api/jotaduo-team/meeting").json()) == 1

    r = client.delete("/api/jotaduo-team/meeting")
    assert r.status_code == 200
    assert r.json() == {"status": "cleared"}
    assert client.get("/api/jotaduo-team/meeting").json() == []
