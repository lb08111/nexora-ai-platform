# -*- coding: utf-8 -*-
"""Agent registration for the nexora-pix plugin.

Registers one Brazilian Pix billing agent (``nexora-cobranca``) and
syncs the eight Pix tools into the agent's builtin tool configuration.
"""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path
from typing import Any

from .agents.cobranca_prompt import SYSTEM_PROMPT
from .constants import AGENT_SPECS, ALL_AGENT_IDS, PIX_EXTRA_TOOLS

logger = logging.getLogger("qwenpaw").getChild(
    "plugin.nexora-pix.agents_setup",
)

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


def ensure_builtin_agents() -> None:
    """Idempotently register the Nexora Pix billing agent."""
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

    _initialize_agent_workspace(expected_ws, role=spec["role"])

    try:
        save_agent_config(agent_id, agent_cfg)
    except ValueError:
        logger.exception("Failed to save agent.json for %s", agent_id)

    register_extra_tools(agent_id, spec.get("extra_tools", PIX_EXTRA_TOOLS))


def _initialize_agent_workspace(workspace_dir: Path, role: str) -> None:
    """Seed the workspace with the Pix billing persona prompt."""
    (workspace_dir / "sessions").mkdir(exist_ok=True)
    (workspace_dir / "memory").mkdir(exist_ok=True)

    persona_path = workspace_dir / "PERSONA.md"
    if not persona_path.exists():
        persona_path.write_text(
            f"# Persona — {role}\n\n{SYSTEM_PROMPT}\n",
            encoding="utf-8",
        )

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


def uninstall_agents() -> None:
    """Remove Nexora Pix agent profiles and workspaces."""
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
