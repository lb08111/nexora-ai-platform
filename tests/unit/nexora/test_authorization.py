# -*- coding: utf-8 -*-
"""Tests for multi-tenant agent authorization logic."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


def _patch_secret_dir(tmp_path: Path):
    return patch(
        "qwenpaw_ext.nexora.agent_grants._secret_dir",
        return_value=tmp_path,
    )


def _patch_no_pg():
    return patch(
        "qwenpaw_ext.nexora.agent_grants._use_pg",
        return_value=False,
    )


def _patch_auth_active(active: bool = True):
    return patch(
        "qwenpaw_ext.nexora.authorization._is_auth_active",
        return_value=active,
    )


class TestUserCanAccessAgent:
    def test_admin_bypasses_grant_check(self, tmp_path):
        with _patch_secret_dir(tmp_path), _patch_no_pg(), _patch_auth_active():
            from qwenpaw_ext.nexora.authorization import user_can_access_agent

            assert (
                user_can_access_agent("admin_user", ["admin"], "any-agent")
                is True
            )

    def test_granted_user_can_access(self, tmp_path):
        with _patch_secret_dir(tmp_path), _patch_no_pg(), _patch_auth_active():
            from qwenpaw_ext.nexora import agent_grants
            from qwenpaw_ext.nexora.authorization import user_can_access_agent

            agent_grants.grant_agent_to_user("bot-1", "zhangming", "admin")
            assert (
                user_can_access_agent("zhangming", ["operator"], "bot-1")
                is True
            )

    def test_non_granted_user_denied(self, tmp_path):
        with _patch_secret_dir(tmp_path), _patch_no_pg(), _patch_auth_active():
            from qwenpaw_ext.nexora.authorization import user_can_access_agent

            assert (
                user_can_access_agent("zhangming", ["operator"], "bot-1")
                is False
            )

    def test_auth_disabled_allows_all(self, tmp_path):
        with _patch_secret_dir(tmp_path), _patch_no_pg(), _patch_auth_active(
            False
        ):
            from qwenpaw_ext.nexora.authorization import user_can_access_agent

            assert user_can_access_agent("anyone", [], "any-agent") is True


class TestFilterAgentIdsForUser:
    def test_admin_sees_all(self, tmp_path):
        with _patch_secret_dir(tmp_path), _patch_no_pg(), _patch_auth_active():
            from qwenpaw_ext.nexora.authorization import (
                filter_agent_ids_for_user,
            )

            result = filter_agent_ids_for_user(
                ["bot-1", "bot-2", "bot-3"],
                "admin_user",
                ["admin"],
            )
            assert result == ["bot-1", "bot-2", "bot-3"]

    def test_user_sees_only_granted(self, tmp_path):
        with _patch_secret_dir(tmp_path), _patch_no_pg(), _patch_auth_active():
            from qwenpaw_ext.nexora import agent_grants
            from qwenpaw_ext.nexora.authorization import (
                filter_agent_ids_for_user,
            )

            agent_grants.grant_agent_to_user("bot-1", "zhangming", "admin")
            agent_grants.grant_agent_to_user("bot-3", "zhangming", "admin")

            result = filter_agent_ids_for_user(
                ["bot-1", "bot-2", "bot-3"],
                "zhangming",
                ["operator"],
            )
            assert result == ["bot-1", "bot-3"]

    def test_user_with_no_grants_sees_nothing(self, tmp_path):
        with _patch_secret_dir(tmp_path), _patch_no_pg(), _patch_auth_active():
            from qwenpaw_ext.nexora.authorization import (
                filter_agent_ids_for_user,
            )

            result = filter_agent_ids_for_user(
                ["bot-1", "bot-2"],
                "newuser",
                ["operator"],
            )
            assert result == []


class TestEnsureAgentAccess:
    def test_raises_403_for_denied_user(self, tmp_path):
        from fastapi import HTTPException

        with _patch_secret_dir(tmp_path), _patch_no_pg(), _patch_auth_active():
            from qwenpaw_ext.nexora.authorization import ensure_agent_access

            with pytest.raises(HTTPException) as exc_info:
                ensure_agent_access("zhangming", ["operator"], "bot-1")
            assert exc_info.value.status_code == 403

    def test_no_raise_for_granted_user(self, tmp_path):
        with _patch_secret_dir(tmp_path), _patch_no_pg(), _patch_auth_active():
            from qwenpaw_ext.nexora import agent_grants
            from qwenpaw_ext.nexora.authorization import ensure_agent_access

            agent_grants.grant_agent_to_user("bot-1", "zhangming", "admin")
            ensure_agent_access("zhangming", ["operator"], "bot-1")


class TestEnforceAgentAccessForRequest:
    def _make_request(self, path: str, username: str, roles: list[str]):
        request = MagicMock()
        request.url.path = path
        request.method = "GET"
        request.headers = {}
        request.state.user = username
        request.state.roles = roles
        return request

    def test_agent_path_denied(self, tmp_path):
        from fastapi import HTTPException

        with _patch_secret_dir(tmp_path), _patch_no_pg(), _patch_auth_active():
            from qwenpaw_ext.nexora.authorization import (
                enforce_agent_access_for_request,
            )

            request = self._make_request(
                "/api/agents/bot-1/config",
                "zhangming",
                ["operator"],
            )
            with pytest.raises(HTTPException):
                enforce_agent_access_for_request(request)

    def test_agent_path_allowed(self, tmp_path):
        with _patch_secret_dir(tmp_path), _patch_no_pg(), _patch_auth_active():
            from qwenpaw_ext.nexora import agent_grants
            from qwenpaw_ext.nexora.authorization import (
                enforce_agent_access_for_request,
            )

            agent_grants.grant_agent_to_user("bot-1", "zhangming", "admin")
            request = self._make_request(
                "/api/agents/bot-1/config",
                "zhangming",
                ["operator"],
            )
            enforce_agent_access_for_request(request)

    def test_non_agent_path_skipped(self, tmp_path):
        with _patch_secret_dir(tmp_path), _patch_no_pg(), _patch_auth_active():
            from qwenpaw_ext.nexora.authorization import (
                enforce_agent_access_for_request,
            )

            request = self._make_request(
                "/api/auth/users",
                "zhangming",
                ["operator"],
            )
            enforce_agent_access_for_request(request)

    def test_header_agent_id_checked(self, tmp_path):
        from fastapi import HTTPException

        with _patch_secret_dir(tmp_path), _patch_no_pg(), _patch_auth_active():
            from qwenpaw_ext.nexora.authorization import (
                enforce_agent_access_for_request,
            )

            request = self._make_request(
                "/api/tools",
                "zhangming",
                ["operator"],
            )
            request.headers = {"X-Agent-Id": "bot-1"}
            with pytest.raises(HTTPException):
                enforce_agent_access_for_request(request)
