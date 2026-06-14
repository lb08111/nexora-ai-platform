# -*- coding: utf-8 -*-
"""Create Nexora audit and approval tables."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_nexora_audit_approval"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "nexora_audit_events",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("timestamp", sa.BigInteger(), nullable=False),
        sa.Column("actor", sa.Text(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column(
            "resource_type", sa.Text(), nullable=False, server_default=""
        ),
        sa.Column("resource_id", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "status", sa.Text(), nullable=False, server_default="success"
        ),
        sa.Column("ip", sa.Text(), nullable=False, server_default=""),
        sa.Column("user_agent", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "detail",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index(
        "idx_cj_audit_created_at",
        "nexora_audit_events",
        ["created_at"],
    )
    op.create_index("idx_cj_audit_actor", "nexora_audit_events", ["actor"])
    op.create_index("idx_cj_audit_action", "nexora_audit_events", ["action"])
    op.create_index("idx_cj_audit_status", "nexora_audit_events", ["status"])
    op.create_index(
        "idx_cj_audit_resource",
        "nexora_audit_events",
        ["resource_type", "resource_id"],
    )

    op.create_table(
        "nexora_approval_requests",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("requester", sa.Text(), nullable=False, server_default=""),
        sa.Column("approver", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "resource_type", sa.Text(), nullable=False, server_default=""
        ),
        sa.Column("resource_id", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "resource_name", sa.Text(), nullable=False, server_default=""
        ),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "result",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
    )
    op.create_index(
        "idx_cj_approvals_status",
        "nexora_approval_requests",
        ["status"],
    )
    op.create_index(
        "idx_cj_approvals_action",
        "nexora_approval_requests",
        ["action"],
    )
    op.create_index(
        "idx_cj_approvals_created_at",
        "nexora_approval_requests",
        ["created_at"],
    )

    op.create_table(
        "nexora_agent_policies",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("agent_id", sa.Text(), nullable=False, unique=True),
        sa.Column(
            "display_name", sa.Text(), nullable=False, server_default=""
        ),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "allowed_roles",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "visible",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "usable",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "manageable",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
    )
    op.create_index(
        "idx_cj_agent_policies_enabled",
        "nexora_agent_policies",
        ["enabled"],
    )

    op.create_table(
        "nexora_resource_policies",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("resource_id", sa.Text(), nullable=False),
        sa.Column(
            "display_name", sa.Text(), nullable=False, server_default=""
        ),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "risk_level", sa.Text(), nullable=False, server_default="low"
        ),
        sa.Column(
            "allowed_agents",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "allowed_roles",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "approval_required",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "audit_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
        sa.UniqueConstraint(
            "source",
            "resource_id",
            name="uq_cj_resource_policy_source_resource",
        ),
    )
    op.create_index(
        "idx_cj_resource_source", "nexora_resource_policies", ["source"]
    )
    op.create_index(
        "idx_cj_resource_resource_id",
        "nexora_resource_policies",
        ["resource_id"],
    )
    op.create_index(
        "idx_cj_resource_enabled",
        "nexora_resource_policies",
        ["enabled"],
    )
    op.create_index(
        "idx_cj_resource_risk_level",
        "nexora_resource_policies",
        ["risk_level"],
    )

    op.create_table(
        "nexora_approval_policies",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("action", sa.Text(), nullable=False, unique=True),
        sa.Column(
            "display_name", sa.Text(), nullable=False, server_default=""
        ),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "approver_roles",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "allow_self_approval",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
    )
    op.create_index(
        "idx_cj_approval_policies_enabled",
        "nexora_approval_policies",
        ["enabled"],
    )

    op.create_table(
        "nexora_users",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("username", sa.Text(), primary_key=True),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("password_salt", sa.Text(), nullable=False),
        sa.Column(
            "status", sa.Text(), nullable=False, server_default="active"
        ),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
    )
    op.create_index("idx_cj_users_status", "nexora_users", ["status"])

    op.create_table(
        "nexora_roles",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "builtin",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
    )

    op.create_table(
        "nexora_user_roles",
        sa.Column("username", sa.Text(), nullable=False),
        sa.Column("role_id", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("username", "role_id"),
    )
    op.create_index(
        "idx_cj_user_roles_role_id", "nexora_user_roles", ["role_id"]
    )

    op.create_table(
        "nexora_role_permissions",
        sa.Column("role_id", sa.Text(), nullable=False),
        sa.Column("permission", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("role_id", "permission"),
    )
    op.create_index(
        "idx_cj_role_permissions_permission",
        "nexora_role_permissions",
        ["permission"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_cj_role_permissions_permission",
        table_name="nexora_role_permissions",
    )
    op.drop_table("nexora_role_permissions")
    op.drop_index("idx_cj_user_roles_role_id", table_name="nexora_user_roles")
    op.drop_table("nexora_user_roles")
    op.drop_table("nexora_roles")
    op.drop_index("idx_cj_users_status", table_name="nexora_users")
    op.drop_table("nexora_users")

    op.drop_index(
        "idx_cj_approval_policies_enabled",
        table_name="nexora_approval_policies",
    )
    op.drop_table("nexora_approval_policies")

    op.drop_index(
        "idx_cj_resource_risk_level", table_name="nexora_resource_policies"
    )
    op.drop_index(
        "idx_cj_resource_enabled", table_name="nexora_resource_policies"
    )
    op.drop_index(
        "idx_cj_resource_resource_id", table_name="nexora_resource_policies"
    )
    op.drop_index(
        "idx_cj_resource_source", table_name="nexora_resource_policies"
    )
    op.drop_table("nexora_resource_policies")

    op.drop_index(
        "idx_cj_agent_policies_enabled", table_name="nexora_agent_policies"
    )
    op.drop_table("nexora_agent_policies")

    op.drop_index(
        "idx_cj_approvals_created_at", table_name="nexora_approval_requests"
    )
    op.drop_index(
        "idx_cj_approvals_action", table_name="nexora_approval_requests"
    )
    op.drop_index(
        "idx_cj_approvals_status", table_name="nexora_approval_requests"
    )
    op.drop_table("nexora_approval_requests")

    op.drop_index("idx_cj_audit_resource", table_name="nexora_audit_events")
    op.drop_index("idx_cj_audit_status", table_name="nexora_audit_events")
    op.drop_index("idx_cj_audit_action", table_name="nexora_audit_events")
    op.drop_index("idx_cj_audit_actor", table_name="nexora_audit_events")
    op.drop_index("idx_cj_audit_created_at", table_name="nexora_audit_events")
    op.drop_table("nexora_audit_events")
