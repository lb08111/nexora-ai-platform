# -*- coding: utf-8 -*-
"""Migrate capability approval config from boolean columns to policy enum strings.

Also creates 0003 tables if they don't exist yet (handles stamp-over scenario).

Old: add_approval (BOOL), remove_approval (BOOL), auto_approve_remove (BOOL)
New: add_policy (TEXT: none/approval), remove_policy (TEXT: none/log/approval)

Revision ID: 0004_jotaduo_capability_approval_policy_enum
Revises: 0003_jotaduo_multi_tenant
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004_cap_approval_enum"
down_revision = "0003_jotaduo_multi_tenant"
branch_labels = None
depends_on = None


def _table_exists(conn, table_name: str) -> bool:
    result = conn.execute(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
            "WHERE table_name = :name)",
        ),
        {"name": table_name},
    )
    return result.scalar()


def _column_exists(conn, table_name: str, column_name: str) -> bool:
    result = conn.execute(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.columns "
            "WHERE table_name = :table AND column_name = :col)",
        ),
        {"table": table_name, "col": column_name},
    )
    return result.scalar()


def upgrade() -> None:
    conn = op.get_bind()

    # Ensure 0003 tables exist (may have been skipped via stamp)
    if not _table_exists(conn, "jotaduo_agent_user_grants"):
        op.create_table(
            "jotaduo_agent_user_grants",
            sa.Column("agent_id", sa.Text(), nullable=False),
            sa.Column("username", sa.Text(), nullable=False),
            sa.Column(
                "granted_by",
                sa.Text(),
                nullable=False,
                server_default="",
            ),
            sa.Column("granted_at", sa.BigInteger(), nullable=False),
            sa.PrimaryKeyConstraint("agent_id", "username"),
        )
        op.create_index(
            "idx_cj_agent_grants_username",
            "jotaduo_agent_user_grants",
            ["username"],
        )
        op.create_index(
            "idx_cj_agent_grants_agent_id",
            "jotaduo_agent_user_grants",
            ["agent_id"],
        )

    if not _table_exists(conn, "jotaduo_agent_templates"):
        op.create_table(
            "jotaduo_agent_templates",
            sa.Column("template_id", sa.Text(), primary_key=True),
            sa.Column("name", sa.Text(), nullable=False),
            sa.Column(
                "description",
                sa.Text(),
                nullable=False,
                server_default="",
            ),
            sa.Column(
                "capabilities",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
            sa.Column(
                "created_by",
                sa.Text(),
                nullable=False,
                server_default="",
            ),
            sa.Column("created_at", sa.BigInteger(), nullable=False),
            sa.Column("updated_at", sa.BigInteger(), nullable=False),
        )
        op.create_index(
            "idx_cj_agent_templates_name",
            "jotaduo_agent_templates",
            ["name"],
        )

    # capability_approval_config: create fresh or migrate from old columns
    if not _table_exists(conn, "jotaduo_capability_approval_config"):
        op.create_table(
            "jotaduo_capability_approval_config",
            sa.Column("capability_type", sa.Text(), primary_key=True),
            sa.Column(
                "add_policy",
                sa.Text(),
                nullable=False,
                server_default="approval",
            ),
            sa.Column(
                "remove_policy",
                sa.Text(),
                nullable=False,
                server_default="log",
            ),
            sa.Column(
                "approver_roles",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'[\"admin\"]'::jsonb"),
            ),
            sa.Column("updated_at", sa.BigInteger(), nullable=False),
        )
    elif _column_exists(
        conn,
        "jotaduo_capability_approval_config",
        "add_approval",
    ):
        # Migrate old boolean columns to new policy strings
        op.add_column(
            "jotaduo_capability_approval_config",
            sa.Column("add_policy", sa.Text(), nullable=True),
        )
        op.add_column(
            "jotaduo_capability_approval_config",
            sa.Column("remove_policy", sa.Text(), nullable=True),
        )

        op.execute(
            """
            UPDATE jotaduo_capability_approval_config SET
                add_policy = CASE WHEN add_approval THEN 'approval' ELSE 'none' END,
                remove_policy = CASE
                    WHEN NOT remove_approval THEN 'none'
                    WHEN auto_approve_remove THEN 'log'
                    ELSE 'approval'
                END
            """,
        )

        op.alter_column(
            "jotaduo_capability_approval_config",
            "add_policy",
            nullable=False,
            server_default="approval",
        )
        op.alter_column(
            "jotaduo_capability_approval_config",
            "remove_policy",
            nullable=False,
            server_default="log",
        )

        op.execute(
            """
            UPDATE jotaduo_capability_approval_config
            SET approver_roles = '["admin"]'::jsonb
            WHERE approver_roles @> '"ops_admin"'::jsonb
            """,
        )

        op.drop_column("jotaduo_capability_approval_config", "add_approval")
        op.drop_column("jotaduo_capability_approval_config", "remove_approval")
        op.drop_column(
            "jotaduo_capability_approval_config",
            "auto_approve_remove",
        )


def downgrade() -> None:
    conn = op.get_bind()
    if _column_exists(
        conn,
        "jotaduo_capability_approval_config",
        "add_policy",
    ):
        op.add_column(
            "jotaduo_capability_approval_config",
            sa.Column("add_approval", sa.Boolean(), nullable=True),
        )
        op.add_column(
            "jotaduo_capability_approval_config",
            sa.Column("remove_approval", sa.Boolean(), nullable=True),
        )
        op.add_column(
            "jotaduo_capability_approval_config",
            sa.Column("auto_approve_remove", sa.Boolean(), nullable=True),
        )

        op.execute(
            """
            UPDATE jotaduo_capability_approval_config SET
                add_approval = (add_policy = 'approval'),
                remove_approval = (remove_policy != 'none'),
                auto_approve_remove = (remove_policy = 'log')
            """,
        )

        op.alter_column(
            "jotaduo_capability_approval_config",
            "add_approval",
            nullable=False,
            server_default=sa.text("true"),
        )
        op.alter_column(
            "jotaduo_capability_approval_config",
            "remove_approval",
            nullable=False,
            server_default=sa.text("true"),
        )
        op.alter_column(
            "jotaduo_capability_approval_config",
            "auto_approve_remove",
            nullable=False,
            server_default=sa.text("true"),
        )

        op.drop_column("jotaduo_capability_approval_config", "add_policy")
        op.drop_column("jotaduo_capability_approval_config", "remove_policy")
