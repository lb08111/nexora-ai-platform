# -*- coding: utf-8 -*-
"""Smoke tests: constants and skill are well-formed."""

from __future__ import annotations

from pathlib import Path

from nexora_team_plugin.constants import (
    AGENT_SPECS,
    ALL_AGENT_IDS,
    AGENT_ROLE_MAP,
    DEFAULT_ENV_KEYS,
    ORCHESTRATOR_AGENT_ID,
    PLUGIN_DIR,
    PLUGIN_SKILLS,
)


def test_agent_specs_cover_all_ids():
    spec_ids = [s["agent_id"] for s in AGENT_SPECS]
    assert spec_ids == list(ALL_AGENT_IDS)


def test_role_map_is_consistent_with_specs():
    for spec in AGENT_SPECS:
        assert AGENT_ROLE_MAP[spec["agent_id"]] == spec["role"]


def test_orchestrator_has_meeting_tool_enabled():
    orch = next(
        s for s in AGENT_SPECS if s["agent_id"] == ORCHESTRATOR_AGENT_ID
    )
    tool = orch["extra_tools"]["convene_meeting"]
    assert tool["enabled"] is True
    assert tool["async_execution"] is True


def test_orchestrator_uses_meeting_skill():
    orch = next(
        s for s in AGENT_SPECS if s["agent_id"] == ORCHESTRATOR_AGENT_ID
    )
    assert "nexora-meeting-pt" in orch["skill_names"]


def test_default_env_keys_are_documented():
    assert "WHATSAPP_PROVIDER" in DEFAULT_ENV_KEYS
    assert "PIX_PROVIDER" in DEFAULT_ENV_KEYS
    assert "BRASILAPI_BASE_URL" in DEFAULT_ENV_KEYS


def test_skill_md_exists_and_has_frontmatter():
    skill_dir = PLUGIN_DIR / "skills" / "nexora-meeting-pt"
    skill_md = skill_dir / "SKILL.md"
    assert skill_md.exists(), f"missing: {skill_md}"
    content = skill_md.read_text(encoding="utf-8")
    assert content.startswith("---\n")
    assert "name: nexora-meeting" in content
    assert "convene_meeting" in content


def test_plugin_skills_list_matches_filesystem():
    skills_root = PLUGIN_DIR / "skills"
    on_disk = {p.name for p in skills_root.iterdir() if p.is_dir()}
    assert set(PLUGIN_SKILLS).issubset(on_disk)


def test_plugin_json_metadata():
    import json

    pj = json.loads(
        (PLUGIN_DIR / "plugin.json").read_text(encoding="utf-8"),
    )
    assert pj["id"] == "nexora-team"
    assert pj["entry"]["backend"] == "plugin.py"
    assert "br-specialist-agents" in pj["meta"]["features"]


def test_plugin_class_is_importable():
    from nexora_team_plugin import NexoraTeamPlugin

    assert NexoraTeamPlugin.__name__ == "NexoraTeamPlugin"
    # Exposes register + lifecycle hooks.
    assert hasattr(NexoraTeamPlugin, "register")
    assert hasattr(NexoraTeamPlugin, "_on_startup")
    assert hasattr(NexoraTeamPlugin, "_on_shutdown")
