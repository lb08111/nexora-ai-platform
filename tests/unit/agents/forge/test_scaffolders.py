# -*- coding: utf-8 -*-
"""Unit tests for the scaffolders.

All tests run with ``dry_run=True`` to guarantee no disk writes.
"""

import json

import pytest

from qwenpaw.agents.forge.tools import (
    inspect_repo,
    scaffold_agent,
    scaffold_plugin,
    scaffold_skill,
    scaffold_team,
)


def _payload(resp):
    """Extract the JSON payload regardless of ToolResponse shape."""
    if hasattr(resp, "content"):
        content = resp.content
        if isinstance(content, list) and content:
            block = content[0]
            text = (
                block.get("text")
                if isinstance(block, dict)
                else getattr(block, "text", None)
            )
            if text:
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    return {"_raw": text}
    return {"_raw": str(resp)}


@pytest.mark.asyncio
async def test_inspect_repo_lists_known_packages():
    resp = await inspect_repo(area="all")
    data = _payload(resp)
    assert "agents" in data
    assert "br_team" in data["agents"]
    assert "skills" in data
    assert any(
        s.startswith("br_") or s == "agent_forge-pt"
        for s in data["skills"]
    )


@pytest.mark.asyncio
async def test_inspect_repo_rejects_bad_area():
    resp = await inspect_repo(area="nope")
    data = _payload(resp)
    assert "error" in data


@pytest.mark.asyncio
async def test_scaffold_skill_dry_run():
    resp = await scaffold_skill(
        name="Teste Reembolso",
        description="Decide reembolso CDC",
        when_to_use="Quando cliente pede dinheiro de volta",
        emoji="💸",
        body_markdown="## Passos\n1. checar",
        dry_run=True,
    )
    data = _payload(resp)
    assert data["kind"] == "skill"
    assert data["slug"] == "teste-reembolso"
    assert data["dry_run"] is True
    assert data["files"][0]["path"].endswith("SKILL.md")
    assert "written" not in data


@pytest.mark.asyncio
async def test_scaffold_skill_requires_name():
    resp = await scaffold_skill(name=" ", description="x")
    text = getattr(resp, "content", None)
    assert text is not None
    flat = json.dumps(text, default=str)
    assert "ERROR" in flat


@pytest.mark.asyncio
async def test_scaffold_agent_dry_run():
    resp = await scaffold_agent(
        name="Cobranca Premium",
        role="cobranca",
        description="Cobra inadimplentes",
        system_prompt="Você é o agente de cobrança.",
        dry_run=True,
    )
    data = _payload(resp)
    assert data["kind"] == "agent"
    assert data["class_name"] == "CobrancaPremiumAgent"
    assert data["module"] == "cobranca_premium"
    assert data["files"][0]["path"].endswith("cobranca_premium_agent.py")
    assert data["dry_run"] is True


@pytest.mark.asyncio
async def test_scaffold_team_dry_run():
    resp = await scaffold_team(
        name="Saude Team",
        roles=["Recepcao", "Triagem", "Pos Consulta"],
        dry_run=True,
    )
    data = _payload(resp)
    assert data["kind"] == "team"
    assert data["slug"] == "saude_team"
    assert data["roles"] == ["recepcao", "triagem", "pos_consulta"]
    paths = [f["path"] for f in data["files"]]
    assert any(p.endswith("__init__.py") for p in paths)
    assert any(p.endswith("prompts.py") for p in paths)
    assert any(p.endswith("factory.py") for p in paths)
    assert any(p.endswith("specialists/base.py") for p in paths)


@pytest.mark.asyncio
async def test_scaffold_team_requires_roles():
    resp = await scaffold_team(name="x", roles=[])
    flat = json.dumps(getattr(resp, "content", []), default=str)
    assert "ERROR" in flat


@pytest.mark.asyncio
async def test_scaffold_plugin_dry_run():
    resp = await scaffold_plugin(
        name="Telegram Notify",
        description="Envia mensagens via Telegram",
        author="Tester",
        dry_run=True,
    )
    data = _payload(resp)
    assert data["kind"] == "plugin"
    assert data["plugin_id"] == "telegram-notify"
    assert data["class_name"] == "TelegramNotifyPlugin"
    paths = [f["path"] for f in data["files"]]
    assert any(p.endswith("plugin.json") for p in paths)
    assert any(p.endswith("plugin.py") for p in paths)
    assert any(p.endswith("routers/health.py") for p in paths)
    assert any(p.endswith("README.md") for p in paths)
