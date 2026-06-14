# -*- coding: utf-8 -*-
"""Agent registration for the nexora-team plugin.

Registers five Brazilian specialist agents (orchestrator + 4 staff)
into the QwenPaw multi-agent manager so they appear in ``list_agents``,
the Console UI, and can receive ``chat_with_agent`` calls.

The role-to-prompt mapping reuses ``qwenpaw.agents.br_team.prompts``
and the tools are seeded from ``br_team`` so this plugin never
duplicates logic — it only wires the agents into the platform.
"""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path
from typing import Any

from .constants import (
    AGENT_SPECS,
    ALL_AGENT_IDS,
    PLUGIN_DIR,
    PLUGIN_SKILLS,
)

logger = logging.getLogger("qwenpaw").getChild(
    "plugin.nexora-team.agents_setup",
)


# ----------------------------------------------------------------------
# Tool injection
# ----------------------------------------------------------------------


_SYNC_FIELDS = (
    "enabled",
    "async_execution",
    "description",
    "icon",
    "display_to_user",
)


def register_extra_tools(
    agent_id: str,
    extra_tools: dict[str, dict],
) -> None:
    """Register / sync plugin tools into the agent's builtin_tools."""
    if not extra_tools:
        return

    try:
        from qwenpaw.config.config import (
            BuiltinToolConfig,
            ToolsConfig,
            load_agent_config,
            save_agent_config,
        )
    except ImportError:
        return

    try:
        cfg = load_agent_config(agent_id)
    except Exception:  # pylint: disable=broad-except
        return

    if not cfg.tools:
        cfg.tools = ToolsConfig()

    changed = False
    for name, spec in extra_tools.items():
        existing = cfg.tools.builtin_tools.get(name)
        if existing is None:
            cfg.tools.builtin_tools[name] = BuiltinToolConfig(**spec)
            changed = True
            logger.info("Tool '%s' added to agent %s", name, agent_id)
            continue
        for field in _SYNC_FIELDS:
            if field not in spec:
                continue
            new_value = spec[field]
            if getattr(existing, field, None) != new_value:
                setattr(existing, field, new_value)
                changed = True

    if changed:
        try:
            save_agent_config(agent_id, cfg)
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning(
                "Save tools failed for %s: %s",
                agent_id,
                exc,
            )


# ----------------------------------------------------------------------
# Agent profile registration
# ----------------------------------------------------------------------


def ensure_builtin_agents() -> None:
    """Idempotently register the 5 Nexora agents."""
    try:
        from qwenpaw.config.config import (
            AgentProfileConfig,
            AgentProfileRef,
            AgentsRunningConfig,
            ChannelConfig,
            HeartbeatConfig,
            MCPConfig,
            save_agent_config,
        )
        from qwenpaw.config.utils import load_config, save_config
        from qwenpaw.constant import WORKING_DIR
    except ImportError:
        logger.error(
            "Cannot import qwenpaw.config; agent registration skipped",
        )
        return

    config = load_config()

    if config.agents.active_agent in ("default", ""):
        from .constants import ORCHESTRATOR_AGENT_ID

        config.agents.active_agent = ORCHESTRATOR_AGENT_ID
        save_config(config)
        logger.info(
            "Set active_agent to %s",
            ORCHESTRATOR_AGENT_ID,
        )

    for spec in AGENT_SPECS:
        _register_one_agent(
            spec=spec,
            config=config,
            WORKING_DIR=WORKING_DIR,
            AgentProfileConfig=AgentProfileConfig,
            AgentProfileRef=AgentProfileRef,
            AgentsRunningConfig=AgentsRunningConfig,
            ChannelConfig=ChannelConfig,
            HeartbeatConfig=HeartbeatConfig,
            MCPConfig=MCPConfig,
            save_config=save_config,
            save_agent_config=save_agent_config,
        )


def _register_one_agent(
    spec: dict[str, Any],
    config: Any,
    WORKING_DIR: str,
    AgentProfileConfig: Any,
    AgentProfileRef: Any,
    AgentsRunningConfig: Any,
    ChannelConfig: Any,
    HeartbeatConfig: Any,
    MCPConfig: Any,
    save_config: Any,
    save_agent_config: Any,
) -> None:
    agent_id = spec["agent_id"]
    expected_ws = (
        (Path(WORKING_DIR) / "workspaces" / agent_id)
        .expanduser()
        .resolve()
    )

    if agent_id in config.agents.profiles:
        ref = config.agents.profiles[agent_id]
        actual = Path(ref.workspace_dir).expanduser().resolve()
        if actual != expected_ws:
            logger.warning(
                "Workspace mismatch for %s (%s vs %s); skipping",
                agent_id,
                actual,
                expected_ws,
            )
            return
    else:
        expected_ws.mkdir(parents=True, exist_ok=True)
        config.agents.profiles[agent_id] = AgentProfileRef(
            id=agent_id,
            workspace_dir=str(expected_ws),
        )
        save_config(config)
        logger.info("Registered agent %s at %s", agent_id, expected_ws)

    running_overrides = spec.get("running_overrides", {})
    running_cfg = (
        AgentsRunningConfig(**running_overrides)
        if running_overrides
        else AgentsRunningConfig()
    )

    agent_cfg = AgentProfileConfig(
        id=agent_id,
        name=spec["name"],
        description=spec["description"],
        workspace_dir=str(expected_ws),
        language=config.agents.language or "pt",
        channels=ChannelConfig(),
        mcp=MCPConfig(),
        heartbeat=HeartbeatConfig(),
        running=running_cfg,
    )

    _initialize_agent_workspace(
        expected_ws,
        role=spec["role"],
        skill_names=spec["skill_names"],
    )

    try:
        save_agent_config(agent_id, agent_cfg)
    except ValueError:
        logger.exception("Failed to save agent.json for %s", agent_id)

    register_extra_tools(agent_id, spec.get("extra_tools", {}))


def _initialize_agent_workspace(
    workspace_dir: Path,
    role: str,
    skill_names: list[str],
) -> None:
    """Seed the workspace with persona prompt + skills."""
    from qwenpaw.agents.br_team.prompts import PROMPTS_BY_ROLE
    from qwenpaw.agents.skill_system import get_workspace_skills_dir

    (workspace_dir / "sessions").mkdir(exist_ok=True)
    (workspace_dir / "memory").mkdir(exist_ok=True)
    skills_dir = get_workspace_skills_dir(workspace_dir)
    skills_dir.mkdir(exist_ok=True)

    # Persona = the br_team pt-BR system prompt for this role.
    persona_path = workspace_dir / "PERSONA.md"
    if not persona_path.exists():
        prompt = PROMPTS_BY_ROLE.get(role, "")
        if prompt:
            persona_path.write_text(
                f"# Persona — {role}\n\n{prompt}\n",
                encoding="utf-8",
            )

    _install_workspace_skills(skills_dir, skill_names)

    for fname, default in [
        ("chats.json", {"version": 1, "chats": []}),
        ("jobs.json", {"version": 1, "jobs": []}),
    ]:
        fpath = workspace_dir / fname
        if not fpath.exists():
            fpath.write_text(
                json.dumps(default, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )


def _install_workspace_skills(
    skills_dir: Path,
    skill_names: list[str],
) -> None:
    """Symlink/copy the relevant skills into the agent workspace."""
    from qwenpaw.agents.skill_system import get_skill_pool_dir

    try:
        pool = get_skill_pool_dir()
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("Cannot resolve skill pool: %s", exc)
        return

    for skill_name in skill_names:
        src = pool / skill_name
        if not src.exists():
            logger.debug("Skill %s not in pool; skipping", skill_name)
            continue
        dst = skills_dir / skill_name
        if dst.exists():
            continue
        try:
            shutil.copytree(src, dst)
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning(
                "Failed to install skill %s: %s",
                skill_name,
                exc,
            )


# ----------------------------------------------------------------------
# Skill pool installation
# ----------------------------------------------------------------------


def install_plugin_skills() -> None:
    """Copy plugin-shipped skills into the shared skill pool."""
    try:
        from qwenpaw.agents.skill_system import (
            ensure_skill_pool_initialized,
            get_skill_pool_dir,
        )
    except ImportError:
        logger.error("skill_system unavailable; skill install skipped")
        return

    try:
        ensure_skill_pool_initialized()
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("Skill pool init failed: %s", exc)

    pool = get_skill_pool_dir()
    src_root = PLUGIN_DIR / "skills"

    for skill_name in PLUGIN_SKILLS:
        src = src_root / skill_name
        if not src.exists():
            logger.warning("Plugin skill source missing: %s", src)
            continue
        dst = pool / skill_name
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        logger.info("Installed plugin skill: %s", skill_name)

    _update_pool_manifest(pool)


def _update_pool_manifest(pool: Path) -> None:
    manifest_path = pool / "skill.json"
    try:
        if manifest_path.exists():
            manifest = json.loads(
                manifest_path.read_text(encoding="utf-8"),
            )
        else:
            manifest = {"skills": {}, "builtin_skill_names": []}

        skills = manifest.setdefault("skills", {})
        for name in PLUGIN_SKILLS:
            if name not in skills:
                skills[name] = {
                    "source": "plugin:nexora-team",
                    "protected": False,
                }

        manifest_path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("Failed to update pool manifest: %s", exc)


# ----------------------------------------------------------------------
# Uninstall
# ----------------------------------------------------------------------


def uninstall_agents() -> None:
    """Remove Nexora agent profiles + workspaces + plugin skills."""
    _uninstall_agent_profiles()
    _uninstall_plugin_skills()


def _uninstall_agent_profiles() -> None:
    try:
        from qwenpaw.config.utils import load_config, save_config
    except ImportError:
        return

    config = load_config()
    changed = False
    for agent_id in ALL_AGENT_IDS:
        if agent_id in config.agents.profiles:
            ref = config.agents.profiles[agent_id]
            ws = Path(ref.workspace_dir).expanduser().resolve()
            del config.agents.profiles[agent_id]
            changed = True
            logger.info("Removed agent profile: %s", agent_id)
            if ws.exists():
                try:
                    shutil.rmtree(ws)
                except Exception as exc:  # pylint: disable=broad-except
                    logger.warning(
                        "Failed to delete workspace %s: %s",
                        ws,
                        exc,
                    )
    if changed:
        try:
            save_config(config)
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Save config failed: %s", exc)


def _uninstall_plugin_skills() -> None:
    try:
        from qwenpaw.agents.skill_system import get_skill_pool_dir
    except ImportError:
        return

    pool = get_skill_pool_dir()
    for name in PLUGIN_SKILLS:
        dst = pool / name
        if dst.exists():
            try:
                shutil.rmtree(dst)
                logger.info("Removed plugin skill: %s", name)
            except Exception as exc:  # pylint: disable=broad-except
                logger.warning(
                    "Failed to remove skill %s: %s",
                    name,
                    exc,
                )
