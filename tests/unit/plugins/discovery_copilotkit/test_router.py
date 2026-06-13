# -*- coding: utf-8 -*-
"""End-to-end router test: drive the scripted session through HTTP.

Uses FastAPI's TestClient against a hermetic ``SessionManager`` so the
test cannot bleed state into other tests via the module-level manager.
"""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from router import SessionManager, build_router


@pytest.fixture
def client() -> TestClient:
    """Hermetic app/client: fresh SessionManager per test."""
    app = FastAPI()
    app.include_router(
        build_router(SessionManager()),
        prefix="/api/discovery-copilotkit",
    )
    with TestClient(app) as c:
        yield c


def test_components_endpoint_returns_manifest(client: TestClient):
    r = client.get("/api/discovery-copilotkit/components")
    assert r.status_code == 200
    data = r.json()
    assert data["version"]
    names = [c["name"] for c in data["components"]]
    for expected in (
        "CompanyProfileCard",
        "OpenAreasList",
        "IntegrationsList",
        "BlueprintPreview",
        "DiscoveryAgentPanel",
    ):
        assert expected in names


def test_create_session_returns_opening_state(client: TestClient):
    r = client.post("/api/discovery-copilotkit/sessions")
    assert r.status_code == 200
    body = r.json()
    sid = body["session_id"]
    assert sid
    state = body["state"]
    assert state["status"] == "in_progress"
    assert state["question"]  # opening question populated
    assert state["blueprint"] is None
    assert state["turn_index"] == 0


def test_full_session_reaches_blueprint(client: TestClient):
    r = client.post("/api/discovery-copilotkit/sessions")
    sid = r.json()["session_id"]

    answers = [
        "Tenho uma loja virtual de roupas femininas.",
        "Uso planilha e WhatsApp.",
        "Atendimento manual no WhatsApp toma o dia inteiro.",
    ]
    final = None
    rendered_seen: set[str] = set()
    rendered_seen.update(r.json()["state"]["rendered_components"])
    for ans in answers:
        rr = client.post(
            f"/api/discovery-copilotkit/sessions/{sid}/turn",
            json={"message": ans},
        )
        assert rr.status_code == 200, rr.text
        final = rr.json()["state"]
        rendered_seen.update(final["rendered_components"])

    assert final is not None
    assert final["status"] == "done"
    assert final["blueprint"] is not None
    assert final["blueprint"]["proposed_team"]

    # All four data-driven components rendered at some point.
    for expected in (
        "CompanyProfileCard",
        "IntegrationsList",
        "BlueprintPreview",
        "DiscoveryAgentPanel",
    ):
        assert expected in rendered_seen


def test_blueprint_endpoint_409_while_in_progress(client: TestClient):
    sid = client.post(
        "/api/discovery-copilotkit/sessions",
    ).json()["session_id"]
    r = client.get(f"/api/discovery-copilotkit/sessions/{sid}/blueprint")
    assert r.status_code == 409


def test_blueprint_endpoint_200_when_done(client: TestClient):
    sid = client.post(
        "/api/discovery-copilotkit/sessions",
    ).json()["session_id"]
    for ans in ("loja virtual", "planilha + whatsapp", "atendimento manual"):
        client.post(
            f"/api/discovery-copilotkit/sessions/{sid}/turn",
            json={"message": ans},
        )
    r = client.get(f"/api/discovery-copilotkit/sessions/{sid}/blueprint")
    assert r.status_code == 200
    body = r.json()
    assert body["session_id"] == sid
    assert body["blueprint"]["proposed_team"]


def test_unknown_session_returns_404(client: TestClient):
    r = client.get("/api/discovery-copilotkit/sessions/nope")
    assert r.status_code == 404
    r = client.post(
        "/api/discovery-copilotkit/sessions/nope/turn",
        json={"message": "hi"},
    )
    assert r.status_code == 404


def test_turn_rejects_empty_message(client: TestClient):
    sid = client.post(
        "/api/discovery-copilotkit/sessions",
    ).json()["session_id"]
    r = client.post(
        f"/api/discovery-copilotkit/sessions/{sid}/turn",
        json={"message": ""},
    )
    # Pydantic min_length=1 → 422
    assert r.status_code == 422


def test_post_turn_after_done_is_idempotent(client: TestClient):
    sid = client.post(
        "/api/discovery-copilotkit/sessions",
    ).json()["session_id"]
    for ans in ("loja virtual", "planilha + whatsapp", "atendimento manual"):
        client.post(
            f"/api/discovery-copilotkit/sessions/{sid}/turn",
            json={"message": ans},
        )
    # Session is now done; another turn must not crash and must return
    # the cached terminal state, not a 5xx.
    r = client.post(
        f"/api/discovery-copilotkit/sessions/{sid}/turn",
        json={"message": "anything else?"},
    )
    assert r.status_code == 200
    assert r.json()["state"]["status"] == "done"
