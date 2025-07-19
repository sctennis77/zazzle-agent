"""add agent_scanned_posts table

Revision ID: b0b7df58eb37
Revises: 81c2b40deaf7
Create Date: 2025-07-16 12:11:26.086590

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b0b7df58eb37"
down_revision: Union[str, Sequence[str], None] = "81c2b40deaf7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "agent_scanned_posts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("post_id", sa.String(32), nullable=False, index=True),
        sa.Column("subreddit", sa.String(100), nullable=False, index=True),
        sa.Column("comment_id", sa.String(32), nullable=True, index=True),
        sa.Column("promoted", sa.Boolean(), nullable=False, default=False),
        sa.Column("scanned_at", sa.DateTime(), nullable=False, index=True),
        sa.Column("post_title", sa.Text(), nullable=True),
        sa.Column("post_score", sa.Integer(), nullable=True),
        sa.Column("promotion_message", sa.Text(), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("post_id", name="uq_agent_scanned_posts_post_id"),
    )
    op.create_index(
        "ix_agent_scanned_posts_promoted_scanned_at",
        "agent_scanned_posts",
        ["promoted", "scanned_at"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_agent_scanned_posts_promoted_scanned_at", table_name="agent_scanned_posts"
    )
    op.drop_table("agent_scanned_posts")
