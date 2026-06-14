# -*- coding: utf-8 -*-
"""Tests for the MeetingStore (in-memory transcript backend)."""

from __future__ import annotations

import pytest

from nexora_team_plugin.store import Contribution, MeetingStore


def test_create_then_get_returns_same_meeting():
    store = MeetingStore()
    meeting = store.create(
        topic="Como tratar reclamação Reclame Aqui?",
        convener="nexora-orchestrator",
        participants=["nexora-suporte", "nexora-financeiro"],
    )

    fetched = store.get(meeting.id)

    assert fetched is meeting
    assert fetched.status == "running"
    assert fetched.id.startswith("mtg-")


def test_add_contribution_appends_in_order():
    store = MeetingStore()
    meeting = store.create("topic", "conv", ["a", "b"])

    store.add_contribution(
        meeting.id,
        Contribution(
            agent_id="a",
            agent_name="A",
            role="vendas",
            content="ok",
            elapsed_ms=10,
        ),
    )
    store.add_contribution(
        meeting.id,
        Contribution(
            agent_id="b",
            agent_name="B",
            role="suporte",
            content="ok2",
            elapsed_ms=15,
        ),
    )

    assert [c.agent_id for c in meeting.contributions] == ["a", "b"]


def test_finish_marks_completed_and_writes_summary():
    store = MeetingStore()
    meeting = store.create("topic", "conv", ["a"])

    store.finish(meeting.id, summary="ok", status="completed")

    assert meeting.summary == "ok"
    assert meeting.status == "completed"
    assert meeting.finished_at is not None


def test_list_filters_by_status_and_reverse_chronological():
    store = MeetingStore()
    m1 = store.create("t1", "c", ["a"])
    m2 = store.create("t2", "c", ["a"])
    store.finish(m1.id, "done", status="completed")

    listed = store.list()
    assert listed[0].id == m2.id  # most recent first

    only_completed = store.list(status="completed")
    assert [m.id for m in only_completed] == [m1.id]


def test_eviction_when_over_capacity():
    store = MeetingStore(max_meetings=3)
    ids = [
        store.create(f"t{i}", "c", ["a"]).id
        for i in range(5)
    ]
    listed = store.list(limit=10)
    assert len(listed) == 3
    # the two oldest are gone
    assert store.get(ids[0]) is None
    assert store.get(ids[1]) is None
    assert store.get(ids[4]) is not None


def test_to_dict_includes_iso_timestamps():
    store = MeetingStore()
    meeting = store.create("t", "c", ["a"])
    store.finish(meeting.id, "ok")
    payload = store.get(meeting.id).to_dict()
    assert "T" in payload["created_at_iso"]
    assert payload["finished_at_iso"] is not None


def test_unknown_meeting_returns_none():
    store = MeetingStore()
    assert store.get("mtg-doesnotexist") is None
    assert (
        store.add_contribution(
            "mtg-doesnotexist",
            Contribution(
                agent_id="a",
                agent_name="A",
                role="x",
                content="",
                elapsed_ms=0,
            ),
        )
        is None
    )
    assert store.finish("mtg-doesnotexist", "summary") is None


@pytest.mark.parametrize("count", [0, 1, 5])
def test_clear_drops_everything(count):
    store = MeetingStore()
    for i in range(count):
        store.create(f"t{i}", "c", ["a"])
    store.clear()
    assert store.list() == []
