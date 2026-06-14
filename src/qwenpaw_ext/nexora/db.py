# -*- coding: utf-8 -*-
"""Database helpers for Nexora persistent storage."""
from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import Any

logger = logging.getLogger(__name__)

DB_URL_ENV = "NEXORA_DB_URL"


def get_database_url() -> str:
    """Return the configured Nexora database URL."""
    return os.environ.get(DB_URL_ENV, "").strip()


def is_database_enabled() -> bool:
    """True when PostgreSQL-backed storage should be used."""
    return bool(get_database_url())


@lru_cache(maxsize=1)
def get_engine() -> Any:
    """Create and cache a SQLAlchemy engine for Nexora storage."""
    database_url = get_database_url()
    if not database_url:
        raise RuntimeError(f"{DB_URL_ENV} is not configured")
    if not database_url.startswith("postgresql"):
        raise RuntimeError(f"{DB_URL_ENV} must use a PostgreSQL URL")

    from sqlalchemy import create_engine

    return create_engine(
        database_url,
        pool_pre_ping=True,
        pool_size=int(os.environ.get("NEXORA_DB_POOL_SIZE", "10")),
        max_overflow=int(os.environ.get("NEXORA_DB_MAX_OVERFLOW", "20")),
        pool_recycle=int(os.environ.get("NEXORA_DB_POOL_RECYCLE", "1800")),
        connect_args={"connect_timeout": 5},
        future=True,
    )


def reset_engine_cache() -> None:
    """Clear the cached engine; used by tests and config reloads."""
    get_engine.cache_clear()
    global _schema_initialized
    _schema_initialized = False


_schema_initialized = False


def initialize_schema() -> None:
    """Create first-phase Nexora PostgreSQL tables if needed.

    This is intentionally conservative: it creates missing tables/indexes but
    does not drop or rewrite existing schema. Later production migrations
    should move to Alembic revision files.
    """
    global _schema_initialized
    if _schema_initialized:
        return
    if not is_database_enabled():
        return

    from sqlalchemy import text

    engine = get_engine()
    statements = [
        """
        CREATE TABLE IF NOT EXISTS nexora_audit_events (
            id TEXT PRIMARY KEY,
            timestamp BIGINT NOT NULL,
            actor TEXT NOT NULL,
            action TEXT NOT NULL,
            resource_type TEXT NOT NULL DEFAULT '',
            resource_id TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'success',
            ip TEXT NOT NULL DEFAULT '',
            user_agent TEXT NOT NULL DEFAULT '',
            detail JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS nexora_approval_requests (
            id TEXT PRIMARY KEY,
            action TEXT NOT NULL,
            status TEXT NOT NULL,
            requester TEXT NOT NULL DEFAULT '',
            approver TEXT NOT NULL DEFAULT '',
            resource_type TEXT NOT NULL DEFAULT '',
            resource_id TEXT NOT NULL DEFAULT '',
            resource_name TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL DEFAULT '',
            reason TEXT NOT NULL DEFAULT '',
            payload JSONB NOT NULL DEFAULT '{}'::jsonb,
            result JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at BIGINT NOT NULL,
            updated_at BIGINT NOT NULL
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_cj_audit_created_at
        ON nexora_audit_events (created_at DESC)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_cj_audit_actor
        ON nexora_audit_events (actor)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_cj_audit_action
        ON nexora_audit_events (action)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_cj_audit_status
        ON nexora_audit_events (status)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_cj_audit_resource
        ON nexora_audit_events (resource_type, resource_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_cj_approvals_status
        ON nexora_approval_requests (status)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_cj_approvals_action
        ON nexora_approval_requests (action)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_cj_approvals_created_at
        ON nexora_approval_requests (created_at DESC)
        """,
        """
        CREATE TABLE IF NOT EXISTS nexora_agent_policies (
            id TEXT PRIMARY KEY,
            agent_id TEXT NOT NULL UNIQUE,
            display_name TEXT NOT NULL DEFAULT '',
            description TEXT NOT NULL DEFAULT '',
            allowed_roles JSONB NOT NULL DEFAULT '[]'::jsonb,
            visible BOOLEAN NOT NULL DEFAULT TRUE,
            usable BOOLEAN NOT NULL DEFAULT TRUE,
            manageable BOOLEAN NOT NULL DEFAULT FALSE,
            enabled BOOLEAN NOT NULL DEFAULT TRUE,
            updated_at BIGINT NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS nexora_resource_policies (
            id TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            resource_id TEXT NOT NULL,
            display_name TEXT NOT NULL DEFAULT '',
            description TEXT NOT NULL DEFAULT '',
            risk_level TEXT NOT NULL DEFAULT 'low',
            allowed_agents JSONB NOT NULL DEFAULT '[]'::jsonb,
            allowed_roles JSONB NOT NULL DEFAULT '[]'::jsonb,
            approval_required BOOLEAN NOT NULL DEFAULT FALSE,
            audit_enabled BOOLEAN NOT NULL DEFAULT TRUE,
            enabled BOOLEAN NOT NULL DEFAULT TRUE,
            updated_at BIGINT NOT NULL,
            CONSTRAINT uq_cj_resource_policy_source_resource
                UNIQUE (source, resource_id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS nexora_approval_policies (
            id TEXT PRIMARY KEY,
            action TEXT NOT NULL UNIQUE,
            display_name TEXT NOT NULL DEFAULT '',
            description TEXT NOT NULL DEFAULT '',
            enabled BOOLEAN NOT NULL DEFAULT TRUE,
            approver_roles JSONB NOT NULL DEFAULT '[]'::jsonb,
            allow_self_approval BOOLEAN NOT NULL DEFAULT FALSE,
            updated_at BIGINT NOT NULL
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_cj_agent_policies_enabled
        ON nexora_agent_policies (enabled)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_cj_resource_source
        ON nexora_resource_policies (source)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_cj_resource_resource_id
        ON nexora_resource_policies (resource_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_cj_resource_enabled
        ON nexora_resource_policies (enabled)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_cj_resource_risk_level
        ON nexora_resource_policies (risk_level)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_cj_approval_policies_enabled
        ON nexora_approval_policies (enabled)
        """,
        """
        CREATE TABLE IF NOT EXISTS nexora_users (
            id TEXT NOT NULL,
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            password_salt TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            created_at BIGINT NOT NULL,
            updated_at BIGINT NOT NULL
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_cj_users_status
        ON nexora_users (status)
        """,
        """
        CREATE TABLE IF NOT EXISTS nexora_roles (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            builtin BOOLEAN NOT NULL DEFAULT FALSE,
            created_at BIGINT NOT NULL,
            updated_at BIGINT NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS nexora_user_roles (
            username TEXT NOT NULL,
            role_id TEXT NOT NULL,
            PRIMARY KEY (username, role_id)
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_cj_user_roles_role_id
        ON nexora_user_roles (role_id)
        """,
        """
        CREATE TABLE IF NOT EXISTS nexora_role_permissions (
            role_id TEXT NOT NULL,
            permission TEXT NOT NULL,
            PRIMARY KEY (role_id, permission)
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_cj_role_permissions_permission
        ON nexora_role_permissions (permission)
        """,
        """
        CREATE TABLE IF NOT EXISTS nexora_global_config (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            data JSONB NOT NULL DEFAULT '{}'::jsonb,
            updated_at BIGINT NOT NULL DEFAULT 0
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS nexora_agent_configs (
            agent_id TEXT PRIMARY KEY,
            data JSONB NOT NULL DEFAULT '{}'::jsonb,
            updated_at BIGINT NOT NULL DEFAULT 0
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_cj_agent_configs_updated_at
        ON nexora_agent_configs (updated_at)
        """,
        # -- Multi-tenant: agent-user grants --
        """
        CREATE TABLE IF NOT EXISTS nexora_agent_user_grants (
            agent_id TEXT NOT NULL,
            username TEXT NOT NULL,
            granted_by TEXT NOT NULL DEFAULT '',
            granted_at BIGINT NOT NULL,
            PRIMARY KEY (agent_id, username)
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_cj_agent_grants_username
        ON nexora_agent_user_grants (username)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_cj_agent_grants_agent_id
        ON nexora_agent_user_grants (agent_id)
        """,
        # -- Per-capability-type approval configuration --
        """
        CREATE TABLE IF NOT EXISTS nexora_capability_approval_config (
            capability_type TEXT PRIMARY KEY,
            add_policy TEXT NOT NULL DEFAULT 'approval',
            remove_policy TEXT NOT NULL DEFAULT 'log',
            approver_roles JSONB NOT NULL DEFAULT '["admin"]'::jsonb,
            updated_at BIGINT NOT NULL
        )
        """,
        # -- Agent initialization templates --
        """
        CREATE TABLE IF NOT EXISTS nexora_agent_templates (
            template_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            capabilities JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_by TEXT NOT NULL DEFAULT '',
            created_at BIGINT NOT NULL,
            updated_at BIGINT NOT NULL
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_cj_agent_templates_name
        ON nexora_agent_templates (name)
        """,
        # -- Token usage per user --
        """
        CREATE TABLE IF NOT EXISTS nexora_token_usage (
            id BIGSERIAL PRIMARY KEY,
            date DATE NOT NULL,
            actor TEXT NOT NULL,
            agent_id TEXT NOT NULL DEFAULT '',
            provider_id TEXT NOT NULL DEFAULT '',
            model TEXT NOT NULL DEFAULT '',
            prompt_tokens BIGINT NOT NULL DEFAULT 0,
            completion_tokens BIGINT NOT NULL DEFAULT 0,
            call_count INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_cj_token_usage_date
        ON nexora_token_usage (date DESC)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_cj_token_usage_actor
        ON nexora_token_usage (actor)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_cj_token_usage_agent_id
        ON nexora_token_usage (agent_id)
        """,
    ]
    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))
    _schema_initialized = True


def check_database_health() -> None:
    """Verify PG is reachable. Raises RuntimeError on failure."""
    if not is_database_enabled():
        return
    from sqlalchemy import text

    engine = get_engine()
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        raise RuntimeError(
            f"Nexora PostgreSQL health check failed: {exc}",
        ) from exc


def cascade_delete_agent(agent_id: str) -> dict:
    """Delete all data associated with an agent in a single transaction."""
    if not is_database_enabled():
        return {"deleted": False, "reason": "database not enabled"}
    from sqlalchemy import text

    engine = get_engine()
    result: dict[str, int] = {}
    with engine.begin() as conn:
        tables = [
            (
                "grants",
                "DELETE FROM nexora_agent_user_grants WHERE agent_id = :aid",
            ),
            (
                "agent_policies",
                "DELETE FROM nexora_agent_policies WHERE agent_id = :aid",
            ),
            (
                "agent_configs",
                "DELETE FROM nexora_agent_configs WHERE agent_id = :aid",
            ),
        ]
        for key, sql in tables:
            r = conn.execute(text(sql), {"aid": agent_id})
            result[key] = r.rowcount
    return result
