# -*- coding: utf-8 -*-
"""Agent registration for the jotaduo-fiscal plugin."""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path
from typing import Any

from .constants import AGENT_SPEC, FISCAL_AGENT_ID, FISCAL_TOOL_CONFIGS

logger = logging.getLogger("jotaduo").getChild(
    "plugin.jotaduo-fiscal.agents_setup",
)

_SYNC_FIELDS = (
    "enabled",
    "async_execution",
    "description",
    "icon",
    "display_to_user",
)


def register_extra_tools(agent_id: str, extra_tools: dict[str, dict]) -> None:
    """Register / sync plugin tools into the agent's builtin_tools."""
    if not extra_tools:
        return

    try:
        from jotaduo.config.config import (  # pylint: disable=import-outside-toplevel
            BuiltinToolConfig,
            ToolsConfig,
            load_agent_config,
            save_agent_config,
        )
    except ImportError:
        logger.error("Cannot import jotaduo.config; tool sync skipped")
        return

    try:
        cfg = load_agent_config(agent_id)
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("Cannot load agent config for %s: %s", agent_id, exc)
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
            logger.warning("Save tools failed for %s: %s", agent_id, exc)


def ensure_builtin_agents() -> None:
    """Idempotently register the Jotaduo Fiscal specialist agent."""
    try:
        from jotaduo.config.config import (  # pylint: disable=import-outside-toplevel
            AgentProfileConfig,
            AgentProfileRef,
            AgentsRunningConfig,
            ChannelConfig,
            HeartbeatConfig,
            MCPConfig,
            save_agent_config,
        )
        from jotaduo.config.utils import load_config, save_config
        from jotaduo.constant import WORKING_DIR
    except ImportError:
        logger.error(
            "Cannot import jotaduo.config; agent registration skipped",
        )
        return

    config = load_config()
    if config.agents.active_agent in ("default", ""):
        config.agents.active_agent = FISCAL_AGENT_ID
        save_config(config)
        logger.info("Set active_agent to %s", FISCAL_AGENT_ID)

    _register_one_agent(
        spec=AGENT_SPEC,
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
        (Path(WORKING_DIR) / "workspaces" / agent_id).expanduser().resolve()
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

    register_extra_tools(
        agent_id,
        spec.get("extra_tools", FISCAL_TOOL_CONFIGS),
    )


def _initialize_agent_workspace(workspace_dir: Path, role: str) -> None:
    """Seed the workspace with persona prompt and minimal state files."""
    from .agents.fiscal_prompt import FISCAL_SYSTEM_PROMPT

    (workspace_dir / "sessions").mkdir(exist_ok=True)
    (workspace_dir / "memory").mkdir(exist_ok=True)

    persona_path = workspace_dir / "PERSONA.md"
    if not persona_path.exists():
        persona_path.write_text(
            f"# Persona — {role}\n\n{FISCAL_SYSTEM_PROMPT}\n",
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
    """Remove Jotaduo Fiscal agent profile and workspace."""
    try:
        from jotaduo.config.utils import load_config, save_config
    except ImportError:
        return

    config = load_config()
    if FISCAL_AGENT_ID not in config.agents.profiles:
        return

    ref = config.agents.profiles[FISCAL_AGENT_ID]
    workspace_dir = Path(ref.workspace_dir).expanduser().resolve()
    del config.agents.profiles[FISCAL_AGENT_ID]
    try:
        save_config(config)
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("Save config failed during uninstall: %s", exc)

    if workspace_dir.exists():
        try:
            shutil.rmtree(workspace_dir)
            logger.info("Removed Jotaduo Fiscal workspace: %s", workspace_dir)
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning(
                "Failed to delete workspace %s: %s",
                workspace_dir,
                exc,
            )
