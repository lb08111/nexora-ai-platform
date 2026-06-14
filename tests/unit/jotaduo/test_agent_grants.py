# -*- coding: utf-8 -*-
"""Tests for agent-user grant management (multi-tenant authorization)."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch


def _patch_secret_dir(tmp_path: Path):
    return patch(
        "jotaduo_ext.jotaduo.agent_grants._secret_dir",
        return_value=tmp_path,
    )


def _patch_no_pg():
    return patch(
        "jotaduo_ext.jotaduo.agent_grants._use_pg",
        return_value=False,
    )


class TestFileBackedGrants:
    def test_grant_and_list(self, tmp_path):
        with _patch_secret_dir(tmp_path), _patch_no_pg():
            from jotaduo_ext.jotaduo import agent_grants as m

            m.grant_agent_to_user("bot-1", "zhangming", "admin")
            m.grant_agent_to_user("bot-1", "liming", "admin")
            m.grant_agent_to_user("bot-2", "zhangming", "admin")

            grants = m.list_grants_for_agent("bot-1")
            assert len(grants) == 2
            names = {g["username"] for g in grants}
            assert names == {"zhangming", "liming"}

            user_grants = m.list_grants_for_user("zhangming")
            assert len(user_grants) == 2
            agent_ids = {g["agent_id"] for g in user_grants}
            assert agent_ids == {"bot-1", "bot-2"}

    def test_revoke(self, tmp_path):
        with _patch_secret_dir(tmp_path), _patch_no_pg():
            from jotaduo_ext.jotaduo import agent_grants as m

            m.grant_agent_to_user("bot-1", "zhangming", "admin")
            assert m.is_user_granted("bot-1", "zhangming") is True

            assert m.revoke_agent_from_user("bot-1", "zhangming") is True
            assert m.is_user_granted("bot-1", "zhangming") is False
            assert m.revoke_agent_from_user("bot-1", "zhangming") is False

    def test_batch_grant_and_revoke(self, tmp_path):
        with _patch_secret_dir(tmp_path), _patch_no_pg():
            from jotaduo_ext.jotaduo import agent_grants as m

            users = ["user1", "user2", "user3"]
            count = m.batch_grant_agent("bot-1", users, "admin")
            assert count == 3
            assert len(m.list_grants_for_agent("bot-1")) == 3

            revoked = m.batch_revoke_agent("bot-1", ["user1", "user3"])
            assert revoked == 2
            remaining = m.list_grants_for_agent("bot-1")
            assert len(remaining) == 1
            assert remaining[0]["username"] == "user2"

    def test_get_authorized_agent_ids(self, tmp_path):
        with _patch_secret_dir(tmp_path), _patch_no_pg():
            from jotaduo_ext.jotaduo import agent_grants as m

            m.grant_agent_to_user("bot-1", "zhangming", "admin")
            m.grant_agent_to_user("bot-2", "zhangming", "admin")

            ids = m.get_authorized_agent_ids("zhangming")
            assert set(ids) == {"bot-1", "bot-2"}

            assert m.get_authorized_agent_ids("nobody") == []

    def test_grant_persists_to_file(self, tmp_path):
        with _patch_secret_dir(tmp_path), _patch_no_pg():
            from jotaduo_ext.jotaduo import agent_grants as m

            m.grant_agent_to_user("bot-1", "zhangming", "admin")

            path = tmp_path / "jotaduo_agent_grants.json"
            assert path.exists()
            data = json.loads(path.read_text())
            assert "bot-1" in data
            assert data["bot-1"][0]["username"] == "zhangming"

    def test_duplicate_grant_updates(self, tmp_path):
        with _patch_secret_dir(tmp_path), _patch_no_pg():
            from jotaduo_ext.jotaduo import agent_grants as m

            m.grant_agent_to_user("bot-1", "zhangming", "admin")
            m.grant_agent_to_user("bot-1", "zhangming", "operator")

            grants = m.list_grants_for_agent("bot-1")
            assert len(grants) == 1
            assert grants[0]["granted_by"] == "operator"
