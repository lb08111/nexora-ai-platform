# -*- coding: utf-8 -*-
"""Regression tests for agent workspace file isolation."""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from starlette.responses import FileResponse


@pytest.mark.asyncio
async def test_file_preview_rejects_paths_outside_current_agent_workspace(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
):
    from qwenpaw.app.routers import files

    workspace_dir = tmp_path / "workspaces" / "agent-a"
    other_dir = tmp_path / "workspaces" / "agent-b"
    workspace_dir.mkdir(parents=True)
    other_dir.mkdir(parents=True)
    inside = workspace_dir / "note.txt"
    outside = other_dir / "secret.txt"
    inside.write_text("inside", encoding="utf-8")
    outside.write_text("outside", encoding="utf-8")

    async def fake_get_agent_for_request(_request):
        return SimpleNamespace(workspace_dir=workspace_dir)

    monkeypatch.setattr(
        files, "get_agent_for_request", fake_get_agent_for_request
    )

    response = await files.preview_file(SimpleNamespace(), "note.txt")
    assert isinstance(response, FileResponse)

    with pytest.raises(HTTPException) as exc_info:
        await files.preview_file(SimpleNamespace(), str(outside))

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_file_tools_reject_paths_outside_current_agent_workspace(
    tmp_path,
):
    from qwenpaw.agents.tools import file_io
    from qwenpaw.config.context import set_current_workspace_dir

    workspace_dir = tmp_path / "workspaces" / "agent-a"
    other_dir = tmp_path / "workspaces" / "agent-b"
    workspace_dir.mkdir(parents=True)
    other_dir.mkdir(parents=True)
    outside = other_dir / "secret.txt"
    outside.write_text("outside", encoding="utf-8")

    try:
        set_current_workspace_dir(workspace_dir)

        write_response = await file_io.write_file("notes/todo.md", "inside")
        assert "Wrote" in write_response.content[0]["text"]
        assert (workspace_dir / "notes" / "todo.md").read_text(
            "utf-8"
        ) == "inside"

        read_response = await file_io.read_file(str(outside))
        assert (
            "limited to the current agent workspace"
            in read_response.content[0]["text"]
        )

        append_response = await file_io.append_file(str(outside), "leak")
        assert (
            "limited to the current agent workspace"
            in append_response.content[0]["text"]
        )
        assert outside.read_text("utf-8") == "outside"
    finally:
        set_current_workspace_dir(None)
