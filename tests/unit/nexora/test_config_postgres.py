# -*- coding: utf-8 -*-
"""Tests for v4 runtime config PostgreSQL dual-mode storage."""
from __future__ import annotations

import importlib
import json
import os
from pathlib import Path
from typing import Any
from unittest import mock

import pytest


# ---------------------------------------------------------------------------
# Repository-level tests (config_postgres.py)
# ---------------------------------------------------------------------------


class TestConfigPostgresRepository:
    """Verify CRUD helpers produce correct SQL interactions."""

    def _make_repo(self):
        from qwenpaw_ext.nexora.repositories import config_postgres

        return config_postgres

    # -- global config --

    def test_load_global_config_returns_none_when_empty(self):
        repo = self._make_repo()
        fake_conn = mock.MagicMock()
        fake_conn.execute.return_value.first.return_value = None
        fake_engine = mock.MagicMock()
        fake_engine.connect.return_value.__enter__ = mock.Mock(
            return_value=fake_conn
        )
        fake_engine.connect.return_value.__exit__ = mock.Mock(
            return_value=False
        )

        with mock.patch(
            "qwenpaw_ext.nexora.db.get_engine", return_value=fake_engine
        ):
            result = repo.load_global_config()

        assert result is None

    def test_load_global_config_parses_dict(self):
        repo = self._make_repo()
        payload = {"agents": {"profiles": {}}, "mcp": {}}

        fake_conn = mock.MagicMock()
        fake_conn.execute.return_value.first.return_value = (payload, 100)
        fake_engine = mock.MagicMock()
        fake_engine.connect.return_value.__enter__ = mock.Mock(
            return_value=fake_conn
        )
        fake_engine.connect.return_value.__exit__ = mock.Mock(
            return_value=False
        )

        with mock.patch(
            "qwenpaw_ext.nexora.db.get_engine", return_value=fake_engine
        ):
            result = repo.load_global_config()

        assert result == payload

    def test_save_global_config_inserts_when_no_row(self):
        repo = self._make_repo()
        fake_conn = mock.MagicMock()
        fake_conn.execute.return_value.first.return_value = (
            None  # no existing row
        )
        fake_engine = mock.MagicMock()
        fake_engine.begin.return_value.__enter__ = mock.Mock(
            return_value=fake_conn
        )
        fake_engine.begin.return_value.__exit__ = mock.Mock(return_value=False)

        with mock.patch(
            "qwenpaw_ext.nexora.db.get_engine", return_value=fake_engine
        ):
            repo.save_global_config({"test": True})

        calls = fake_conn.execute.call_args_list
        assert len(calls) == 2  # SELECT FOR UPDATE + INSERT
        insert_sql = str(calls[1][0][0])
        assert "INSERT" in insert_sql.upper()

    def test_save_global_config_updates_when_row_exists(self):
        repo = self._make_repo()
        fake_conn = mock.MagicMock()
        fake_conn.execute.return_value.first.return_value = (
            1,
        )  # existing row
        fake_engine = mock.MagicMock()
        fake_engine.begin.return_value.__enter__ = mock.Mock(
            return_value=fake_conn
        )
        fake_engine.begin.return_value.__exit__ = mock.Mock(return_value=False)

        with mock.patch(
            "qwenpaw_ext.nexora.db.get_engine", return_value=fake_engine
        ):
            repo.save_global_config({"test": True})

        calls = fake_conn.execute.call_args_list
        assert len(calls) == 2  # SELECT FOR UPDATE + UPDATE
        update_sql = str(calls[1][0][0])
        assert "UPDATE" in update_sql.upper()

    # -- agent config --

    def test_load_agent_config_returns_none_when_missing(self):
        repo = self._make_repo()
        fake_conn = mock.MagicMock()
        fake_conn.execute.return_value.first.return_value = None
        fake_engine = mock.MagicMock()
        fake_engine.connect.return_value.__enter__ = mock.Mock(
            return_value=fake_conn
        )
        fake_engine.connect.return_value.__exit__ = mock.Mock(
            return_value=False
        )

        with mock.patch(
            "qwenpaw_ext.nexora.db.get_engine", return_value=fake_engine
        ):
            result = repo.load_agent_config("test-agent")

        assert result is None

    def test_save_agent_config_upserts(self):
        repo = self._make_repo()
        fake_conn = mock.MagicMock()
        fake_conn.execute.return_value.first.return_value = None
        fake_engine = mock.MagicMock()
        fake_engine.begin.return_value.__enter__ = mock.Mock(
            return_value=fake_conn
        )
        fake_engine.begin.return_value.__exit__ = mock.Mock(return_value=False)

        with mock.patch(
            "qwenpaw_ext.nexora.db.get_engine", return_value=fake_engine
        ):
            repo.save_agent_config("test-agent", {"id": "test-agent"})

        calls = fake_conn.execute.call_args_list
        assert len(calls) == 2
        insert_sql = str(calls[1][0][0])
        assert "INSERT" in insert_sql.upper()

    def test_delete_agent_config(self):
        repo = self._make_repo()
        fake_conn = mock.MagicMock()
        fake_engine = mock.MagicMock()
        fake_engine.begin.return_value.__enter__ = mock.Mock(
            return_value=fake_conn
        )
        fake_engine.begin.return_value.__exit__ = mock.Mock(return_value=False)

        with mock.patch(
            "qwenpaw_ext.nexora.db.get_engine", return_value=fake_engine
        ):
            repo.delete_agent_config("test-agent")

        calls = fake_conn.execute.call_args_list
        assert len(calls) == 1
        delete_sql = str(calls[0][0][0])
        assert "DELETE" in delete_sql.upper()


# ---------------------------------------------------------------------------
# Dual-mode switching tests (load_config / save_config)
# ---------------------------------------------------------------------------


class TestGlobalConfigDualMode:
    """Verify load_config and save_config switch to PG when enabled."""

    def _reset_cache(self):
        import qwenpaw.config.utils as utils_mod

        utils_mod._config_cache = None
        utils_mod._config_mtime = None

    def test_load_config_uses_pg_when_version_available(self):
        self._reset_cache()
        from qwenpaw.config.config import Config

        pg_data = {"user_timezone": "UTC"}

        with (
            mock.patch(
                "qwenpaw.config.utils._get_pg_config_version",
                return_value=42,
            ),
            mock.patch(
                "qwenpaw.config.utils._load_config_from_pg",
                return_value=Config.model_validate(pg_data),
            ),
        ):
            from qwenpaw.config.utils import load_config

            cfg = load_config()

        assert cfg.user_timezone == "UTC"

    def test_load_config_falls_back_to_file_when_pg_unavailable(
        self, tmp_path
    ):
        self._reset_cache()
        from qwenpaw.config.config import Config

        config_file = tmp_path / "config.json"
        config_file.write_text(
            json.dumps({"user_timezone": "Asia/Tokyo"}),
            encoding="utf-8",
        )

        with mock.patch(
            "qwenpaw.config.utils._get_pg_config_version",
            return_value=None,
        ):
            from qwenpaw.config.utils import load_config

            cfg = load_config(config_path=config_file)

        assert cfg.user_timezone == "Asia/Tokyo"

    def test_save_config_writes_to_pg_and_file(self, tmp_path):
        self._reset_cache()
        from qwenpaw.config.config import Config
        from qwenpaw.config.utils import save_config

        config_file = tmp_path / "config.json"
        cfg = Config(user_timezone="Europe/London")

        with mock.patch(
            "qwenpaw.config.utils._save_config_to_pg",
            return_value=True,
        ) as pg_save:
            save_config(cfg, config_path=config_file)

        pg_save.assert_called_once()
        assert config_file.exists()
        saved = json.loads(config_file.read_text("utf-8"))
        assert saved["user_timezone"] == "Europe/London"

    def test_load_config_caches_pg_result(self):
        self._reset_cache()
        from qwenpaw.config.config import Config

        pg_data = Config(user_timezone="US/Eastern")
        call_count = 0

        def counting_load():
            nonlocal call_count
            call_count += 1
            return pg_data

        with (
            mock.patch(
                "qwenpaw.config.utils._get_pg_config_version",
                return_value=99,
            ),
            mock.patch(
                "qwenpaw.config.utils._load_config_from_pg",
                side_effect=counting_load,
            ),
        ):
            from qwenpaw.config.utils import load_config

            cfg1 = load_config()
            cfg2 = load_config()

        assert cfg1.user_timezone == "US/Eastern"
        assert call_count == 1  # second call served from cache


# ---------------------------------------------------------------------------
# Dual-mode switching tests (load_agent_config / save_agent_config)
# ---------------------------------------------------------------------------


class TestAgentConfigDualMode:
    """Verify agent config dual-mode switching."""

    def _reset_cache(self):
        import qwenpaw.config.utils as utils_mod

        utils_mod._config_cache = None
        utils_mod._config_mtime = None
        utils_mod._agent_config_cache.clear()

    def _make_test_config(self, tmp_path):
        """Build a Config object with a test agent and return (config, workspace)."""
        from qwenpaw.config.config import Config

        workspace = tmp_path / "workspaces" / "test-bot"
        workspace.mkdir(parents=True, exist_ok=True)

        config_data = {
            "agents": {
                "profiles": {
                    "test-bot": {
                        "id": "test-bot",
                        "workspace_dir": str(workspace),
                    },
                },
                "agent_order": ["test-bot"],
            },
        }
        return Config.model_validate(config_data), workspace

    def test_load_agent_config_uses_pg_when_available(self, tmp_path):
        self._reset_cache()
        from qwenpaw.config.config import AgentProfileConfig

        cfg_obj, workspace = self._make_test_config(tmp_path)
        (workspace / "agent.json").write_text(
            json.dumps({"id": "test-bot", "name": "File Bot"}),
            encoding="utf-8",
        )

        pg_agent = AgentProfileConfig(id="test-bot", name="PG Bot")

        with (
            mock.patch(
                "qwenpaw.config.utils.load_config",
                return_value=cfg_obj,
            ),
            mock.patch(
                "qwenpaw.config.config._get_pg_agent_config_version",
                return_value=55,
            ),
            mock.patch(
                "qwenpaw.config.config._load_agent_config_from_pg",
                return_value=pg_agent,
            ),
        ):
            from qwenpaw.config.config import load_agent_config

            cfg = load_agent_config("test-bot")

        assert cfg.name == "PG Bot"

    def test_save_agent_config_writes_to_pg_and_file(self, tmp_path):
        self._reset_cache()
        from qwenpaw.config.config import AgentProfileConfig

        cfg_obj, workspace = self._make_test_config(tmp_path)
        agent_cfg = AgentProfileConfig(id="test-bot", name="Saved Bot")

        with (
            mock.patch(
                "qwenpaw.config.utils.load_config",
                return_value=cfg_obj,
            ),
            mock.patch(
                "qwenpaw.config.config._save_agent_config_to_pg",
                return_value=True,
            ) as pg_save,
        ):
            from qwenpaw.config.config import save_agent_config

            save_agent_config("test-bot", agent_cfg)

        pg_save.assert_called_once()
        saved_file = workspace / "agent.json"
        assert saved_file.exists()
        saved = json.loads(saved_file.read_text("utf-8"))
        assert saved["name"] == "Saved Bot"


# ---------------------------------------------------------------------------
# Migration script tests
# ---------------------------------------------------------------------------


class TestRuntimeConfigMigration:
    """Verify the migration script imports config.json and agent.json."""

    def test_migrate_runtime_config(self, tmp_path):
        import sys

        repo_root = Path(__file__).resolve().parents[3]
        src = repo_root / "src"
        scripts = repo_root / "scripts"
        if str(src) not in sys.path:
            sys.path.insert(0, str(src))
        if str(scripts) not in sys.path:
            sys.path.insert(0, str(scripts))

        from nexora_migrate_files_to_postgres import _migrate_runtime_config

        working_dir = tmp_path / "qwenpaw"
        working_dir.mkdir()
        config_json = working_dir / "config.json"
        config_json.write_text(json.dumps({"agents": {}}), encoding="utf-8")

        ws = working_dir / "workspaces" / "bot1"
        ws.mkdir(parents=True)
        (ws / "agent.json").write_text(
            json.dumps({"id": "bot1", "name": "Bot One"}),
            encoding="utf-8",
        )

        saved_global = []
        saved_agents = {}

        def fake_save_global(data):
            saved_global.append(data)

        def fake_save_agent(aid, data):
            saved_agents[aid] = data

        with (
            mock.patch(
                "qwenpaw_ext.nexora.repositories.config_postgres.save_global_config",
                side_effect=fake_save_global,
            ),
            mock.patch(
                "qwenpaw_ext.nexora.repositories.config_postgres.save_agent_config",
                side_effect=fake_save_agent,
            ),
        ):
            result = _migrate_runtime_config(working_dir)

        assert result["global_config"] == 1
        assert result["agent_configs"] == 1
        assert len(saved_global) == 1
        assert saved_agents["bot1"]["name"] == "Bot One"
