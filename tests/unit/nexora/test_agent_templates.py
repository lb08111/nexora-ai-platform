# -*- coding: utf-8 -*-
"""Tests for agent initialization templates."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch


def _patch_secret_dir(tmp_path: Path):
    return patch(
        "qwenpaw_ext.nexora.agent_templates._secret_dir",
        return_value=tmp_path,
    )


def _patch_no_pg():
    return patch(
        "qwenpaw_ext.nexora.agent_templates._use_pg",
        return_value=False,
    )


class TestAgentTemplates:
    def test_create_and_list(self, tmp_path):
        with _patch_secret_dir(tmp_path), _patch_no_pg():
            from qwenpaw_ext.nexora import agent_templates as m

            t = m.create_template(
                {
                    "name": "测试模板",
                    "description": "用于测试",
                    "capabilities": {
                        "tools": ["read_file"],
                        "skills": [],
                        "mcps": [],
                    },
                    "created_by": "admin",
                }
            )
            assert t["name"] == "测试模板"
            assert t["template_id"]

            templates = m.list_templates()
            assert len(templates) == 1

    def test_get_template(self, tmp_path):
        with _patch_secret_dir(tmp_path), _patch_no_pg():
            from qwenpaw_ext.nexora import agent_templates as m

            t = m.create_template(
                {
                    "template_id": "test-1",
                    "name": "测试",
                    "capabilities": {"tools": ["read_file"]},
                }
            )
            fetched = m.get_template("test-1")
            assert fetched is not None
            assert fetched["name"] == "测试"
            assert fetched["capabilities"]["tools"] == ["read_file"]

            assert m.get_template("nonexistent") is None

    def test_update_template(self, tmp_path):
        with _patch_secret_dir(tmp_path), _patch_no_pg():
            from qwenpaw_ext.nexora import agent_templates as m

            m.create_template(
                {
                    "template_id": "test-1",
                    "name": "原名称",
                    "capabilities": {"tools": []},
                }
            )
            updated = m.update_template(
                "test-1",
                {
                    "name": "新名称",
                    "capabilities": {"tools": ["read_file", "write_file"]},
                },
            )
            assert updated is not None
            assert updated["name"] == "新名称"
            assert len(updated["capabilities"]["tools"]) == 2

            assert m.update_template("nonexistent", {"name": "x"}) is None

    def test_delete_template(self, tmp_path):
        with _patch_secret_dir(tmp_path), _patch_no_pg():
            from qwenpaw_ext.nexora import agent_templates as m

            m.create_template({"template_id": "t1", "name": "t1"})
            m.create_template({"template_id": "t2", "name": "t2"})

            assert m.delete_template("t1") is True
            assert m.delete_template("t1") is False
            assert len(m.list_templates()) == 1

    def test_ensure_builtin_templates(self, tmp_path):
        with _patch_secret_dir(tmp_path), _patch_no_pg():
            from qwenpaw_ext.nexora import agent_templates as m

            m.ensure_builtin_templates()
            templates = m.list_templates()
            assert len(templates) == 4
            names = {t["name"] for t in templates}
            assert "运维基础包" in names
            assert "开发助手包" in names
            assert "只读查询包" in names
            assert "办公助手包" in names

    def test_ensure_builtin_is_idempotent(self, tmp_path):
        with _patch_secret_dir(tmp_path), _patch_no_pg():
            from qwenpaw_ext.nexora import agent_templates as m

            m.ensure_builtin_templates()
            m.ensure_builtin_templates()
            assert len(m.list_templates()) == 4

    def test_persists_to_file(self, tmp_path):
        with _patch_secret_dir(tmp_path), _patch_no_pg():
            from qwenpaw_ext.nexora import agent_templates as m

            m.create_template(
                {
                    "template_id": "t1",
                    "name": "持久化测试",
                    "capabilities": {},
                }
            )
            path = tmp_path / "nexora_agent_templates.json"
            assert path.exists()
            data = json.loads(path.read_text())
            assert len(data) == 1
            assert data[0]["name"] == "持久化测试"
