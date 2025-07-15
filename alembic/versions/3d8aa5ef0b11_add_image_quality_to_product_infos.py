"""add_image_quality_to_product_infos

Revision ID: 3d8aa5ef0b11
Revises: 885bd979b52a
Create Date: 2025-07-14 17:07:13.709432

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3d8aa5ef0b11"
down_revision: Union[str, Sequence[str], None] = "885bd979b52a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Check if column exists before adding it
    from sqlalchemy import inspect

    connection = op.get_bind()
    inspector = inspect(connection)
    columns = [col["name"] for col in inspector.get_columns("product_infos")]

    if "image_quality" not in columns:
        # Add image_quality column to product_infos table
        op.add_column(
            "product_infos",
            sa.Column(
                "image_quality",
                sa.String(16),
                nullable=False,
                server_default="standard",
            ),
        )
        # Create index on image_quality column
        op.create_index(
            "ix_product_infos_image_quality", "product_infos", ["image_quality"]
        )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove index
    op.drop_index("ix_product_infos_image_quality", "product_infos")
    # Remove image_quality column
    op.drop_column("product_infos", "image_quality")
