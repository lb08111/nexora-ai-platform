# -*- coding: utf-8 -*-
"""Add runtime config tables for global and per-agent configuration."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_nexora_runtime_config"
down_revision = "0001_nexora_audit_approval"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "nexora_global_config",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "updated_at",
            sa.BigInteger(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.CheckConstraint("id = 1", name="ck_global_config_single_row"),
    )

    op.create_table(
        "nexora_agent_configs",
        sa.Column("agent_id", sa.Text(), primary_key=True),
        sa.Column(
            "data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "updated_at",
            sa.BigInteger(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )

    op.create_index(
        "idx_cj_agent_configs_updated_at",
        "nexora_agent_configs",
        ["updated_at"],
    )


def downgrade() -> None:
    op.drop_table("nexora_agent_configs")
    op.drop_table("nexora_global_config")
