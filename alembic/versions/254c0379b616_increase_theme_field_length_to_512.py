"""increase theme field length to 512

Revision ID: 254c0379b616
Revises: b0b7df58eb37
Create Date: 2025-07-16 16:01:15.150871

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "254c0379b616"
down_revision: Union[str, Sequence[str], None] = "81c2b40deaf7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # For SQLite, we need to recreate the table to change column length
    with op.batch_alter_table("product_infos", schema=None) as batch_op:
        batch_op.alter_column(
            "theme",
            existing_type=sa.String(length=256),
            type_=sa.String(length=512),
            existing_nullable=True,
        )


def downgrade() -> None:
    """Downgrade schema."""
    # For SQLite, we need to recreate the table to change column length
    with op.batch_alter_table("product_infos", schema=None) as batch_op:
        batch_op.alter_column(
            "theme",
            existing_type=sa.String(length=512),
            type_=sa.String(length=256),
            existing_nullable=True,
        )
