# -*- coding: utf-8 -*-
"""Add multi-tenant agent grants, capability approval config, and templates.

Revision ID: 0003_nexora_multi_tenant
Revises: 0002_nexora_runtime_config
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003_nexora_multi_tenant"
down_revision = "0002_nexora_runtime_config"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -- Agent-user grants (multi-tenant authorization) --
    op.create_table(
        "nexora_agent_user_grants",
        sa.Column("agent_id", sa.Text(), nullable=False),
        sa.Column("username", sa.Text(), nullable=False),
        sa.Column("granted_by", sa.Text(), nullable=False, server_default=""),
        sa.Column("granted_at", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint("agent_id", "username"),
    )
    op.create_index(
        "idx_cj_agent_grants_username",
        "nexora_agent_user_grants",
        ["username"],
    )
    op.create_index(
        "idx_cj_agent_grants_agent_id",
        "nexora_agent_user_grants",
        ["agent_id"],
    )

    # -- Per-capability-type approval configuration --
    op.create_table(
        "nexora_capability_approval_config",
        sa.Column("capability_type", sa.Text(), primary_key=True),
        sa.Column(
            "add_approval",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "remove_approval",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "auto_approve_remove",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "approver_roles",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text('\'["admin","ops_admin"]\'::jsonb'),
        ),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
    )

    # -- Agent initialization templates --
    op.create_table(
        "nexora_agent_templates",
        sa.Column("template_id", sa.Text(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "capabilities",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_by", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
    )
    op.create_index(
        "idx_cj_agent_templates_name",
        "nexora_agent_templates",
        ["name"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_cj_agent_templates_name",
        table_name="nexora_agent_templates",
    )
    op.drop_table("nexora_agent_templates")
    op.drop_table("nexora_capability_approval_config")
    op.drop_index(
        "idx_cj_agent_grants_agent_id",
        table_name="nexora_agent_user_grants",
    )
    op.drop_index(
        "idx_cj_agent_grants_username",
        table_name="nexora_agent_user_grants",
    )
    op.drop_table("nexora_agent_user_grants")
