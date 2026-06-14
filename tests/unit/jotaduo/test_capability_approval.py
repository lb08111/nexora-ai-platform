# -*- coding: utf-8 -*-
"""Tests for per-capability-type approval configuration."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch


def _patch_secret_dir(tmp_path: Path):
    return patch(
        "jotaduo_ext.jotaduo.capability_approval._secret_dir",
        return_value=tmp_path,
    )


def _patch_no_pg():
    return patch(
        "jotaduo_ext.jotaduo.capability_approval._use_pg",
        return_value=False,
    )


class TestCapabilityApprovalConfig:
    def test_upsert_and_list(self, tmp_path):
        with _patch_secret_dir(tmp_path), _patch_no_pg():
            from jotaduo_ext.jotaduo import capability_approval as m

            m.upsert_config(
                {
                    "capability_type": "mcp",
                    "add_policy": "approval",
                    "remove_policy": "log",
                    "approver_roles": ["admin"],
                },
            )
            m.upsert_config(
                {
                    "capability_type": "tool",
                    "add_policy": "none",
                    "remove_policy": "log",
                    "approver_roles": ["admin"],
                },
            )

            configs = m.list_configs()
            assert len(configs) == 2
            types = {c["capability_type"] for c in configs}
            assert types == {"mcp", "tool"}

    def test_get_config(self, tmp_path):
        with _patch_secret_dir(tmp_path), _patch_no_pg():
            from jotaduo_ext.jotaduo import capability_approval as m

            m.upsert_config(
                {
                    "capability_type": "skill",
                    "add_policy": "approval",
                    "remove_policy": "none",
                },
            )
            config = m.get_config("skill")
            assert config is not None
            assert config["add_policy"] == "approval"
            assert config["remove_policy"] == "none"

            assert m.get_config("nonexistent") is None

    def test_requires_approval(self, tmp_path):
        with _patch_secret_dir(tmp_path), _patch_no_pg():
            from jotaduo_ext.jotaduo import capability_approval as m

            m.upsert_config(
                {
                    "capability_type": "tool",
                    "add_policy": "none",
                    "remove_policy": "approval",
                },
            )
            assert m.requires_approval("tool", "add") is False
            assert m.requires_approval("tool", "remove") is True
            # Unknown type defaults to requiring approval
            assert m.requires_approval("unknown", "add") is True

    def test_requires_approval_remove_log(self, tmp_path):
        with _patch_secret_dir(tmp_path), _patch_no_pg():
            from jotaduo_ext.jotaduo import capability_approval as m

            m.upsert_config(
                {
                    "capability_type": "mcp",
                    "add_policy": "approval",
                    "remove_policy": "log",
                },
            )
            assert m.requires_approval("mcp", "remove") is True

    def test_requires_approval_remove_none(self, tmp_path):
        with _patch_secret_dir(tmp_path), _patch_no_pg():
            from jotaduo_ext.jotaduo import capability_approval as m

            m.upsert_config(
                {
                    "capability_type": "mcp",
                    "add_policy": "approval",
                    "remove_policy": "none",
                },
            )
            assert m.requires_approval("mcp", "remove") is False

    def test_should_auto_approve(self, tmp_path):
        with _patch_secret_dir(tmp_path), _patch_no_pg():
            from jotaduo_ext.jotaduo import capability_approval as m

            m.upsert_config(
                {
                    "capability_type": "mcp",
                    "add_policy": "approval",
                    "remove_policy": "log",
                },
            )
            assert m.should_auto_approve("mcp", "add") is False
            assert m.should_auto_approve("mcp", "remove") is True

    def test_should_not_auto_approve_when_approval(self, tmp_path):
        with _patch_secret_dir(tmp_path), _patch_no_pg():
            from jotaduo_ext.jotaduo import capability_approval as m

            m.upsert_config(
                {
                    "capability_type": "mcp",
                    "add_policy": "approval",
                    "remove_policy": "approval",
                },
            )
            assert m.should_auto_approve("mcp", "remove") is False

    def test_get_approver_roles(self, tmp_path):
        with _patch_secret_dir(tmp_path), _patch_no_pg():
            from jotaduo_ext.jotaduo import capability_approval as m

            m.upsert_config(
                {
                    "capability_type": "plugin",
                    "add_policy": "approval",
                    "approver_roles": ["admin"],
                },
            )
            assert m.get_approver_roles("plugin") == ["admin"]
            assert m.get_approver_roles("unknown") == ["admin"]

    def test_ensure_default_configs(self, tmp_path):
        with _patch_secret_dir(tmp_path), _patch_no_pg():
            from jotaduo_ext.jotaduo import capability_approval as m

            m.ensure_default_configs()
            configs = m.list_configs()
            assert len(configs) == 5
            types = {c["capability_type"] for c in configs}
            assert types == {"skill", "mcp", "tool", "acp", "plugin"}

            tool_cfg = m.get_config("tool")
            assert tool_cfg["add_policy"] == "none"

    def test_upsert_overwrites_existing(self, tmp_path):
        with _patch_secret_dir(tmp_path), _patch_no_pg():
            from jotaduo_ext.jotaduo import capability_approval as m

            m.upsert_config(
                {
                    "capability_type": "mcp",
                    "add_policy": "approval",
                },
            )
            m.upsert_config(
                {
                    "capability_type": "mcp",
                    "add_policy": "none",
                },
            )
            config = m.get_config("mcp")
            assert config["add_policy"] == "none"
            assert len(m.list_configs()) == 1

    def test_migrate_legacy_booleans(self, tmp_path):
        """Old boolean config is transparently migrated to policy enums."""
        with _patch_secret_dir(tmp_path), _patch_no_pg():
            from jotaduo_ext.jotaduo import capability_approval as m

            m.upsert_config(
                {
                    "capability_type": "skill",
                    "add_approval": True,
                    "remove_approval": True,
                    "auto_approve_remove": True,
                    "approver_roles": ["admin"],
                },
            )
            config = m.get_config("skill")
            assert config["add_policy"] == "approval"
            assert config["remove_policy"] == "log"
            assert "add_approval" not in config
            assert "remove_approval" not in config
            assert "auto_approve_remove" not in config

    def test_migrate_legacy_no_remove(self, tmp_path):
        with _patch_secret_dir(tmp_path), _patch_no_pg():
            from jotaduo_ext.jotaduo import capability_approval as m

            m.upsert_config(
                {
                    "capability_type": "tool",
                    "add_approval": False,
                    "remove_approval": False,
                },
            )
            config = m.get_config("tool")
            assert config["add_policy"] == "none"
            assert config["remove_policy"] == "none"

    def test_migrate_legacy_remove_approval_required(self, tmp_path):
        with _patch_secret_dir(tmp_path), _patch_no_pg():
            from jotaduo_ext.jotaduo import capability_approval as m

            m.upsert_config(
                {
                    "capability_type": "acp",
                    "add_approval": True,
                    "remove_approval": True,
                    "auto_approve_remove": False,
                },
            )
            config = m.get_config("acp")
            assert config["add_policy"] == "approval"
            assert config["remove_policy"] == "approval"
