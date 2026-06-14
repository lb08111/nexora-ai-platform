# -*- coding: utf-8 -*-
"""Unit tests for Jotaduo audit persistence."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from jotaduo_ext.jotaduo import audit


@pytest.fixture(autouse=True)
def _isolated_audit_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(audit, "AUDIT_FILE", tmp_path / "jotaduo_audit.jsonl")


def test_record_audit_event_appends_jsonl_and_lists_newest_first():
    first = audit.record_audit_event(
        actor="alice",
        action="login.success",
        resource_type="auth",
        status="success",
    )
    second = audit.record_audit_event(
        actor="bob",
        action="api.denied",
        resource_type="api",
        status="denied",
    )

    lines = audit.AUDIT_FILE.read_text("utf-8").splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["id"] == first["id"]
    assert json.loads(lines[1])["id"] == second["id"]

    events = audit.list_audit_events(limit=10)
    assert [event["id"] for event in events] == [second["id"], first["id"]]


def test_list_audit_events_filters_by_actor_action_and_status():
    audit.record_audit_event(
        actor="alice",
        action="login.success",
        status="success",
    )
    denied = audit.record_audit_event(
        actor="alice",
        action="api.denied",
        status="denied",
    )
    audit.record_audit_event(actor="bob", action="api.denied", status="denied")

    events = audit.list_audit_events(
        limit=10,
        actor="alice",
        action="api.denied",
        status="denied",
    )

    assert [event["id"] for event in events] == [denied["id"]]


def test_record_tool_audit_event_stores_bounded_preview():
    event = audit.record_tool_audit_event(
        actor="admin",
        agent_id="ops-agent",
        tool_name="execute_shell_command",
        status="success",
        tool_call_id="call-1",
        session_id="session-1",
        channel="console",
        detail={"input_preview": audit.safe_preview({"cmd": "x" * 800})},
    )

    [stored] = audit.list_audit_events(limit=1)
    assert stored["id"] == event["id"]
    assert stored["action"] == "agent.tool.execute"
    assert stored["resource_type"] == "tool"
    assert stored["resource_id"] == "execute_shell_command"
    assert stored["detail"]["agent_id"] == "ops-agent"
    assert stored["detail"]["session_id"] == "session-1"
    assert len(stored["detail"]["input_preview"]) <= 2003
