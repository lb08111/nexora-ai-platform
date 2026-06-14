# -*- coding: utf-8 -*-
"""Unit tests for path guards and helpers."""

import pytest

from jotaduo.agents.forge._paths import (
    ALLOWED_ROOTS,
    PathGuardError,
    REPO_ROOT,
    kebab,
    safe_join,
    slugify,
)


class TestSlugify:
    def test_strips_accents(self):
        assert slugify("Saúde Total") == "saude_total"

    def test_kebab_uses_hyphen(self):
        assert kebab("Atendente WhatsApp") == "atendente-whatsapp"

    def test_collapses_specials(self):
        assert slugify("Pedido #42 — urgente!") == "pedido_42_urgente"

    def test_empty(self):
        assert slugify("") == ""


class TestSafeJoin:
    def test_accepts_allowed_root(self):
        result = safe_join("src/jotaduo/agents/foo_agent.py")
        assert result.is_absolute()
        assert str(result).startswith(str(REPO_ROOT))

    def test_accepts_each_allowed_root(self):
        for root in ALLOWED_ROOTS:
            rel = root.relative_to(REPO_ROOT) / "x.py"
            safe_join(str(rel))

    def test_rejects_absolute_path(self):
        with pytest.raises(PathGuardError):
            safe_join("/etc/passwd")

    def test_rejects_dotdot_escape(self):
        with pytest.raises(PathGuardError):
            safe_join("src/jotaduo/agents/../../../etc/passwd")

    def test_rejects_unrelated_dir(self):
        with pytest.raises(PathGuardError):
            safe_join("docs/foo.md")
