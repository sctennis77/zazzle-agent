"""add dry_run column to agent_scanned_posts

Revision ID: 0c44bf314eb7
Revises: 254c0379b616
Create Date: 2025-07-16 18:51:39.242354

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0c44bf314eb7"
down_revision: Union[str, Sequence[str], None] = "254c0379b616"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add dry_run column to track whether the agent action was a dry run
    # Use server_default for SQLite compatibility with existing data
    op.add_column(
        "agent_scanned_posts",
        sa.Column("dry_run", sa.Boolean(), nullable=False, server_default="1"),
    )

    # Note: SQLite constraint changes may require manual intervention in production


def downgrade() -> None:
    """Downgrade schema."""
    # Remove dry_run column
    op.drop_column("agent_scanned_posts", "dry_run")
