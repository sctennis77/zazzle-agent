"""add community agent tables

Revision ID: 81c2b40deaf7
Revises: 687b4d7540f4
Create Date: 2025-07-15 21:11:18.308948

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "81c2b40deaf7"
down_revision: Union[str, Sequence[str], None] = "687b4d7540f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create community_agent_actions table
    op.create_table(
        "community_agent_actions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("action_type", sa.String(length=32), nullable=False),
        sa.Column("target_type", sa.String(length=32), nullable=True),
        sa.Column("target_id", sa.String(length=64), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("decision_reasoning", sa.Text(), nullable=True),
        sa.Column("clouvel_mood", sa.String(length=32), nullable=True),
        sa.Column("royal_decree_type", sa.String(length=32), nullable=True),
        sa.Column("success_status", sa.String(length=16), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("subreddit_id", sa.Integer(), nullable=True),
        sa.Column("timestamp", sa.DateTime(), nullable=True),
        sa.Column("dry_run", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["subreddit_id"],
            ["subreddits.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_community_agent_actions_action_type"),
        "community_agent_actions",
        ["action_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_community_agent_actions_success_status"),
        "community_agent_actions",
        ["success_status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_community_agent_actions_subreddit_id"),
        "community_agent_actions",
        ["subreddit_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_community_agent_actions_target_id"),
        "community_agent_actions",
        ["target_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_community_agent_actions_target_type"),
        "community_agent_actions",
        ["target_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_community_agent_actions_timestamp"),
        "community_agent_actions",
        ["timestamp"],
        unique=False,
    )

    # Create community_agent_state table
    op.create_table(
        "community_agent_state",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("subreddit_name", sa.String(length=100), nullable=False),
        sa.Column("last_scan_time", sa.DateTime(), nullable=True),
        sa.Column("daily_action_count", sa.JSON(), nullable=True),
        sa.Column("community_knowledge", sa.JSON(), nullable=True),
        sa.Column("welcomed_users", sa.JSON(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_community_agent_state_last_scan_time"),
        "community_agent_state",
        ["last_scan_time"],
        unique=False,
    )
    op.create_index(
        op.f("ix_community_agent_state_subreddit_name"),
        "community_agent_state",
        ["subreddit_name"],
        unique=True,
    )
    op.create_index(
        op.f("ix_community_agent_state_updated_at"),
        "community_agent_state",
        ["updated_at"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop community_agent_state table
    op.drop_index(
        op.f("ix_community_agent_state_updated_at"), table_name="community_agent_state"
    )
    op.drop_index(
        op.f("ix_community_agent_state_subreddit_name"),
        table_name="community_agent_state",
    )
    op.drop_index(
        op.f("ix_community_agent_state_last_scan_time"),
        table_name="community_agent_state",
    )
    op.drop_table("community_agent_state")

    # Drop community_agent_actions table
    op.drop_index(
        op.f("ix_community_agent_actions_timestamp"),
        table_name="community_agent_actions",
    )
    op.drop_index(
        op.f("ix_community_agent_actions_target_type"),
        table_name="community_agent_actions",
    )
    op.drop_index(
        op.f("ix_community_agent_actions_target_id"),
        table_name="community_agent_actions",
    )
    op.drop_index(
        op.f("ix_community_agent_actions_subreddit_id"),
        table_name="community_agent_actions",
    )
    op.drop_index(
        op.f("ix_community_agent_actions_success_status"),
        table_name="community_agent_actions",
    )
    op.drop_index(
        op.f("ix_community_agent_actions_action_type"),
        table_name="community_agent_actions",
    )
    op.drop_table("community_agent_actions")
